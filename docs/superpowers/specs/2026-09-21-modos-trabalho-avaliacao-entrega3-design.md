# Modos de Trabalho e de Avaliação — Entrega 3 (Fila real + Fórmula relativa + Migração de modo)

Versão 1.0 · 2026-09-21 · Deriva de `2026-09-20-modos-trabalho-avaliacao-design.md`
(spec original da Entrega 1). Decisões fechadas via brainstorming em 2026-09-21.

---

## 0. Contexto — por que esta entrega existe

O spec original da Entrega 1 desenhou 3 fatias (seção "Roadmap", linhas 91-140):
**Entrega 1 — Fundação** (feita, 2026-09-20), **Entrega 2 — O experimento roda**
(fila real, hidratação, pull atômico, fórmula PONTOS_RELATIVO, migração mid-sprint)
e **Entrega 3 — Evidência** (indicadores/CSV).

A Entrega 2 que de fato rodou (2026-09-21, `docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md`)
foi **re-escopada em chat** para cobrir só elegibilidade temporal (D15) e métricas
comparativas entre modos — CSV foi cortado explicitamente ("usuário confirmou que
não precisa"). O resto do roadmap original de "Entrega 2 — O experimento roda"
(fila, hidratação, pull atômico, `PONTOS_RELATIVO`, migração mid-sprint RF-M1..M8)
**nunca foi retomado nem formalmente descartado** — ficou como pendência
silenciosa. Auditoria confirmou no código: nenhuma das colunas de fila
(`entrou_na_fila_em`, `pull_em`, `rascunho`, `ordem_fila`), nenhum endpoint de
pull/devolução, e nenhuma das colunas congeladas de `PONTOS_RELATIVO` existe hoje.
`modo_trabalho = PULL` é, na prática, um rótulo que só força WIP=1.

Esta entrega (chamada de **Entrega 3** por ordem cronológica, não porque segue o
nome "Entrega 3 — Evidência" do roadmap original) fecha essa lacuna: implementa
o que a "Entrega 2 — O experimento roda" original previa, mais um requisito novo
levantado nesta sessão (Onda A-3).

---

## 1. Decisões desta sessão

| # | Tema | Decisão | Motivo |
|---|---|---|---|
| E3-D1 | Escopo geral | Tudo entra nesta rodada: fórmula + fila real + pull atômico + hidratação + devolução + migração estruturada de modo. | Pedido explícito do usuário: "quero formula, fila, e pull atomico. tudo isso ja era pra existir." |
| E3-D2 | Ordem de execução | 3 ondas sequenciais dentro do mesmo plano: **A** (motor de score) → **B** (migração de modo) → **C** (fila real). B depende de A (migração precisa saber calcular pontuação nos dois modos); C depende de B (não faz sentido ligar a fila num projeto sem trilha de migração seguro). | A é fundação de baixo risco; B é a preocupação que o usuário levantou de "não perder nada, não estragar avaliação do squad" ao trocar de modo; C é o maior volume de trabalho e a única onda com UI nova. |
| E3-D3 | Score só com avaliação do gerente (sem task formal) | Confirmado que `_score_final` **já redistribui peso** entre as dimensões disponíveis quando Entrega fica indisponível (`alocados=0` → `None`) — o comportamento pedido já existe no motor. Falta: (1) teste ponta-a-ponta cobrindo esse caminho, (2) sinalização na UI de extrato/painel para não parecer bug. Nenhuma mudança de fórmula necessária aqui. | Confirmado por leitura de `_score_final` (services/performance.py:209-221) — nenhuma dimensão disponível retorna `None`; com pelo menos Gerente disponível, o score se calcula normalmente com peso redistribuído. |
| E3-D4 | Retroatividade | Sprints já fechadas em modo PULL antes desta entrega **não são recalculadas** — `entrega_modo` já está congelado com a fórmula antiga aplicada (efetivamente a fórmula de ATRIBUIÇÃO, já que `PONTOS_RELATIVO` nunca rodou). Nenhuma sprint real foi fechada em PULL até agora (mesma constatação do spec original D10 — "recalibrar depois da primeira sprint real"), então o impacto prático é zero, mas o princípio de não-retroatividade (RF-C8 do SDD original) se mantém. | Consistente com a política já estabelecida em Entrega 1/2: pontuação travada nunca recalcula com regra nova. |
| E3-D5 | RF-M4 (SDD original, não mapeado no spec de Entrega 1) e D14 (Módulo D — compromisso semanal) | Fora de escopo, como já estava na spec de Entrega 1. | Sem mudança — nenhuma decisão nova, só reafirmando o que já estava excluído. |

### 1.1 Dependência técnica entre ondas B e C (achada na auto-revisão do spec)

A migração de modo (B2) já precisa gravar `rascunho`/`motivo_rascunho`/
`entrou_na_fila_em`/`pull_em`/`ordem_fila` em `tasks` — colunas descritas na
seção C6 — e precisa da função de hidratação (C1) pra decidir `rascunho` na
hora de migrar. Ou seja: **o schema de `tasks` (C6) e a função de hidratação
(C1) são pré-requisito técnico de B2**, mesmo que C2/C3 (endpoints de puxar/
devolver) e a UI (C5) só façam sentido depois de B estar pronto.

Isso não muda a ordem de entrega pro usuário (A → B → C continua sendo a
ordem em que cada onda fica **utilizável**), mas o plano de execução
(`/write-plan`) deve tratar "schema de tasks + hidratação" como uma tarefa
que roda junto com o início de B, não estritamente depois. Marcar isso
explicitamente no plano evita a task de migração quebrar por coluna
inexistente.

---

## 2. Onda A — Motor de score

### A1. Fórmula `PONTOS_RELATIVO`

```
pontos_pessoa      = soma de pontos das tasks concluídas pela pessoa na sprint (0 se nenhuma)
denominador_bruto  = média de pontos_pessoa entre operacionais elegíveis da sprint
denominador        = max(denominador_bruto, projects.pull_piso_pontos)
entrega_bruta       = pontos_pessoa / denominador
entrega_nota_relativa = min(entrega_bruta, projects.pull_teto) * 100 / projects.pull_teto
```

- Só roda quando `modo_avaliacao == 'PONTOS_RELATIVO'` no momento do fechamento
  (mesmo ponto onde `services/pontuacao.py` já lê `projects.modo_avaliacao` hoje,
  linha 40-43). Quando `PONTOS_ATRIBUIDOS`, comportamento **inalterado**
  (fórmula de ATRIBUIÇÃO como está hoje) — zero mudança de comportamento pra
  projetos que não usam o modo relativo, mesma garantia que a Entrega 1 já dava.
- Quem não concluiu nada: `entrega_nota_relativa = 0` — **não** vira indisponível
  (exceção deliberada, já documentada no spec original).
- Congelada em `pontuacao_operacional_sprint`, 3 colunas novas: `entrega_pontos_pessoa`,
  `entrega_denominador`, `entrega_nota_relativa`. Nunca recalculada depois
  (E3-D4).
- `services/performance.py::_entrega_por_projeto` passa a ler
  `entrega_nota_relativa` diretamente quando a linha tem `entrega_modo ==
  'PONTOS_RELATIVO'`, em vez de recalcular `concluidos/alocados` — a nota já
  vem pronta do fechamento, igual ATRIBUIÇÃO já funciona hoje.
- **Teste obrigatório, escrito primeiro** (mesmo padrão de risco §11 do SDD):
  projeto em ATRIBUICAO + PONTOS_ATRIBUIDOS, sprint de referência com dado
  fixo, produz exatamente as mesmas notas de antes desta mudança — golden
  regression, igual Entrega 1/2 já validaram.

### A2. Score só com avaliação do gerente — confirmação + blindagem

Não é fórmula nova. É:
1. Teste novo cobrindo o fechamento ponta-a-ponta: operacional vinculado ao
   projeto, zero tasks na sprint, avaliação do gerente completa (7 perguntas)
   → `calcular_e_travar_pontuacao` gera linha com `entrega_pontos_alocados=0`
   → `performance.py` calcula `score_final` não-nulo, usando só
   Gerente/Evolução/Autonomia (Qualidade também fica indisponível sem task
   concluída nem commit).
2. Sinalização na UI: no extrato de pontos (`PainelTab.tsx`) e em qualquer
   card que mostre a dimensão Entrega, quando `entrega_pontos_alocados == 0`
   E a pessoa está vinculada (não é ausência por erro), mostrar um selo
   "Sem task formal — score calculado sem a dimensão Entrega" em vez de
   deixar em branco/zero sem explicação. Evita que pareça bug pra quem olha
   depois.
3. **Não precisa de flag manual novo.** A elegibilidade da Entrega 2 já
   distingue "vinculado sem task" (gera linha zerada) de "não vinculado ao
   projeto" (nem aparece) — o sinal que faltava era só de leitura/exibição,
   não de captura de dado novo.

### A3. Config morta reativada

`pull_piso_pontos`/`pull_teto` passam a ser lidos de verdade (A1).
`pull_exigir_hidratacao` é consumido na Onda C (hidratação faz parte da fila).

---

## 3. Onda B — Migração estruturada de modo (RF-M1..M8)

Objetivo do usuário: trocar `modo_trabalho` de um projeto em andamento (ex.:
ATRIBUICAO → PULL) sem perder tasks, sem quebrar a avaliação em curso, com o
gerente sabendo exatamente o que vai mudar antes de confirmar.

### B1. Preview (dry-run)

`GET /projects/{id}/migrar-modo/preview?para=PULL` — não grava nada, retorna
contagem de tasks por categoria (tabela abaixo) pro frontend montar o diálogo
de confirmação.

### B2. Aplicar migração

`POST /projects/{id}/migrar-modo` (body: `{"para": "PULL"}` ou `{"para":
"ATRIBUICAO"}`):

| Situação da task (ao migrar pra PULL) | Ação |
|---|---|
| Planejado, com responsável | Limpa `operacional_id`; `rascunho` recalculado pela regra de hidratação (B3); entra na fila (`entrou_na_fila_em=now()`); pontos preservados |
| Planejado, sem responsável | Entra na fila |
| Planejado, não hidratada | `rascunho=true`, `motivo_rascunho` preenchido |
| Em andamento, com responsável | Mantém responsável; grava `pull_em=now()` só pra manter o dado consistente com o resto da fila |
| Concluída | Sem alteração — histórico de conclusão não se mexe |
| Bloqueada | Mantém responsável e estado de bloqueio como está |

Reversão PULL→ATRIBUICAO usa o mesmo endpoint com `para=ATRIBUICAO`: tasks na
fila voltam a `planejado` sem responsável (o gerente reatribui na mão, fluxo
que já existe).

Garantias:
- **Nunca** escreve em `task_transicoes`/`task_reaberturas` — migração de modo
  não é "movimento de task" pro histórico de Kanban, é reclassificação
  estrutural.
- Grava uma linha em `migracoes_modo` (tabela nova) com a contagem exata
  aplicada por categoria — auditoria de "o que mudou quando trocamos de modo".
- Marca `sprints.hibrida = true` na sprint ativa do projeto (coluna já existe
  no schema desde a Entrega 1, nunca usada até agora).
- Fechamento de sprint híbrida usa o `modo_avaliacao` **vigente no momento do
  fechamento** — isso já é o comportamento atual de `services/pontuacao.py`
  (lê `projects.modo_avaliacao` no momento de `calcular_e_travar_pontuacao`,
  não um valor congelado antes). Nenhuma mudança de código necessária aqui,
  só confirmar com teste.

### B3. Ação em massa independente: desvincular planejado

`POST /projects/{id}/desvincular-planejado` — para toda task
`coluna_kanban='planejado'` da sprint ativa, limpa `operacional_id`. Útil pro
gerente "abrir a fila" numa sprint em andamento sem trocar de modo inteiro.
Mesmo diálogo de confirmação de B1/B2 (reaproveita o preview).

### B4. Dados novos

```sql
CREATE TABLE IF NOT EXISTS migracoes_modo (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    de_modo text NOT NULL,
    para_modo text NOT NULL,
    contagem jsonb NOT NULL,          -- {"entrou_na_fila": 3, "manteve_responsavel": 2, "rascunho": 1, ...}
    aplicado_por uuid REFERENCES pessoa(id),
    created_at timestamptz DEFAULT now()
);
```

---

## 4. Onda C — Fila real

### C1. Hidratação

Recalculada em toda escrita de task (`POST /tasks`, `PATCH /tasks/{id}`)
quando `projects.pull_exigir_hidratacao = true` E `modo_trabalho = 'PULL'`:

```
hidratada ⟺ titulo não vazio AND pontos > 0 AND descricao não vazia AND len(checklist) >= 1
```

`rascunho = not hidratada`; `motivo_rascunho` lista os critérios que faltam
em texto (ex.: "Faltam: descrição, checklist"). Task rascunho nunca aparece
na fila de puxar.

### C2. Pull atômico

`POST /tasks/{id}/puxar`:
1. Checa WIP (reaproveita `services/wip_check.py` — pessoa já com task em
   `em_andamento` → 409).
2. Update condicional numa única chamada:
   `UPDATE tasks SET operacional_id=:op, coluna_kanban='em_andamento',
   entrou_em_andamento_em=now(), pull_em=now(), ordem_fila=NULL WHERE
   id=:id AND operacional_id IS NULL AND rascunho=false`. `rowcount==0` →
   409 "Esta task já foi puxada."
3. Botão "Puxar" só aparece no frontend pra task fora da fila (não hidratada
   ou já com responsável) — reforçado pelo `WHERE` acima no backend (nunca
   confiar só na UI pra essa regra).

### C3. Devolução

`POST /tasks/{id}/devolver`:
1. RBAC: `pessoa.id == task.operacional_id` OU `pessoa.cargo IN ('gerente',
   'lider')` (E3 herda D5 — operacional pode devolver a própria task, não só
   o gerente).
2. Se `task.travado_automatico == true` no momento: grava evento
   `devolucao_penalidade` em `pontuacao_eventos`, mesmo valor que
   `_somar_travamentos` contaria (reaproveita a função — sem duplicar regra
   de cálculo). Devolução antes de travar não penaliza.
3. Limpa `operacional_id`, `coluna_kanban='planejado'`, `pull_em=NULL`,
   `entrou_em_andamento_em=NULL`, `travado_automatico=false`, `ordem_fila` =
   MAX(ordem_fila)+1 do projeto/sprint (vai pro fim da fila).

### C4. Pergunta 1 da Avaliação Semanal condicional por modo

Mesma coluna (`resposta_1`), mesma escala 0-5, mesmo peso — só o enunciado
muda: em projetos `PULL`, exibe "Puxou e entregou num ritmo consistente?" em
vez de "Entregou o que se comprometeu dentro do combinado?". Muda só o texto
exibido no frontend, condicionado a `projects.modo_trabalho`; nenhuma coluna
nova.

### C5. UI (Onda C é a única com componente novo)

- Kanban: botão "Puxar" substitui atribuição manual quando `modo_trabalho ==
  'PULL'` e a task está sem responsável e hidratada. Atribuição manual
  continua disponível como válvula de escape pro gerente (D4, mantido).
- Card de task rascunho: badge visual + `motivo_rascunho` em tooltip.
- Botão "Devolver" na task em andamento (visível pro dono da task e pro
  gerente/líder).

### C6. Dados novos

```sql
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS entrou_na_fila_em timestamptz;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS pull_em timestamptz;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS atribuida_manualmente boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS motivo_atribuicao_manual text;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rascunho boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS motivo_rascunho text;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ordem_fila int;

ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_pontos_pessoa numeric(10,2);
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_denominador numeric(10,2);
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_nota_relativa numeric(6,2);
```

(As duas últimas colunas de `pontuacao_operacional_sprint` pertencem à Onda A,
listadas aqui de novo por proximidade de schema — todo o SQL desta entrega
vai num bloco só, idempotente, anexado ao final de `supabase_schema.sql`,
seguindo a convenção já estabelecida.)

---

## 5. Fora de escopo (reafirmado)

- CSV export (cortado na Entrega 2, sem mudança).
- Módulo D / compromisso semanal (D14 da Entrega 1, sem mudança).
- Indicadores de "Entrega 3 — Evidência" do roadmap original (tempo em fila,
  lead time) — não pedidos nesta sessão, viram backlog se o usuário quiser
  depois.
- Janela de pull (D1 da Entrega 1) — fila inteira sempre puxável, decisão já
  fechada, sem revisão nesta rodada.

---

## 6. Riscos e testes obrigatórios

1. **Golden regression** (igual toda entrega anterior): projeto ATRIBUICAO +
   PONTOS_ATRIBUIDOS não pode mudar de nota com nenhuma mudança desta
   entrega — escrito primeiro, roda a cada onda.
2. **Condição de corrida no pull**: teste simulando duas chamadas
   concorrentes em `POST /tasks/{id}/puxar` na mesma task — só uma pode
   suceder.
3. **Migração de modo não deve mexer em tasks concluídas ou bloqueadas** —
   teste explícito por categoria da tabela B2.
4. **Fechamento com zero tasks só-gerente** (A2) — teste ponta-a-ponta citado
   acima.
5. Nenhuma sprint fechada anteriormente pode ter sua nota alterada por esta
   entrega (E3-D4) — teste de imutabilidade de linha já congelada.
