# Stack Research: DocuData

**Project:** DocuData — Automated Data Project Documentation Agent
**Dimension:** Stack
**Confidence:** MEDIUM-HIGH (training knowledge Aug 2025)

---

## Key Findings

- LangGraph `StateGraph` API is stable since 0.1.x. Correct pattern: `TypedDict` state + node functions returning partial dicts + `add_conditional_edges` for retry. `compile()` once at module level, `invoke()` per request.
- `langchain-google-genai` `ChatGoogleGenerativeAI` supports multimodal via `HumanMessage` with `image_url` content type using `data:{mime};base64,{str}` inline URLs.
- `supabase-py` v2 sync API handles `dict` → `jsonb` serialization automatically. Use `service_role` key on backend.
- FastAPI requires `python-multipart` installed explicitly; without it, `UploadFile` routes fail with 422.
- `pdf2image` requires `poppler-utils` system package on Railway — **not installed by default**. Add `nixpacks.toml`.
- LangChain, FastAPI, and supabase-py have all made breaking API changes in the last 2 years.

---

## Recommended Stack (prescriptive)

### Backend
```
fastapi>=0.111,<0.113
uvicorn[standard]>=0.29
python-multipart>=0.0.9
pydantic>=2.6,<3
langchain>=0.2,<0.3
langchain-core>=0.2,<0.3
langgraph>=0.2,<0.3
langchain-google-genai>=1.0,<2
supabase>=2.4,<3
python-docx>=1.1
pdfplumber>=0.11
pdf2image>=1.17
Pillow>=10.3
python-dotenv>=1.0
httpx>=0.27
```

### Frontend
```
next: ^14.2.0
react: ^18.3.0
react-markdown: ^9.0.0
remark-gfm: ^4.0.0
```

---

## LangGraph StateGraph Pattern

```python
# Define state
class ExtractionState(TypedDict):
    arquivo_bytes: bytes
    arquivo_nome: str
    mime_type: str
    sprint_numero: int
    projeto_id: str
    tipo: str
    texto_preprocessado: str
    conteudo_estruturado: dict
    valido: bool
    tentativas: int
    erro: str

# Compile once at module level (NOT inside a request handler)
builder = StateGraph(ExtractionState)
builder.add_node("detectar_tipo", detectar_tipo)
# ... add nodes ...
builder.add_conditional_edges("estruturar_output", decide_retry, {
    "salvar": "salvar",
    "extrair_conteudo": "extrair_conteudo",
})
graph = builder.compile()
```

**Invoke from FastAPI async route:**
```python
import asyncio
result = await asyncio.to_thread(graph.invoke, initial_state)
```

---

## Gemini Multimodal Pattern

```python
# Image / scanned PDF path
HumanMessage(content=[
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_str}"}},
    {"type": "text", "text": extraction_prompt}
])

# Text path
HumanMessage(content=extraction_prompt + text_content)
```

Flag `texto_preprocessado` with `base64_image:` prefix to signal vision path in `extrair_conteudo` node.

---

## Railway Deployment

**`nixpacks.toml`** (required for pdf2image):
```toml
[phases.setup]
aptPkgs = ["poppler-utils"]
```

**`Procfile`:**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Critical "What NOT To Do"

1. **Do not use `LLMChain`** — deprecated in LangChain v0.1, breaks in v0.3. Use LCEL or LangGraph nodes.
2. **Do not call `graph.compile()` inside a request handler** — compile once at module level.
3. **Do not use `anon` Supabase key on backend** — use `service_role` key to bypass RLS.
4. **Do not use Pydantic v1 `class Config` syntax** — FastAPI v0.111+ uses Pydantic v2; use `model_config = ConfigDict(...)`.
5. **Do not deploy `pdf2image` without `nixpacks.toml`** — poppler-utils not included by default on Railway.
6. **Do not hardcode port 8000 in Procfile** — Railway injects `$PORT`.

---

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| LangGraph StateGraph API | HIGH | Stable API, well-documented |
| langchain-google-genai multimodal | MEDIUM | Verify exact HumanMessage dict structure against current PyPI |
| supabase-py v2 sync API | HIGH | Stable, canonical API |
| FastAPI file upload | HIGH | Unchanged since FastAPI 0.95+ |
| Library versions | MEDIUM | Accurate Aug 2025; verify before pinning |
| Railway + poppler | MEDIUM | nixpacks.toml approach documented; verify current Railway defaults |

---

## Roadmap Implications

- **Phase 1:** `schemas.py` + `supabase_client.py` + `file_parser.py` can be built in parallel — no LangGraph dependency.
- **Phase 2:** `extraction_graph.py` is highest risk — depends on pdf2image + poppler on Railway, Gemini multimodal, JSON retry. Build and test locally before Railway deploy.
- **Phase 3:** `generation_graph.py` simpler — no multimodal, no retry. Depends on Phase 1 being stable.
- **Phase 4:** Routers + frontend — mechanical wiring after Phase 3.

---

## Open Questions

1. Gemini 1.5 Flash inline base64 has 20MB limit. Large scanned PDFs may exceed it — mitigation: use Gemini Files API for files >4MB (different code path).
2. LangGraph 0.3 may have changed `StateGraph` builder API — verify current PyPI version.
3. CORS `allow_origins=["*"]` fine for MVP; restrict to Vercel URL before sharing with full team.
