---
phase: 14-confirmacao-de-transicao-reabertura-bloqueio-manual
plan: 01
subsystem: api
tags: [fastapi, pydantic, supabase, react, kanban, task-transicoes]

requires:
  - phase: 13-kanban-de-tasks-metricas-ganchos
    provides: task_transicoes, patch_task com gates DoR/DoD/WIP, kanban de tasks (TasksKanbanTab)
provides:
  - ConfirmTransicaoModal reutilizável (drag-and-drop + aceite de sugestão da IA), sem chamada de API antes da confirmação
  - resolve_task_sugestao delegando a patch_task (mesmo caminho gated de DoR/DoD/WIP + task_transicoes)
  - Tabela task_reaberturas + tasks.contador_reaberturas para a transição concluida -> em_andamento
  - Campos de bloqueio manual (bloqueado_manual/_em/_por/_resolvido_por/_resolvido_em) com gate 422 ao desmarcar sem informar quem resolveu
affects: [18-score-qualidade-tecnica, 19-score-autonomia, 15-rbac-papeis, 16-travamento-automatico]

actuals:
  tokens: 13000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Endpoint de confirmação de UI: modal só bloqueia a intenção do usuário (setPending*), a chamada de API só acontece no confirm — cancelar nunca toca a rede"
    - "Reuso de caminho gated: qualquer entrada nova de mudança de status (aceite de sugestão) delega ao mesmo patch_task usado por PATCH/mover, em vez de duplicar lógica de gates"
    - "Migration única antecipando colunas de tasks futuras (bloqueio manual adicionado no bloco da Task 2, usado só na Task 3) para não reabrir supabase_schema.sql duas vezes"

key-files:
  created:
    - docudata-backend/tests/test_task_confirmacao_sugestao.py
    - docudata-backend/tests/test_task_reabertura.py
    - docudata-backend/tests/test_bloqueio_manual.py
  modified:
    - docudata-backend/routers/tasks.py
    - docudata-backend/models/schemas.py
    - docudata-backend/supabase_schema.sql
    - docudata-backend/tests/test_tasks_dod_gate.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/components/TasksKanbanTab.tsx

key-decisions:
  - "resolve_task_sugestao passou a chamar `await patch_task(...)` diretamente (in-process), não via HTTP — mesmo padrão já usado por mover_task delegando a patch_task"
  - "Erro em confirmPendingMove (frontend) fecha o modal mesmo em falha (409/outro erro), em vez de deixá-lo aberto — o erro já é comunicado via wipError/alert; ambiguidade do plano resolvida a favor de não deixar o usuário com um modal travado"
  - "Migration da Task 2 já cria as colunas de bloqueio manual (Task 3), conforme instruído no plano, para editar supabase_schema.sql uma única vez"

requirements-completed: [TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05]

coverage:
  - id: D1
    description: "Drag-and-drop e aceite de sugestão da IA exigem confirmação explícita em modal antes de qualquer chamada de API; cancelar não altera estado nem chama API"
    requirement: "TRANS-01"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_task_confirmacao_sugestao.py — cobre o backend gated; frontend (handleDrop/cancelPendingMove/cancelPendingSugestao) verificado por leitura de código e tsc/next build, sem teste de componente React no projeto"
        status: pass
    human_judgment: true
    rationale: "O comportamento de UI (modal abre no drag/aceite, cancelar não chama API) não tem cobertura de teste de componente neste projeto — só o backend gated tem testes automatizados. Spot-check manual recomendado na verification do plano."
  - id: D2
    description: "resolve_task_sugestao delega a patch_task (mesmo caminho gated DoR/DoD/WIP + task_transicoes) em vez de update direto de coluna_kanban"
    requirement: "TRANS-02"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_task_confirmacao_sugestao.py#test_aceitar_sugestao_caminho_feliz_move_task_e_grava_transicao"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_task_confirmacao_sugestao.py#test_aceitar_sugestao_com_checklist_incompleto_propaga_409_e_nao_resolve"
        status: pass
    human_judgment: false
  - id: D3
    description: "Transição concluida -> em_andamento grava task_reaberturas e incrementa contador_reaberturas; nenhuma outra saída de concluida grava; motivo é opcional"
    requirement: "TRANS-03"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_task_reabertura.py (5 testes)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Task ganha bloqueado_manual/_em/_por/_resolvido_por/_resolvido_em; desmarcar bloqueado_manual sem bloqueado_resolvido_por retorna 422 antes de qualquer escrita"
    requirement: "TRANS-04, TRANS-05"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_bloqueio_manual.py (5 testes)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-03
status: complete
---

# Quick Task 260903-awe: Phase 14 — Confirmação de Transição + Reabertura + Bloqueio Manual

**Modal de confirmação obrigatório no kanban (drag-and-drop + aceite de sugestão da IA), aceite de sugestão roteado pelo caminho gated de patch_task, tabela task_reaberturas com contador, e campos de bloqueio manual com gate 422 exigindo quem resolveu.**

## Performance

- **Duration:** 55min
- **Started:** 2026-09-03T11:11Z (aprox.)
- **Completed:** 2026-09-03T12:06Z (aprox.)
- **Tasks:** 3
- **Files modified:** 9 (3 novos arquivos de teste, 6 modificados)

## Accomplishments

- `ConfirmTransicaoModal` reutilizável — usado tanto por `handleDrop` (drag-and-drop) quanto pelo botão "Aceitar" do banner de sugestão da IA; cancelar em qualquer um dos dois não faz nenhuma chamada de API nem altera estado (TRANS-01).
- Corrigido o bug real de `resolve_task_sugestao`: antes fazia `update` direto de `coluna_kanban` sem gate nenhum; agora delega a `patch_task`, o mesmo caminho gated (DoR/DoD/WIP + `task_transicoes`) usado por `PATCH /tasks/{id}` e `POST /tasks/{id}/mover` — se o gate rejeitar, a sugestão permanece não resolvida (TRANS-02).
- Nova tabela `task_reaberturas` + `tasks.contador_reaberturas`, gravados estritamente na transição `coluna_kanban: concluida -> em_andamento`; `motivo` opcional em schema, endpoint (`mover_task`) e UI (campo no modal) (TRANS-03).
- Task ganha `bloqueado_manual`/`bloqueado_em`/`bloqueado_por`/`bloqueado_resolvido_por`/`bloqueado_resolvido_em`; `patch_task` recusa (422) desmarcar `bloqueado_manual` sem `bloqueado_resolvido_por` válido, antes de qualquer escrita; `TaskModal` pede "Quem bloqueou?"/"Quem resolveu?" na hora certa (TRANS-04, TRANS-05).

## Task Commits

1. **Task 1: Confirmação obrigatória, ponta a ponta** - `4cc68e4` (feat)
2. **Task 2: Reabertura de task** - `d46f611` (feat)
3. **Task 3: Bloqueio manual com captura de quem resolveu** - `947074d` (feat)

_Nenhum commit de metadata de plano criado por este agente — o orquestrador cuida do commit de docs (SUMMARY.md/STATE.md/PLAN.md) separadamente, conforme constraint da tarefa._

## Files Created/Modified

- `docudata-backend/routers/tasks.py` - `resolve_task_sugestao` delegando a `patch_task`; `_registrar_task_transicao` agora retorna o id da transição; `_registrar_reabertura`; gate 422 de `bloqueado_manual`; `mover_task` aceita `motivo`
- `docudata-backend/models/schemas.py` - `TaskSugestaoResponse.task_coluna_atual`; `TaskResponse.contador_reaberturas`/`bloqueado_manual`/etc; `TaskUpdate.bloqueado_manual`/`bloqueado_por`/`bloqueado_resolvido_por` com `field_validator`
- `docudata-backend/supabase_schema.sql` - bloco "Phase 14": `task_reaberturas`, `tasks.contador_reaberturas`, colunas de bloqueio manual (antecipadas na mesma migration)
- `docudata-backend/tests/test_task_confirmacao_sugestao.py` - 4 testes (caminho feliz, gate DoD, recusa, listagem com `task_coluna_atual`)
- `docudata-backend/tests/test_task_reabertura.py` - 5 testes (reabertura, contador cumulativo, não-reabertura em duas direções, motivo opcional)
- `docudata-backend/tests/test_bloqueio_manual.py` - 5 testes (marcar, gate 422, resolver válido, validação Pydantic, patch sem tocar bloqueio)
- `docudata-backend/tests/test_tasks_dod_gate.py` - mock de `task_transicoes.insert` ajustado para incluir `id` (regressão da mudança de assinatura de `_registrar_task_transicao`)
- `docudata-frontend/app/lib/api.ts` - `TaskSugestaoResponse.task_coluna_atual`; `TaskKanbanResponse` com `contador_reaberturas`/campos de bloqueio manual; `moverTaskKanban` aceita `motivo`; `patchTaskKanban` aceita campos de bloqueio manual
- `docudata-frontend/app/components/TasksKanbanTab.tsx` - `ConfirmTransicaoModal` (com campo de motivo condicional para reabertura); `handleDrop`/`confirmPendingMove`/`cancelPendingMove`; `confirmPendingSugestao`/`cancelPendingSugestao`; `TaskModal` com "Quem bloqueou?"/"Quem resolveu?"

## Decisions Made

- `resolve_task_sugestao` chama `patch_task` diretamente como função Python (não HTTP), reaproveitando exatamente o mesmo padrão que `mover_task` já usava — evita duplicar a lógica de gates DoR/DoD/WIP.
- Em erro (409 ou outro) dentro de `confirmPendingMove`, o modal é fechado (`setPendingMove(null)`) mesmo assim — o plano não especificava esse caso explicitamente; optei por não deixar o usuário com um modal de confirmação travado enquanto o erro já é comunicado via banner (`wipError`) ou `alert`.
- A migration da Task 2 já criou as 5 colunas de bloqueio manual (antecipando a Task 3), exatamente como instruído no plano, para evitar editar `supabase_schema.sql` duas vezes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mock de `task_transicoes.insert` em `test_tasks_dod_gate.py` quebrado pela mudança de retorno de `_registrar_task_transicao`**
- **Found during:** Task 2 (Reabertura de task)
- **Issue:** `_registrar_task_transicao` passou a retornar `resp.data[0]["id"]` (necessário para popular `task_reaberturas.transicao_id`). O mock pré-existente em `test_tasks_dod_gate.py` devolvia `resp.data = [payload]` sem chave `"id"`, causando `KeyError` em 3 testes já existentes.
- **Fix:** Ajustado o mock para `resp.data = [dict(payload, id="transicao-1")]`, mesmo padrão já usado nos novos arquivos de teste desta phase.
- **Files modified:** `docudata-backend/tests/test_tasks_dod_gate.py`
- **Verification:** `pytest tests/test_tasks_dod_gate.py -q` — 5/5 passam novamente.
- **Committed in:** `d46f611` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix necessário para não deixar a suíte pré-existente quebrada por uma mudança de assinatura interna. Nenhum scope creep — o arquivo não estava em `files_modified` do plano, mas a quebra foi causada diretamente pela mudança da Task 2.

## Issues Encountered

None.

## Known Stubs

None. Todos os três comportamentos (confirmação, reabertura, bloqueio manual) estão completamente implementados de ponta a ponta (schema → endpoint → UI), sem placeholders.

## User Setup Required

None — nenhuma configuração de serviço externo necessária. A migration em `docudata-backend/supabase_schema.sql` precisa ser aplicada manualmente no Supabase (não há runner de migration automático neste projeto — mesma convenção das phases anteriores).

## Next Phase Readiness

- `task_reaberturas` e `tasks.contador_reaberturas` prontos para alimentar a dimensão Qualidade Técnica (taxa de retrabalho) nas Phases 18/19, sem nenhum cálculo de score implementado aqui.
- `bloqueado_manual`/`bloqueado_resolvido_por` prontos para alimentar a dimensão Autonomia (proporção resolvida pelo próprio operacional) nas Phases 18/19.
- RBAC/papéis (Phase 15/16) permanece fora de escopo — nenhuma checagem de papel/permissão foi adicionada; `bloqueado_resolvido_por` aceita qualquer cliente alegando ser "operacional" ou "gerente" sem verificação de identidade (ver `threat_model` do plano, T-14-04, disposition `accept`).
- Verificação manual (não automatizada) recomendada antes de considerar a phase 100% fechada: arrastar uma task de `concluida` para `em_andamento` no kanban real (com Supabase configurado) e confirmar que o modal mostra o campo de motivo, grava a transição, e uma linha aparece em `task_reaberturas`.

---
*Phase: 14-confirmacao-de-transicao-reabertura-bloqueio-manual*
*Completed: 2026-09-03*

## Self-Check: PASSED

All files created/modified and all task commit hashes (`4cc68e4`, `d46f611`, `947074d`) verified present on disk / in `git log`.
