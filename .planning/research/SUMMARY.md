# Research Summary: DocuData

**Synthesized from:** STACK.md · FEATURES.md · ARCHITECTURE.md · PITFALLS.md
**Date:** 2026-05-22

---

## Executive Summary

DocuData solves a documentation debt problem specific to data project managers at CITi: structured knowledge accumulates in people's heads and disappears at project end. The real competition is "just paste into ChatGPT" — the defensible gap is the structured 6-field extraction schema, sprint attribution, cross-sprint context accumulation, and four first-class document types. The `decisoes` document type is the highest-value differentiator: no mainstream tool treats technical decision logs as first-class institutional knowledge.

The riskiest component is the extraction graph — combines multimodal LLM calls, JSON parsing reliability, and a system-level binary dependency (`poppler`) that must be declared before the first Railway deploy. The generation graph is simpler: no multimodal, no retry. A 3-day MVP is achievable if build order is respected and scope is held.

The most dangerous failure modes are **silent** — sync `invoke()` blocking the event loop and supabase-py v1/v2 mismatches both return HTTP 200 with no rows written to the database.

---

## 1. Recommended Stack

| Layer | Package | Notes |
|-------|---------|-------|
| Backend | `fastapi>=0.111,<0.113` + `uvicorn[standard]>=0.29` | Async I/O required for `ainvoke()` |
| File upload | `python-multipart>=0.0.9` | Required explicitly; without it, UploadFile returns 422 |
| Validation | `pydantic>=2.6,<3` | Use `model_config = ConfigDict(...)`, NOT `class Config` |
| LangGraph | `langgraph>=0.2,<0.3` | Compile once at module level |
| LangChain | `langchain>=0.2,<0.3` + `langchain-core>=0.2,<0.3` | Do NOT use `LLMChain` (deprecated in 0.1, broken in 0.3) |
| Gemini | `langchain-google-genai>=1.0,<2` | Flat `image_url` string, NOT nested dict like OpenAI |
| Database | `supabase==2.4.6` **(pin exactly)** | v1/v2 breaking change; unpinned silently breaks inserts |
| DOCX | `python-docx>=1.1` | |
| PDF text | `pdfplumber>=0.11` | Text-layer PDFs |
| PDF image | `pdf2image>=1.17` | Requires `poppler-utils` via `nixpacks.toml` on Railway |
| Images | `Pillow>=10.3` | |
| Frontend | `next@^14.2.0` + `react@^18.3.0` | |
| Markdown | `react-markdown@^9.0.0` + `remark-gfm@^4.0.0` | `remarkGfm` required for tables |

---

## 2. Table Stakes Features

- Create project (name, client, description)
- Upload file with sprint number + explicit success/error feedback
- Extract 6-field JSON via Gemini — entire generation pipeline depends on this schema
- Ingestion history grouped by sprint
- Generate all 4 document types (sprint_status, sprint_retro, decisoes, completo)
- Markdown rendering with `react-markdown` + `remarkGfm`
- Copy generated document to clipboard (primary exit ramp)
- Handle DOCX, PDF (text + scanned), TXT, PNG, JPG/WEBP
- Error feedback when extraction fails

---

## 3. Key Differentiators

- **Structured 6-field schema** — ChatGPT gives prose; DocuData gives queryable fields that compose into richer docs over time
- **Sprint attribution** — "generate retro for Sprint 3" with zero copy-paste
- **Context accumulation** — more uploads = richer generated output; progressive improvement
- **Multimodal ingestion** — kanban screenshots + scanned PDFs; no mainstream tool does this for project docs
- **`decisoes` doc type** — first-class technical decision log, highest value for handoffs
- **Standardized format** — enforced across all PMs without requiring anyone to learn a new tool

---

## 4. Top Pitfalls to Avoid

| # | Pitfall | Prevention (one line) |
|---|---------|----------------------|
| 1 | Sync `invoke()` blocks event loop — second request hangs until first completes | `await graph.ainvoke(state)` everywhere; all I/O nodes as `async def` |
| 2 | `JsonOutputParser` drops ingestions when Gemini wraps JSON in markdown fences (HTTP 200, no DB row) | Use `with_structured_output()` on `ChatGoogleGenerativeAI` |
| 3 | `pdf2image` requires `poppler-utils` — not on Railway by default; scanned PDF uploads 500 in prod | Add `nixpacks.toml` with `nixPkgs = ["poppler_utils"]` before first deploy |
| 4 | supabase-py v1/v2 breaking API — silent HTTP 200, no rows written | Pin `supabase==2.4.6`; use async client |
| 5 | `langchain-google-genai` `image_url` is flat string, not nested dict — `ValidationError` only on image uploads | `{"type": "image_url", "image_url": f"data:{mime};base64,{b64}"}` |

**Scope pitfall:** Spend day 1 prompt-tuning instead of wiring the pipeline. **Target for day 1: upload a `.txt`, see a Supabase row, click generate, see markdown on screen.**

---

## 5. Architecture Decisions

- Compile LangGraph graphs once at module level — never inside request handlers
- Singleton Supabase client via `get_supabase()` with module-level `_client`
- `async def` for `/ingest` and `/generate` endpoints; sync OK for `/projects` and `/ingestions`
- `base64_image:` prefix is the internal contract between `preprocessar_arquivo` and `extrair_conteudo`
- All DB calls in graph nodes or `supabase_client.py` — routers own only HTTP boundary
- MIME type fallback: DOCX from macOS uploads as `application/octet-stream` → extension-based detection
- Cap `completo` context at 10 sprints — 20k+ tokens causes 25–40s response, exceeds Railway timeout
- `/health` endpoint + 60s fetch timeout on frontend — Railway cold start is 30–60s

---

## 6. Build Order (3-Day MVP)

```
Day 1 — Backend foundation + extraction pipeline
  1. schemas.py               — Pydantic contracts, no deps
  2. supabase_client.py       — singleton client, only needs .env
  3. file_parser.py           — DOCX/PDF/TXT/image parsing
  4. extraction_graph.py      — 5 nodes, retry edge
  5. routers/ingest.py        — HTTP boundary
  6. main.py (partial)        — ingest router + CORS
  TARGET: .txt upload → Supabase row visible

Day 2 — Generation pipeline + Railway deploy
  7. generation_graph.py      — 5 nodes, 4 doc types (parallel with step 4)
  8. routers/generate.py      — HTTP boundary
  9. routers/projects.py      — project CRUD
  10. main.py (complete)      — all routers
  11. nixpacks.toml           — poppler-utils BEFORE Railway deploy
  TARGET: all 4 doc types working; backend on Railway

Day 3 — Frontend
  12. lib/api.ts              — all fetch functions
  13. page.tsx                — project list
  14. projects/new/page.tsx   — creation form
  15. projects/[id]/page.tsx  — upload, history, generate, render, copy
  16. End-to-end test with real manager files
  TARGET: demo-ready on Vercel
```

Steps 4 and 7 are independent and can be parallelized.

---

## 7. Open Questions

- **Gemini base64 size limit:** Inline base64 cap ~20MB. Large scanned PDFs may exceed — mitigation: Gemini Files API for files >4MB (post-MVP).
- **Real file quality:** Extraction prompt quality unknown until tested against actual manager files (low-res kanban JPEGs, DOCX with tracked changes). Get one real file on day 1.
- **PDF scanned threshold:** 100-character threshold misclassifies short-text PDFs (cover pages ~80 chars). Lower to 50 chars.
- **LangGraph version:** Verify current PyPI `langgraph` version before writing graph files — 0.3 may have changed `StateGraph` builder API.
- **CORS restriction:** `allow_origins=["*"]` acceptable for MVP; restrict to Vercel URL before sharing if project data is sensitive.
- **Output integration target:** Does the team use Notion/Confluence/Google Docs? Informs whether clipboard is sufficient for v2.
