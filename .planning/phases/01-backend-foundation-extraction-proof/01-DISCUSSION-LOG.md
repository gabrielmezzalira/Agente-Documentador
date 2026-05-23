# Phase 1: Backend Foundation + Extraction Proof - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 1-backend-foundation-extraction-proof
**Areas discussed:** Phase 1 file validation scope

---

## Phase 1 File Validation Scope

### Q1: What should POST /ingest do with non-TXT files?

| Option | Description | Selected |
|--------|-------------|----------|
| Reject with 422 | Return immediate error: `{"detail": "Unsupported file type. Accepted: text/plain"}`. Explicit boundary, easiest to test. | ✓ |
| Accept but skip processing | Return 200 with `{"status": "skipped", "reason": "unsupported type"}`. No row saved. | |
| Full routing table with 501 | Build all type branches now but return 501 for non-TXT. Future-proofs Phase 2. | |

**User's choice:** Reject with 422
**Notes:** Simplest, cleanest boundary for Phase 1.

---

### Q2: What should the 422 error response look like?

| Option | Description | Selected |
|--------|-------------|----------|
| Simple string detail | `{"detail": "Unsupported file type. Accepted: text/plain"}` — standard FastAPI format. | ✓ |
| Structured error object | `{"error": "unsupported_file_type", "received": "...", "accepted": [...]}` — machine-readable. | |
| You decide | Claude picks simplest format matching FastAPI conventions. | |

**User's choice:** Simple string detail
**Notes:** Consistent with FastAPI's standard 422 shape.

---

### Q3: Where should validation happen?

| Option | Description | Selected |
|--------|-------------|----------|
| Router-level validation | Check MIME type in the endpoint before calling the graph. Fails fast, easy to unit test. | ✓ |
| Inside detectar_tipo node | Graph node raises error state on unsupported type. Keeps type logic centralized but runs graph for nothing. | |
| You decide | Claude picks based on FastAPI best practices. | |

**User's choice:** Router-level validation
**Notes:** Fail fast — no graph overhead for invalid uploads.

---

## Claude's Discretion

- Ingest response schema on success (returned fields after successful extraction)
- Project CRUD response shape (`POST /projects`, `GET /projects`, `GET /projects/{id}`)
- Error handling for Gemini API failures and LangGraph node propagation
- LangGraph state error field handling

## Deferred Ideas

None — discussion stayed within phase scope.
