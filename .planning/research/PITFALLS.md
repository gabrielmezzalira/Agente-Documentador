# Pitfalls Research: DocuData

**Project:** DocuData — LangGraph + FastAPI + Gemini document processing
**Dimension:** Pitfalls
**Confidence:** MEDIUM-HIGH

---

## Critical Pitfalls

### 1. Sync `graph.invoke()` inside async FastAPI route blocks the event loop

**What goes wrong:** `graph.invoke()` is synchronous. Called inside `async def`, it freezes the entire uvicorn event loop for the duration of the LLM call (3–15s). Second upload hangs until the first completes.

**Detection:** Second request to `/ingest` hangs until the first completes.

**Prevention:** Use `await graph.ainvoke(state)` throughout both graphs. Declare all I/O-bound nodes as `async def`.

**Phase:** Both graph files — day 1, do it correctly from the start.

---

### 2. `JsonOutputParser` silently fails on Gemini markdown wrappers — retry never fixes the root cause

**What goes wrong:** Gemini 1.5 Flash frequently wraps JSON in markdown fences even when instructed not to. If retry uses the same prompt structure, it fails twice, `salvar` is never reached, and the ingestion is silently dropped (200 response, no Supabase row).

**Detection:** Endpoint returns 200 but no new row in `ingestions` table.

**Prevention:**
- Use `with_structured_output()` on `ChatGoogleGenerativeAI` — uses Gemini's native function-calling to guarantee valid JSON matching a Pydantic schema. Recommended approach in LangChain ≥ 0.2.
- Fallback: explicit strip before parsing: `raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()`
- Validate all 6 required keys using a Pydantic model, not just "is it valid JSON?"

**Phase:** `extraction_graph.py` — day 1. Use `with_structured_output()` from the start.

---

### 3. `pdf2image` requires system-level `poppler` — not installed on Railway by default

**What goes wrong:** `pip install pdf2image` succeeds but `convert_from_bytes()` raises `PDFInfoNotInstalledError` at runtime. Railway build logs are clean; scanned-PDF uploads fail with 500.

**Detection:** `pdfplumber` works locally; scanned PDF upload fails in production.

**Prevention:** Add `nixpacks.toml` at backend root:
```toml
[phases.setup]
nixPkgs = ["poppler_utils"]
```
Alternative: replace `pdf2image` with `PyMuPDF` (`fitz`) — compiled wheel, no external binary needed.

**Phase:** Before first Railway deploy (day 2). Check before demo.

---

### 4. LangGraph state replaces top-level keys — stale values bleed between retry attempts

**What goes wrong:** Keys not returned by a node are left unchanged. If `extrair_conteudo` fails to explicitly reset `conteudo_estruturado` to `None`, a prior value can persist into the retry cycle.

**Prevention:**
- Always initialize fresh state dict for each `graph.ainvoke()` call — never reuse state across requests.
- In `extrair_conteudo`, always return `{"conteudo_estruturado": None, "valido": False}` before routing to retry edge.

**Phase:** `extraction_graph.py` — day 1.

---

### 5. `supabase-py` v1 vs v2 breaking API — unpinned version causes silent insert failures

**What goes wrong:** Code written for v1 in an async context silently returns a coroutine object instead of executing the insert. Endpoint returns 200; nothing lands in Supabase.

**Detection:** Endpoint returns 200, Supabase dashboard shows no new rows.

**Prevention:** Pin version: `supabase==2.4.6`. Use async client:
```python
from supabase import acreate_client
supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
await supabase.table("ingestions").insert(data).execute()
```

**Phase:** `supabase_client.py` — step 2 in implementation. Pin before writing any graph node.

---

### 6. Gemini multimodal `image_url` format in `langchain-google-genai` differs from OpenAI convention

**What goes wrong:** OpenAI uses `{"type": "image_url", "image_url": {"url": "data:..."}}}` (nested dict). LangChain Google GenAI uses `{"type": "image_url", "image_url": "data:..."}` (flat string). Using the OpenAI format raises `ValidationError` at runtime — not caught during text-only testing.

**Detection:** Text uploads work; image uploads fail with `ValidationError` or `TypeError` in `extrair_conteudo`.

**Prevention:**
```python
content = [
    {"type": "text", "text": prompt_text},
    {"type": "image_url", "image_url": f"data:{mime_type};base64,{b64_data}"}
]
message = HumanMessage(content=content)
```
Test with an actual image on day 1.

**Phase:** `extraction_graph.py` node `extrair_conteudo` — day 1.

---

## Moderate Pitfalls

### 7. `ChatPromptTemplate` variable name mismatch between state and template

LangGraph state field `contexto` ≠ template `{context}` → `KeyError` or literal `{contexto}` in output.

**Prevention:** Consistent naming. Test all 4 `tipo_doc` variants before declaring generation graph done.

---

### 8. `UploadFile.read()` must be awaited in async routes

Missing `await` in `async def` route silently returns a coroutine object as `bytes`.

**Prevention:** `arquivo_bytes = await arquivo.read()` in `routers/ingest.py`.

---

### 9. Railway cold start causes first-request timeout at the frontend

Heavy dependencies (Pillow, pdfplumber, langchain) → 30–60s cold start. First request may exceed default fetch timeout.

**Prevention:**
- Add `/health` endpoint; ping on page load.
- Set 60s timeout on `/ingest` and `/generate` fetches: `fetch(url, { signal: AbortSignal.timeout(60000) })`.

---

### 10. `pdfplumber` 100-character threshold misclassifies short-text PDFs as scanned

Cover page with title + date = ~80 chars → misrouted to image processing.

**Prevention:** Lower threshold to 50 characters, or check chars-per-page < 20.

---

### 11. LangGraph graph compiled inside request handler instead of module level

`graph.compile()` on every request adds 50–100ms overhead.

**Prevention:** Compile at module load, import the compiled object in the router.

---

### 12. `POST /generate` for "documento completo" with many sprints may hit timeout

20,000+ tokens of context → 25–40s Gemini response, exceeding Railway default timeout.

**Prevention:** Cap context at most recent 10 sprints for `completo` type (MVP limit).

---

## Minor Pitfalls

### 13. DOCX files from macOS upload with `application/octet-stream` MIME type

**Prevention:** Extension-based fallback when `mime_type == "application/octet-stream"`:
```python
ext = arquivo_nome.rsplit(".", 1)[-1].lower()
mime_type = {"docx": "application/vnd.openxmlformats-...", ...}.get(ext, mime_type)
```

### 14. `react-markdown` silently drops tables without `remarkGfm`

**Prevention:** `remarkPlugins={[remarkGfm]}` on the `<ReactMarkdown>` component. Do not enable `rehypeRaw` (XSS risk).

---

## Scope Pitfalls (3-Day MVP Killers)

### 15. Spending day 1 perfecting prompt engineering instead of wiring the full pipeline

The extraction prompt is tangible and tempting to iterate. Three hours of prompt tuning later, there is no frontend.

**Prevention:** Build the vertical slice first — TXT file, one graph, one save, one generate, one frontend page. **"Done for day 1" = upload a `.txt`, see a row in Supabase, click generate, see markdown on screen.**

### 16. Building error handling before the happy path

Retry logic, scanned-PDF fallback, and MIME edge cases are secondary. Implementing them on day 1 means day 3 arrives and the happy path still has bugs.

**Prevention:** Day 1: assume well-formed JSON, text-based PDFs, valid DOCX. Day 2: add retry, fallbacks.

### 17. Testing with synthetic files instead of real manager files

A well-crafted `test.txt` extracts perfectly. A real kanban screenshot (low-res JPEG, Portuguese text) or a real DOCX with tracked changes will not.

**Prevention:** Get one real file from an actual manager on day 1. Use it throughout development.

---

## Phase-Specific Warnings Summary

| Phase / File | Pitfall | Fix |
|---|---|---|
| `extraction_graph.py` day 1 | Sync `invoke()` blocks event loop | `ainvoke` + `async def` nodes |
| `extraction_graph.py` day 1 | JsonOutputParser fails on Gemini fences | Use `with_structured_output()` |
| `extraction_graph.py` day 1 | MIME `octet-stream` for DOCX from Mac | Extension fallback in `detectar_tipo` |
| `extraction_graph.py` day 1 | Wrong `image_url` dict shape | Flat string format, test day 1 |
| `supabase_client.py` day 1 | Silent inserts from v1/v2 mismatch | Pin `supabase==2.4.6`, async client |
| `file_parser.py` day 1 | 100-char threshold misclassifies | Lower to 50 chars |
| Railway deploy day 2 | `poppler` missing | Add `nixpacks.toml` |
| `generation_graph.py` day 2 | Template variable name mismatch | Consistent naming, test all 4 types |
| `routers/ingest.py` day 2 | `UploadFile.read()` not awaited | `await arquivo.read()` |
| `main.py` + `lib/api.ts` | Railway cold start kills first request | `/health` ping, 60s fetch timeout |
| `projects/[id]/page.tsx` day 3 | Tables missing in react-markdown | Add `remarkGfm` |
| All days | Prompt engineering before pipeline | End-to-end TXT on day 1 |
| All days | Synthetic files miss real failures | Use a real manager file from day 1 |

---

## Key Takeaways

- **Most dangerous (silent):** Pitfalls 1, 5 — produce no exceptions but break core functionality.
- **Most likely to kill the demo:** Pitfall 3 (poppler on Railway) + Pitfalls 15–17 (scope sequencing).
- **Most subtle:** Pitfall 2 (retry that never changes strategy) + Pitfall 4 (stale state bleed).
- **Quick one-liners:** Pitfalls 10, 13, 14 — fix during implementation.
