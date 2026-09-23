# Estado "Pendente de aprovação" — Design

Data: 2026-09-22 · Gabriel Mezzalira · DocuData

## 1. Problema

Em projetos no modo de trabalho PULL, o WIP por pessoa é sempre travado em 1 task "em andamento" por vez (RF-A5). Quando um operacional termina de fato o trabalho de uma task, mas ela depende de aprovação do gerente antes de virar "Concluída", a task fica presa em `em_andamento` — e como o WIP está ocupado, o operacional não consegue puxar a próxima task da fila até alguém aprovar a que já terminou. Isso trava o fluxo de trabalho na prática, mesmo a pessoa já estando livre.

O mesmo problema de fundo (task tecnicamente pronta, mas dependente de sign-off do gerente) também é relevante em modo ATRIBUICAO, mesmo sem a consequência de WIP — por isso o recurso vale para os dois modos.

## 2. Objetivo

Introduzir um novo estado no fluxo de conclusão de task — "Pendente de aprovação" — entre `em_andamento` e `concluida`, que:
- libera o slot de WIP da pessoa assim que ela declara o trabalho pronto (não conta como `em_andamento`);
- exige uma ação explícita de gerente/líder (aprovar ou rejeitar) antes da task virar `concluida` de verdade;
- é **opcional por task**, não obrigatório para todas.

## 3. Modelo de dados

- `tasks.coluna_kanban` ganha um 4º valor válido: `pendente_aprovacao`. Ordem lógica: `planejado → em_andamento → pendente_aprovacao → concluida`.
- `tasks.requer_aprovacao: boolean NOT NULL DEFAULT false` (coluna nova, precisa de migração manual de schema — ver §9).
  - Quando `true`: a task **não pode** ir direto de `em_andamento` para `concluida` — só passando por `pendente_aprovacao`.
  - Quando `false` (padrão): o caminho rápido de hoje continua disponível (`em_andamento → concluida` direto), mas o operacional pode, por iniciativa própria, escolher mandar a task para `pendente_aprovacao` em vez de `concluida` quando achar que precisa de revisão. Não é uma escolha persistida — é só a coluna de destino que ele escolhe.
- `requer_aprovacao` é setável **só por gerente/líder**, ao criar ou editar a task (mesmo padrão de RBAC de `pontos`/`sprint_id`/`operacional_id` — entra em `_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL`).

## 4. Transições e regras de negócio

| De | Para | Quem pode | Gate |
|---|---|---|---|
| `em_andamento` | `pendente_aprovacao` | operacional ou gerente/líder (via PATCH/drag normal) | DoD: checklist completo ou vazio (mesmo gate que hoje existe para `concluida`, redirecionado) |
| `em_andamento` | `concluida` (direto) | operacional ou gerente/líder (caminho de hoje) | DoD (igual hoje) **+ bloqueado (422) se `task.requer_aprovacao == true`** |
| `pendente_aprovacao` | `concluida` | **só gerente/líder**, via `POST /tasks/{id}/aprovar` | nenhum gate novo — DoD já foi checado na entrada |
| `pendente_aprovacao` | `planejado` (rejeição) | **só gerente/líder**, via `POST /tasks/{id}/rejeitar` | `motivo` obrigatório |
| `pendente_aprovacao` | qualquer outra coisa via PATCH/drag genérico (`/tasks/{id}` ou `/tasks/{id}/mover`) | ninguém | **bloqueado (422)** — mesmo princípio já aplicado a `modo_trabalho` na Entrega 4: fechar a transição na origem, não confiar só no frontend não oferecer o botão. A única saída de `pendente_aprovacao` é `/aprovar` ou `/rejeitar`. |

**Rejeição é uniforme nos dois modos**: limpa `operacional_id` e move para `planejado`, sem responsável.
- Em PULL, isso reinsere a task na fila de puxar (qualquer um pode pegá-la de novo, inclusive a mesma pessoa).
- Em ATRIBUICAO, o gerente vê a task em `planejado` sem responsável e reatribui manualmente, do jeito que já faz hoje.

Rejeição **não é reabertura** (TRANS-03 continua sendo estritamente `concluida → em_andamento`) — é registrada como uma transição de coluna normal, com o `motivo` obrigatório gravado (mesmo padrão de campo livre já usado em `motivo_bloqueio`).

**Limpeza de campos na rejeição**: mesmo padrão de `devolver_task` (`routers/tasks.py`) — `operacional_id=None`, `coluna_kanban="planejado"`, `pull_em=None`, `entrou_em_andamento_em=None`, `travado_automatico=False`, `ordem_fila` recalculado pro fim da fila (`max(ordem_fila existente) + 1`). `sprint_id` **não muda** — a task continua na mesma sprint, só perde o responsável. Diferente de `devolver_task`, **não há penalidade de travamento** aqui: o relógio já estava pausado desde a entrada em `pendente_aprovacao` (§5), então não houve travamento ativo para penalizar.

## 5. WIP e travamento automático

- `services/wip_check.py::check_wip` já compara `coluna_kanban == "em_andamento"` explicitamente (tanto o limite por coluna quanto o limite por pessoa) — **nenhuma mudança de código necessária aqui**: `pendente_aprovacao` já não conta, por construção, assim que existir como valor distinto.
- O relógio de travamento automático (ALERT-01/04, `routers/tasks.py::patch_task`) hoje só para de contar quando `coluna_efetiva == "concluida"`. Precisa passar a tratar `pendente_aprovacao` do mesmo jeito — senão o relógio continuaria rodando contra o operacional por um atraso que já não é responsabilidade dele. Mesma lógica se aplica ao job diário de travamento (`services/travamento_job.py` ou equivalente) se ele fizer a mesma checagem separadamente — precisa ser conferido na fase de implementação.

## 6. Pontuação (confirmado, sem mudança necessária)

`services/pontuacao.py::calcular_e_travar_pontuacao` roda **uma única vez, no fechamento da Avaliação Semanal** (`routers/avaliacoes.py::confirmar_avaliacao_semanal`), lendo o estado final de `tasks.coluna_kanban` naquele momento — não é um contador incremental disparado por evento de transição. Toda comparação relevante (`services/pontuacao.py` linhas ~99, ~271) usa `coluna_kanban == "concluida"` como igualdade exata, nunca "diferente de planejado/em_andamento". Consequência: uma task em `pendente_aprovacao` nunca é contada como entregue, não importa quanto tempo fique nesse estado — só conta quando (e se) `/aprovar` de fato mudar `coluna_kanban` para `concluida`. **Nenhuma mudança de código necessária no motor de pontuação.**

Único cuidado na implementação: `_resolver_quem_completou` (mesmo arquivo) atribui os pontos a quem estava alocado na task no momento da transição `para=concluida`, lendo `task_transicoes`. Isso significa que **`/aprovar` precisa gravar essa transição** (`campo=coluna_kanban, para=concluida`) do mesmo jeito que `patch_task` já faz hoje na conclusão direta — senão a atribuição cai no fallback (`operacional_id` atual da task), que ainda funciona mas perde o rastro caso a task tenha trocado de responsável entre a entrada em `pendente_aprovacao` e a aprovação (não deveria acontecer, já que ninguém mais pode mexer no `operacional_id` de uma task em `pendente_aprovacao`, mas o registro correto é mais seguro).

## 7. Notificações por e-mail (reusa o padrão já existente — `services/email_service.py` + Resend)

- **Ao entrar em `pendente_aprovacao`**: e-mail para gerente(s)/líder(es) do projeto avisando que há uma task esperando aprovação. Mesmo público de `_avisar_gerente_task_concluida` (`routers/tasks.py`).
- **Ao rejeitar**: e-mail para o operacional que estava na task, com o motivo da rejeição. Mesmo padrão de `email_task_atribuida`.
- **Ao aprovar**: não é pedido explicitamente — a conclusão já dispara o fluxo de e-mail existente de "task concluída" (`_avisar_gerente_task_concluida`, se aplicável) sem necessidade de e-mail novo.
- Todos best-effort: falha de envio nunca bloqueia a transição (mesmo padrão de toda notificação já existente no app).

## 8. Backend — endpoints afetados/novos

- `models/schemas.py`:
  - `_COLUNAS_VALIDAS` ganha `"pendente_aprovacao"`.
  - `TaskCreate`/`TaskUpdate` ganham `requer_aprovacao: Optional[bool]`.
  - `_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL` (routers/tasks.py) ganha `"requer_aprovacao"`.
  - `TaskResponse` ganha `requer_aprovacao: bool = False`.
- `routers/tasks.py`:
  - `create_task`: aceita `requer_aprovacao` (só se `pessoa.cargo != operacional` — já coberto pelo gate RBAC existente no topo de `create_task`/`patch_task`).
  - `patch_task`: bloqueia (422) `em_andamento → concluida` quando `task.requer_aprovacao == true` e o destino pedido é `concluida` direto (sem passar por `pendente_aprovacao`). Bloqueia (422) qualquer saída de `pendente_aprovacao` que não seja via `/aprovar` ou `/rejeitar`. Estende o gate de DoD (checklist) pra também cobrir entrada em `pendente_aprovacao`. Estende a parada do relógio de travamento pra também cobrir `pendente_aprovacao`.
  - `mover_task` (`/tasks/{id}/mover`): sua lista própria de colunas válidas (`{"planejado", "em_andamento", "concluida"}`) precisa incluir `"pendente_aprovacao"` — hoje está desincronizada de `_COLUNAS_VALIDAS` e bloquearia o drag-and-drop pro novo estado mesmo depois do resto pronto.
  - Novo `POST /tasks/{id}/aprovar` (RBAC: `Depends(require_not_operacional)`). Valida `task.coluna_kanban == "pendente_aprovacao"` (409 se não for). Grava a transição de coluna (`campo=coluna_kanban, para=concluida`, mesma função `_registrar_task_transicao` usada em `patch_task`), atualiza `coluna_kanban=concluida`, dispara `on_task_transition` e `auto_update_sprint_health` (mesmos efeitos que `patch_task` já dispara ao concluir).
  - Novo `POST /tasks/{id}/rejeitar` (RBAC: `Depends(require_not_operacional)`, body com `motivo: str` obrigatório). Valida `task.coluna_kanban == "pendente_aprovacao"` (409 se não for). Registra a transição, limpa `operacional_id`, muda `coluna_kanban=planejado`, dispara e-mail pro operacional que estava na task.

## 9. Migração manual de schema

Nova coluna `tasks.requer_aprovacao boolean NOT NULL DEFAULT false` — segue a mesma convenção já usada no projeto (SQL manual, `supabase_schema.sql` não roda sozinho). O SQL exato entra no plano de implementação (Onda 1, Task 1), e o usuário aplica manualmente no Supabase antes do deploy usar essa funcionalidade — mesmo processo de sempre.

## 10. Métricas

`routers/metricas.py::get_cfd` conta `planejado`/`em_andamento`/`concluida` por sprint — precisa somar um 4º bucket `pendente_aprovacao`, senão essas tasks somem silenciosamente do gráfico (contadas em nenhuma faixa) em vez de aparecerem como uma faixa própria.

## 11. Frontend

- `TasksKanbanTab.tsx`: `Coluna` type e o array `COLUNAS` ganham a entrada `pendente_aprovacao` — o board já renderiza a 4ª coluna automaticamente (é `.map` sobre `COLUNAS`, sem lista hardcoded em outro lugar).
- `TaskModal` (criar/editar task): novo checkbox "Requer aprovação do gerente" — visível e editável só quando `pessoa.cargo != operacional` (mesmo padrão de outros campos administrativos já escondidos/mostrados condicionalmente).
- Cards na coluna "Pendente de aprovação": para gerente/líder, botões "Aprovar" e "Rejeitar" (rejeitar abre campo de motivo obrigatório, mesmo estilo do modal de confirmação de reabertura já existente). Para operacional, sem ação — só visualização (a bola está com o gerente agora).
- `api.ts`: novas funções `aprovarTask(taskId)` e `rejeitarTask(taskId, motivo)`.

## 12. Fora de escopo (YAGNI, deferido)

- Relógio de travamento próprio contra o **gerente** por demora em aprovar (só uma ideia levantada durante o brainstorm — não pedida, não entra nesta entrega).
- Múltiplos níveis de aprovação ou aprovação por mais de uma pessoa.
- Reversão de uma aprovação já feita (uma vez `concluida` via `/aprovar`, seguem as mesmas regras que qualquer outra task concluída hoje — inclusive reabertura manual por PATCH, que já existe).

## 13. Testes (cobertura mínima, detalhada no plano de implementação)

- DoD gate cobrindo `pendente_aprovacao` além de `concluida`.
- `requer_aprovacao=true` bloqueia `em_andamento → concluida` direto; `false` não bloqueia.
- `/aprovar`: só gerente/líder; 409 se task não está em `pendente_aprovacao`; grava transição correta; dispara pontuação corretamente no fechamento (teste de integração com `calcular_e_travar_pontuacao`).
- `/rejeitar`: só gerente/líder; exige `motivo`; limpa `operacional_id`; volta pra `planejado`; dispara e-mail pro operacional.
- WIP: task em `pendente_aprovacao` não conta pro limite por pessoa nem por coluna (`check_wip`).
- Travamento: relógio para ao entrar em `pendente_aprovacao`, mesmo comportamento que `concluida` hoje.
- `mover_task`: aceita `pendente_aprovacao` como destino; bloqueia saída de `pendente_aprovacao` que não seja via `/aprovar`/`/rejeitar`.
- CFD: soma corretamente a 4ª faixa.
