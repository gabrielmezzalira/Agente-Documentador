# Rodada A1 — Régua única, aprovação de funcionalidade e previsto da sprint

Data: 2026-10-22 · Branch: `feat/regua-aprovacao-escopo` (base `fix/painel-ajustes-pequenos` sobre `origin/main`)

## Contexto

A proposta institucional (Cultura Data Driven, Método de Entrega pull, Piso mínimo e Pontuação padronizada) pede três bases que o DocuData ainda não tem:

1. **Uma régua única de dificuldade** (1, 2, 3 e 5), igual em todos os projetos. Hoje `tasks.pontos` aceita qualquer inteiro positivo.
2. **Funcionalidade "concluída e aprovada"**. Hoje só existe "concluída". As colunas antigas de aprovação do cliente (`status_cliente`, `data_aprovacao_cliente`) estão órfãs.
3. **Um previsto da sprint que não dependa dos "100 pontos do projeto"**. Hoje o gerente divide 100 pontos entre as sprints (`sprints.pontos_orcamento`), e isso alimenta orçamento, bloqueio de criação de task, redistribuição e preço (`valor_por_ponto = valor_projeto ÷ 100`).

Esta rodada (A1) entrega o modelo de dados e as regras. O agente que classifica o nível de cada task é a rodada **A2**, com spec própria. SPI só da sprint, piso por pessoa, relógio do cliente e bônus por rapidez são a rodada **B**.

## Decisões

| Tema | Decisão |
|---|---|
| Papel dos pontos | **Só nível de dificuldade da task.** Não existe total de pontos do projeto. Pontos só são somados dentro de uma sprint (SPI, piso, tamanho de funcionalidade). |
| Orçamento e preço | Saem: orçamento por sprint, bloqueio por orçamento, redistribuir pontos, `valor_por_ponto` e o campo `valor_projeto` da tela. |
| Comparação de modos | Sai inteira (página, menu, bloco da aba Métricas, endpoint, serviço e testes). |
| Tasks legadas | Abertas são convertidas para o nível mais próximo; concluídas ficam como estão. |
| Quem aprova a funcionalidade | O gerente (ou líder). |
| Escopo concluído do painel | Funcionalidades aprovadas ÷ total, cada uma com peso igual. |
| Previsto da sprint | Foto das tasks no início da sprint + tasks que surgiram depois, sem extras. |

## 1. Régua única

**Banco**
- `tasks.pontos`: a restrição passa de `pontos > 0` para `pontos IN (1, 2, 3, 5)`.
- Nova coluna `tasks.pontos_legado int NULL`, com o valor original das tasks convertidas.

**Conversão das tasks legadas** (só nas que não estão em `concluida`):

| Valor antigo | Nível |
|---|---|
| 1 | 1 |
| 2 | 2 |
| 3 ou 4 | 3 |
| 5 ou mais | 5 |

As tasks concluídas mantêm o número antigo porque o fechamento das sprints (`pontuacao_operacional_sprint`) já registrou os números delas. A regra existe em dois lugares que precisam concordar: uma função pura em Python (`services/regua.py::converter_pontos_legado`, coberta por teste) e o `UPDATE` da migração.

**API**
- `TaskCreate` e `TaskUpdate` validam `pontos ∈ {1, 2, 3, 5}`. Fora disso, devolvem 422 com a mensagem "Use um nível da régua: 1, 2, 3 ou 5".
- `services/regua.py` expõe `NIVEIS = (1, 2, 3, 5)` e os rótulos provisórios, para o backend e os testes usarem uma fonte só.

**Interface**
- O campo numérico de pontos (criar/editar task no Kanban e nas duas telas de planning, `SprintDocModal` e `PlanningModal`) vira um seletor de 4 níveis: "1 · simples", "2 · moderada", "3 · complexa" e "5 · muito complexa". A A2 vai substituir esses rótulos.

**O que não muda:** o limite de travamento continua em pontos × 1,5 dia (1,5 / 3 / 4,5 / 7,5 dias).

## 2. Pontos só como dificuldade

**Backend: sai**
- `PATCH /sprints/{id}/orcamento` e a regra de "no máximo 100 por projeto" (`routers/sprints.py`).
- O valor em R$ por sprint no retorno de sprints.
- `POST /tasks/redistribuir-pontos` e `_pontos_usados_na_sprint` (`routers/tasks.py`).
- O bloqueio por orçamento ao criar task e ao editar pontos ou sprint da task (`routers/tasks.py`).
- `valor_projeto` e `valor_por_ponto` em criar e editar projeto (`routers/projects.py`) e nos schemas.
- A comparação de modos: endpoint em `routers/metricas.py`, `services/metricas_comparacao.py`, `tests/test_metricas_comparacao.py` e `tests/test_endpoint_comparacao_modos.py`.

**Frontend: sai**
- `SprintOrcamentoPlanner` e o orçamento e o valor no `SprintCard`.
- O campo "Valor do projeto" no formulário de contrato do painel (`TempoEscopoCard`).
- O botão e o fluxo de redistribuir pontos no Kanban.
- O texto do "i" do SPI que manda "distribuir os 100 pontos", e o estado vazio que leva à aba Planejamento para definir orçamento.
- A página `/comparacao-modos`, os itens de menu (`navItems.ts`, `ChooserHeader.tsx`), o bloco na aba Métricas, `getComparacaoModos` e os tipos em `api.ts`, e o trecho correspondente em `tests/modos-trabalho-avaliacao-entrega2.test.mjs`.

**Banco:** `sprints.pontos_orcamento`, `projects.valor_por_ponto` e `projects.valor_projeto` **ficam**, sem uso, marcadas como órfãs no `supabase_schema.sql`. É o mesmo padrão de `status_cliente`: nenhuma migração destrutiva. `sprints.modo_trabalho` e `modo_avaliacao` continuam como histórico.

## 3. Aprovação de funcionalidade

**Banco:** `funcionalidades.aprovada_em timestamptz NULL` e `funcionalidades.aprovada_por uuid NULL REFERENCES pessoa(id)`.

**Regra:** "concluída e aprovada" significa `status = 'concluida' AND aprovada_em IS NOT NULL`. Os valores de `status` não mudam, então as telas e métricas que já leem `status` continuam funcionando.

**API** (protegida por `require_not_operacional`, o mesmo gate de gerente ou líder já usado em tasks):
- `POST /funcionalidades/{id}/aprovar`
  - 404 se a funcionalidade não existe; 409 se `status != 'concluida'`; 409 se já está aprovada.
  - Grava `aprovada_em = now()` e `aprovada_por` com a pessoa da sessão.
  - Insere em `transicoes_status` uma linha com `campo = 'aprovacao'`, `de = 'pendente'`, `para = 'aprovada'` e a duração desde a última transição de status.
- `DELETE /funcionalidades/{id}/aprovacao`
  - 409 se não está aprovada. Limpa os dois campos e insere a transição `aprovada → pendente`, com motivo "desfeita pelo gerente".

**Revogação automática:** se uma funcionalidade aprovada deixar de estar concluída, a aprovação é limpa e a transição é registrada com motivo "revogada: task reaberta" ou "revogada: task nova". Isso acontece quando uma task dela sai de `concluida` ou quando entra uma task nova nela. A regra fica num helper único, `services/aprovacao_funcionalidade.py::revogar_se_aprovada(client, funcionalidade_id, motivo)`, chamado nos pontos de criar task, mudar a coluna de task e vincular task a funcionalidade.

**Painel (`routers/painel.py::calcular_bloco_a`):** `pct_escopo_concluido` = funcionalidades aprovadas ÷ total. O texto do "i" de "Escopo concluído" passa a ser "Funcionalidades aprovadas pelo gerente ÷ total de funcionalidades do projeto. Cada funcionalidade pesa igual."

**Interface** (onde a funcionalidade aparece com status: aba Escopo e quadro de funcionalidades da sprint):
- Concluída e não aprovada: selo "Aguardando aprovação" e botão "Aprovar" (só para gerente ou líder).
- Aprovada: "Aprovada em DD/MM por Nome" e a ação "Desfazer aprovação".

## 4. Previsto da sprint

**Banco:** `tasks.prevista_no_inicio boolean NOT NULL DEFAULT false` e `tasks.surgiu_na_sprint boolean NOT NULL DEFAULT false`.

**Quando cada marca é gravada**
- **Início da sprint** (`services/sprints.py::iniciar_sprint_e_ancorar_tasks`): todas as tasks da sprint com `extra = false` recebem `prevista_no_inicio = true`.
- **Task criada numa sprint já iniciada** (`sprints.iniciada = true`) com `extra = false`: `surgiu_na_sprint = true`.
- **Task movida para uma sprint já iniciada:** `surgiu_na_sprint = true` e `prevista_no_inicio = false`, porque a foto pertence à sprint de origem.
- **Task movida para uma sprint ainda não iniciada:** as duas marcas voltam a `false`. A foto vai ser tirada quando aquela sprint começar.

**Regra:** `previsto(sprint)` = soma de `pontos` das tasks com `sprint_id = sprint`, `extra = false` e (`prevista_no_inicio` ou `surgiu_na_sprint`). Task que sai da sprint ou é excluída deixa de contar porque não está mais nela. Task devolvida à fila no pull continua na sprint e continua contando.

**Fonte única:** `services/previsto_sprint.py::previsto_da_sprint(client, sprint_id) -> {"previsto": int, "planejado_no_inicio": int, "surgiu_na_sprint": int}`.

**Quem consome**
- `GET /metricas/{project_id}/spi`: `pontos_previstos = previsto`. O realizado continua sendo a soma de pontos das tasks em `concluida` (a exigência de aprovação no realizado é da rodada B).
- `services/spi_health.py::auto_update_sprint_health`: usa `previsto` no lugar de `pontos_orcamento`. Com previsto 0, não altera a saúde, que é o comportamento atual sem orçamento.
- Retorno de sprints: inclui `previsto`, `planejado_no_inicio` e `surgiu_na_sprint`. O `SprintCard` mostra "Previsto 21 pts · 18 planejados + 3 surgiram na sprint".

**Sprints já iniciadas antes da migração:** a migração marca as tasks atuais delas (não extras) como `prevista_no_inicio = true`. É uma aproximação, porque não existe registro de quais tasks estavam lá no início.

## 5. Migração

Um bloco idempotente no fim do `supabase_schema.sql`, aplicado manualmente no SQL Editor do Supabase:

1. `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS pontos_legado int;`
2. Conversão: `UPDATE tasks SET pontos_legado = pontos, pontos = <regra da seção 1> WHERE coluna_kanban <> 'concluida' AND pontos NOT IN (1,2,3,5);`
3. Troca da restrição: `DROP CONSTRAINT IF EXISTS tasks_pontos_check`, e depois `ADD CONSTRAINT tasks_pontos_check CHECK (pontos IN (1,2,3,5) OR coluna_kanban = 'concluida')`. As concluídas antigas podem manter valores fora da régua; qualquer task aberta ou nova precisa estar nela.
4. `funcionalidades.aprovada_em` e `aprovada_por`.
5. `tasks.prevista_no_inicio` e `surgiu_na_sprint`, mais o preenchimento das sprints com `iniciada = true`.
6. `COMMENT ON COLUMN` marcando `sprints.pontos_orcamento`, `projects.valor_por_ponto` e `projects.valor_projeto` como órfãs.

**Ordem de deploy:** migração e backend juntos, frontend logo em seguida. Entre a migração e o backend novo, o backend antigo ainda aceita pontos como 4 ou 8, e o banco recusaria isso com erro 500. Por isso a migração é aplicada imediatamente antes do deploy do backend, para deixar essa janela mínima. Com o backend novo no ar e o frontend antigo, digitar 4 devolve 422 com a mensagem da régua, que é um erro legível.

**Ponto de atenção:** com a restrição do passo 3, uma task concluída com valor fora da régua que for **reaberta** precisa ganhar um nível válido. O endpoint que reabre a task converte o valor com `converter_pontos_legado` e guarda o original em `pontos_legado` antes de mudar a coluna.

## 6. Erros

| Situação | Resposta |
|---|---|
| Pontos fora da régua ao criar ou editar task | 422 "Use um nível da régua: 1, 2, 3 ou 5" |
| Aprovar funcionalidade não concluída | 409 |
| Aprovar funcionalidade já aprovada, ou desfazer sem aprovação | 409 |
| Operacional tentando aprovar ou desfazer | 403 (gate existente) |
| Endpoints removidos (`/sprints/{id}/orcamento`, `/tasks/redistribuir-pontos`, comparação de modos) | 404 |
| Sprint sem tasks | previsto 0, SPI "—", saúde inalterada |

## 7. Testes

**Backend (pytest, TDD)**
- Régua: criar e editar task aceita 1/2/3/5 e rejeita 4, 0 e 8 com 422.
- `converter_pontos_legado`: tabela completa (1, 2, 3, 4, 5, 8, 13).
- Reabrir task concluída com valor legado: o valor é convertido e o original fica em `pontos_legado`.
- Aprovação: aprova concluída; 409 para não concluída e para dupla aprovação; 403 para operacional; desfazer; transições gravadas.
- Revogação automática ao reabrir task, ao criar task na funcionalidade e ao vincular task a ela.
- `previsto_da_sprint`: só foto; foto + surgiu; extra fora; task que saiu da sprint; sprint vazia; task movida para sprint não iniciada perde as marcas.
- Início da sprint marca `prevista_no_inicio` só nas tasks não extras.
- SPI e saúde usam o novo previsto.
- Painel: escopo = aprovadas ÷ total.
- Endpoints removidos devolvem 404; criar task numa sprint não é mais bloqueado por orçamento.

**Frontend:** `tsc --noEmit` e `npm test`, com testes estruturais para:
- seletor de nível no lugar do campo numérico;
- botão "Aprovar" e selo "Aguardando aprovação";
- `SprintCard` mostrando previsto sem orçamento nem R$;
- ausência de `SprintOrcamentoPlanner`, do campo de valor do projeto e da comparação de modos.

## Fora de escopo

- Agente classificador de nível e rótulos definitivos da régua (rodada A2).
- SPI com realizado "concluído e aprovado", piso, meta por sprint, relógio do cliente que pausa e bônus por rapidez (rodada B).
- Status de funcionalidade derivado das tasks e eficiência de fluxo corrigida (fases 3 e 5 do plano geral).
- Tamanho estimado de funcionalidade (P/M/G) e precificação por histórico.
