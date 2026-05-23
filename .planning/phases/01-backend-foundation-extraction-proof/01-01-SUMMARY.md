---
phase: 01-backend-foundation-extraction-proof
plan: 01
subsystem: backend
tags: [fastapi, pydantic, supabase, config, schemas, crud]
requirements: [PROJ-01, PROJ-02, PROJ-03]
dependency_graph:
  requires: []
  provides: [models/schemas.py, services/supabase_client.py, routers/projects.py, main.py, supabase_schema.sql]
  affects: [plan-02-extraction-graph, plan-03-generation]
tech_stack:
  added:
    - fastapi>=0.100
    - uvicorn>=0.20
    - python-multipart>=0.0.7
    - supabase==2.4.6
    - pydantic>=2.9.0
    - python-dotenv>=1.0.0
    - langchain-google-genai==4.1.1 (pinned for async perf)
    - langgraph>=1.0,<2
    - langchain-core>=1.4.0,<2
    - langsmith>=0.7
    - python-docx==1.2.0, pdfplumber==0.11.9, pdf2image==1.17.0, Pillow==12.2.0 (Phase 2 prepwork)
  patterns:
    - load_dotenv() first in main.py before all imports (Pitfall 3 guard)
    - Lazy get_client() factory — reads env at call time, not import time
    - response.data guard after every Supabase .execute() (Pitfall 5 guard)
    - HTTPException with standard detail strings per FastAPI convention
key_files:
  created:
    - docudata-backend/main.py
    - docudata-backend/models/schemas.py
    - docudata-backend/services/supabase_client.py
    - docudata-backend/routers/projects.py
    - docudata-backend/requirements.txt
    - docudata-backend/nixpacks.toml
    - docudata-backend/.env.example
    - docudata-backend/.gitignore
    - docudata-backend/Procfile
    - docudata-backend/supabase_schema.sql
    - docudata-backend/models/__init__.py
    - docudata-backend/services/__init__.py
    - docudata-backend/routers/__init__.py
    - docudata-backend/graphs/__init__.py
    - docudata-backend/tests/test_schemas_and_client.py
    - docudata-backend/tests/__init__.py
  modified: []
decisions:
  - "supabase==2.4.6 pinned exactly — v1/v2 silent API break risk (D-07)"
  - "langchain-google-genai==4.1.1 pinned — 4.2.x has unresolved async slowdown 3-4x regression (issue #1600)"
  - "load_dotenv() as first two lines in main.py — prevents KeyError when extraction_graph imports ChatGoogleGenerativeAI at module level"
  - "Lazy get_client() reads env vars at call time — env may not be loaded at import time"
  - "nixpacks.toml added with poppler_utils for Phase 2 Railway deploy prep"
  - "GET /projects/{id} raises HTTPException 404 with detail='Project not found' for unknown UUID"
metrics:
  duration: "~4 minutes"
  completed_date: "2026-05-23T17:43:36Z"
  tasks_completed: 3
  tasks_total: 4
  files_created: 16
  files_modified: 0
---

# Phase 1 Plan 01: Backend Foundation Summary

**One-liner:** FastAPI backend skeleton with pinned deps (supabase==2.4.6, langchain-google-genai==4.1.1), 3-table Supabase schema SQL, Pydantic models including ConteudoEstruturado extraction schema, lazy Supabase client factory, and project CRUD router — app boots with load_dotenv-first ordering.

## What Was Built

Established the complete backend foundation for the DocuData walking skeleton:

1. **Config and environment:** `requirements.txt` with exact version pins, `nixpacks.toml` with poppler_utils (Phase 2 Railway prep), `.env.example`, `.gitignore`, `Procfile` for Railway deploy.

2. **Database schema:** `supabase_schema.sql` creates all 3 tables (`projects`, `ingestions`, `generated_docs`) with proper UUID PKs via `gen_random_uuid()` and FK cascade deletes on `project_id`.

3. **Pydantic schemas:** `models/schemas.py` defines `ConteudoEstruturado` (6-field extraction schema consumed by Plan 02's `with_structured_output()`), `ProjectCreate`, `ProjectResponse`, and `IngestResponse`.

4. **Supabase client:** `services/supabase_client.py` with lazy `get_client()` factory — reads env vars at call time, never at module import time.

5. **Project CRUD router:** `routers/projects.py` with `POST /projects` (201), `GET /projects`, `GET /projects/{id}` — each endpoint calls `get_client()` and guards `response.data` after `.execute()`.

6. **App entry point:** `main.py` with `load_dotenv()` as the first two lines, CORSMiddleware with `allow_origins=["*"]`, projects router registered, and `GET /health` returning `{"status": "ok"}`.

## Checkpoint Status

**Task 4 (human-verify) is the current stopping point.** The user must:
1. Create Supabase project and run `supabase_schema.sql`
2. Create `docudata-backend/.env` with real credentials
3. Install dependencies and boot the app
4. Smoke test project CRUD endpoints

See Task 4 checkpoint details below.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Config files, dependency pins, Supabase schema SQL | 5c3404b | requirements.txt, nixpacks.toml, supabase_schema.sql, Procfile, __init__.py files |
| 2 (TDD RED) | Failing tests for schemas/client/router | fee223c | tests/test_schemas_and_client.py |
| 2 (TDD GREEN) | Pydantic schemas, lazy Supabase client, project CRUD router | 011af4e | models/schemas.py, services/supabase_client.py, routers/projects.py |
| 3 | main.py entry point with load_dotenv-first and CORS | 85f2ea5 | main.py |

## TDD Gate Compliance

- RED gate commit: `fee223c` (test(01-01): add failing tests...)
- GREEN gate commit: `011af4e` (feat(01-01): implement Pydantic schemas...)
- 13 tests written, all passed after implementation.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- `pytest` and `supabase==2.4.6` were installed globally for local test execution (not a deviation — these are in requirements.txt and needed for the TDD cycle).
- One deprecation warning during tests: `gotrue` package deprecated in favor of `supabase_auth`. This is a supabase-py 2.4.6 internal dependency warning and does not affect functionality. It will be resolved when supabase is upgraded in a future phase.

## Known Stubs

None. No stub patterns found in created files. All endpoints contain real implementation logic.

## Threat Surface Scan

No new security-relevant surface beyond what is documented in the plan's threat model:
- `POST /projects` body validated by Pydantic v2 (T-01-01 mitigated)
- `.env` in `.gitignore` (T-01-02 mitigated)
- `response.data` guarded after every `.execute()` (T-01-05 mitigated)

## Success Criteria Status

- [x] ROADMAP Phase 1 success criteria #2 (POST /projects creates + returns UUID, GET /projects lists) — code complete, pending human Supabase setup
- [x] ROADMAP Phase 1 success criteria #3 (GET /projects/{id} returns by ID) — code complete, pending human Supabase setup
- [x] Requirements PROJ-01, PROJ-02, PROJ-03 satisfied in code
- [x] ConteudoEstruturado with exactly 6 fields ready for Plan 02's `with_structured_output()`
- [x] Supabase client and main.py wiring ready for Plan 02

## Self-Check: PASSED

- [x] `docudata-backend/main.py` exists
- [x] `docudata-backend/models/schemas.py` exists
- [x] `docudata-backend/services/supabase_client.py` exists
- [x] `docudata-backend/routers/projects.py` exists
- [x] `docudata-backend/supabase_schema.sql` exists
- [x] `docudata-backend/requirements.txt` contains `supabase==2.4.6`
- [x] `docudata-backend/nixpacks.toml` contains `poppler_utils`
- [x] Commits 5c3404b, fee223c, 011af4e, 85f2ea5 all exist
- [x] 13/13 tests pass
