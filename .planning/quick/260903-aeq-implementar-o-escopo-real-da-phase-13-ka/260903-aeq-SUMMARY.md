---
phase: 13-kanban-de-tasks-m-tricas-ganchos
plan: 260903-aeq
subsystem: api
tags: [fastapi, supabase, statistics, recharts, kanban, metrics]

requires:
  - phase: 13-kanban-de-tasks-m-tricas-ganchos
    provides: "Wave 5/6 shipped metrics endpoints (/spi, /throughput, /cycle-time, /cfd) and MetricasTab.tsx dashboard, plus the existing DoR gate in patch_task"
provides:
  - "GET /metricas/{project_id}/performance-operacional (MET-01, MET-06)"
  - "GET /metricas/{project_id}/cycle-time/stats (MET-02)"
  - "DoD checklist gate in PATCH /tasks/{id} (MET-08)"
  - "MetricasTab.tsx SPI-por-operacional chart + inline p50/p85 cycle-time text"
affects: [phase-18-score, metrics, kanban]

actuals:
  tokens: 7600
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Single-fetch-then-group-in-Python aggregation for project-wide per-operational metrics (avoids N+1)"
    - "Additive percentile endpoint pattern (/cycle-time/stats) that doesn't touch a shipped array-contract endpoint"

key-files:
  created:
    - docudata-backend/tests/test_metricas_novos_endpoints.py
    - docudata-backend/tests/test_tasks_dod_gate.py
  modified:
    - docudata-backend/routers/metricas.py
    - docudata-backend/routers/tasks.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/components/MetricasTab.tsx

key-decisions:
  - "SPI por operacional is an interim, live-recomputed proxy (sum of all points ever assigned / points delivered) — explicitly labeled 'estimado' in both the API doc and UI tooltip, not a locked baseline. Phase 18/SCORE-03 owns the real per-operational baseline mechanism."
  - "MET-07 (ganchos daily/commit/retrospectiva -> sinais de saude) is explicitly deferred, not built — no natural extension point exists per 13-RESEARCH.md Open Question 2."
  - "Task 1 and Task 2 from PLAN.md were committed together (one commit) instead of two, since both touch the same four files with interleaved edits — splitting after the fact would have required complex partial hunk staging for no real benefit."
  - "Synced docudata-backend/.venv with requirements.txt (installed missing apscheduler/resend/tzlocal, all already-declared dependencies) — this was blocking ALL backend tests, including pre-existing ones, and was required to run the plan's own verification commands."

patterns-established:
  - "New per-operational or project-wide aggregate endpoints in metricas.py should fetch once (tasks/operacionais) and group in a Python dict, not loop per-row with additional Supabase calls."

requirements-completed:
  - MET-01
  - MET-02
  - MET-06
  - MET-08

coverage:
  - id: D1
    description: "GET /metricas/{project_id}/performance-operacional returns per-operational pontos_atribuidos/pontos_realizados/tasks_concluidas/spi"
    requirement: "MET-01"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_metricas_novos_endpoints.py#test_performance_operacional_agrega_por_operacional"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_metricas_novos_endpoints.py#test_performance_operacional_operacional_sem_tasks_retorna_zeros"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /metricas/{project_id}/cycle-time/stats returns {p50_horas, p85_horas} via statistics.quantiles, without changing the existing /cycle-time array response"
    requirement: "MET-02"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_metricas_novos_endpoints.py#test_cycle_time_stats_multi_task_p50_p85"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_metricas_novos_endpoints.py#test_cycle_time_stats_zero_tasks_returns_none"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_metricas_novos_endpoints.py#test_cycle_time_stats_existing_cycle_time_endpoint_unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "MET-06 performance por operacional exposed via the same performance-operacional endpoint as D1"
    requirement: "MET-06"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_metricas_novos_endpoints.py#test_performance_operacional_agrega_por_operacional"
        status: pass
    human_judgment: false
  - id: D4
    description: "PATCH /tasks/{id} (and POST /tasks/{id}/mover) rejects a move to coluna_kanban=concluida with 409 when checklist has incomplete items, allows it when complete or empty"
    requirement: "MET-08"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_tasks_dod_gate.py#test_dod_bloqueia_com_item_pendente"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_tasks_dod_gate.py#test_dod_permite_com_checklist_completo"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_tasks_dod_gate.py#test_dod_checklist_vazio_permite"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_tasks_dod_gate.py#test_dod_item_sem_chave_done_bloqueia"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_tasks_dod_gate.py#test_dod_nao_afeta_movimento_para_outra_coluna"
        status: pass
    human_judgment: false
  - id: D5
    description: "MetricasTab.tsx renders SPI-por-operacional (estimado) bar chart and inline p50/p85 cycle-time text"
    verification:
      - kind: other
        ref: "npx tsc --noEmit (zero errors) + npm run build (Compiled successfully, all routes generated)"
        status: pass
    human_judgment: true
    rationale: "Type-checking and production build confirm the code compiles and the component renders without throwing, but visual placement/styling of the new chart section and tooltip has not been screenshotted or manually reviewed in a running dev server."

duration: 35min
completed: 2026-09-03
status: complete
---

# Quick Task 260903-aeq: Phase 13 Real Scope (Métricas + DoD) Summary

**Two additive backend endpoints (performance-operacional, cycle-time/stats) plus a DoD checklist gate on task completion, closing MET-01/02/06/08 without touching any already-shipped Phase 13 code.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-09-03T10:11:00Z (approx, per plan hand-off)
- **Completed:** 2026-09-03T10:46:29Z
- **Tasks:** 3 (Task 1 and Task 2 committed together, Task 3 separately)
- **Files modified:** 4 (+2 new test files)

## Accomplishments
- `GET /metricas/{project_id}/performance-operacional`: single-fetch-then-group aggregation returning `pontos_atribuidos`/`pontos_realizados`/`tasks_concluidas`/`spi` (interim, estimated) for every operacional in a project, including operacionais with zero tasks (MET-01, MET-06)
- `GET /metricas/{project_id}/cycle-time/stats`: `{p50_horas, p85_horas}` via `statistics.quantiles(..., n=100, method="inclusive")`, handling 0/1-datapoint edge cases without exceptions, as a fully additive endpoint that leaves `/cycle-time`'s existing array contract byte-for-byte unchanged (MET-02)
- DoD gate in `patch_task`: blocks `coluna_kanban -> "concluida"` with 409 `"DoD: N item(ns)..."` when any checklist item's `done` is falsy or missing (using `.get("done")`, never `["done"]`), allows the move when the checklist is complete or empty; `POST /tasks/{id}/mover` inherits this automatically since it delegates to `patch_task` (MET-08)
- `MetricasTab.tsx` wired to both new endpoints: new "SPI por operacional (estimado)" bar-chart section plus p50/p85 appended inline to the existing cycle-time subtitle
- MET-07 explicitly left unimplemented, with a code comment and this summary both flagging it as deferred (no natural extension point per 13-RESEARCH.md), not silently dropped
- 12 new backend tests (7 for the two metrics endpoints, 5 for the DoD gate), all passing

## Task Commits

Each task was committed atomically (Task 1 and Task 2 merged into one commit — see Deviations):

1. **Task 1 + Task 2: performance-operacional + cycle-time/stats** - `0d277e2` (feat)
2. **Task 3: DoD checklist gate** - `040cb2c` (feat)

**Plan metadata:** committed separately by the orchestrator after this summary (per constraints, this executor does not commit docs artifacts)

## Files Created/Modified
- `docudata-backend/routers/metricas.py` - added `_percentiles` helper, `get_performance_operacional`, `get_cycle_time_stats`
- `docudata-backend/routers/tasks.py` - added DoD gate to `patch_task`, immediately after the existing DoR check
- `docudata-backend/tests/test_metricas_novos_endpoints.py` - new, 7 tests for both new metrics endpoints
- `docudata-backend/tests/test_tasks_dod_gate.py` - new, 5 tests for the DoD gate
- `docudata-frontend/app/lib/api.ts` - `PerformanceOperacionalPoint`, `CycleTimeStats` types + `getMetricasPerformanceOperacional`, `getMetricasCycleTimeStats` fetch fns
- `docudata-frontend/app/components/MetricasTab.tsx` - new state, extended `Promise.all`, new tooltip entry, new tutorial step, new chart section, p50/p85 inline text

## Decisions Made
- SPI-por-operacional formula uses "sum of all points ever assigned to the operacional, any column" as the denominator — labeled "estimado" everywhere (API doc comment + UI tooltip + tutorial step) since no per-operational baseline field exists in the schema; Phase 18/SCORE-03 owns the real mechanism (per 13-RESEARCH.md Assumption A1)
- `/cycle-time/stats` built as a fully separate route rather than a query param on `/cycle-time`, preserving the existing array contract already consumed by the shipped bucket-histogram and "Top tasks mais lentas" UI
- Empty checklist does NOT block the DoD gate (task with no checklist items is trivially done), matching 13-RESEARCH.md Assumption A4
- MET-07 deferred entirely — no code written for it, flagged explicitly rather than silently dropped

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Synced backend `.venv` with `requirements.txt`**
- **Found during:** Task 1 (running the plan's own pytest verify command)
- **Issue:** `.venv` was missing `apscheduler` (already declared in `requirements.txt` at `>=3.10.0`), which is imported unconditionally by `main.py`. This blocked `TestClient(app)` construction for every test in the suite — including pre-existing tests, not just the new ones — with `ModuleNotFoundError: No module named 'apscheduler'`.
- **Fix:** Ran `.venv/bin/pip install -r requirements.txt`, which installed `apscheduler`, `resend`, and `tzlocal` — all already-declared, already-vetted dependencies, not new package choices. No `requirements.txt` change.
- **Files modified:** None (venv-only, not tracked in git)
- **Verification:** `pytest` now imports `main.py` successfully; full suite runs
- **Committed in:** N/A (venv state, not a git-tracked file)

**2. [Process] Task 1 and Task 2 committed together instead of as two atomic commits**
- **Found during:** Commit step after implementing both tasks
- **Issue:** Task 1 and Task 2 both modify the same four files (`metricas.py`, `test_metricas_novos_endpoints.py`, `api.ts`, `MetricasTab.tsx`) with edits interleaved in the same functions/sections (e.g., both add functions to `metricas.py`, both extend the same `Promise.all` in `MetricasTab.tsx`). Implementing them in sequence as originally planned, then splitting into two commits after the fact, would require complex partial-hunk staging with no meaningful benefit (both tasks are part of the same tracer-task deliverable per the plan's own `type="tracer"` framing for Task 1, which folds MET-01/MET-06/MET-02's frontend+backend wiring into one verifiable slice).
- **Fix:** Committed as a single `feat(13-01)` commit covering both tasks' scope, with the deviation noted in the commit message body.
- **Files modified:** `docudata-backend/routers/metricas.py`, `docudata-backend/tests/test_metricas_novos_endpoints.py`, `docudata-frontend/app/lib/api.ts`, `docudata-frontend/app/components/MetricasTab.tsx`
- **Verification:** All Task 1 and Task 2 `<verify>` commands from PLAN.md pass individually (grep counts, pytest -k filters, route introspection) — the merged commit does not hide any verification gap.
- **Committed in:** `0d277e2`

---

**Total deviations:** 2 (1 blocking auto-fix, 1 commit-granularity process deviation)
**Impact on plan:** Both necessary to complete the plan as specified; no scope creep, no architectural changes, no plan-check-in required.

## Issues Encountered
- Pre-existing failures in `docudata-backend/tests/test_schemas_and_client.py` (4 tests: `test_conteudo_estruturado_has_exactly_6_fields`, `test_conteudo_estruturado_instantiation`, `test_project_response_has_required_fields`, `test_projects_router_has_3_routes`) — these assert a stale field/route count for `ProjectResponse`/`routers/projects.py` from an earlier phase of the project, unrelated to any file this quick task touches. Confirmed pre-existing (not caused by this task's changes, `routers/projects.py` and `models/schemas.py` were not modified) and out of scope per the SCOPE BOUNDARY rule. Not fixed — flagged here for visibility.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 13's remaining literal scope (MET-01/02/06/08) is now closed; MET-03/04/05/09 remain untouched and unmodified, as required.
- MET-07 remains explicitly deferred — a future phase or discussion should decide its scope (per 13-RESEARCH.md Open Question 2) before any implementation is attempted.
- Phase 18/SCORE-03 should supersede the interim SPI-por-operacional proxy in `performance-operacional` with a real locked baseline mechanism when that phase is planned.
- Manual visual spot-check of the new "SPI por operacional (estimado)" chart section and p50/p85 inline text in a running dev server (`npm run dev`) was not performed in this session — `tsc --noEmit` and `npm run build` both passed cleanly, confirming compile-time correctness, but the plan's own `<verification>` section lists this manual spot-check as "not automated." Flagged as D5 in the coverage block above (`human_judgment: true`).

## Test Results

**Backend:**
```
docudata-backend/tests/test_metricas_novos_endpoints.py: 7 passed
docudata-backend/tests/test_tasks_dod_gate.py: 5 passed
Full suite: 48 passed, 4 failed (pre-existing, unrelated — see Issues Encountered)
```

**Frontend:**
```
npx tsc --noEmit: 0 errors
npm run build: Compiled successfully, all 5 routes generated (static + dynamic)
```

---
*Phase: 13-kanban-de-tasks-m-tricas-ganchos*
*Completed: 2026-09-03*

## Self-Check: PASSED

All created/modified files verified present on disk; both task commits (`0d277e2`, `040cb2c`) verified present in `git log`.
