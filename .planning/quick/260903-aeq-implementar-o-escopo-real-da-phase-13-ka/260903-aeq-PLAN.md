---
phase: 13-kanban-de-tasks-m-tricas-ganchos
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docudata-backend/routers/metricas.py
  - docudata-backend/routers/tasks.py
  - docudata-backend/tests/test_metricas_novos_endpoints.py
  - docudata-backend/tests/test_tasks_dod_gate.py
  - docudata-frontend/app/lib/api.ts
  - docudata-frontend/app/components/MetricasTab.tsx
autonomous: true
requirements:
  - "MET-01"
  - "MET-02"
  - "MET-06"
  - "MET-08"

estimate:
  tokens: 45000
  raw_tokens: 45000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "GET /metricas/{project_id}/performance-operacional returns, for every operacional in the project, pontos_atribuidos/pontos_realizados/tasks_concluidas and an interim (estimated) spi — MET-01 + MET-06"
    - "GET /metricas/{project_id}/cycle-time/stats returns {p50_horas, p85_horas} computed via statistics.quantiles, without changing the existing /cycle-time array response consumed by MetricasTab.tsx — MET-02"
    - "PATCH /tasks/{id} (and POST /tasks/{id}/mover, which delegates to it) rejects a move to coluna_kanban=concluida with 409 when any checklist item has done falsy/missing, and allows it when the checklist is complete or empty — MET-08"
    - "MetricasTab.tsx renders a new 'SPI por operacional (estimado)' bar-chart section fed by performance-operacional, and shows p50/p85 inline in the existing cycle-time section — frontend wiring for MET-01/MET-06/MET-02"
    - "MET-07 (ganchos daily/commit/retrospectiva -> sinais de saude) is explicitly NOT implemented by this plan — deferred, not silently dropped"
  artifacts:
    - "docudata-backend/routers/metricas.py (performance-operacional + cycle-time/stats endpoints appended)"
    - "docudata-backend/routers/tasks.py (DoD gate added to patch_task, mirrors existing DoR gate)"
    - "docudata-backend/tests/test_metricas_novos_endpoints.py (new — covers both new endpoints)"
    - "docudata-backend/tests/test_tasks_dod_gate.py (new — covers DoD 409 + success path)"
    - "docudata-frontend/app/lib/api.ts (PerformanceOperacionalPoint, CycleTimeStats types + fetch fns)"
    - "docudata-frontend/app/components/MetricasTab.tsx (new performance-operacional section + p50/p85 inline text)"
  key_links:
    - "MetricasTab.tsx useEffect Promise.all -> getMetricasPerformanceOperacional/getMetricasCycleTimeStats -> GET /metricas/{project_id}/performance-operacional and /cycle-time/stats -> routers/metricas.py"
    - "TasksKanbanTab.tsx moverTaskKanban/patchTaskKanban (existing, unchanged) -> PATCH /tasks/{id} -> patch_task DoD gate -> existing generic 409 error banner (setWipError) already renders e.message verbatim, no frontend change needed for MET-08"
---

<objective>
Close the real remaining gap of Phase 13 (Kanban de Tasks — Métricas + Ganchos). Per 13-RESEARCH.md, MET-03/04/05/09 are already shipped and MUST NOT be touched or rewritten. This plan adds exactly the four still-missing pieces: a per-operational performance/SPI-estimado endpoint (MET-01 + MET-06), a cycle-time percentile endpoint (MET-02), a DoD checklist gate on task completion (MET-08), and the MetricasTab.tsx/api.ts wiring to display the two new endpoints. MET-07 is explicitly out of scope for this plan (optional, no natural extension point per RESEARCH.md Open Question 2) — noted here so it is visibly deferred, not silently dropped.

Purpose: Deliver the literal MET-01/MET-02/MET-06/MET-08 requirement text that the already-shipped Wave 5/6 code does not satisfy, as small additive edits to existing, working, committed files — no rebuilds, no new files beyond tests.
Output: Two new backend endpoints, one backend gate, two new frontend types/fetch functions, one new frontend chart section + inline stat text, two new backend test files.
</objective>

<execution_context>
@/Users/gabrielmezzalira/.claude/gsd-core/workflows/execute-plan.md
@/Users/gabrielmezzalira/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/STATE.md
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/phases/13-kanban-de-tasks-m-tricas-ganchos/13-RESEARCH.md
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/phases/13-kanban-de-tasks-m-tricas-ganchos/13-PATTERNS.md
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Performance-operacional end-to-end — backend endpoint + frontend chart (MET-01, MET-06)</name>
  <files>
    docudata-backend/routers/metricas.py,
    docudata-backend/tests/test_metricas_novos_endpoints.py,
    docudata-frontend/app/lib/api.ts,
    docudata-frontend/app/components/MetricasTab.tsx
  </files>
  <read_first>
    - docudata-backend/routers/metricas.py — read whole file (210 lines); note the project-existence-check repeated in every endpoint and the exact style of get_spi/get_cfd, which are the closest analogs
    - docudata-backend/tests/test_project_usage.py — read whole file; `_make_mock_client`/`_patch_and_client` is the exact mocking pattern to reuse (monkeypatch `get_client` on the router module, drive via `TestClient(app)` from `main`)
    - docudata-frontend/app/lib/api.ts lines 1290-1343 — SpiPoint/CfdPoint interfaces + getMetricasSpi/getMetricasCfd fetch fns, the exact style to mirror
    - docudata-frontend/app/components/MetricasTab.tsx — read whole file (271 lines); note the section/title/empty style constants (lines 35-61), TOOLTIPS record (63-68), InfoTooltip component (70-93), the existing SPI BarChart section (157-183) as the closest analog, and the Promise.all fetch block (110-127)
    - .planning/phases/13-kanban-de-tasks-m-tricas-ganchos/13-PATTERNS.md — "Pattern 1" and the "MetricasTab.tsx" section have the exact, already-verified-against-this-session's-file-contents code to copy for this task
    - .planning/phases/13-kanban-de-tasks-m-tricas-ganchos/13-RESEARCH.md — Assumption A1 (why spi here is an interim/estimated proxy, not a locked baseline) and Pitfall 3 (single-fetch-then-group, no per-row N+1)
  </read_first>
  <action>
Backend: append a new endpoint `GET /{project_id}/performance-operacional` to the end of `docudata-backend/routers/metricas.py`, after `get_cfd`. Use the same project-existence-check every other endpoint in this file uses (404 if the project doesn't exist). Fetch `operacionais` (columns `id, nome`) filtered by `project_id`, and fetch `tasks` (columns `operacional_id, pontos, coluna_kanban`) filtered by `project_id` — each as one query, not a per-row loop (per Pitfall 3, this endpoint aggregates project-wide and must not repeat the per-sprint N+1 style used by get_spi/get_throughput/get_cycle_time in this same file). Group tasks in a plain Python dict keyed by `operacional_id`, accumulating `pontos_atribuidos` (sum of `pontos` for every task ever assigned to that operacional, any column), `pontos_realizados` (sum of `pontos` where `coluna_kanban == "concluida"`), and `tasks_concluidas` (count where `coluna_kanban == "concluida"`). Return one object per operacional (including operacionais with zero tasks) with `operacional_id`, `operacional_nome`, `pontos_atribuidos`, `pontos_realizados`, `tasks_concluidas`, and `spi` = `round(pontos_realizados / pontos_atribuidos, 3)` when `pontos_atribuidos > 0`, else `None`. Follow 13-PATTERNS.md's "Pattern 1" code block verbatim (it is already verified against the current file). Label this `spi` as an interim, live-recomputed estimate — not a locked baseline (RESEARCH.md Assumption A1; Phase 18/SCORE-03 owns the real per-operational baseline mechanism) — do not add any schema column or baseline-lock table.

Backend tests: create `docudata-backend/tests/test_metricas_novos_endpoints.py` reusing the exact `_make_mock_client`/`_patch_and_client` pattern from `tests/test_project_usage.py` (monkeypatch `get_client` on `routers.metricas`, drive requests through `fastapi.testclient.TestClient(app)`). Write one test with 2 mocked operacionais and a handful of mocked tasks split across them (mixing `coluna_kanban` values including at least one `concluida` per operacional and at least one non-`concluida`), asserting the response includes both operacionais with `pontos_atribuidos`/`pontos_realizados`/`tasks_concluidas`/`spi` matching values computed by hand from the fixture in the assertion.

Frontend types/fetch: in `docudata-frontend/app/lib/api.ts`, append (immediately after the existing `getMetricasCfd` function, end of the "── Métricas ──" section) a `PerformanceOperacionalPoint` interface with fields `operacional_id: string`, `operacional_nome: string`, `pontos_atribuidos: number`, `pontos_realizados: number`, `tasks_concluidas: number`, `spi: number | null`, and an async `getMetricasPerformanceOperacional(projectId: string): Promise<PerformanceOperacionalPoint[]>` fetching `${API}/metricas/${projectId}/performance-operacional`, throwing `new Error("Erro ao buscar performance por operacional")` on a non-ok response — mirror `getMetricasCfd`'s exact style immediately above it.

Frontend UI: in `docudata-frontend/app/components/MetricasTab.tsx`, import `getMetricasPerformanceOperacional` and `type PerformanceOperacionalPoint` from `../lib/api`; add `const [perfOp, setPerfOp] = useState<PerformanceOperacionalPoint[]>([]);`; extend the existing `Promise.all` in the component's `useEffect` (currently `getMetricasSpi`/`getMetricasThroughput`/`getMetricasCycleTime`/`getMetricasCfd`) with a fifth call `getMetricasPerformanceOperacional(projectId)`, destructure the fifth resolved value into `setPerfOp`; add a `perfop` entry to the `TOOLTIPS` record explaining this is an *estimated* SPI (sum of all points ever assigned to the operacional, not a locked baseline); add a new `<div style={section}>` block after the CFD section (same `section`/`title`/`empty` style constants, same `ResponsiveContainer`+`BarChart`+`CartesianGrid`+`XAxis`+`YAxis`+`Tooltip` shape as the existing SPI bar chart at lines ~157-183) titled "SPI por operacional (estimado)" with `<InfoTooltip id="perfop" />`, `operacional_nome` on the X axis, two bars (`pontos_atribuidos` fill `#e2e8f0`, `pontos_realizados` fill `#0f172a`), and an empty-state message when `perfOp.length === 0` ("Nenhum operacional com tasks atribuídas ainda."). Add one short bullet to the `tutorialSteps` array explaining the estimate label. Copy the exact code from 13-PATTERNS.md's "MetricasTab.tsx — new sections" block rather than freehand-styling it.
  </action>
  <verify>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && python3 -c "import ast; ast.parse(open('routers/metricas.py').read()); print('metricas.py syntax OK')"</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && .venv/bin/pytest tests/test_metricas_novos_endpoints.py -q -k performance_operacional</automated>
    <automated>grep -c "getMetricasPerformanceOperacional" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-frontend/app/lib/api.ts"</automated>
    <automated>grep -c "getMetricasPerformanceOperacional" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-frontend/app/components/MetricasTab.tsx"</automated>
  </verify>
  <done>
    GET /metricas/{project_id}/performance-operacional returns one entry per operacional with pontos_atribuidos/pontos_realizados/tasks_concluidas/spi computed correctly; the new pytest test passes; MetricasTab.tsx renders the "SPI por operacional (estimado)" section fed by this endpoint via api.ts's getMetricasPerformanceOperacional.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Cycle-time percentiles — /cycle-time/stats endpoint + frontend p50/p85 (MET-02)</name>
  <files>
    docudata-backend/routers/metricas.py,
    docudata-backend/tests/test_metricas_novos_endpoints.py,
    docudata-frontend/app/lib/api.ts,
    docudata-frontend/app/components/MetricasTab.tsx
  </files>
  <read_first>
    - docudata-backend/routers/metricas.py get_cycle_time (lines 85-167) — reuse this exact task/transition fetch loop; do not re-query differently
    - .planning/phases/13-kanban-de-tasks-m-tricas-ganchos/13-PATTERNS.md "Pattern 2" — the exact `_percentiles` helper and wiring notes (separate endpoint, non-breaking to existing /cycle-time contract)
    - docudata-frontend/app/components/MetricasTab.tsx lines 205-246 — existing cycle-time section (subtitle line + bucket histogram + "Top tasks mais lentas" list) where the p50/p85 text is appended
  </read_first>
  <behavior>
    - Test: mock client returns >=2 completed tasks with known cycle_time_horas values (e.g. [10, 20, 30, 40, 50]) -> GET /metricas/{id}/cycle-time/stats returns p50_horas and p85_horas matching statistics.quantiles(data, n=100, method="inclusive") rounded to 1 decimal (assert exact expected numbers computed by hand in the test).
    - Edge case: mock client returns 0 or 1 completed tasks -> p50_horas/p85_horas equal that single value (or None if zero), no ZeroDivisionError/IndexError from statistics.quantiles (which requires >= 2 points).
    - Existing /cycle-time endpoint's response shape (array of task rows) must remain byte-for-byte unchanged — do not touch get_cycle_time itself.
  </behavior>
  <action>
Backend: add `import statistics` to the top of `docudata-backend/routers/metricas.py` alongside the existing imports. Add a module-level helper `_percentiles(cycle_times_horas: list[float]) -> dict` per 13-PATTERNS.md "Pattern 2" verbatim: if fewer than 2 data points, return `{"p50_horas": cycle_times_horas[0] if cycle_times_horas else None, "p85_horas": cycle_times_horas[0] if cycle_times_horas else None}`; otherwise compute `q = statistics.quantiles(cycle_times_horas, n=100, method="inclusive")` and return `{"p50_horas": round(q[49], 1), "p85_horas": round(q[84], 1)}`. Add a new endpoint `GET /{project_id}/cycle-time/stats` (a fully separate route from `/{project_id}/cycle-time`, both are distinct literal path segments so there is no FastAPI route-ordering conflict) that runs the identical task/transition fetch loop already in `get_cycle_time` (same project-existence check, same `tasks` query filtered to `coluna_kanban == "concluida"`, same `task_transicoes` lookup for `duracao_fase_anterior_segundos`) to build the same list of `cycle_time_horas` values, then calls `_percentiles(...)` on that list and returns its result directly. Do not add a `sprint_numero` query param to this new endpoint (project-wide only, matching the MET-02 requirement text). Do not modify `get_cycle_time` itself — its array contract is already consumed by the shipped bucket-histogram and "Top tasks mais lentas" UI.

Backend tests: append a second test function to `docudata-backend/tests/test_metricas_novos_endpoints.py` (same mocking pattern as Task 1's test) covering both `<behavior>` cases above — a multi-task case with hand-computed expected p50/p85, and a 0/1-task edge case.

Frontend types/fetch: in `docudata-frontend/app/lib/api.ts`, append (after the `getMetricasPerformanceOperacional` function added in Task 1) a `CycleTimeStats` interface with fields `p50_horas: number | null`, `p85_horas: number | null`, and an async `getMetricasCycleTimeStats(projectId: string): Promise<CycleTimeStats>` fetching `${API}/metricas/${projectId}/cycle-time/stats`, throwing `new Error("Erro ao buscar estatísticas de cycle-time")` on non-ok response.

Frontend UI: in `docudata-frontend/app/components/MetricasTab.tsx`, import `getMetricasCycleTimeStats` and `type CycleTimeStats`; add `const [ctStats, setCtStats] = useState<CycleTimeStats | null>(null);`; extend the same `Promise.all` from Task 1 with a sixth call `getMetricasCycleTimeStats(projectId)`, destructure into `setCtStats`; extend the existing cycle-time section's subtitle line (currently showing average cycle-time) to also append ` · p50: {ctStats?.p50_horas}h` and ` · p85: {ctStats?.p85_horas}h` when those values are non-null, following the exact ternary-string convention already used for the average (`avgCT`) in that subtitle. Copy the exact snippet from 13-PATTERNS.md's "p50/p85 inline-stat pattern".
  </action>
  <verify>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && python3 -c "import ast; ast.parse(open('routers/metricas.py').read()); print('metricas.py syntax OK')"</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && .venv/bin/pytest tests/test_metricas_novos_endpoints.py -q</automated>
    <automated>grep -c "getMetricasCycleTimeStats" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-frontend/app/components/MetricasTab.tsx"</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && python3 -c "from routers import metricas; routes = [r.path for r in metricas.router.routes]; assert '/metricas/{project_id}/cycle-time/stats' in routes, routes; assert '/metricas/{project_id}/cycle-time' in routes, routes; print('routes OK:', routes)"</automated>
  </verify>
  <done>
    GET /metricas/{project_id}/cycle-time/stats returns {p50_horas, p85_horas} matching statistics.quantiles math; the existing /cycle-time endpoint's response shape is unchanged; both pytest tests in test_metricas_novos_endpoints.py pass; MetricasTab.tsx's cycle-time section shows p50/p85 inline.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: DoD checklist gate on task completion (MET-08) — MET-07 explicitly deferred</name>
  <files>
    docudata-backend/routers/tasks.py,
    docudata-backend/tests/test_tasks_dod_gate.py
  </files>
  <read_first>
    - docudata-backend/routers/tasks.py lines 243-329 (patch_task) — the exact function to edit; lines 278-289 hold the existing DoR check (sprint required for em_andamento) and the WIP check (check_wip) that must stay intact and unmoved
    - docudata-backend/routers/tasks.py lines 332-337 (mover_task) — confirms POST /tasks/{id}/mover delegates to patch_task, so the gate added here automatically covers drag-and-drop too; no separate edit needed there
    - docudata-backend/models/schemas.py lines 397, 418, 443 — checklist is `Optional[list[dict]]` / `list[dict]`, untyped dicts shaped `{texto, done}` — a missing `done` key must be treated as not-done
    - .planning/phases/13-kanban-de-tasks-m-tricas-ganchos/13-PATTERNS.md "Pattern 3" — the exact DoD gate code, mirroring the existing DoR gate's placement and 409 status-code convention
    - docudata-frontend/app/lib/api.ts lines ~1205-1245 (patchTaskKanban, moverTaskKanban) — confirms the frontend already throws `{status: 409}` with the backend's `detail` message verbatim for ANY 409 response; docudata-frontend/app/components/TasksKanbanTab.tsx lines ~540-549 confirms the catch block displays `e.message` in the existing WIP error banner — this means NO frontend file needs to change for MET-08, the DoD 409 message will surface automatically through the existing generic error handling
  </read_first>
  <behavior>
    - Test: PATCH /tasks/{id} with coluna_kanban="concluida" on a task whose checklist has at least one item with done=false -> 409, detail contains "DoD".
    - Test: PATCH /tasks/{id} with coluna_kanban="concluida" on a task whose checklist has all items done=true -> 200 (no DoD block).
    - Test: PATCH /tasks/{id} with coluna_kanban="concluida" on a task whose checklist is empty ([]) or has an item missing the "done" key entirely -> empty checklist allows the move (200); missing "done" key is treated as not-done (409), per `.get("done")` truthiness semantics.
    - Test: PATCH /tasks/{id} moving to a column other than "concluida" is unaffected by the new gate (no DoD check runs).
  </behavior>
  <action>
In `docudata-backend/routers/tasks.py`, inside `patch_task`, insert a new DoD gate immediately after the existing DoR `raise HTTPException(...)` block (ends at line 285) and before the existing `op_efetivo = ...` / WIP-check lines (286-289) — same `if coluna_nova is not None and coluna_nova != coluna_atual:` block, so it only runs on an actual column change. When `coluna_nova == "concluida"`: compute `checklist_efetivo` as `data.checklist if data.checklist is not None else task.get("checklist", [])`, then build `pendentes` as the list of items in `checklist_efetivo` (guard against `None` with `or []`) where `item.get("done")` is falsy — use `.get("done")`, never `["done"]`, since checklist items are untyped dicts and a missing key must count as not-done (Pitfall 4). If `pendentes` is non-empty, raise `HTTPException(status_code=409, detail=f"DoD: {len(pendentes)} item(ns) do checklist ainda não concluído(s).")` — same 409 status code and "raise before any write" placement as the DoR and WIP checks immediately around it, no new error shape. An empty checklist does NOT block the move (Assumption A4 — a task with no checklist items is trivially done). Because `mover_task` (POST /tasks/{id}/mover) calls `patch_task` internally, this single edit covers both the direct PATCH endpoint and drag-and-drop — do not duplicate the check there.

MET-07 note (visible, not code): ganchos daily/commit/retrospectiva -> sinais de saúde do projeto is explicitly NOT built in this task. Per RESEARCH.md Open Question 2, it has no existing extension point and was descoped by the user for this quick task — leave `services/spi_health.py` and the sprint-level `status_saude` auto-derivation (MET-09, already shipped) untouched, and do not add any new "health signal" mechanism.

Backend tests: create `docudata-backend/tests/test_tasks_dod_gate.py` reusing the `_make_mock_client`/`_patch_and_client`-style Supabase mock from `tests/test_project_usage.py`, adapted for the `tasks` table (mock `client.table("tasks").select(...).eq("id", ...).execute()` to return a task fixture with a `checklist` field, and mock the `.update(...).eq(...).execute()` chain to return the updated row) and monkeypatching `get_client` on `routers.tasks`. Cover all four `<behavior>` cases above via `TestClient(app).patch(f"/tasks/{{id}}", json={{"coluna_kanban": "concluida"}})`.
  </action>
  <verify>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && python3 -c "import ast; ast.parse(open('routers/tasks.py').read()); print('tasks.py syntax OK')"</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && .venv/bin/pytest tests/test_tasks_dod_gate.py -q</automated>
    <automated>grep -n "def patch_task" -A 60 "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend/routers/tasks.py" | grep -c "DoD:"</automated>
  </verify>
  <done>
    PATCH /tasks/{id} (and POST /tasks/{id}/mover) blocks a move to coluna_kanban=concluida with 409 "DoD: N item(ns)..." when the checklist has incomplete items, allows it when the checklist is complete or empty; all four pytest cases in test_tasks_dod_gate.py pass; no frontend file was modified for this task (existing 409 handling already surfaces the message).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client -> GET /metricas/{project_id}/performance-operacional, /cycle-time/stats | project_id path param is unauthenticated (no auth in v1, per CLAUDE.md constraint) — any caller can request any project's metrics |
| client -> PATCH /tasks/{id} (DoD gate) | data.checklist in the request body is client-supplied and could be crafted to bypass the gate if the check trusts client-provided "done" values without server-side task-state cross-check |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-13q-01 | Information Disclosure | GET /metricas/{project_id}/performance-operacional, /cycle-time/stats | low | accept | MVP has no auth by explicit design (CLAUDE.md "Sem auth v1") — unchanged posture from the already-shipped /spi, /throughput, /cycle-time, /cfd endpoints in the same file, which follow the same unauthenticated pattern |
| T-13q-02 | Tampering | PATCH /tasks/{id} — checklist item shape (missing `done` key) | medium | mitigate | Use `.get("done")` not `["done"]` when computing `pendentes`, so a malformed/legacy item (missing key) is treated as not-done rather than raising KeyError or silently passing (Pitfall 4) |
| T-13q-03 | Tampering | PATCH /tasks/{id} — client could send `checklist` in the same request body that also sets `coluna_kanban=concluida`, self-marking all items done to bypass the gate | low | accept | Same trust model as the existing DoR/WIP checks in this handler (sprint_id, operacional_id are also client-supplied in the same request) — this is a shared-space MVP with no auth; not a new risk introduced by this plan |
| T-13q-04 | Denial of Service | GET /metricas/{project_id}/performance-operacional | low | accept | Single-fetch-then-group-in-Python (Pitfall 3) bounds this to two Supabase queries regardless of task count, same complexity class as existing endpoints in this file |
</threat_model>

<verification>
- `python3 -c "import ast; ast.parse(...)"` on `routers/metricas.py` and `routers/tasks.py`: both parse without SyntaxError
- `docudata-backend/.venv/bin/pytest tests/test_metricas_novos_endpoints.py tests/test_tasks_dod_gate.py -q`: all tests pass
- `from routers import metricas; [r.path for r in metricas.router.routes]` includes both `/metricas/{project_id}/performance-operacional` and `/metricas/{project_id}/cycle-time/stats`, and the pre-existing `/metricas/{project_id}/cycle-time` path is still present and unchanged
- `grep -c "getMetricasPerformanceOperacional" api.ts` and `MetricasTab.tsx`, `grep -c "getMetricasCycleTimeStats" api.ts` and `MetricasTab.tsx`: all >= 1
- `grep -n "def patch_task" -A 60 routers/tasks.py | grep -c "DoD:"`: >= 1, confirming the gate lives inside patch_task
- Manual spot-check (not automated): `docudata-frontend` dev server renders MetricasTab.tsx without a console error for a project with at least one operacional and one completed task
</verification>

<success_criteria>
- [ ] GET /metricas/{project_id}/performance-operacional live, tested, returns per-operational pontos_atribuidos/pontos_realizados/tasks_concluidas/spi (MET-01, MET-06)
- [ ] GET /metricas/{project_id}/cycle-time/stats live, tested, returns {p50_horas, p85_horas}; existing /cycle-time endpoint untouched (MET-02)
- [ ] PATCH /tasks/{id} (and POST /tasks/{id}/mover) blocks concluida transition on incomplete checklist with 409, tested (MET-08)
- [ ] MetricasTab.tsx displays both new endpoints (new bar-chart section + inline p50/p85 text)
- [ ] MET-07 not implemented, deferral explicit in this PLAN.md and in code comments — not silently dropped
- [ ] MET-03, MET-04, MET-05, MET-09 and all four already-shipped endpoints (/spi, /throughput, /cycle-time, /cfd) unmodified
</success_criteria>

<output>
Create `.planning/quick/260903-aeq-implementar-o-escopo-real-da-phase-13-ka/260903-aeq-SUMMARY.md` when done
</output>

