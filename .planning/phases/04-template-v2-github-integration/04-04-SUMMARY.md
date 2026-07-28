---
phase: 04-template-v2-github-integration
plan: "04-04"
subsystem: backend + github-integration
tags: [github-actions, commit-ingestion, fastapi, python, stdlib]
dependency_graph:
  requires: [04-01-PLAN.md]
  provides: [GET /projects/{id}/current-sprint, POST /ingest/commit, hooks/docudata_agent.py, hooks/docudata.yml]
  affects: [docudata-backend/routers/commit_ingest.py, docudata-backend/main.py]
tech_stack:
  added: [GitHub Actions, urllib.request (stdlib HTTP)]
  patterns: [stdlib-only Python agent, GitHub Commit Status API, sprint detection via planning ingestion]
key_files:
  created:
    - docudata-backend/routers/commit_ingest.py
    - docudata-backend/hooks/docudata_agent.py
    - docudata-backend/hooks/docudata.yml
  modified:
    - docudata-backend/main.py
decisions:
  - "stdlib-only for docudata_agent.py — keeps GitHub Actions runner lightweight with zero pip install"
  - "sprint detection via última ingestion de tipo planning — matches DocuData's source of truth"
  - "diff truncated at 8000 chars in agent to avoid Gemini context overflow"
  - "POST /ingest/commit returns 201 so agent can distinguish success from failure for Commit Status"
metrics:
  duration: "~10 minutes"
  completed_date: "2026-07-28"
  tasks_completed: 3
  tasks_total: 4
  files_created: 3
  files_modified: 1
---

# Phase 04 Plan 04: GitHub Integration — SUMMARY

**One-liner:** GET /current-sprint + POST /ingest/commit + stdlib-only Python agent + GitHub Actions workflow for automatic commit documentation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Adicionar GET /current-sprint e CommitPayload.diff em commit_ingest.py | 68894ef | commit_ingest.py (created), main.py |
| 2 | Criar docudata_agent.py — stdlib-only GitHub Actions agent | 593f069 | hooks/docudata_agent.py (created) |
| 3 | Criar docudata.yml — GitHub Actions workflow | 899304f | hooks/docudata.yml (created) |

## What Was Built

### commit_ingest.py (new router)

- `GET /projects/{project_id}/current-sprint`: queries ingestions table for the latest `tipo_documentacao='planning'` record and returns `{"sprint_number": N, "started_at": "..."}`. Returns `{"sprint_number": 1, "started_at": null}` when no planning exists. 404 for unknown project.
- `CommitPayload` model: `project_id`, `sprint_number`, `commit_hash`, `commit_message`, `author`, `date`, `diff_stat`, `diff: Optional[str] = None`
- `POST /ingest/commit`: validates project + api_key, ensures sprint row, calls Gemini 2.5 Flash with structured output (`ConteudoEstruturado`), saves to `ingestions` with `tipo_documentacao='commit'`, returns 201 with ingestion_id.

### main.py (modified)

- Added `commit_ingest` to import line and `app.include_router(commit_ingest.router)`

### hooks/docudata_agent.py (new)

Stdlib-only Python script (no pip install needed):
1. Reads `DOCUDATA_API_URL`, `DOCUDATA_PROJECT_ID`, `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_SHA` from env
2. Calls `GET /projects/{PROJECT_ID}/current-sprint` to detect sprint automatically
3. Checks for `[sprint:N]` override in commit message via regex
4. Collects `git log` metadata + `git show HEAD --unified=3` diff (truncated at 8000 chars)
5. POSTs payload to `POST /ingest/commit`
6. Writes GitHub Commit Status (`success`/`failure`) with description `"DocuData — Sprint N"`

### hooks/docudata.yml (new)

GitHub Actions workflow to be copied to `.github/workflows/` in the project repo:
- Triggers on `push` with `branches: ['**']` (all branches)
- `permissions: statuses: write`
- `actions/checkout@v4` with `fetch-depth: 2`
- Passes `DOCUDATA_API_URL`, `DOCUDATA_PROJECT_ID`, `GITHUB_TOKEN` as env vars
- Installation comment with 4-step instructions + 2 required Secrets documented

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The endpoint calls real Gemini API and saves to real Supabase.

## Task 4 — Checkpoint (Pending)

Task 4 is a `checkpoint:human-verify` requiring manual installation and testing in a real GitHub repository. This task is NOT complete — awaiting human verification.

## Self-Check

- [x] `docudata-backend/routers/commit_ingest.py` — created
- [x] `docudata-backend/hooks/docudata_agent.py` — created
- [x] `docudata-backend/hooks/docudata.yml` — created
- [x] `docudata-backend/main.py` — router registered
- [x] Commits: 68894ef, 593f069, 899304f

## Self-Check: PASSED
