# Phase 13: Kanban de Tasks — Métricas + Ganchos - Pattern Map

**Mapped:** 2026-09-03
**Files analyzed:** 3 (all edits to existing files — no new files in this phase)
**Analogs found:** 3 / 3

Per RESEARCH.md, most of Phase 13 is already shipped. Remaining scope is additive edits to three existing files:
1. `docudata-backend/routers/metricas.py` — add `performance-operacional` (MET-01+MET-06) and `cycle-time/stats` (MET-02) endpoints
2. `docudata-backend/routers/tasks.py` — add DoD checklist gate to `patch_task` (MET-08)
3. `docudata-frontend/app/lib/api.ts` + `docudata-frontend/app/components/MetricasTab.tsx` — add types, fetch fns, and chart/table sections for the two new endpoints

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `docudata-backend/routers/metricas.py` (add `get_performance_operacional`) | controller (FastAPI route) | request-response / CRUD-read (aggregate) | `get_spi` in same file (lines 9-46) | exact — same file, same aggregation style |
| `docudata-backend/routers/metricas.py` (add `get_cycle_time_stats`) | controller (FastAPI route) | request-response / transform (percentile) | `get_cycle_time` in same file (lines 85-167) | exact — same file, reuses same task/transition fetch |
| `docudata-backend/routers/tasks.py` (edit `patch_task`) | controller (FastAPI route) — gate logic | request-response / validation gate | existing DoR check, same function, lines 281-285 | exact — same function, same file, mirror pattern |
| `docudata-frontend/app/lib/api.ts` (add types + fetch fns) | service (API client) | request-response | `SpiPoint`/`getMetricasSpi`, lines 1292-1324 | exact — same file, same section |
| `docudata-frontend/app/components/MetricasTab.tsx` (add sections) | component | request-response (fetch + render) | existing SPI section (lines 157-183) and CFD section (lines 248-267) | exact — same file, same component |

## Pattern Assignments

### `docudata-backend/routers/metricas.py` — new endpoint `GET /{project_id}/performance-operacional` (MET-01 + MET-06)

**Analog:** `get_spi` (`docudata-backend/routers/metricas.py:9-46`) for project-existence-check + aggregation style; but note Pitfall 3 — do NOT loop per-sprint/per-row here, fetch `tasks` once for the whole project and group in Python.

**Imports pattern** (top of file, lines 1-6 — no new imports needed):
```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.supabase_client import get_client

router = APIRouter(prefix="/metricas", tags=["metricas"])
```

**Project-existence-check pattern** (copy exactly, appears in every endpoint in this file — lines 13-15, 54-55, 96-97, 177-179):
```python
client = get_client()
proj = client.table("projects").select("id").eq("id", project_id).execute()
if not proj.data:
    raise HTTPException(status_code=404, detail="Project not found")
```

**Core aggregation pattern (single-fetch-then-group-in-Python — RESEARCH.md Pattern 1, verbatim recommended implementation):**
```python
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
Note: `spi` here is an interim live-recomputed proxy (no locked per-operational baseline exists in schema — that's Phase 18/SCORE-03's job). Label as "SPI estimado" in the API/UI, not "SPI oficial."

---

### `docudata-backend/routers/metricas.py` — new endpoint `GET /{project_id}/cycle-time/stats` (MET-02)

**Analog:** `get_cycle_time` (`docudata-backend/routers/metricas.py:85-167`) — reuse the exact same task/transition fetch logic (lines 99-117, 125-140), do not re-query differently.

**Percentile helper (stdlib, no new dependency):**
```python
import statistics

def _percentiles(cycle_times_horas: list[float]) -> dict:
    if len(cycle_times_horas) < 2:
        return {
            "p50_horas": cycle_times_horas[0] if cycle_times_horas else None,
            "p85_horas": cycle_times_horas[0] if cycle_times_horas else None,
        }
    q = statistics.quantiles(cycle_times_horas, n=100, method="inclusive")
    return {"p50_horas": round(q[49], 1), "p85_horas": round(q[84], 1)}
```
Wire it as a fully separate endpoint (`/cycle-time/stats`) that runs the same fetch loop as `get_cycle_time` and then calls `_percentiles([r["cycle_time_horas"] for r in result])` — non-breaking, preserves the existing `/cycle-time` array contract already consumed by `MetricasTab.tsx`.

---

### `docudata-backend/routers/tasks.py` — DoD gate in `patch_task` (MET-08)

**Analog:** existing DoR check, same function, `docudata-backend/routers/tasks.py:279-285`.

**Existing DoR pattern to mirror** (lines 278-285):
```python
coluna_nova = data.coluna_kanban
coluna_atual = task.get("coluna_kanban")
if coluna_nova is not None and coluna_nova != coluna_atual:
    # DoR: task sem sprint não pode ir para em_andamento
    sprint_efetivo = data.sprint_id if data.sprint_id is not None else task.get("sprint_id")
    if coluna_nova == "em_andamento" and not sprint_efetivo:
        raise HTTPException(
            status_code=409,
            detail="DoR: associe a task a uma sprint antes de movê-la para Em Andamento.",
        )
```

**New DoD gate to add immediately after** (same `if coluna_nova is not None and coluna_nova != coluna_atual:` block, before the WIP check at line 286-289):
```python
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
Critical detail (Pitfall 4): use `.get("done")` not `["done"]` — checklist items are untyped `dict`s (`TaskUpdate.checklist: Optional[list[dict]]`, `docudata-backend/models/schemas.py:397,418`); missing key must be treated as not-done, and `.get()` avoids `KeyError` on malformed/legacy data. Empty checklist (`[]`) does NOT block (trivially done) — no extra `if not checklist_efetivo` branch needed unless requirements change.

Same 409 status code convention as DoR and the WIP check (`check_wip`, line 287-289) — block before any write, no new error shape.

---

### `docudata-frontend/app/lib/api.ts` — types + fetch fns for the two new endpoints

**Analog:** `SpiPoint` interface + `getMetricasSpi` (`docudata-frontend/app/lib/api.ts:1292-1324`) and `CfdPoint`/`getMetricasCfd` (lines 1313-1342) — same "── Métricas ──" section, append after `getMetricasCfd` (line 1342).

**Pattern to copy exactly:**
```typescript
export interface PerformanceOperacionalPoint {
  operacional_id: string;
  operacional_nome: string;
  pontos_atribuidos: number;
  pontos_realizados: number;
  tasks_concluidas: number;
  spi: number | null;
}

export interface CycleTimeStats {
  p50_horas: number | null;
  p85_horas: number | null;
}

export async function getMetricasPerformanceOperacional(projectId: string): Promise<PerformanceOperacionalPoint[]> {
  const res = await fetch(`${API}/metricas/${projectId}/performance-operacional`);
  if (!res.ok) throw new Error("Erro ao buscar performance por operacional");
  return res.json();
}

export async function getMetricasCycleTimeStats(projectId: string): Promise<CycleTimeStats> {
  const res = await fetch(`${API}/metricas/${projectId}/cycle-time/stats`);
  if (!res.ok) throw new Error("Erro ao buscar estatísticas de cycle-time");
  return res.json();
}
```
`API` is the module-level base URL constant already defined near the top of `api.ts` (same one used by every other `getMetricas*` fn) — no new import needed.

---

### `docudata-frontend/app/components/MetricasTab.tsx` — new sections for performance-operacional + cycle-time stats

**Analog:** existing SPI bar-chart section (lines 157-183) for the operacional-performance chart (bar chart, same `spiColor`/`ReferenceLine` convention), and the cycle-time "Top tasks mais lentas" list (lines 226-245) as the analog for rendering p50/p85 as inline stat text near the existing cycle-time section (lines 205-246) rather than a new chart.

**Fetch wiring pattern** (extend the existing `Promise.all` at lines 110-127):
```typescript
import {
  getMetricasSpi,
  getMetricasThroughput,
  getMetricasCycleTime,
  getMetricasCfd,
  getMetricasPerformanceOperacional,
  getMetricasCycleTimeStats,
  type SpiPoint,
  type ThroughputPoint,
  type CycleTimePoint,
  type CfdPoint,
  type PerformanceOperacionalPoint,
  type CycleTimeStats,
} from "../lib/api";

// inside component:
const [perfOp, setPerfOp] = useState<PerformanceOperacionalPoint[]>([]);
const [ctStats, setCtStats] = useState<CycleTimeStats | null>(null);

useEffect(() => {
  setLoading(true);
  Promise.all([
    getMetricasSpi(projectId),
    getMetricasThroughput(projectId),
    getMetricasCycleTime(projectId),
    getMetricasCfd(projectId),
    getMetricasPerformanceOperacional(projectId),
    getMetricasCycleTimeStats(projectId),
  ])
    .then(([s, t, ct, c, po, cts]) => {
      setSpi(s);
      setThroughput(t);
      setCycleTime(ct);
      setCfd(c);
      setPerfOp(po);
      setCtStats(cts);
      setErr("");
    })
    .catch((e) => setErr(e instanceof Error ? e.message : "Erro ao carregar métricas"))
    .finally(() => setLoading(false));
}, [projectId]);
```

**Chart section pattern to copy for performance-operacional** (mirrors the SPI `BarChart` section, lines 157-183 — reuse `section`/`title`/`empty` style constants already defined at lines 35-61, and `spiColor` helper at lines 95-100):
```tsx
<div style={section}>
  <p style={title}>SPI por operacional (estimado) <InfoTooltip id="perfop" /></p>
  {perfOp.length === 0 ? (
    <p style={empty}>Nenhum operacional com tasks atribuídas ainda.</p>
  ) : (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={perfOp} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="operacional_nome" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} domain={[0, "auto"]} />
        <Tooltip formatter={(v, name) => [v, name === "spi" ? "SPI" : name]} />
        <Bar dataKey="pontos_atribuidos" fill="#e2e8f0" radius={[4, 4, 0, 0]} />
        <Bar dataKey="pontos_realizados" fill="#0f172a" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )}
</div>
```
Add `perfop` to the `TOOLTIPS` record (lines 63-68) following the same one-line-string convention, and label it clearly as an estimate (e.g. "SPI estimado — soma de todos os pontos já atribuídos ao operacional, não um baseline travado").

**p50/p85 inline-stat pattern** (extend the existing cycle-time subtitle line, lines 208-211, following the same `avgCT` ternary-string convention):
```tsx
<p style={subtitle}>
  Tempo em em_andamento antes de concluir.
  {avgCT !== null && ` Média: ${avgCT < 24 ? `${avgCT}h` : `${Math.round(avgCT / 24)}d`}`}
  {ctStats?.p50_horas != null && ` · p50: ${ctStats.p50_horas}h`}
  {ctStats?.p85_horas != null && ` · p85: ${ctStats.p85_horas}h`}
</p>
```

## Shared Patterns

### Project-existence check (backend)
**Source:** every endpoint in `docudata-backend/routers/metricas.py` (e.g. lines 13-15)
**Apply to:** both new metrics endpoints
```python
proj = client.table("projects").select("id").eq("id", project_id).execute()
if not proj.data:
    raise HTTPException(status_code=404, detail="Project not found")
```

### 409 gate pattern (backend)
**Source:** `docudata-backend/routers/tasks.py:281-285` (DoR) and `check_wip` call at 286-289
**Apply to:** the new DoD gate — same status code, same "raise before any write" placement inside `patch_task`, no new error shape.

### Single-fetch-then-group-in-Python (backend)
**Source:** RESEARCH.md Pattern 1 / Pitfall 3 — explicitly do NOT copy the per-sprint N+1 loop style used in `get_spi`/`get_throughput`/`get_cycle_time` (one Supabase call per sprint or per task) for the new project-wide per-operational endpoint. Fetch `tasks` once with `.eq("project_id", project_id)` and aggregate with a plain Python dict, as shown in Pattern 1 above.

### Recharts section shell (frontend)
**Source:** `docudata-frontend/app/components/MetricasTab.tsx` — shared `section`/`title`/`subtitle`/`empty` style objects (lines 35-61) and `InfoTooltip`/`TOOLTIPS` component (lines 63-93)
**Apply to:** any new chart section — reuse these exact style constants and the tooltip mechanism rather than inventing new ones.

## No Analog Found

None — all three files in scope have direct, same-file or same-function analogs already established by the shipped Wave 5/6 code.

## Metadata

**Analog search scope:** `docudata-backend/routers/metricas.py`, `docudata-backend/routers/tasks.py`, `docudata-frontend/app/components/MetricasTab.tsx`, `docudata-frontend/app/lib/api.ts` (all read directly this session)
**Files scanned:** 4
**Pattern extraction date:** 2026-09-03
