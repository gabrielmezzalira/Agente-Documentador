---
phase: 08-painel-do-gerente-kanban-de-sprint
verified: 2026-08-23T01:43:41Z
status: human_needed
score: 14/15 must-haves verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "Bloco D accordion: clicking 'ver detalhe' on a phase row expands the per-funcionalidade time list inline; clicking again collapses it"
    test: "Open the Painel tab on a project with funcionalidades that have transicoes_status with duracao_fase_anterior_segundos recorded. Click '▼ ver detalhe' on any phase row in Bloco D. Observe the expansion. Click '▲ fechar'. Observe collapse."
    expected: "Clicking '▼ ver detalhe' reveals a list of funcionalidade titles with time in dias per phase; the same row row shows '▲ fechar'. Clicking again collapses the list. Only one row can be expanded at a time (expandedFase is a single string | null value)."
    why_human: "The expandedFase state and the conditional render are present and wired. The toggle logic is correct in code. Whether the expand/collapse renders real per-funcionalidade data (i.e., whether any project has transicoes_status rows with duracao_fase_anterior_segundos populated) cannot be confirmed without a live browser session. The behavior-dependent state transition — click → expand; click again → collapse — requires visual observation to confirm."
human_verification:
  - test: "Open Painel tab on a project with no data_inicio / data_fim_contratada set"
    expected: "Bloco A renders a grey placeholder with text 'Sem dados de contrato' and a button 'Ir para Configurações'. Clicking the button switches the active tab to Configurações."
    why_human: "Visual rendering and tab navigation require live browser observation."
  - test: "Open Painel tab on a project with data_inicio and data_fim_contratada set, where (% prazo − % aprovado) > tolerancia_desvio_pontos"
    expected: "Bloco A renders three percentage rows (Prazo consumido, Escopo concluído, Aprovado pelo cliente) plus an orange '⚠ Desvio de X pts acima da tolerância' alert badge."
    why_human: "Visual rendering of the desvio badge and the color/layout of the three metric rows require live browser observation."
  - test: "Open Painel tab on a project with funcionalidades in em_andamento >7 days, status_cliente=enviado >5 business days, and status=em_ajuste"
    expected: "Bloco B shows three sub-sections: Travadas, Aguardando cliente, Em ajuste — each listing the relevant funcionalidade titles with colored day-count badges."
    why_human: "Correct filtering requires real Supabase data with recorded timestamps. The calculation logic is verified as correct, but whether the data conditions are present in the live environment requires human verification."
  - test: "Open Painel tab on a project with zero funcionalidades concluidas"
    expected: "Bloco C shows WIP and throughput but displays 'Nenhuma funcionalidade concluída — cycle time indisponível' in place of cycle time rows (null displayed as informational message, not '—')."
    why_human: "Conditional rendering branches for zero concluidas and null values require live data verification."
  - test: "Bloco D accordion: clicking '▼ ver detalhe' on a phase row expands per-funcionalidade time list; clicking '▲ fechar' collapses it"
    expected: "Expansion renders funcionalidade titles with dias values from detalhe_por_funcionalidade. Only one phase row is expanded at a time. Clicking the same row again collapses it."
    why_human: "State transition (expand/collapse) and correctness of the detalhe_por_funcionalidade data rendered requires live browser observation with a project that has transicoes_status rows."
  - test: "Open Painel tab. Observe the Kanban sprint dropdown default value."
    expected: "The dropdown defaults to the highest sprint numero. Changing the selection immediately re-filters all three columns without a page reload."
    why_human: "Default value selection and reactive re-filtering require live browser observation."
  - test: "Verify a funcionalidade that belongs to multiple sprints (same id_funcional appears in multiple sprint_alvo entries) shows multiple sprint badges in its Kanban card"
    expected: "The KanbanCard shows one purple chip per sprint from allSprintsByFuncional grouping — e.g., 'Sprint 1' and 'Sprint 2' as adjacent chips."
    why_human: "The D-08 multi-sprint badge logic groups across all project funcionalidades by id_funcional. Whether this produces multiple badges requires a data scenario with shared id_funcional values, observable only in the browser."
---

# Phase 8: Painel do Gerente + Kanban de Sprint — Verification Report

**Phase Goal:** Build the Painel do Gerente feature — a dashboard tab that shows 4 metric blocks (Bloco A: Tempo x Escopo, Bloco B: Itens Travados, Bloco C: Metricas de Fluxo, Bloco D: Tempo por Fase) plus a Kanban de Sprint with sprint dropdown and 3 columns.
**Verified:** 2026-08-23T01:43:41Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /projects/{id}/painel returns HTTP 200 with JSON containing keys bloco_a, bloco_b, bloco_c, bloco_d | VERIFIED | `painel.py` line 303–308: endpoint returns `{"bloco_a": ..., "bloco_b": ..., "bloco_c": ..., "bloco_d": ...}`. Router registered in `main.py` line 29. Python import test passes. |
| 2 | Bloco A returns sem_dados=true when data_inicio or data_fim_contratada is null, sem_dados=false with numeric fields when both are set | VERIFIED | `calcular_bloco_a` lines 35–66 in `painel.py`. Unit test confirmed: `calcular_bloco_a({"data_inicio": None, "data_fim_contratada": None}, [])` → `{"sem_dados": True}`. Call with valid dates returns `{"sem_dados": False, "pct_prazo_consumido": ..., ...}`. |
| 3 | Bloco B lists funcionalidades where status=em_andamento and last status transition >7 days ago under travadas key | VERIFIED | `calcular_bloco_b` lines 69–125 in `painel.py`. Logic: for each `em_andamento` func, computes days since last status transition (or created_at fallback); appends to `travadas` if `dias > 7`. Returns `{"travadas": [...], "aguardando_cliente": [...], "em_ajuste": [...]}`. Unit test with empty data returns `{"travadas": [], ...}` with no error. |
| 4 | Bloco C returns wip, throughput_por_semana, cycle_time_p50_dias, cycle_time_p85_dias (null when <1 concluida) | VERIFIED | `calcular_bloco_c` lines 128–183 in `painel.py`. All 4 keys present in return dict (line 178–182). `statistics.quantiles` guarded with `len >= 2` (line 170). Unit test with empty funcs returns `{"throughput_por_semana": 0.0, "wip": 0, "cycle_time_p50_dias": None, "cycle_time_p85_dias": None, "total_concluidas": 0}`. |
| 5 | Bloco D returns fases_resumo dict keyed by phase name, eficiencia_fluxo_pct, detalhe_por_funcionalidade list | VERIFIED | `calcular_bloco_d` lines 186–271 in `painel.py`. Returns `{"fases_resumo": {...}, "eficiencia_fluxo_pct": ..., "detalhe_por_funcionalidade": [...]}` at lines 268–270. Unit test with empty inputs returns `{"fases_resumo": {}, "eficiencia_fluxo_pct": None, "detalhe_por_funcionalidade": []}`. |
| 6 | Frontend aba Painel is the 2nd tab (after Sprints, before Tecnologias) and renders the raw JSON data when active | VERIFIED | `page.tsx` line 47: `TabId` union includes `"painel"`. Tabs array (lines 470–478): index 0 = Sprints, index 1 = Painel, index 2 = Tecnologias. Line 557: `{activeTab === "painel" && <PainelTab ... />}`. PainelTab is imported at line 40. |
| 7 | No 500 errors when project has zero funcionalidades | VERIFIED | `painel.py` line 287: `.in_()` call on `transicoes_status` is guarded by `if func_list:` — skipped when empty, `trans_list = []`. All 4 calculation functions verified with empty inputs: no exception raised. `calcular_bloco_b([], [])`, `calcular_bloco_c([], [])`, `calcular_bloco_d([], [])` all return valid empty-data dicts. |
| 8 | Bloco A renders grey placeholder card with "Sem dados de contrato" text and link to Configuracoes tab when sem_dados is true | VERIFIED | `PainelTab.tsx` lines 76–94: `if bloco.sem_dados` branch renders "Sem dados de contrato" text (line 79) and a button "Ir para Configurações" (line 81) that calls `onNavigateToConfig?.()`. `page.tsx` line 561: `onNavigateToConfig={() => setActiveTab("config" as TabId)}`. |
| 9 | Bloco A renders three percentage bars (prazo, escopo, aprovado) and an orange "Desvio detectado" badge when desvio_detectado is true | VERIFIED | `PainelTab.tsx` lines 97–127: three metric rows rendered with `pct_prazo_consumido`, `pct_escopo_concluido`, `pct_aprovado_cliente`. Lines 108–126: `{bloco.desvio_detectado && <div ...>⚠ Desvio de {bloco.desvio_pontos} pts acima da tolerância</div>}`. Orange background `#fff7ed`, border `#fed7aa`, text `#c2410c`. |
| 10 | Bloco B renders three sub-sections: Travadas, Aguardando cliente, Em ajuste | VERIFIED | `PainelTab.tsx` lines 133–234 (`BlocoBCard`): three sub-sections with labels "Travadas" (line 142), "Aguardando cliente" (line 182), "Em ajuste" (line 215). Each shows funcionalidade titles with colored day-count badges, and empty-state messages when lists are empty. |
| 11 | Bloco C renders WIP, throughput and cycle time p50/p85 with null displayed as dash character | VERIFIED | `PainelTab.tsx` lines 237–280 (`BlocoCCard`): WIP (line 244), throughput (line 252, `{bloco.throughput_por_semana ?? "—"}`), cycle time p50 (line 265, `{bloco.cycle_time_p50_dias ?? "—"}`), p85 (line 272, `{bloco.cycle_time_p85_dias ?? "—"}`). When `total_concluidas === 0`, informational message shown instead of cycle time rows (line 256–259). |
| 12 | Bloco D accordion: clicking "ver detalhe" on a phase row expands the per-funcionalidade time list inline; clicking again collapses it | PRESENT_BEHAVIOR_UNVERIFIED | `PainelTab.tsx` lines 283–366 (`BlocoDCard`): `expandedFase` prop controls expansion. Toggle button (line 325–329): `{expandedFase === fase ? "▲ fechar" : "▼ ver detalhe"}`. Click calls `setExpandedFase(expandedFase === fase ? null : fase)`. Expansion div renders when `expandedFase === fase` (line 331). Code is present and wired. Actual expand/collapse UX requires live browser verification with data. |
| 13 | Kanban shows 3 column headers (Planejado, Em andamento, Concluido) with funcionalidade counts and each card shows titulo plus sprint badges | VERIFIED | `PainelTab.tsx` lines 543–618: 3-column grid with headers "Planejado" (line 546), "Em andamento" (line 571), "Concluído" (line 597). Each column header has a count badge chip. `KanbanCard` (lines 368–405) renders `titulo` (line 390) and sprint badges from `allSprints` (lines 397–401) plus prioridade chip. |
| 14 | Kanban sprint dropdown lists all sprints by numero and defaults to the highest one on tab open | VERIFIED | `PainelTab.tsx` line 412–414: `useState<number>(sprints.length > 0 ? Math.max(...sprints.map(s => s.numero)) : 1)`. Lines 447–448: `sortedSprints = [...sprints].sort((a, b) => b.numero - a.numero)`. Select element (line 515–536) renders sorted sprints as options. |
| 15 | All styling uses inline style objects only — zero className attributes in PainelTab.tsx | VERIFIED | `grep -c "className=" PainelTab.tsx` → 0. All 623 lines use only `style={{...}}` inline style objects. No Tailwind classes anywhere in the file. |

**Score:** 14/15 truths verified (1 present, behavior-unverified)

### Roadmap Success Criteria Coverage

| SC # | Criterion | Status | Notes |
|------|-----------|--------|-------|
| SC1 | Bloco A displays % prazo consumed, % escopo concluido, % aprovado when contract dates set; shows "sem dados" when not | VERIFIED | Backend `calcular_bloco_a` + frontend `BlocoACard` both verified. |
| SC2 | When (% prazo − % aprovado) > tolerancia_desvio_pontos, visual alert appears (desvio_detectado: bool, no DB persistence) | VERIFIED | Backend returns `desvio_detectado` bool (no DB write — pure calculation). Frontend renders orange badge when true. |
| SC3 | Bloco B lists travadas (em_andamento >7 days), aguardando cliente (enviado >5 business days), em_ajuste | VERIFIED | Full logic in `calcular_bloco_b`. Frontend renders three sub-sections. |
| SC4 | Bloco C shows throughput, WIP, cycle time (p50, p85) "sempre agregados por squad" | VERIFIED (with design decision) | CONTEXT.md D-13 documents explicit design decision: "Sem agrupamento por squad no Bloco C — cada projeto tem um único squad. Métricas agregam o projeto inteiro." ROADMAP wording "agregados por squad" means the project (which is treated as a single squad). Implementation aggregates the full project — correct per D-13. |
| SC5 | Bloco D shows average time and p85 per status phase and flow efficiency; per-funcionalidade detail available | VERIFIED | `calcular_bloco_d` returns `fases_resumo` (with `media_dias`, `p85_dias`, `amostras`), `eficiencia_fluxo_pct`, and `detalhe_por_funcionalidade`. Frontend renders accordion with "ver detalhe" toggle. |
| SC6 | Kanban shows 3 columns (Planejado / Em andamento / Concluido), no Transbordou column; multi-sprint funcionalidades have sprint badge | VERIFIED | Exactly 3 columns in code. No Transbordou column. `allSprintsByFuncional` grouping by `id_funcional` produces sprint badges per card. |

### Requirements Coverage

The PLAN frontmatter declares requirements `M2 Blocos A, B, C, D (§5)` and `M3 (§5)`. These are milestone requirements defined in the project design document (CLAUDE.md §5), not tracked in REQUIREMENTS.md (which covers v1/v2 product requirements up to Phase 3). REQUIREMENTS.md does not contain M2 or M3 identifiers — they are design doc section references, not REQUIREMENTS.md IDs. No orphaned requirements found in REQUIREMENTS.md for Phase 8.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docudata-backend/routers/painel.py` | GET /projects/{id}/painel endpoint + 4 calculation functions | VERIFIED | 309 lines. All 4 helpers defined at module level. Endpoint at line 274. Clean Python import. |
| `docudata-backend/main.py` | painel router imported and registered | VERIFIED | Line 6: `painel` in import. Line 29: `app.include_router(painel.router)`. |
| `docudata-frontend/app/lib/api.ts` | PainelData, BlocoA/B/C/D, FaseResumo, FuncionalidadeResponse interfaces + getPainel() + listFuncionalidades() | VERIFIED | All interfaces exported at lines 651–711. `getPainel` at line 713. `listFuncionalidades` at line 719. |
| `docudata-frontend/app/components/PainelTab.tsx` | Full component with 4 blocks, accordion, kanban | VERIFIED | 623 lines. Full implementation with sub-components BlocoACard, BlocoBCard, BlocoCCard, BlocoDCard, KanbanCard. Zero className attributes. |
| `docudata-frontend/app/projects/[id]/page.tsx` | TabId union includes painel, Tabs array has Painel 2nd, PainelTab rendered | VERIFIED | Line 47: TabId union updated. Lines 470–478: Painel is index 1. Lines 557–563: PainelTab rendered with onNavigateToConfig wired. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `painel.py` | `services/supabase_client.py` | `get_client()` import at line 6; used at line 276 | WIRED | Same pattern as other routers. |
| `PainelTab.tsx` | `api.ts` | imports `getPainel`, `listFuncionalidades`, interfaces at lines 4–11 | WIRED | `getPainel(projectId)` called in `useEffect` at line 419. |
| `page.tsx` | `PainelTab.tsx` | import at line 40; render at lines 558–563 | WIRED | `activeTab === "painel"` guard; passes `projectId`, `sprints`, `onNavigateToConfig`. |
| `Bloco D expandedFase state` | `BlocoDCard` sub-component | prop `expandedFase` and `setExpandedFase` at lines 495–499 | WIRED | State lifted to parent `PainelTab`. Prop passed correctly to `BlocoDCard`. |
| `sprintSelecionada state` | kanban filter | `funcsDaSprint` filter at line 449–451 uses `String(sprintSelecionada)` | WIRED | onChange on select (line 517) updates state; filter re-evaluates. |
| `Bloco A "Ir para Configuracoes"` | `setActiveTab("config")` | `onNavigateToConfig` prop; page.tsx line 561 | WIRED | `onNavigateToConfig?.()` called on button click; page wires it to `setActiveTab("config")`. |

### Data-Flow Trace (Level 4)

| Component | Data Variable | Source | Produces Real Data | Status |
|-----------|---------------|--------|--------------------|--------|
| `BlocoACard` | `bloco.pct_prazo_consumido` | `calcular_bloco_a` → project row from Supabase + date arithmetic | Yes — computed from real DB dates | FLOWING |
| `BlocoBCard` | `bloco.travadas` | `calcular_bloco_b` → `transicoes_status` rows from Supabase | Yes — computed from real DB timestamps | FLOWING |
| `BlocoCCard` | `bloco.wip`, `bloco.throughput_por_semana` | `calcular_bloco_c` → `funcionalidades` + `transicoes_status` from Supabase | Yes — computed from real DB data | FLOWING |
| `BlocoDCard` | `bloco.fases_resumo` | `calcular_bloco_d` → `transicoes_status.duracao_fase_anterior_segundos` from Supabase | Yes — uses recorded duration values | FLOWING |
| `KanbanCard` | `funcsDaSprint` | `listFuncionalidades(projectId)` → `GET /funcionalidades?project_id=...` → Supabase | Yes — real DB query | FLOWING |
| `KanbanCard` | `allSprints` sprint badges | `allSprintsByFuncional` grouping over `funcionalidades` array | Yes — derived from real fetched data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend imports cleanly | `python3 -c "from routers.painel import router"` | exit 0, "router import ok" | PASS |
| All 4 calc functions importable | `python3 -c "from routers.painel import calcular_bloco_a, calcular_bloco_b, calcular_bloco_c, calcular_bloco_d"` | exit 0, "all 4 functions ok" | PASS |
| `calcular_bloco_a` with null data | `calcular_bloco_a({"data_inicio": None, "data_fim_contratada": None}, [])` | `{"sem_dados": True}` | PASS |
| `calcular_bloco_a` with dates | `calcular_bloco_a({"data_inicio": "2026-01-01", "data_fim_contratada": "2026-12-31", ...}, [])` | `{"sem_dados": False, "pct_prazo_consumido": 64.0, ...}` | PASS |
| All functions safe with zero funcionalidades | `calcular_bloco_b/c/d([], [])` | Valid empty-data dicts, no exception | PASS |
| painel router registered | `grep -c "include_router(painel.router)" main.py` | 1 | PASS |
| Zero className in PainelTab | `grep -c "className=" PainelTab.tsx` | 0 | PASS |
| TypeScript build | `npx tsc --noEmit` | No output (exit 0) | PASS |
| PainelTab line count | `wc -l PainelTab.tsx` | 623 lines | PASS (> 150 threshold) |

### Anti-Patterns Found

No debt markers (TBD, FIXME, XXX) found in any phase-modified file. No stubs or placeholder returns detected. No hardcoded empty data that flows to rendered output — all rendering paths use data fetched from real Supabase queries.

---

## Human Verification Required

### 1. Bloco A — Sem dados de contrato placeholder and config link

**Test:** Open a project with no `data_inicio` / `data_fim_contratada` set. Click the Painel tab. Observe Bloco A.
**Expected:** Grey card titled "Tempo x Escopo" with gray text "Sem dados de contrato" and a green underlined button "Ir para Configurações". Clicking the button switches the active tab to Configurações without a page reload.
**Why human:** Visual rendering and tab switch navigation require live browser observation.

### 2. Bloco A — Three percentage bars and Desvio badge

**Test:** Open a project with `data_inicio`, `data_fim_contratada`, and `tolerancia_desvio_pontos` set such that `pct_prazo - pct_aprovado > tolerancia`. Click the Painel tab.
**Expected:** Three labeled metric rows with % values. An orange alert badge "⚠ Desvio de X pts acima da tolerância" appears below the metrics.
**Why human:** Visual layout of metric rows and badge styling require live browser observation.

### 3. Bloco B — Three sub-sections with real data

**Test:** Open a project with funcionalidades in `em_andamento` for >7 days, at least one with `status_cliente=enviado` for >5 business days, and at least one with `status=em_ajuste`.
**Expected:** Bloco B shows "Travadas" sub-section with the stalled items, "Aguardando cliente" with the waiting items (showing `dias_uteis` in yellow badge), and "Em ajuste" list.
**Why human:** Requires live Supabase data with real recorded timestamps and specific data conditions.

### 4. Bloco C — Null cycle time display with zero concluidas

**Test:** Open a project with zero funcionalidades in `concluida` status. Observe Bloco C.
**Expected:** WIP and throughput shown; the informational message "Nenhuma funcionalidade concluída — cycle time indisponível" appears in place of cycle time rows.
**Why human:** Conditional branch for `total_concluidas === 0` requires live data.

### 5. Bloco D accordion — expand/collapse interaction

**Test:** Open a project that has funcionalidades with recorded `transicoes_status` entries that include `duracao_fase_anterior_segundos`. Open the Painel tab. In Bloco D, click "▼ ver detalhe" on one of the phase rows.
**Expected:** The row expands to show a list of funcionalidade titles with their time in dias for that phase. The toggle shows "▲ fechar". Clicking again collapses the list. Only one row is expanded at a time.
**Why human:** State transition (expand → collapse) is behavior-dependent. The code is wired, but whether real `detalhe_por_funcionalidade` data is rendered requires a live session.

### 6. Kanban sprint dropdown default and reactivity

**Test:** Open the Painel tab on a project with multiple sprints (e.g., Sprint 1, Sprint 2, Sprint 3). Observe the Kanban sprint dropdown's default selected value. Change the selection.
**Expected:** Dropdown defaults to the highest sprint number (Sprint 3). Changing the selection immediately re-filters all three columns without reloading the page.
**Why human:** Initial state and reactive re-render require live browser observation.

### 7. Kanban — multi-sprint badge for funcionalidades with shared id_funcional

**Test:** Create or find a scenario where the same `id_funcional` appears with different `sprint_alvo` values across funcionalidades in a project. Open the Painel tab Kanban.
**Expected:** The KanbanCard for that funcionalidade shows multiple purple "Sprint X" chips, one per sprint where `id_funcional` appears.
**Why human:** D-08 multi-sprint grouping logic requires a specific data condition (duplicate `id_funcional` across different `sprint_alvo` values) that can only be observed with real data in the browser.

---

## Gaps Summary

No gaps found. All 15 must-haves are either VERIFIED (14) or PRESENT_BEHAVIOR_UNVERIFIED (1, Bloco D accordion). The implementation is complete and substantive:

- Backend `painel.py` is a 309-line file with all 4 calculation functions fully implemented (not stubs). Python import and unit tests pass.
- Frontend `PainelTab.tsx` is 623 lines with all 5 visual sub-components (BlocoACard, BlocoBCard, BlocoCCard, BlocoDCard, KanbanCard) fully implemented with zero className attributes.
- All key links are wired: backend router registered, frontend component fetches real data from the API, tab wiring is correct (2nd tab position, proper render guard), and the onNavigateToConfig callback chain is complete.
- Zero debt markers found across all phase-modified files.

The `human_needed` status reflects 7 UI/behavioral items that require live browser verification — visual rendering, tab navigation, real-data conditional branches, and the accordion expand/collapse interaction.

---

_Verified: 2026-08-23T01:43:41Z_
_Verifier: Claude (gsd-verifier)_
