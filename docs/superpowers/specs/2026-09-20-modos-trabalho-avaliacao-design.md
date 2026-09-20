# Modos de Trabalho e de Avaliação no DocuData — Spec de Implementação

Versão 1.1 · 2026-09-20 · Deriva do SDD "Modos de Trabalho e de Avaliação no
DocuData" (v1.0, Maio 2026), com decisões fechadas via brainstorming em
2026-09-20. Este documento é o contrato de implementação — onde diverge do
SDD original, a divergência é intencional e está registrada aqui com o motivo.

---

## 0. Como este documento se relaciona com o SDD original

O SDD original (colado pelo usuário, não versionado neste repo até agora)
define os requisitos funcionais (RF-A/B/C/D/M/E) e o vocabulário. Esta spec:

1. Resolve as 4 perguntas em aberto do §12 do SDD.
2. Resolve 6 conflitos entre o SDD e o código atual do DocuData (levantados
   por leitura direta do repositório antes do brainstorming).
3. Registra 2 requisitos extras pedidos pelo usuário fora do SDD.
4. Fatiam a entrega em 3 partes, cada uma implementável e verificável
   isoladamente.

Onde este documento não repete um RF do SDD original literalmente, o RF
original continua valendo. Onde há conflito de texto, **esta spec vence**.

---

## 1. Decisões que divergem do SDD original

| # | SDD original | Decisão desta spec | Motivo |
|---|---|---|---|
| D1 | RF-A4: janela de pull (N primeiras posições, únicas puxáveis), destacada visualmente | **Removida.** Fila inteira é puxável, sem destaque visual diferenciado por posição. Ordem da fila é sugestão do gerente, não regra de acesso. | Pedido explícito do usuário. A objeção óbvia (pessoa escolhe sempre a task fácil) é mitigada pela decisão D2: como o denominador da fórmula relativa é soma de **pontos**, não contagem de tasks, pegar tasks fáceis (poucos pontos) rende pouco no numerador — o incentivo de "descascar o fácil" perde força sozinho. |
| D2 | RF-C2: `tarefas_pessoa` = contagem de tasks concluídas; denominador = média de contagem de tasks | **Renomeado `TASKS_RELATIVO` → `PONTOS_RELATIVO`.** `pontos_pessoa` = soma de pontos das tasks concluídas; denominador = média de soma de pontos entre elegíveis. | Pedido explícito do usuário: contar tasks igualava uma task de 1 ponto a uma de 8, criando incentivo pra pegar só as fáceis — o problema que a janela de pull (D1) existia para conter por outro caminho. |
| D3 | RF-C6: bônus por volume, teto de 10 pontos no score final | **Mantido teto em 5 (`BONUS_EXTRA_TETO`), igual hoje, nos dois modos.** Conceito de "task extra" (RF-B13 diz que deixa de existir em PULL) é substituído por "pontos além do orçamento normal da sprint" — mesma mecânica de bônus já existente em `services/performance.py`, sem mudança de teto. | Decisão explícita do usuário: preservar o teto atual evita reabrir o teste de regressão do motor de score (risco nº1 do próprio SDD, §11) só para mudar um número que não tem efeito perceptível provado ainda. |
| D4 | RF-B9: gerente pode atribuir manualmente, com motivo e contador visível | Mantido como está — sem mudança. | — |
| D5 | Caso de borda 3 (§8): "Task puxada e devolvida à fila **pelo gerente**" | **Estendido:** o próprio operacional também pode devolver a task que está com ele, além do gerente. | Pedido explícito do usuário: quando uma task demora muito, alguém pode pedir para a pessoa devolver, e outra pessoa a puxa. |
| D6 | SDD não define penalidade de devolução | **Se a task já estava `travado_automatico=true` no momento da devolução, a devolução gera o mesmo desconto de pontos que um travamento normal geraria** (reaproveita `_somar_travamentos`). Devolução antes de travar não penaliza. Sempre aparece no extrato de pontos (D8). | Decisão do usuário: não punir devolução cedo (incentivaria segurar a task), mas registrar padrão de "puxa e devolve muito" no extrato para o gerente enxergar. |
| D7 | RF-B4 (janela destacada) | Removido — ver D1. | — |
| D8 | Não existe no SDD original | **Extra do usuário:** tabela `pontuacao_eventos`, uma linha por fato de pontuação (task concluída, travamento, devolução pós-travamento, bônus), visível a Gerente e Líder (RBAC igual ao score hoje). | Pedido explícito do usuário: "log claro de todo ponto ganho ou descontado por operacional no fechamento das sprints". |
| D9 | Não existe no SDD original | **Extra do usuário:** contador "N/M" de avaliação semanal (avaliados/elegíveis) exibido no card da sprint. | Pedido explícito do usuário: deixar claro quando falta avaliação semanal de alguma sprint. |
| D10 | §12.1: piso (1) e teto (1,5) são "chute" | **Configuráveis por projeto** (`pull_piso_pontos`, `pull_teto`), padrão 1 e 1,5. Como o denominador virou soma de pontos (D2), o piso 1 **provavelmente é baixo demais na prática** — recalibrar após a primeira sprint real do Grupo Ara é esperado, não uma falha. | Decisão do usuário. |
| D11 | §12.2: task na fila conta no SPI da sprint? | **Conta.** SPI mede saúde da sprint (planejado vs. entregue), não esforço individual — nada muda em `services/spi_health.py`. | Decisão do usuário (opção recomendada). |
| D12 | §12.3: operacional vê fila inteira ou só a janela? | Fila inteira, sem distinção visual entre posições (consequência de D1). | Decisão do usuário. |
| D13 | §12.4: pergunta 1 da Avaliação Semanal ("Entregou o que se comprometeu?") não faz sentido sem compromisso formal em PULL | **Reescrita condicional por modo:** em projetos `PULL`, o enunciado exibido vira "Puxou e entregou num ritmo consistente?". Mesma coluna (`resposta_1`), mesma escala 0-5, mesmo peso — só o texto muda conforme `projects.modo_trabalho`. | Decisão do usuário. |
| D14 | Módulo D (compromisso semanal), opcional no SDD | **Fora desta rodada inteira.** Registrado como backlog. | Decisão do usuário. |
| D15 | Elegibilidade (RF-C2: "cadastrado no projeto durante a sprint") | Nova definição temporal: `operacionais.entrou_no_projeto_em` / `saiu_do_projeto_em`, cobrindo a janela `[sprint.data_inicio, sprint.data_fim]`. Substitui a derivação atual por "tem task na sprint" em `avaliacoes.py` e `performance.py`. | Resolve conflito nº1 e nº2 (ver §2) e implementa literalmente o RF-C2/C4 e os casos de borda 4 e 5. |

---

## 2. Conflitos entre o SDD e o código atual (resolvidos)

1. **`services/performance.py::_sequencia_pessoal`** filtra
   `entrega_pontos_alocados > 0`. Em PULL, quem não puxou nada tinha
   alocados=0 e sumiria da sequência pessoal — quebraria RF-C3 (deve receber
   nota 0, nunca virar "indisponível"). **Resolução:** quando
   `entrega_modo == PONTOS_RELATIVO`, a linha nunca é filtrada por esse
   critério — a elegibilidade (D15) decide quem entra, não o volume alocado.

2. **`routers/avaliacoes.py::_operacionais_com_task_na_sprint`** deriva quem
   avaliar a partir de `tasks.operacional_id`. Em PULL, quem nunca puxou nada
   nunca aparece em pendências, nunca é avaliado, e nunca entraria no
   denominador (RF-C4 exige o oposto). **Resolução:** troca por
   `services/operacionais.py::listar_elegiveis_da_sprint` (D15).

3. **`confirmar_avaliacao_semanal`** já bloqueia (409) fechar sprint com
   pendência — então o requisito novo (D9, contador "N/M") não é sobre
   destravar o fechamento, é sobre visibilidade **antes** do fechamento, no
   card da sprint. Nenhuma mudança na trava existente.

4. **`projects.wip_config`** existe no banco e é lido por
   `services/wip_check.py`, mas não tem UI nenhuma no frontend hoje. RF-A5
   (WIP por pessoa forçado a 1, read-only, quando PULL) exige construir essa
   tela pela primeira vez — não é edição de UI existente.

5. **`routers/metodologia.py`** serve markdown estático de
   `docudata-backend/docs/`. RF-C7 (lista de elegíveis da sprint com
   contagem de cada um, auditável) exige um endpoint dinâmico novo, que a
   tela de metodologia (ou o Painel) vai consumir — não é conteúdo do doc
   estático.

6. **`BONUS_EXTRA_TETO = 5.0`** diverge do RF-C6 (10). Resolvido por D3:
   mantém 5.

---

## 3. Fatiamento da entrega

Três entregas, cada uma passando pelo feature-flow-lean completo (planejar →
implementar → verificar) antes da próxima começar.

### Entrega 1 — Base (não muda nenhum comportamento existente)
- `projects`: `modo_trabalho`, `modo_avaliacao`, `pull_exigir_hidratacao`,
  `pull_piso_pontos`, `pull_teto` (colunas novas, defaults preservam o
  comportamento atual).
- `configuracao_historico` (RF-A6): registro imutável de mudança de modo.
- `sprints`: `modo_trabalho`, `modo_avaliacao` congelados no fechamento
  (RF-E1); `hibrida` (usado só a partir da Entrega 2, mas a coluna nasce
  aqui).
- `pontuacao_eventos` (D8): tabela nova, extrato de pontos. Escrita dentro
  de `calcular_e_travar_pontuacao`, uma linha por evento, para todo
  fechamento a partir de agora (sprints fechadas antes não ganham
  retroativamente).
- UI: aba Configurações ganha os dois selects + campos condicionais + WIP
  read-only quando PULL (mesmo que PULL não faça nada ainda — a config
  precisa existir antes do comportamento); `SprintCard` ganha o chip "N/M"
  (D9); tela/seção de extrato de pontos (Gerente/Líder).
- **Importante:** o contador "N/M" (D9) desta entrega reusa a derivação
  **atual** de quem precisa ser avaliado
  (`avaliacoes.py::_operacionais_com_task_na_sprint`, por task na sprint) —
  não a elegibilidade nova de §6, que só nasce na Entrega 2. Motivo: trocar
  o denominador do contador já mudaria quem "conta como pendente" em
  projetos ATRIBUICAO hoje, violando a promessa de zero mudança de
  comportamento desta entrega. Quando a Entrega 2 substituir a derivação em
  `avaliacoes.py` pela elegibilidade nova, o contador herda o denominador
  correto automaticamente, sem código extra.
- **Teste obrigatório, escrito primeiro:** projeto em ATRIBUICAO +
  PONTOS_ATRIBUIDOS, sprint de referência com dado fixo, produz exatamente
  as mesmas notas de antes desta mudança (risco §11 do SDD).

### Entrega 2 — O experimento roda
- `tasks`: `entrou_na_fila_em`, `pull_em`, `atribuida_manualmente`,
  `motivo_atribuicao_manual`, `rascunho`, `motivo_rascunho`, `ordem_fila`.
- `operacionais`: `entrou_no_projeto_em`, `saiu_do_projeto_em` (D15) —
  backfill: `entrou_no_projeto_em = created_at` para linhas existentes.
- Fila (RF-B2, sem janela — D1), hidratação (RF-B8), pull atômico (RF-B6/B7),
  devolução por operacional ou gerente (D5/D6), WIP forçado a 1 (RF-A5),
  relógio de travamento a partir do pull (RF-B10), atribuição manual com
  motivo e contador de exceções (RF-B9).
- Fórmula `PONTOS_RELATIVO` (D2) com piso/teto configuráveis (D10),
  congelada em `pontuacao_operacional_sprint` (colunas `entrega_modo`,
  `entrega_pontos_pessoa`, `entrega_denominador`, `entrega_nota_relativa`).
  `performance.py` passa a ler a nota congelada quando o modo é relativo.
- Elegibilidade (D15) substitui a derivação por task em `avaliacoes.py` e
  `performance.py`.
- Migração mid-sprint (RF-M1..M8), tabela `migracoes_modo`, ação em massa de
  desvincular (RF-M7), reversão PULL→ATRIBUICAO (RF-M8).
- Pergunta 1 da Avaliação Semanal reescrita condicional por modo (D13).
- Sinalização de sprint híbrida em relatórios (RF-M5).

### Entrega 3 — Evidência
- 4 indicadores por sprint/projeto (RF-E2): tempo em fila, lead time total,
  eficiência de fluxo (RF-E3: sem contar fim de semana), vazão por pessoa.
- CSV por sprint (RF-E4) e por task (RF-E5).

### Backlog (fora das 3 entregas)
- Módulo D — compromisso semanal (D14).

---

## 4. Modelo de dados completo

```sql
-- projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_trabalho text NOT NULL DEFAULT 'ATRIBUICAO'
    CHECK (modo_trabalho IN ('ATRIBUICAO','PULL'));
ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_avaliacao text NOT NULL DEFAULT 'PONTOS_ATRIBUIDOS'
    CHECK (modo_avaliacao IN ('PONTOS_ATRIBUIDOS','PONTOS_RELATIVO'));
ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_exigir_hidratacao boolean NOT NULL DEFAULT true;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_piso_pontos numeric(6,2) NOT NULL DEFAULT 1;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_teto numeric(4,2) NOT NULL DEFAULT 1.5;

-- histórico de config (RF-A6)
CREATE TABLE IF NOT EXISTS configuracao_historico (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    campo           text NOT NULL CHECK (campo IN ('modo_trabalho','modo_avaliacao')),
    valor_anterior  text,
    valor_novo      text NOT NULL,
    usuario_email   text NOT NULL,
    criado_em       timestamptz NOT NULL DEFAULT now()
);

-- sprints
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_trabalho text;
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_avaliacao text;
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS hibrida boolean NOT NULL DEFAULT false;

-- tasks (Entrega 2)
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS entrou_na_fila_em timestamptz;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS pull_em timestamptz;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS atribuida_manualmente boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS motivo_atribuicao_manual text;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rascunho boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS motivo_rascunho text;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ordem_fila int;

-- operacionais (Entrega 2, D15)
ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS entrou_no_projeto_em timestamptz;
ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS saiu_do_projeto_em timestamptz;
UPDATE operacionais SET entrou_no_projeto_em = created_at WHERE entrou_no_projeto_em IS NULL;

-- migração (Entrega 2, RF-M)
CREATE TABLE IF NOT EXISTS migracoes_modo (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sprint_id               uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    de_modo                 text NOT NULL,
    para_modo               text NOT NULL,
    usuario_email           text NOT NULL,
    contagem_por_categoria  jsonb NOT NULL,
    criado_em               timestamptz NOT NULL DEFAULT now()
);

-- pontuação relativa congelada (Entrega 2)
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_modo text;
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_pontos_pessoa int;
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_denominador numeric(8,2);
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_nota_relativa numeric(5,2);

-- extrato de pontos (D8, Entrega 1)
CREATE TABLE IF NOT EXISTS pontuacao_eventos (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id  uuid NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    sprint_id       uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    projeto_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id         uuid REFERENCES tasks(id) ON DELETE SET NULL,
    tipo            text NOT NULL CHECK (tipo IN
        ('entrega_concluida','travamento_penalidade','devolucao_penalidade','bonus_extra','reabertura')),
    pontos          int NOT NULL DEFAULT 0,
    descricao       text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pontuacao_eventos_operacional ON pontuacao_eventos(operacional_id, sprint_id);
```

Todas as migrações são idempotentes (`IF NOT EXISTS`) e **manuais** — não
rodam sozinhas, seguindo a convenção já registrada do projeto.

---

## 5. Fórmula PONTOS_RELATIVO (substitui TASKS_RELATIVO do SDD original)

```
pontos_pessoa      = soma de pontos das tasks concluídas pela pessoa na sprint (0 se nenhuma)
denominador_bruto  = média de pontos_pessoa entre operacionais elegíveis da sprint
denominador        = max(denominador_bruto, projects.pull_piso_pontos)
entrega_bruta       = pontos_pessoa / denominador
entrega_nota_relativa = min(entrega_bruta, projects.pull_teto) * 100 / projects.pull_teto
```

- Quem não concluiu nada: `entrega_nota_relativa = 0`. Esta dimensão **não**
  é marcada indisponível por ausência de entrega — exceção deliberada à
  regra geral de redistribuição de peso (mesma exceção do RF-C3 original,
  agora sobre pontos em vez de tasks).
- Operacional elegível que não puxou nada entra no denominador com
  `pontos_pessoa = 0`.
- `pull_piso_pontos` (default 1) e `pull_teto` (default 1.5) são
  configuráveis por projeto; **1 ponto de piso é provavelmente baixo demais**
  agora que o denominador é soma de pontos — o SDD original já alertava
  isso mesmo para a versão em contagem de tasks (§11), e o risco é maior
  aqui. Recalibrar após a primeira sprint real do Grupo Ara.
- Congelada em `pontuacao_operacional_sprint` no fechamento — nunca
  recalculada depois, mesmo que o projeto mude piso/teto/modo posteriormente
  (RF-C8: sprints com fórmulas diferentes não são somadas/mediadas sem
  sinalização).

---

## 6. Elegibilidade (D15) — implementação

```
elegível na sprint S ⟺
    operacional.entrou_no_projeto_em <= S.data_fim (ou "agora", se S ainda aberta)
    AND (operacional.saiu_do_projeto_em IS NULL OR operacional.saiu_do_projeto_em >= S.data_inicio)
```

Nova função `services/operacionais.py::listar_elegiveis_da_sprint(client,
sprint_id)`, usada por:
- `routers/avaliacoes.py::listar_pendencias` (substitui
  `_operacionais_com_task_na_sprint`)
- denominador da fórmula relativa (§5)
- `services/performance.py::_sequencia_pessoal` (remove o filtro
  `entrega_pontos_alocados > 0` quando o modo da linha é `PONTOS_RELATIVO`)
- contador "N/M" do card da sprint (D9)

---

## 7. Fluxos de Pull e Devolução

**Pull** — `POST /tasks/{id}/puxar` (RF-B6/B7):
1. Verifica WIP (reusa `services/wip_check.py`) — se a pessoa já tem task em
   `em_andamento`, 409.
2. Update condicional em uma única chamada:
   `UPDATE tasks SET operacional_id=:op, coluna_kanban='em_andamento',
   entrou_em_andamento_em=now(), pull_em=now(), ordem_fila=NULL
   WHERE id=:id AND operacional_id IS NULL AND rascunho=false`.
   Se `rowcount == 0` (outra pessoa chegou primeiro, ou já saiu da fila),
   409 "Esta task já foi puxada."
3. Task fora da fila (não hidratada, ou já tem responsável) nunca mostra o
   botão Puxar no frontend — reforçado pelo `WHERE` acima no backend.

**Devolução** — `POST /tasks/{id}/devolver` (D5/D6):
1. RBAC: permitido se `pessoa.id == task.operacional_id` OU
   `pessoa.cargo IN ('gerente','lider')`.
2. Se `task.travado_automatico == true`: grava `pontuacao_eventos` tipo
   `devolucao_penalidade`, pontos = mesmo valor que `_somar_travamentos`
   contaria (reaproveita a função, sem duplicar a regra de cálculo).
3. Limpa `operacional_id`, `coluna_kanban='planejado'`, `pull_em=NULL`,
   `entrou_em_andamento_em=NULL`, `travado_automatico=false`,
   `ordem_fila` = MAX(ordem_fila) + 1 do projeto/sprint (vai para o fim da
   fila — gerente reordena manualmente se quiser priorizar).

**Hidratação** — recalculada em toda escrita de task (create/update) quando
`projects.pull_exigir_hidratacao = true` e `modo_trabalho = 'PULL'`:
```
hidratada ⟺ titulo não vazio AND pontos > 0 AND descricao não vazia AND len(checklist) >= 1
```
`rascunho = not hidratada`; `motivo_rascunho` lista os critérios que faltam,
em texto (ex.: "Faltam: descrição, checklist").

---

## 8. Migração mid-sprint (RF-M1..M8)

`GET /projects/{id}/migrar-modo/preview?para=PULL` — dry-run, retorna
contagem de tasks por categoria (tabela RF-M2) sem gravar nada. Frontend usa
isso para popular o diálogo de confirmação (RF-M1).

`POST /projects/{id}/migrar-modo` — aplica:

| Situação da task | Ação |
|---|---|
| Planejado, com responsável | Limpa responsável, `rascunho` recalculado, entra na fila com `entrou_na_fila_em=now()`, pontos preservados |
| Planejado, sem responsável | Entra na fila |
| Planejado, não hidratada | `rascunho=true` com motivo |
| Em andamento, com responsável | Mantém responsável; `pull_em=now()` (RF-M2) |
| Concluída | Sem alteração |
| Bloqueada | Mantém responsável e estado de bloqueio |

Nunca escreve em `task_transicoes`/`task_reaberturas` (RF-M3). Grava
`migracoes_modo` com a contagem exata aplicada. Marca `sprints.hibrida =
true` na sprint ativa (RF-M5). Fechamento de sprint híbrida usa o
`modo_avaliacao` vigente no momento do fechamento (RF-M6), sem cálculo misto.

`POST /projects/{id}/desvincular-planejado` (RF-M7) — ação em massa
independente de troca de modo: para toda task `coluna_kanban='planejado'` da
sprint ativa, limpa `operacional_id` (mesmo registro/confirmação da
migração completa).

Reversão PULL→ATRIBUICAO (RF-M8) usa o mesmo endpoint de migração com
`para=ATRIBUICAO`: tasks na fila voltam para Planejado sem responsável.

---

## 9. Métricas e exportação (Entrega 3)

| Indicador | Fórmula |
|---|---|
| Tempo em fila | Mediana de dias entre `tasks.created_at` (ou `entrou_na_fila_em`, o que existir) e início efetivo (`pull_em` em PULL, atribuição em ATRIBUICAO) |
| Lead time total | Mediana de dias entre criação e `coluna_kanban='concluida'` |
| Eficiência de fluxo | (tempo em `em_andamento` ÷ lead time total) × 100, **excluindo sábado e domingo** (RF-E3) |
| Vazão por pessoa | tasks concluídas na sprint ÷ operacionais elegíveis (§6) |

CSV por sprint (RF-E4): uma linha por sprint — número, datas, modo de
trabalho, modo de avaliação, `hibrida`, os 4 indicadores acima, SPI,
throughput, reaberturas, travamentos, contagem de `atribuida_manualmente`.

CSV por task (RF-E5): id, título, pontos, responsável final, criação, entrada
na fila, pull/atribuição, conclusão, reaberturas, tempo bloqueado.

---

## 10. Plano de teste (mínimo, do SDD original + extras)

**Regressão (primeiro código escrito, antes de qualquer feature nova):**
sprint de referência com dado fixo, projeto ATRIBUICAO+PONTOS_ATRIBUIDOS,
produz exatamente as mesmas notas de antes desta mudança.

**Extras desta spec:**
- Contador "N/M" reflete elegíveis corretos (entrada/saída no meio da
  sprint).
- `pontuacao_eventos` tem exatamente uma linha por fato no fechamento
  (task concluída, travamento, devolução pós-travamento, bônus) e RBAC
  bloqueia operacional de ler o extrato.
- Devolução antes de travar não gera evento de penalidade; depois de travar,
  gera.

**Do SDD original** (RF-B, RF-C, RF-M, RF-E): ver §9 do SDD colado pelo
usuário — mantido integralmente, não repetido aqui.

---

## 11. Casos de borda — status

Todos os 10 casos de borda do §8 do SDD original permanecem válidos como
escritos, com estas notas:
- Casos 4 e 5 (entrada/saída no meio da sprint) são resolvidos pela
  elegibilidade temporal (D15/§6).
- Caso 3 (devolução) ganha o ator "operacional" além de "gerente" (D5), e a
  penalidade condicional (D6) que o SDD original deixava em aberto.
- Caso 9 ("todas as tasks da janela exigem skill que a pessoa não tem") fica
  sem objeto: sem janela (D1), a pessoa pode puxar qualquer task da fila.
  A válvula continua sendo RF-B9 (atribuição manual com motivo), agora sem
  a limitação de "só as N primeiras" para justificar o uso.

---

## 12. Backlog explícito (fora desta spec)

- Módulo D — compromisso semanal (RF-D1..D4).
- Recalibração de `pull_piso_pontos`/`pull_teto` após a primeira sprint real
  do Grupo Ara.
- RF-C6 (teto de bônus = 10) fica registrado como divergência consciente
  (D3) — não implementado nesta rodada.
