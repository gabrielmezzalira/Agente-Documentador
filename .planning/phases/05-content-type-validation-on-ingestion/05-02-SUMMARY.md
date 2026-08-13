---
phase: 05-content-type-validation-on-ingestion
plan: "02"
subsystem: backend-routers
status: complete
tags:
  - fastapi
  - validation
  - langgraph
  - routers
dependency_graph:
  requires:
    - extraction_graph.validar_tipo_node
  provides:
    - ingest.force_field
    - ingest.validation_422
    - sprint_docs.force_field_all_endpoints
    - sprint_docs.validation_422_attachment_paths
  affects:
    - docudata-backend/routers/ingest.py
    - docudata-backend/routers/sprint_docs.py
tech_stack:
  added: []
  patterns:
    - "FastAPI Form(False) boolean field in multipart endpoint signature"
    - "Structured 422 detail dict (tipo_detectado, tipo_esperado, mensagem, pode_forcar)"
    - "Re-raise pattern for 422 in broad HTTPException catch blocks"
key_files:
  created: []
  modified:
    - docudata-backend/routers/ingest.py
    - docudata-backend/routers/sprint_docs.py
decisions:
  - "tipo_esperado='upload_livre' hardcoded in /ingest — only nao_relacionado is blocked per D-08"
  - "tipo_esperado is always router-controlled (hardcoded per endpoint), never user-supplied (T-05-07 mitigation)"
  - "_extract_anexo_to_content project param defaults to None with internal _project fallback for backward safety"
  - "submit_review and submit_retrospectiva re-raise 422 but continue non-fatal on 502 — preserves existing behavior for extraction failures"
metrics:
  duration_minutes: 10
  completed_date: "2026-08-13"
  tasks_completed: 2
  commits: 2
estimate:
  tokens: 60000
actuals:
  tokens: 14500
  tasks: 2
  commits: 2
requirements:
  - VAL-03
---

# Phase 05 Plan 02: Router Wiring — Summary

Wired the new `validar_tipo` graph node into both ingestion routers: `/ingest` now accepts `force` and passes full project context + `tipo_esperado="upload_livre"` to the graph; all sprint-doc endpoints with optional or mandatory attachments propagate `tipo_esperado`, `force`, and project context through `_extract_anexo_to_content`. Validation failures return HTTP 422 with a structured JSON detail dict instead of being swallowed or surfaced as 502.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update ingest.py — accept force, pass project context and tipo_esperado to graph | da0f8ab | docudata-backend/routers/ingest.py |
| 2 | Update sprint_docs.py — pass tipo_esperado + force + project context for attachment paths | 4c25cfe | docudata-backend/routers/sprint_docs.py |

## What Was Built

### Task 1 — ingest.py

Modified `POST /ingest` endpoint:

- Added `force: bool = Form(False)` to function signature (after `projeto_id`)
- Changed project select from `"gemini_api_key"` to `"gemini_api_key, name, client, description"`
- Extracted `projeto_nome`, `cliente`, `projeto_descricao` from project row
- Added to `ExtractionState` dict: `tipo_esperado="upload_livre"`, `force`, `projeto_nome`, `cliente`, `projeto_descricao`, `tipo_detectado=""`, `mensagem_validacao=""`, `valido_tipo=False`
- Added validation 422 check BEFORE existing 502 check: when `result.get("valido_tipo") is False and not result.get("valido")`, raises `HTTPException(status_code=422, detail={"tipo_detectado": ..., "tipo_esperado": "upload_livre", "mensagem": ..., "pode_forcar": True})`

### Task 2 — sprint_docs.py

Updated `_extract_anexo_to_content` helper:

- Added `tipo_esperado: str = "upload_livre"`, `force: bool = False`, `project: dict = None` parameters
- Added all 7 validation fields to the `ExtractionState` dict inside the helper
- Added validation 422 check (structured dict) before existing 502 check
- Returns structured 422 detail with `tipo_detectado`, `tipo_esperado`, `mensagem`, `pode_forcar: True`

Updated 5 endpoint signatures — added `force: bool = Form(False)` to:
- `submit_planning` + call site: `tipo_esperado="planning"`
- `submit_daily` + call site: `tipo_esperado="daily"`
- `submit_review` + call site: `tipo_esperado="review"`
- `submit_retrospectiva` + call site: `tipo_esperado="retrospectiva"`
- `submit_ata_with_upload` — inline state with `tipo_esperado="ata_reuniao"` + its own validation 422 check

Fixed exception propagation in `submit_review` and `submit_retrospectiva`: changed broad `except HTTPException as exc: print(...)` to re-raise when `exc.status_code == 422`; 502 extraction failures remain non-fatal (continue without attachment content).

## Verification Results

Task 1 (`ingest.py`):
- AST parse: OK
- Assertions: `force`, `tipo_esperado`, `projeto_nome`, `pode_forcar`, `valido_tipo`, `"upload_livre"` all present

Task 2 (`sprint_docs.py`):
- AST parse: OK
- Assertions: `tipo_esperado`, `pode_forcar`, `valido_tipo`, `"planning"`, `"ata_reuniao"`, `"review"`, `"retrospectiva"`, `"daily"` all present
- Import check: `from routers.sprint_docs import router` exits 0

## Deviations from Plan

None — plan executed exactly as written. The `project: dict = None` default in `_extract_anexo_to_content` (with internal `_project = project or {}` guard) was added for defensive safety when the caller passes `None`; this does not change any callable behavior since all updated call sites now pass the real project dict.

## Threat Model Coverage

| Threat ID | Mitigation | Implemented |
|-----------|------------|-------------|
| T-05-05 | force=True override accepted — logged via _meta_force_override in Plan 01 | Yes — force param wired through to graph state |
| T-05-06 | 422 detail exposes tipo_detectado (document category label only — no PII) | Accepted — reviewed and confirmed |
| T-05-07 | tipo_esperado is hardcoded per endpoint, never user-supplied | Yes — all tipo_esperado values are string literals in router code |

## Known Stubs

None. All validation fields are fully wired end-to-end:
- `/ingest`: force + project context → graph → 422 response on mismatch
- `/sprint-docs/planning`, `/daily`, `/review`, `/retrospectiva`, `/ata`: same path via `_extract_anexo_to_content` or inline state (ata)

Form-only paths (planning/daily/review/retrospectiva without attachment) do not invoke the extraction graph — no validation call, consistent with D-02.

## Self-Check: PASSED

- docudata-backend/routers/ingest.py: FOUND (modified)
- docudata-backend/routers/sprint_docs.py: FOUND (modified)
- Commit da0f8ab (Task 1): FOUND
- Commit 4c25cfe (Task 2): FOUND
