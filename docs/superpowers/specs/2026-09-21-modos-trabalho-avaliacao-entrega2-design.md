# Modos de Trabalho e de Avaliação — Entrega 2

Data: 2026-09-21
Status: aprovado (design confirmado em chat, ver histórico de sessão)
Depende de: Entrega 1 (Base) — completa, ver `docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md` e `docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1-VERIFICACAO.md`

## 1. Contexto

A Entrega 1 implementou modo de trabalho (ATRIBUICAO/PULL) e modo de avaliação
(PONTOS_ATRIBUIDOS/PONTOS_RELATIVO) por projeto, com congelamento por sprint e
extrato de pontos auditável. Três itens ficaram conscientemente fora do
escopo:

1. Elegibilidade nova por entrada/saída de operacional no meio do projeto.
2. Exportação CSV das métricas — **removido do escopo desta entrega** (o
   usuário confirmou que não é necessário agora).
3. Métricas comparativas entre modo A (ATRIBUICAO/PONTOS_ATRIBUIDOS) e modo B
   (PULL/PONTOS_RELATIVO).

Esta Entrega 2 cobre os itens 1 e 3.

## 2. Elegibilidade temporal

### 2.1 Problema atual

`operacionais` só tem um vínculo binário com o projeto (`ativo boolean`,
`supabase_schema.sql:266`), sem histórico de quando a pessoa entrou ou saiu.
"Elegível" hoje é derivado de `routers/avaliacoes.py::_operacionais_com_task_na_sprint`
— quem tem pelo menos uma task na sprint. Em modo PULL, quem não puxou
nenhuma task nunca aparece como pendente e nunca é avaliado — um achado
registrado (não corrigido) na Etapa 1 da Entrega 1.

Sprints não têm data de início/fim real: só `numero` sequencial e
`created_at`. Toda janela de performance hoje é contada por número de
sprints, nunca por calendário (`services/performance.py`).

### 2.2 Schema

```sql
ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_entrada timestamptz NOT NULL DEFAULT now();
ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_saida timestamptz;
```

Backfill: linhas existentes recebem `data_entrada = created_at` (ajuste no
mesmo `UPDATE` idempotente que o resto do `supabase_schema.sql` já usa pra
backfill de colunas novas).

### 2.3 Semântica

- Desativar um operacional (`ativo: true → false`) grava `data_saida = now()`
  automaticamente, se ainda não estiver setada.
- Reativar (`ativo: false → true`) limpa `data_saida` (volta pra `NULL`).
  **Limitação assumida:** não há histórico de múltiplos ciclos de
  entrada/saída — só o vínculo mais recente. Decisão do usuário (colunas
  simples em vez de tabela de histórico), aceitando essa limitação.
- **Elegível numa sprint** = estava vinculado no momento do fechamento dessa
  sprint: `data_entrada <= momento_do_fechamento AND (data_saida IS NULL OR
  data_saida > momento_do_fechamento)`. Sem proração — quem entrou no meio é
  avaliado normalmente, nota cheia, igual quem esteve a sprint toda. Mesmo
  padrão de "congelar no fechamento" que `modo_trabalho`/`modo_avaliacao`
  já usam.

### 2.4 Redefinição de "elegível" — muda comportamento existente

Trocar o critério de elegibilidade de "tem task na sprint" para "estava
vinculado ao projeto no fechamento" em:

- `routers/avaliacoes.py::_operacionais_com_task_na_sprint` (ou substituto)
  — usado pra derivar quem está pendente de Avaliação Semanal.
- `services/avaliacoes.py::contar_avaliacao_por_sprint` — usado pelo
  contador "N/M" no `SprintCard` (Entrega 1) e pelo bloqueio de fechamento.
- `services/performance.py::_sequencia_pessoal` — hoje filtra
  `.gt("entrega_pontos_alocados", 0)`, o que faz quem não puxou nada em
  PULL sumir da própria sequência em vez de aparecer com 0. Passa a incluir
  todo elegível, com 0 quando não houve alocação.

**Efeito colateral esperado e aceito:** em projetos PULL com sprints já
fechadas, a contagem de "avaliação pendente" pode aumentar retroativamente
(mais gente vinculada = mais gente esperada com avaliação daqui pra
frente). Pontuação já travada (linhas existentes em
`pontuacao_operacional_sprint`) não é recalculada — só a contagem de
pendências passa a considerar o novo critério dali em diante.

**Golden regression:** o teste de regressão da Entrega 1
(`test_golden_fixture_multidimensional_trava_de_regressao`) deve continuar
passando sem alteração — ele cobre ATRIBUICAO/PONTOS_ATRIBUIDOS, onde
"tem task" e "está vinculado" coincidem na prática (fluxo de atribuição
direta não deixa operacional vinculado sem task numa sprint ativa). Um novo
teste dedicado cobre o caso que muda: PULL, operacional vinculado mas sem
task na sprint, antes ausente e agora presente com 0.

### 2.5 RF-C7 — listagem de elegíveis auditável

Endpoint novo (rota exata a definir no plano) que lista, por sprint,
todos os elegíveis com: nome, se tem avaliação registrada, contagem de
tasks (0 é válido). Substitui a listagem estática de
`routers/metodologia.py` para esse propósito — deriva direto da nova regra
de vínculo, não precisa mais de heurística de task. RBAC: mesmo nível hoje
usado pra consultar avaliação semanal (Gerente+).

## 3. Métricas comparativas — modo A × modo B

### 3.1 Escopo (ambos, confirmado pelo usuário)

1. **Dentro do mesmo projeto:** agrupa sprints fechadas pelo
   `modo_trabalho`/`modo_avaliacao` congelado em cada uma
   (`sprints.modo_trabalho`/`modo_avaliacao`, já existem desde a Entrega 1),
   mostra médias lado a lado por grupo de modo — cobre o caso de "troquei de
   modo no meio do projeto, quero ver antes/depois".
2. **Entre projetos:** seletor de 2+ projetos, mesma agregação, por projeto
   inteiro — usando o modo congelado de CADA SPRINT do projeto (não o
   `project.modo_trabalho`/`modo_avaliacao` atual, que só reflete o modo
   vigente agora e pode não bater com o histórico se o projeto já trocou de
   modo).

### 3.2 Backend

`services/performance.py` hoje não lê `modo_trabalho`/`modo_avaliacao` em
lugar nenhum (confirmado por grep) — a agregação por modo é peça nova.
Endpoint(s) novo(s) (rota exata a definir no plano), algo como:

- `GET /projects/{id}/comparacao-modos` — agregação dentro do projeto,
  agrupada por `(modo_trabalho, modo_avaliacao)` das sprints fechadas.
- `GET /comparacao-modos?projeto_ids=...` — agregação entre projetos
  informados, mesma lógica de agrupamento por modo congelado de cada sprint.

Métricas a comparar por grupo: SPI médio, cycle-time médio, throughput
médio, distribuição da nota final (mesmas dimensões que `MetricasTab.tsx`
já calcula pra visão single-projeto — reaproveitar as funções de agregação
existentes, parametrizando por grupo de sprints em vez de "todas as sprints
do projeto").

### 3.3 Frontend

Nova seção em `MetricasTab.tsx` (ou aba própria, a definir no plano) com
`BarChart` agrupado do `recharts` — mesmo padrão visual já usado em "SPI por
sprint" e "SPI por operacional" (dois `<Bar>` por categoria). Nenhuma lib
nova, nenhum padrão visual novo — mantém o tier PADRÃO já classificado pra
esta entrega. Seletor de projetos (pra comparação entre projetos) reaproveita
padrão de `<select>`/multi-seleção já usado em outras partes do app.

## 4. Fora do escopo desta Entrega 2

- Exportação CSV — removida a pedido do usuário.
- Proração de pontos por tempo parcial numa sprint — rejeitada (exigiria
  datas reais de início/fim de sprint, que não existem e não estão sendo
  adicionadas aqui).
- Histórico de múltiplos ciclos de entrada/saída do mesmo operacional no
  mesmo projeto — rejeitado a favor de colunas simples (1 vínculo mais
  recente por pessoa).

## 5. Testes obrigatórios

- Golden regression da Entrega 1 continua verde, sem alteração de
  assertions.
- Novo teste: operacional vinculado (`data_entrada`/`data_saida`) mas sem
  task na sprint, em modo PULL — aparece na listagem de elegíveis com 0,
  não some.
- Novo teste: desativar operacional grava `data_saida`; reativar limpa.
- Novo teste: fechamento de sprint calcula elegibilidade usando
  `data_entrada`/`data_saida` no momento exato do fechamento (não a data
  atual de quando o teste roda).
- Novo teste: agregação de métricas por modo agrupa corretamente sprints
  com `modo_trabalho`/`modo_avaliacao` diferentes dentro do mesmo projeto.
- Novo teste: comparação entre projetos agrega por modo congelado de cada
  sprint, não pelo modo atual do projeto.

## 6. Migração

Duas colunas novas em `operacionais` (`data_entrada`, `data_saida`) — segue
a convenção do projeto: idempotente, nunca roda sozinha, precisa de
aplicação manual no Supabase SQL Editor antes do deploy. Deve ser somada ao
mesmo lote pendente da Entrega 1 se ela ainda não tiver rodado em produção
(ver memória `project_manual_migrations.md`).
