---
id: "08-01"
phase: "08-painel-do-gerente-kanban-de-sprint"
plan: "01"
status: complete
completed_at: "2026-08-22T00:00:00Z"
---

# Plan 08-01 Summary — Tracer: Backend + Frontend Wiring

## What Was Built

Full end-to-end path for the Painel tab:

- **`docudata-backend/routers/painel.py`** — `GET /projects/{id}/painel` endpoint with all 4 calculation helpers:
  - `calcular_bloco_a` — prazo vs escopo vs aprovação, desvio detection
  - `calcular_bloco_b` — travadas (>7 dias), aguardando cliente (>5 d.u.), em ajuste
  - `calcular_bloco_c` — WIP, throughput, cycle time p50/p85
  - `calcular_bloco_d` — fases_resumo, eficiência de fluxo, detalhe por funcionalidade
- **`docudata-backend/main.py`** — painel router imported and registered
- **`docudata-frontend/app/lib/api.ts`** — `PainelData`, `BlocoA/B/C/D`, `FaseResumo`, `FuncionalidadeResponse` interfaces + `getPainel()` and `listFuncionalidades()` functions
- **`docudata-frontend/app/components/PainelTab.tsx`** — full component: 4 metric blocks, Bloco D accordion, 3-column kanban with sprint dropdown
- **`docudata-frontend/app/projects/[id]/page.tsx`** — `TabId` union extended with `"painel"`, Painel tab inserted 2nd, `PainelTab` rendered with `onNavigateToConfig` wiring

## Key Decisions / Deviations

- PainelTab.tsx already includes the full polished rendering (accordion + kanban) rather than a minimal stub, since the component is completely self-contained. Wave 2 (08-02) will refine and polish the visual output.
- `.in_()` call on `transicoes_status` is guarded by `if func_list:` to avoid empty-list query.
- `statistics.quantiles` guarded with `len >= 2` check per pitfall 1 from RESEARCH.md.

## Artifacts Created

- `docudata-backend/routers/painel.py` (new)
- `docudata-backend/main.py` (updated)
- `docudata-frontend/app/lib/api.ts` (updated)
- `docudata-frontend/app/components/PainelTab.tsx` (new)
- `docudata-frontend/app/projects/[id]/page.tsx` (updated)

## Self-Check: PASSED

- `python -c "from routers.painel import router"` → OK
- `python -c "from routers.painel import calcular_bloco_a, calcular_bloco_b, calcular_bloco_c, calcular_bloco_d"` → OK
- `grep -c "include_router(painel.router)" main.py` → 1
- `npx tsc --noEmit` → no errors
- `grep -c "className=" PainelTab.tsx` → 0 (all inline styles)
- `grep "activeTab === \"painel\"" page.tsx` → found, wired correctly
- `calcular_bloco_a({"data_inicio": None}, [])` → `{"sem_dados": True}` ✓
