# Phase 13: Kanban de Tasks — Métricas + Ganchos - Research

**Researched:** 2026-09-02
**Domain:** FastAPI/Supabase metrics endpoints + Recharts dashboard, extending an already-partially-shipped feature
**Confidence:** HIGH

## Summary

**The single most important finding of this research: most of Phase 13 is already built and shipped.** Git history shows two commits — `efd5a1b feat(wave-5): métricas — SPI, throughput, cycle-time e CFD` and `742bf83 feat(wave-6): auto-derivação status_saude via SPI + DoR básico` — landed on 2026-09-02, after `.planning/.continue-here.md` was written (that handoff file is stale; it still lists `routers/metricas.py` and `MetricasTab.tsx` as not-yet-created, but both exist on disk today `[VERIFIED: docudata-backend/routers/metricas.py, docudata-frontend/app/components/MetricasTab.tsx]`). `.continue-here.md`'s *current* top-of-file pointer has also since moved on to an unrelated Phase 7 thread, confirming it is not tracking Phase 13 anymore.

Concretely, of MET-01..09:
- **MET-03 (throughput), MET-04 (CFD), MET-05 (MetricasTab.tsx/Recharts), MET-09 (auto status_saude from SPI)** are fully implemented, wired end-to-end (router → `main.py` → `lib/api.ts` → tab visible in `page.tsx`'s Tabs), and committed.
- **MET-08 (DoR/DoD)** is half-done: DoR (can't enter `em_andamento` without a sprint) is enforced in `tasks.py:281-285`. DoD (checklist-complete gate before `concluida`) is **not** enforced anywhere — `checklist` is stored but never read as a gate.
- **MET-01 (SPI por operacional)** and **MET-06 (performance por operacional)** are **not implemented**. The existing `/metricas/{project_id}/spi` endpoint computes SPI per *sprint*, not per *operacional* — this was the Wave-1 locked EVM formula applied at the wrong granularity for MET-01's literal requirement text.
- **MET-02 (cycle-time p50/p85)** is **not implemented** as stated. The existing `/metricas/{project_id}/cycle-time` endpoint returns a raw per-task list (already consumed by `MetricasTab.tsx` for a bucket histogram and a "top 5 slowest" list) — no percentile aggregation exists.
- **MET-07 (ganchos daily/commit/retrospectiva → project health signals)** is **not implemented** and has no natural home to extend into — see Open Questions.
- **ROADMAP.md success criterion #3** ("CFD calculável a partir do histórico de `task_transicoes`") is **not literally satisfied** by the shipped `/cfd` endpoint: it computes a live snapshot of `tasks.coluna_kanban` per sprint at query time, not a reconstruction from `task_transicoes` history. Its own docstring calls it a "flow snapshot," not a CFD. Flagged as an open question — accept as MVP-adequate or rebuild from transition history.

**Primary recommendation:** Treat this phase as a small, additive extension — not a rebuild. Add one new endpoint that answers MET-01 + MET-06 together (`performance-operacional`, since both need the same per-operational aggregation), add percentile stats as an *additive* endpoint (don't change the existing `/cycle-time` array contract — it's already consumed by shipped UI), close the DoD gap in `tasks.py`'s existing PATCH handler (same pattern as the DoR check already there), and treat MET-07 as either explicitly deferred or narrowly scoped after a decision with the user (see Open Questions) — do not invent scope for it.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MET-01 | SPI por operacional (Σ pontos_realizados ÷ Σ pontos_previstos) exposto via API | Not yet built — see Pattern 1 (`performance-operacional` endpoint) and Open Question 1 (baseline semantics) |
| MET-02 | Cycle-time (p50, p85) exposto via API | Not yet built — see Pattern 2 (additive `/cycle-time/stats` endpoint using `statistics.quantiles`) |
| MET-03 | Throughput exposto via API | Already built — `GET /metricas/{project_id}/throughput` (`docudata-backend/routers/metricas.py:49-82`) |
| MET-04 | CFD calculável a partir de task_transicoes | Built, but as a live per-sprint snapshot, not derived from `task_transicoes` history — see Pitfall 2 and Open Question 3 |
| MET-05 | MetricasTab.tsx (Recharts) exibe SPI/cycle-time/throughput/CFD | Already built — `docudata-frontend/app/components/MetricasTab.tsx`, wired into `page.tsx` |
| MET-06 | Performance por operacional exposta via API | Not yet built — recommend merging into the same endpoint as MET-01 (Pattern 1) |
| MET-07 *(opcional)* | Ganchos daily/commit/retrospectiva alimentam sinais de saúde do projeto | Not yet built, no existing extension point — see Open Question 2; recommend scoping decision before planning |
| MET-08 *(opcional)* | DoR/DoD bloqueante na transição de status de task | DoR already built (`tasks.py:281-285`); DoD not built — see Pattern 3 (checklist-complete gate) |
| MET-09 *(opcional)* | status_saude auto-derivado do SPI | Already built — `docudata-backend/services/spi_health.py`, wired into `routers/sprints.py:180` and `routers/tasks.py:325` |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SPI/throughput/cycle-time/CFD aggregation | API / Backend (FastAPI) | Database (Supabase queries) | Business logic — percentile math, EVM ratios — belongs server-side; Supabase does raw filtering only, no aggregate SQL is used today (all aggregation is Python-side after `.execute()`) |
| Per-operational baseline semantics | API / Backend | Database (schema) | No schema field exists for "planned points per operational" — must be decided as a backend computation (see Open Questions), not a UI concern |
| Chart rendering (SPI/throughput/cycle-time/CFD/performance) | Browser / Client (Recharts in `MetricasTab.tsx`) | — | Recharts renders client-side from JSON already shaped by the backend; no server-side chart generation |
| DoD gate on task transition | API / Backend (`routers/tasks.py` PATCH handler) | — | Mirrors the existing DoR gate — enforced at the same choke point (`patch_task`), not duplicated in the frontend |
| status_saude auto-derivation | API / Backend (`services/spi_health.py`) | Database (sprints.status_saude) | Already correctly placed; MET-07 (if scoped) should reuse this same call site pattern, not a new mechanism |
| Ganchos daily/commit/retrospectiva (MET-07) | Undetermined — see Open Questions | — | No existing ingestion→signal pipeline to extend; `revisoes_diarias` (Phase 9 "Revisor Diário") is a *different* feature (code-diff review findings), not project health |

## Current Implementation State (read this before planning)

| Req | Status | Evidence | Gap to close |
|-----|--------|----------|---------------|
| MET-01 | ❌ Not built | `/metricas/{id}/spi` in `docudata-backend/routers/metricas.py:9-46` returns per-*sprint* rows, no `operacional_id` grouping | New endpoint or extension grouping by `operacional_id` |
| MET-02 | ❌ Not built | `/metricas/{id}/cycle-time` in `metricas.py:85-167` returns raw per-task array, no percentile | New additive endpoint/field for p50/p85 |
| MET-03 | ✅ Done | `/metricas/{id}/throughput`, `metricas.py:49-82`; consumed in `MetricasTab.tsx:186-203` | None |
| MET-04 | ⚠️ Built, but literal wording mismatch | `/metricas/{id}/cfd`, `metricas.py:170-209`; docstring says "Flow snapshot por sprint," computes from live `tasks.coluna_kanban`, not `task_transicoes` history | Decide: accept as-is (flag ROADMAP wording as satisfied-in-spirit) or rebuild from `task_transicoes` |
| MET-05 | ✅ Done | `docudata-frontend/app/components/MetricasTab.tsx` (271 lines), wired into `page.tsx:598,711` as "Métricas" tab | None |
| MET-06 | ❌ Not built | No per-operational aggregate endpoint exists | New endpoint (recommend merging with MET-01, see below) |
| MET-07 | ❌ Not built, scope undefined | No code references "sinais de saúde" beyond sprint-level `status_saude` | Needs scoping decision — see Open Questions |
| MET-08 | ⚠️ Half-built | DoR: `tasks.py:281-285` blocks `em_andamento` without `sprint_id`. DoD: `checklist` field exists (`tasks` table, `TaskCreate`/`TaskUpdate` schemas) but is never read as a gate | Add checklist-complete check before allowing `coluna_kanban → concluida` |
| MET-09 | ✅ Done | `docudata-backend/services/spi_health.py`, called from `routers/sprints.py:180` (on baseline update) and `routers/tasks.py:325` (on task → concluida) | None |

## Standard Stack

### Core
No new external packages are required for this phase.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `statistics` (stdlib) | bundled with Python 3.13 (already in use — `[VERIFIED: python3 --version → 3.13.7]`) | p50/p85 percentile calculation for MET-02 | Zero new dependency; `statistics.quantiles(data, n=100, method="inclusive")` gives exactly the cut points needed, no need for numpy/pandas for this data volume |
| `recharts` | `^3.10.1` (already installed — `[VERIFIED: docudata-frontend/package.json]`, confirmed current on npm registry `[VERIFIED: npm registry — npm view recharts version → 3.10.1]`) | Chart rendering, already used across `BarChart`/`LineChart`/`AreaChart` in `MetricasTab.tsx` | Already the project's charting standard since MET-05 shipped; no reason to introduce a second charting library for MET-06/07 additions |
| `supabase-py` | already in use throughout `routers/` | DB access | Existing project convention — `client.table(...).select(...).eq(...).execute()` pattern used uniformly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `statistics.quantiles` | `numpy.percentile` | numpy is a heavier dependency (native build) for a feature that only needs two percentile cutoffs on small per-project task counts (tens to low hundreds) — not worth adding |
| Python-side aggregation loop (current project convention) | Postgres aggregate SQL / a new view (like `sprint_spi`) | A `operacional_spi` view mirroring `sprint_spi` (already in schema, `supabase_schema.sql:312-330`) is architecturally cleaner and avoids N+1 queries, but every other metrics endpoint in this codebase computes aggregates in Python post-fetch — introducing a second SQL-view pattern for only this one endpoint adds inconsistency. Recommend Python aggregation for consistency unless task/operational volume becomes a proven perf issue. |

**Installation:** None — no new packages.

## Package Legitimacy Audit

Not applicable — this phase adds no new external dependencies to either `requirements.txt` or `package.json`. Skip the legitimacy gate.

## Architecture Patterns

### System Architecture Diagram

```
Browser (MetricasTab.tsx)
   │
   │ GET /metricas/{project_id}/spi            (existing, per-sprint)
   │ GET /metricas/{project_id}/throughput      (existing)
   │ GET /metricas/{project_id}/cycle-time      (existing, per-task list)
   │ GET /metricas/{project_id}/cfd             (existing, per-sprint snapshot)
   │ GET /metricas/{project_id}/performance-operacional   ← NEW (MET-01 + MET-06)
   │ GET /metricas/{project_id}/cycle-time/stats           ← NEW, additive (MET-02)
   ▼
FastAPI router (routers/metricas.py)
   │
   │ client.table("tasks").select(...).eq("project_id", ...).execute()
   │ client.table("operacionais").select(...).execute()
   │ client.table("task_transicoes").select(...).execute()
   ▼
Supabase (Postgres) — tasks / operacionais / task_transicoes / sprints

Separately, on task PATCH (routers/tasks.py, patch_task):
   coluna_kanban change → em_andamento: DoR check (sprint_id required) [existing]
                        → concluida:    DoD check (checklist complete) ← NEW (MET-08)
                                        + auto_update_sprint_health(...) [existing, MET-09]
```

### Recommended Project Structure
No new files needed beyond editing existing ones — this is an additive-endpoint phase, not a new-module phase.
```
docudata-backend/
├── routers/
│   └── metricas.py          # ADD: performance-operacional, cycle-time/stats endpoints
├── routers/
│   └── tasks.py             # EDIT: add DoD checklist gate next to existing DoR gate (line ~281)
docudata-frontend/
└── app/
    ├── lib/api.ts            # ADD: types + fetch fns for new endpoints (follow SpiPoint/... pattern at line 1290+)
    └── components/
        └── MetricasTab.tsx   # ADD: new chart section(s) for performance-operacional + percentile display
```

### Pattern 1: Per-operational aggregation (MET-01 + MET-06 combined)
**What:** A single endpoint that, for each `operacional` in a project, returns points delivered, an interim SPI proxy, task counts, and average cycle-time — merging MET-01 and MET-06 since they need the identical group-by.
**When to use:** MET-01 and MET-06 both require "aggregate tasks by `operacional_id`" — building two separate endpoints duplicates the fetch-and-group logic for no benefit; the existing UI convention (`MetricasTab.tsx`) already renders multiple metrics from one fetched dataset per section.
**Example (follows the exact style already used in `metricas.py`):**
```python
# Source: pattern extracted from docudata-backend/routers/metricas.py:9-46 (existing get_spi)
@router.get("/{project_id}/performance-operacional")
async def get_performance_operacional(project_id: str):
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    operacionais = (
        client.table("operacionais")
        .select("id, nome")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    tasks = (
        client.table("tasks")
        .select("operacional_id, pontos, coluna_kanban")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    # single pass, avoid N+1 (existing /spi and /cfd endpoints loop per-sprint —
    # do NOT repeat that pattern here since this endpoint groups by operacional
    # across the whole project, which is a much larger fan-out)
    by_op: dict = {}
    for t in tasks:
        op_id = t.get("operacional_id")
        if not op_id:
            continue
        bucket = by_op.setdefault(op_id, {"pontos_atribuidos": 0, "pontos_realizados": 0, "tasks_concluidas": 0})
        bucket["pontos_atribuidos"] += t["pontos"]
        if t["coluna_kanban"] == "concluida":
            bucket["pontos_realizados"] += t["pontos"]
            bucket["tasks_concluidas"] += 1

    result = []
    for op in operacionais:
        b = by_op.get(op["id"], {"pontos_atribuidos": 0, "pontos_realizados": 0, "tasks_concluidas": 0})
        spi = round(b["pontos_realizados"] / b["pontos_atribuidos"], 3) if b["pontos_atribuidos"] > 0 else None
        result.append({
            "operacional_id": op["id"],
            "operacional_nome": op["nome"],
            **b,
            "spi": spi,
        })
    return result
```
**Note on the SPI formula here:** `pontos_atribuidos` (sum of ALL tasks ever assigned to the operational, any column) is used as the "previsto" denominator — this is an *interim proxy*, not a locked baseline. There is no per-operational baseline field in the schema (only `sprints.pontos_previstos` at the whole-sprint level, `[VERIFIED: docudata-backend/supabase_schema.sql:301]` `ALTER TABLE sprints ADD COLUMN IF NOT EXISTS pontos_previstos int;`, and `[VERIFIED: docudata-backend/supabase_schema.sql:244-253]` the `operacionais` table columns are `id, project_id, nome, email, papel, ativo, created_at` — no points/baseline column). Locking a real per-operational baseline that survives task reassignment is explicitly the job of **Phase 18 / SCORE-03** ("Reatribuição de task mid-período recalcula `entrega_pontos_alocados`") per `.planning/REQUIREMENTS.md:96`. **Do not build baseline-locking infrastructure in Phase 13** — that would duplicate Phase 18's job with an incompatible mechanism. Use the live-recompute proxy above and label it clearly as interim in both the API response name and the UI copy.

### Pattern 2: Additive percentile endpoint (MET-02), not a breaking change
**What:** A second endpoint (or query param) that returns `{p50_horas, p85_horas}` computed via `statistics.quantiles`, without altering the shape of the existing `/cycle-time` array (which `MetricasTab.tsx` already consumes for its bucket histogram at lines 141-148 and top-5 list at lines 226-245).
**When to use:** Always prefer additive over breaking when a shipped endpoint already has a live consumer.
**Example:**
```python
# Source: Python stdlib docs (statistics.quantiles) — https://docs.python.org/3/library/statistics.html
import statistics

def _percentiles(cycle_times_horas: list[float]) -> dict:
    if len(cycle_times_horas) < 2:
        # statistics.quantiles requires at least 2 data points
        return {"p50_horas": cycle_times_horas[0] if cycle_times_horas else None, "p85_horas": cycle_times_horas[0] if cycle_times_horas else None}
    q = statistics.quantiles(cycle_times_horas, n=100, method="inclusive")
    return {"p50_horas": round(q[49], 1), "p85_horas": round(q[84], 1)}
```
Reuse the exact same task/transition fetch already in `get_cycle_time` (`metricas.py:85-167`) — do not re-query; either add a `stats: bool` query param to the existing endpoint that returns an envelope `{tasks: [...], p50_horas, p85_horas}` (breaking — requires a frontend type update, acceptable since `MetricasTab.tsx` is the only consumer and would be edited in the same phase anyway) or add a fully separate `/cycle-time/stats` endpoint (non-breaking, more consistent with "don't touch what's shipped"). Recommend the separate endpoint given the phase's low-risk, additive posture.

### Pattern 3: DoD gate mirrors the existing DoR gate
**What:** Block `coluna_kanban → 'concluida'` unless all `checklist` items have `done: true` (or the checklist is empty, if empty checklists are meant to be exempt — flag as open question).
**Where:** `docudata-backend/routers/tasks.py`, inside `patch_task`, immediately after the existing DoR block.
**Example (extends the existing code exactly, same file/function):**
```python
# Source: pattern extracted from docudata-backend/routers/tasks.py:279-285 (existing DoR check)
if coluna_nova == "em_andamento" and not sprint_efetivo:
    raise HTTPException(status_code=409, detail="DoR: associe a task a uma sprint antes de movê-la para Em Andamento.")

# NEW — DoD gate (MET-08)
if coluna_nova == "concluida":
    checklist_efetivo = data.checklist if data.checklist is not None else task.get("checklist", [])
    pendentes = [item for item in checklist_efetivo if not item.get("done")]
    if pendentes:
        raise HTTPException(
            status_code=409,
            detail=f"DoD: {len(pendentes)} item(ns) do checklist ainda não concluído(s).",
        )
```
This 409 pattern (same status code, same "block before any write" placement) is exactly how the existing DoR and WIP checks behave (`tasks.py:281-289`) — the executor should follow this, not invent a new error shape.

### Anti-Patterns to Avoid
- **Building a `pontos_previstos_operacional` schema column / new baseline-lock table in Phase 13:** this duplicates Phase 18's SCORE-01..05 scope (`pontuacao_operacional_sprint`, `entrega_pontos_alocados`) with a different, likely incompatible data model. Keep Phase 13's per-operational SPI as a live-recomputed, unlocked proxy.
- **Repeating the per-sprint N+1 query loop for a project-wide, per-operational endpoint:** the existing `/spi`, `/throughput`, `/cycle-time` endpoints each issue one Supabase query per sprint (and `/cycle-time` issues up to 3 additional queries per completed task). That's tolerable at current data volumes for sprint-scoped loops, but a *per-operational* aggregation should fetch `tasks` once for the whole project and group in Python (see Pattern 1) rather than looping per-operational with N queries each.
- **Changing the response shape of `/metricas/{id}/spi`, `/throughput`, `/cycle-time`, or `/cfd`:** these are live, shipped, and consumed by `MetricasTab.tsx` today. Any change to their JSON shape breaks the frontend without a corresponding `lib/api.ts` type edit — prefer new endpoints for new data.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| p50/p85 percentile calculation | A manual sort + index-math percentile function | `statistics.quantiles(data, n=100, method="inclusive")` | Stdlib, zero dependency, avoids off-by-one errors in manual percentile math (a classic source of subtle metric bugs) |
| Stacked/area charts for CFD, bar charts for SPI/throughput | Custom SVG/Canvas chart code | `recharts` (`AreaChart`, `BarChart` — already used in `MetricasTab.tsx`) | Already the established pattern in this exact file; introducing a second charting approach for new metrics would fragment the component |

**Key insight:** This phase has almost no genuinely new technical risk — the risk is entirely in *scope confusion* (re-doing already-shipped work) and in the two data-model gaps (no per-operational baseline, no defined "health signal" source for MET-07). Both gaps have precedent-based recommendations above; neither needs a new library.

## Common Pitfalls

### Pitfall 1: Re-planning or re-implementing MET-03/04/05/09 as if they don't exist
**What goes wrong:** `.planning/.continue-here.md` and the phase description both describe Wave 5/6 as pending. A planner working strictly from those documents (without reading the actual `routers/metricas.py` and `MetricasTab.tsx` files) will plan to build things that are already built, wasting a wave and risking overwriting working, committed code.
**Why it happens:** `.continue-here.md` is a stale handoff file — the commits landed in a session after it was last written, and it was never updated (its own top section has since moved to tracking an unrelated Phase 7 thread).
**How to avoid:** The planner MUST read `docudata-backend/routers/metricas.py`, `docudata-frontend/app/components/MetricasTab.tsx`, and `docudata-backend/services/spi_health.py` directly before drafting tasks — this research's Current Implementation State table above is the source of truth, derived from those files, not from `.continue-here.md`.
**Warning signs:** Any planned task titled "create routers/metricas.py" or "create MetricasTab.tsx" from scratch is wrong — the correct tasks are "extend" or "add endpoint to".

### Pitfall 2: MET-04 (CFD) success-criteria mismatch going unnoticed
**What goes wrong:** ROADMAP.md's Phase 13 success criterion #3 literally requires CFD to be "calculável a partir do histórico de `task_transicoes`" but the shipped implementation computes a live per-sprint column-count snapshot instead. If the planner marks MET-04 "done, no action" without addressing this, phase verification may later fail the literal success criterion.
**Why it happens:** The shipped code was written to match the requirement text loosely ("CFD... exibe SPI/cycle-time/throughput/CFD") rather than the more precise ROADMAP success-criteria wording.
**How to avoid:** Surface this explicitly as a decision point (see Open Questions) rather than silently picking one interpretation.
**Warning signs:** If `/gsd-verify-work` or a future audit checks the literal success-criteria text against `task_transicoes`-sourced data, the current `/cfd` endpoint will not visibly use that table (`grep task_transicoes routers/metricas.py` returns zero matches in the CFD function).

### Pitfall 3: N+1 query pattern already present, don't propagate it further
**What goes wrong:** `get_cycle_time` (`metricas.py:85-167`) issues up to 3 Supabase round-trips per completed task (transition lookup, sprint lookup, operacional lookup) inside a Python loop. At small task counts (tens) this is invisible; at hundreds of tasks across many sprints it becomes a real latency problem. If MET-01/06's new endpoint copies this loop-per-row style instead of the single-fetch-then-group approach in Pattern 1, the problem compounds.
**Why it happens:** It's the path of least resistance when translating "for each X, look up Y" directly into code.
**How to avoid:** For the new performance-operacional and cycle-time-stats endpoints, fetch the full `tasks`/`task_transicoes` set for the project once, then aggregate in Python (as shown in Pattern 1). Do not add new per-row Supabase calls.
**Warning signs:** A new endpoint with a `for task in tasks: client.table(...).execute()` loop.

### Pitfall 4: checklist items are `dict`, not a typed model — DoD check must handle both `done` and missing/`None`
**What goes wrong:** `TaskCreate.checklist: Optional[list[dict]]` and `TaskUpdate.checklist: Optional[list[dict]]` (`[VERIFIED: docudata-backend/models/schemas.py:397, 418]` — `checklist: Optional[list[dict]] = None  # [{texto, done}]`) are untyped dicts, so a checklist item missing the `done` key entirely (not just `false`) must be treated as "not done" (`item.get("done")` — falsy for both `False` and missing key — already handles this correctly if written as shown in Pattern 3).
**How to avoid:** Use `.get("done")` truthiness check, not `item["done"]` (which would `KeyError` on malformed/legacy data).

## Code Examples

See Pattern 1, 2, and 3 above — all three are copy-adjacent extensions of code already in the repository, verified by direct file read this session (`docudata-backend/routers/metricas.py`, `docudata-backend/routers/tasks.py`, `docudata-backend/routers/sprints.py`, `docudata-backend/services/spi_health.py`).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| N/A — no prior metrics implementation to supersede | Wave 5/6 metrics (SPI-per-sprint, throughput, cycle-time list, CFD snapshot, auto status_saude) | Landed 2026-09-02, commits `efd5a1b`/`742bf83`/`4b6a31f`/`43e105a` | Phase 13's actual remaining surface is much smaller than its description implies |

**Deprecated/outdated:** `.planning/.continue-here.md`'s Wave 5/6 "remaining work" section — describes work as pending that is now committed. Do not treat it as current state for this phase; it should be updated or archived once this phase's planning is finalized.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Pontos atribuídos" (sum of all tasks ever assigned to an operational, any column, live-recomputed) is an acceptable interim proxy for the "previsto" denominator in MET-01's SPI-por-operacional formula, given no per-operational baseline field exists in the schema | Pattern 1 | If the user actually wants a locked, point-in-time baseline per operational in Phase 13 (not deferred to Phase 18), the recommended endpoint design under-delivers and needs a schema addition + baseline endpoint before MET-01 can be considered done |
| A2 | MET-07 (ganchos daily/commit/retrospectiva → health signals) has no natural existing extension point and should be scoped narrowly or explicitly deferred rather than freely designed by the planner | Open Questions | If the user has a specific mechanism in mind (e.g., a keyword/sentiment scan of daily/retro text, or a "N daily reports mention blockers → flag" rule) that isn't captured here, the planner may build something that doesn't match intent — this is optional (Wave 6) so low risk if simply deferred |
| A3 | Accepting the shipped `/cfd` endpoint's "live per-sprint snapshot" semantics as satisfying MET-04 in spirit, rather than rebuilding it to derive from `task_transicoes` history, is acceptable for this MVP phase | Pitfall 2 | If a stricter reading of ROADMAP.md's success criterion #3 is required, `/cfd` needs a rebuild reconstructing state-at-each-point-in-time from `task_transicoes`, which is a materially larger task than an additive endpoint |
| A4 | An empty `checklist` (`[]`) should NOT block a task from moving to `concluida` (task without any checklist items is trivially "done") — the DoD gate in Pattern 3 only blocks when there's at least one item with `done: false`/missing | Pattern 3 | If the intended behavior is "task MUST have a non-empty checklist to be moved to concluida," Pattern 3's code needs an added `if not checklist_efetivo: raise ...` branch |

## Open Questions

1. **What should "SPI por operacional" mean given no per-operational baseline exists?**
   - What we know: Phase 18/SCORE-03 will formally handle mid-sprint reassignment recalculation of `entrega_pontos_alocados` — a rigorous, locked mechanism is explicitly a *later* phase's job.
   - What's unclear: Whether the user wants Phase 13 to ship a clearly-labeled interim/live-recomputed proxy (Assumption A1) or whether they'd rather MET-01 wait until Phase 18 provides the real baseline mechanism.
   - Recommendation: Ship the interim proxy, label it as such in the API/UI (e.g. "SPI estimado" not "SPI oficial"), and note in the phase's plan that Phase 18 will supersede this calculation.

2. **What is the actual scope of MET-07 ("ganchos daily/commit/retrospectiva alimentam sinais de saúde do projeto")?**
   - What we know: `daily`/`retrospectiva`/`commit` are all existing `tipo_documentacao` values on `ingestions` (`[VERIFIED: docudata-backend/supabase_schema.sql:22]` — `tipo_documentacao text CHECK (tipo_documentacao IS NULL OR tipo_documentacao IN ('planning','daily','review','retrospectiva','commit','outro'))`). Sprint-level `status_saude` is already auto-derived from SPI (MET-09). `revisoes_diarias` (Phase 9) is a separate, unrelated feature (code-diff findings, not project health).
   - What's unclear: What signal, specifically, should flow from daily/commit/retrospectiva content into "saúde do projeto" — is it a count of blockers mentioned in dailies, commit velocity, retrospectiva sentiment, or something else? No prior art in the codebase suggests an answer.
   - Recommendation: Since this is explicitly optional (Wave 6, MET-07), recommend deferring it out of Phase 13 entirely unless the user has a concrete mechanism in mind — flag for `/gsd-discuss-phase` follow-up or a direct question before planning, rather than the planner inventing a design.

3. **Does the shipped `/cfd` endpoint satisfy Phase 13, or does ROADMAP.md's success criterion #3 require a rebuild from `task_transicoes`?**
   - What we know: Current `/cfd` is a live per-sprint snapshot of `tasks.coluna_kanban`, already displayed in `MetricasTab.tsx` as a stacked `AreaChart`. ROADMAP.md's Phase 13 text says "CFD (cumulative flow diagram) calculável a partir de `task_transicoes`" (MET-04) and success criterion #3 repeats "a partir do histórico de `task_transicoes`."
   - What's unclear: Whether this wording was aspirational/approximate (in which case ship-as-is is fine) or a strict acceptance criterion.
   - Recommendation: Confirm with the user during planning; if strict, the rebuild reconstructs, for each sprint/day, cumulative counts of tasks that have *ever* reached each column by walking `task_transicoes` chronologically — meaningfully larger scope than the rest of this phase.

## Environment Availability

Skipped — this phase adds no new external dependencies, services, or CLI tools. All required infrastructure (FastAPI, Supabase, Recharts, Python stdlib) is already running and verified present in the existing codebase.

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json` (absent = enabled), so this section is included, scoped to what's relevant.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Project has no auth in v1 by explicit design decision (`CLAUDE.md` Constraints: "Sem auth v1: Espaço compartilhado sem isolamento por usuário") — unchanged by this phase |
| V3 Session Management | No | Same as above |
| V4 Access Control | No | CORS is `allow_origins=["*"]` by design for this dev-stage MVP; this phase does not alter that posture |
| V5 Input Validation | Yes | Pydantic models (`TaskUpdate`, existing pattern) already validate `coluna_kanban` via `@field_validator`; new endpoints should follow the same convention — no raw string params without validation |
| V6 Cryptography | No | Not applicable — no new secrets or crypto operations introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Unvalidated `project_id`/`operacional_id` path params leading to cross-project data leakage | Information Disclosure | Every existing endpoint in `metricas.py` checks `client.table("projects").select("id").eq("id", project_id).execute()` before proceeding — new endpoints must follow this exact existence-check pattern before running any aggregation |
| Checklist item shape confusion (missing `done` key) causing DoD gate to silently allow bypass | Tampering (of task state) | Use `.get("done")` not `["done"]`, as shown in Pattern 3 / Pitfall 4 |

## Sources

### Primary (HIGH confidence)
- Direct file reads this session: `docudata-backend/routers/metricas.py`, `docudata-backend/routers/tasks.py`, `docudata-backend/routers/sprints.py`, `docudata-backend/services/spi_health.py`, `docudata-backend/supabase_schema.sql`, `docudata-backend/models/schemas.py`, `docudata-frontend/app/components/MetricasTab.tsx`, `docudata-frontend/app/lib/api.ts`, `docudata-backend/routers/revisao_ingest.py`, `docudata-backend/routers/commit_ingest.py`
- `git log --oneline` on the relevant files — confirmed commit history and dates
- `npm view recharts version` — confirmed registry-current version matches installed version

### Secondary (MEDIUM confidence)
- Python `statistics.quantiles` documentation (training knowledge, standard library API stable since Python 3.8 — not independently re-fetched this session, but low-risk given it's stdlib and unrelated to fast-moving ecosystems)

### Tertiary (LOW confidence)
- None used for factual claims in this document — all findings above are grounded in direct file reads or tool output.

## Metadata

**Confidence breakdown:**
- Current implementation state: HIGH — every claim verified by direct `Read` of the source file this session
- Standard stack / architecture: HIGH — no new libraries; patterns extracted directly from existing shipped code
- Open questions (MET-01 baseline semantics, MET-07 scope, MET-04 literal interpretation): by definition unresolved — flagged, not guessed

**Research date:** 2026-09-02
**Valid until:** 14 days — this phase sits directly on top of actively-changing code in the same feature area; re-verify Current Implementation State table if significant time passes before planning executes
