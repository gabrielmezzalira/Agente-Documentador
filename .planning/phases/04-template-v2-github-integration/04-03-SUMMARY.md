---
phase: "04"
plan: "03"
subsystem: "backend/services"
tags: ["google-docs", "export", "supabase", "placeholders", "citi-v2"]
dependency_graph:
  requires: ["04-01", "04-02"]
  provides: ["export-gdocs-campos-planning", "export-gdocs-campos-review"]
  affects: ["docudata-backend/services/google_docs.py", "docudata-backend/routers/export.py"]
tech_stack:
  added: []
  patterns: ["supabase lazy query inside service function", "fallback to em-dash on missing data"]
key_files:
  created: []
  modified:
    - "docudata-backend/services/google_docs.py"
    - "docudata-backend/routers/export.py"
decisions:
  - "Fetched campos_planning and campos_review directly inside export_to_gdocs() rather than passing them as parameters — avoids breaking every caller and keeps Supabase logic co-located with template rendering"
  - "Used '—' (em-dash) as fallback when Supabase returns no matching ingestion, so templates never show literal '[A definir]' or empty strings"
  - "_cp() helper accepts explicit source dict instead of closing over a single dict — allows using it for both campos_planning and campos_review without duplication"
metrics:
  duration: "~12 minutes"
  completed_date: "2026-07-28"
  tasks_completed: 4
  tasks_total: 5
  files_modified: 2
---

# Phase 04 Plan 03: Export Google Docs com placeholders CITi v2 Summary

**One-liner:** Wired all CITi v2 structured fields (SQUAD, PERIODO, HORAS, PERCEPCAO_CLIENTE, etc.) from Supabase into Google Docs export by fixing 3 wrong placeholder names and adding real Supabase queries inside `export_to_gdocs()`.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Fixed 3 wrong placeholder names in `_SECTION_PLACEHOLDERS` | 24c9adc |
| 2 | Added `project_id` as first param to `export_to_gdocs()`, updated `export.py` | 8da7805 |
| 3 | Fetched `campos_planning` from Supabase, filled SQUAD/PERIODO/HORAS/DEPENDENCIAS/CARRY_OVER | f4ae9fa |
| 4 | Fetched `campos_review` from Supabase, filled PERCEPCAO_CLIENTE/SINAL_SATISFACAO/PEDIDOS_FORA_ESCOPO | a841ea7 |
| 5 | checkpoint:human-verify — awaiting manual export verification | — |

## What Was Built

### Task 1 — Placeholder name fixes (`_SECTION_PLACEHOLDERS`)

Three keys in the `"review"` and `"retrospectiva"` mappings had wrong placeholder names that would never match the actual CITi v2 template:

- `"o que foi planejado": "PLANEJADO"` → `"PLANEJADO_ENTREGUE"`
- `"causa raiz": "CAUSA_RAIZ"` → `"CAUSA_RAIZ_IMPACTO"`
- `"pedido fora de escopo": "PEDIDO_FORA_ESCOPO"` → `"PEDIDO_FORA_ESCOPO_STATUS"`

### Task 2 — `project_id` parameter + `get_client` import

`export_to_gdocs()` now receives `project_id: str` as its first positional argument. `get_client` imported from `services.supabase_client`. `export.py` updated to pass `project_id=doc["project_id"]`.

### Task 3 — `campos_planning` Supabase fetch

When `doc_type == "planning"` and `sprint_numero` is not None, queries:

```
ingestions WHERE project_id=? AND sprint_number=? AND tipo_documentacao='planning'
ORDER BY created_at DESC LIMIT 1
```

Extracts `extracted_content.campos_planning` and maps keys to template placeholders:
- `squad` → `SQUAD`
- `periodo_inicio` + `periodo_fim` → `PERIODO` (joined as "X a Y")
- `horas_disponiveis` → `HORAS_REAIS`
- `horas_estimadas` → `HORAS_ESTIMADAS`
- `dependencias_cliente` → `DEPENDENCIAS_CLIENTE`
- `carry_over` → `CARRY_OVER`

### Task 4 — `campos_review` Supabase fetch

When `doc_type == "review"` and `sprint_numero` is not None, queries:

```
ingestions WHERE project_id=? AND sprint_number=? AND tipo_documentacao='review'
ORDER BY created_at DESC LIMIT 1
```

Extracts `extracted_content.campos_review`:
- `percepcao_cliente` → `PERCEPCAO_CLIENTE`
- `sinal_satisfacao` → `SINAL_SATISFACAO`
- `pedidos_fora_escopo` → `PEDIDOS_FORA_ESCOPO`

Note: `PLANEJADO_ENTREGUE` and `ITENS_PROXIMA_SPRINT` are populated by `_extract_section_replacements()` via markdown parsing — NOT duplicated here.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one small refactor applied automatically:

**[Rule 2 - Improvement] `_cp()` helper signature**
- **Found during:** Task 4 (when needing to call `_cp()` for both `campos_planning` and `campos_review`)
- **Issue:** Original plan implied `_cp(key)` closing over `campos_planning`. After Task 4 introduced a second source dict, a single-source closure would require duplicating the helper or using `campos_review` instead.
- **Fix:** Made `_cp(source: dict, key: str)` explicit. Both planning and review fields use the same helper — no duplication.
- **Files modified:** `docudata-backend/services/google_docs.py`
- **Commit:** f4ae9fa (refactor included in Task 3 commit) + a841ea7

## Known Stubs

None. All placeholders that had hardcoded `"[A definir]"` values now receive real data from Supabase or gracefully fall back to `"—"`. The `"—"` fallback is intentional and visible to the user, not a hidden stub.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes introduced. Supabase queries use read-only `.select()` with the existing service-role key pattern already established in the codebase.

## Self-Check: PASSED

- `docudata-backend/services/google_docs.py` — modified (verified content above)
- `docudata-backend/routers/export.py` — modified (verified content above)
- Commits 24c9adc, 8da7805, f4ae9fa, a841ea7 all exist in git log
