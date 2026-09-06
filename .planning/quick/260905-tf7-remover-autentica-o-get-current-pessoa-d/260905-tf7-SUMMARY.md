---
phase: commit-ingest-router-auth-revert
plan: 01
subsystem: api
tags: [fastapi, auth, ci-cd, github-actions]

requires: []
provides:
  - "commit_ingest.router registered without auth dependency — restores anonymous access to POST /ingest/commit and GET /projects/{project_id}/current-sprint"
affects: [docudata-sync.yml, commit_ingest]

actuals:
  tokens: 30
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - docudata-backend/main.py

key-decisions:
  - "Reverted only commit_ingest.router's auth gate; all other 20 router registrations from Phase 16's global enforcement rollout remain untouched, per explicit scope in the plan's threat model (T-quick-01, T-quick-02 both accepted as intentional pre-Phase-16 risk reintroduction)."

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "commit_ingest.router registered with no dependencies kwarg in main.py, restoring anonymous access for CI sync calls"
    verification:
      - kind: other
        ref: "grep -c -F 'app.include_router(commit_ingest.router)' docudata-backend/main.py -> 1; grep -c -F 'app.include_router(commit_ingest.router, dependencies=' docudata-backend/main.py -> 0"
        status: pass
      - kind: other
        ref: "grep -c -F 'Depends(get_current_pessoa)' docudata-backend/main.py -> 17 (was 18)"
        status: pass
      - kind: other
        ref: "python3 -c \"import ast; ast.parse(open('main.py').read())\" from docudata-backend/"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-09-06
status: complete
---

# Quick Task 260905-tf7: Remove auth gate from commit_ingest.router Summary

**Dropped `dependencies=[Depends(get_current_pessoa)]` from `commit_ingest.router`'s registration in `main.py`, restoring anonymous access for the CI sync pipeline.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-09-06T00:14:00Z
- **Completed:** 2026-09-06T00:14:44Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- `commit_ingest.router` is now registered as `app.include_router(commit_ingest.router)` — no auth dependency — undoing an unintended side effect of commit 88b13d8's global auth rollout (Phase 16) that broke the anonymous `docudata-sync.yml` CI workflow with HTTP 401 errors.
- All other 20 router registrations in `main.py` remain unchanged (17 occurrences of `Depends(get_current_pessoa)`, down from 18 — exactly the one removed; `require_not_operacional`-gated routers untouched).

## Task Commits

Each task was committed atomically:

1. **Task 1: Drop the auth dependency from commit_ingest.router's registration** - `a99631a` (fix)

_Note: Docs/state artifacts (SUMMARY.md, STATE.md) are committed separately by the orchestrator, not part of the task commits above._

## Files Created/Modified
- `docudata-backend/main.py` - `commit_ingest.router` registration line changed from `app.include_router(commit_ingest.router, dependencies=[Depends(get_current_pessoa)])` to `app.include_router(commit_ingest.router)` (single-line diff)

## Decisions Made
- None beyond the plan's explicit scope — reverted exactly one line, matching the plan's `must_haves.artifacts` spec of a bare `app.include_router(commit_ingest.router)` call with all 20 other registrations byte-for-byte unchanged.

## Deviations from Plan

None - plan executed exactly as written. Single-line diff, all four automated verification checks passed on first attempt.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required. This fix should immediately unblock the next `docudata-sync.yml` CI run against the deployed backend once this change is deployed to Railway.

## Next Phase Readiness
- CI sync pipeline (`docudata-sync.yml`) should now succeed against `POST /ingest/commit` and `GET /projects/{project_id}/current-sprint` once this change reaches the Railway deployment.
- No blockers. This was an isolated one-line revert with no follow-on work implied.

---
*Phase: commit-ingest-router-auth-revert*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: docudata-backend/main.py
- FOUND: a99631a (task commit)
- FOUND: .planning/quick/260905-tf7-remover-autentica-o-get-current-pessoa-d/260905-tf7-SUMMARY.md
