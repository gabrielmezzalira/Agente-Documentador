# Phase 1: Backend Foundation + Extraction Proof - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

FastAPI backend that can receive a TXT file upload for a project/sprint and write a structured 6-field JSON row to Supabase — proving the extraction pipeline (LangGraph → Gemini 2.5 Flash → Supabase) works end to end. Also includes project CRUD endpoints (create, list, get by ID).

**Not in Phase 1:** DOCX, PDF, image processing; generation graph; frontend; Railway deploy.

</domain>

<decisions>
## Implementation Decisions

### File Validation in POST /ingest
- **D-01:** Phase 1 accepts ONLY `text/plain` (TXT files). Any other MIME type is rejected immediately with HTTP 422 and `{"detail": "Unsupported file type. Accepted: text/plain"}`.
- **D-02:** Validation happens at the **router level** — inside the `/ingest` FastAPI endpoint, before the LangGraph graph is invoked. The graph is not called for unsupported types.
- **D-03:** Error format follows FastAPI's standard `detail` string convention — no structured error object needed at this stage.

### Carried Forward from Project Init
- **D-04:** Use `Gemini 2.5 Flash` as the model — overrides the "1.5 Flash" in the design doc. Use `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`.
- **D-05:** Use `with_structured_output()` for JSON extraction — do NOT use `JsonOutputParser`. Avoids silent JSON drop.
- **D-06:** Use `await graph.ainvoke()` in async FastAPI endpoints — sync `invoke()` blocks the event loop.
- **D-07:** Pin `supabase==2.4.6` exactly in requirements.txt — silent v1/v2 API break risk.

### Claude's Discretion
- Other aspects of the API contract (ingest response schema, project CRUD response shape, error handling for Gemini failures, LangGraph node error propagation) are left to Claude to implement following FastAPI conventions and the design doc.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Design Document
- `CLAUDE.md` — Complete software design document: API spec (section 6), extraction graph nodes and edges (section 4), LangGraph state schema (section 4.1), Pydantic schemas, file parser logic, folder structure (section 8), dependency list (section 9), and critical implementation decisions (section 12).

### Planning Artifacts
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria (5 items), and requirements mapped to this phase: PROJ-01, PROJ-02, PROJ-03, INGS-01, INGS-02, EXTR-01, EXTR-02.
- `.planning/REQUIREMENTS.md` — Full requirement definitions for all Phase 1 requirements.
- `.planning/STATE.md` — Accumulated decisions from project init, including pinned library versions and critical pitfalls.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing code.

### Established Patterns
- None yet — Phase 1 establishes the patterns.

### Integration Points
- Phase 1 backend is the sole integration target for Phase 3 frontend. API contract defined in `CLAUDE.md §6` is the interface.

</code_context>

<specifics>
## Specific Ideas

- The extraction graph retry logic (up to 2 retries) is already specified in the design doc (section 4.2, `estruturar_output` node). `with_structured_output()` replaces the `JsonOutputParser` + retry pattern — the retry counter from the design doc may not be needed with structured output, but implement the state field to match the schema.
- `nixpacks.toml` with `poppler_utils` is required for Railway but not needed for Phase 1 (PDF processing is Phase 2). Include it anyway to avoid a Phase 2 deploy surprise.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Backend Foundation + Extraction Proof*
*Context gathered: 2026-05-22*
