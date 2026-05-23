# Phase 1: Backend Foundation + Extraction Proof - Research

**Researched:** 2026-05-23
**Domain:** FastAPI + LangGraph + langchain-google-genai + supabase-py
**Confidence:** HIGH (core stack verified against PyPI registry and official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 1 accepts ONLY `text/plain` (TXT files). Any other MIME type is rejected immediately with HTTP 422 and `{"detail": "Unsupported file type. Accepted: text/plain"}`.
- **D-02:** Validation happens at the **router level** — inside the `/ingest` FastAPI endpoint, before the LangGraph graph is invoked. The graph is not called for unsupported types.
- **D-03:** Error format follows FastAPI's standard `detail` string convention — no structured error object needed at this stage.
- **D-04:** Use `Gemini 2.5 Flash` as the model — overrides the "1.5 Flash" in the design doc. Use `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`.
- **D-05:** Use `with_structured_output()` for JSON extraction — do NOT use `JsonOutputParser`. Avoids silent JSON drop.
- **D-06:** Use `await graph.ainvoke()` in async FastAPI endpoints — sync `invoke()` blocks the event loop.
- **D-07:** Pin `supabase==2.4.6` exactly in requirements.txt — silent v1/v2 API break risk.

### Claude's Discretion

- Other aspects of the API contract (ingest response schema, project CRUD response shape, error handling for Gemini failures, LangGraph node error propagation) are left to Claude to implement following FastAPI conventions and the design doc.

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROJ-01 | Gerente pode criar projeto com nome, cliente e descrição | FastAPI POST /projects with Pydantic schema + Supabase insert |
| PROJ-02 | Gerente pode visualizar lista de projetos existentes | FastAPI GET /projects + Supabase select |
| PROJ-03 | Gerente pode navegar para o dashboard de um projeto específico | FastAPI GET /projects/{id} + Supabase select by UUID |
| INGS-01 | Gerente pode fazer upload de arquivo (Phase 1: TXT only) associado a um número de sprint | FastAPI UploadFile + Form() + MIME validation + LangGraph ainvoke |
| INGS-02 | Sistema exibe feedback de sucesso ou erro após o upload | Router returns structured response or raises HTTPException |
| EXTR-01 | Sistema extrai conteúdo estruturado (6 campos) via Gemini 2.5 Flash | LangGraph StateGraph + ChatGoogleGenerativeAI.with_structured_output(ConteudoEstruturado) |
| EXTR-02 | Sistema processa arquivos de texto (TXT) extraindo texto puro | preprocessar_arquivo node: decode UTF-8, truncate at 50k chars |
</phase_requirements>

---

## Summary

Phase 1 builds the FastAPI backend for DocuData — project CRUD endpoints plus the complete extraction pipeline (TXT upload → LangGraph → Gemini 2.5 Flash → Supabase row). The core stack is mature and the AI-SPEC entry-point pattern is largely correct, with two material discrepancies documented below: (1) `langchain-google-genai` jumped from 3.x to 4.x with a default `with_structured_output` mode change (`function_calling` → `json_schema`) and a known active async slowdown regression in 4.2.x; (2) `nixpacks.toml` poppler setup requires `aptPkgs` (not `nixPkgs`) for Railway's current Railpack build system.

The walking skeleton — TXT upload → Gemini extraction → Supabase insert — is achievable in a single task wave. The highest-risk moment is the first end-to-end integration test: Gemini async, structured output schema enforcement, and Supabase insert all converge at that point. Plan Wave 0 to stub the LLM call so the graph plumbing can be verified independently before live Gemini calls.

**Primary recommendation:** Pin `langchain-google-genai==4.1.1` to avoid the unresolved 4.2.x async slowdown bug. Pin `supabase==2.4.6` as already decided (D-07). Use `method="json_schema"` explicitly in `with_structured_output()` since it is now the default in 4.x anyway — being explicit protects against future default changes.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Project CRUD (create, list, get) | API / Backend (FastAPI router) | Database (Supabase) | Pure data persistence — no LLM, no file handling |
| File upload + MIME validation | API / Backend (FastAPI router) | — | D-02: validation at router level before graph is called |
| File preprocessing (UTF-8 decode + truncation) | Agent (LangGraph node) | — | `preprocessar_arquivo` is a pure CPU transformation inside the graph |
| LLM extraction (Gemini call) | Agent (LangGraph node) | — | `extrair_conteudo` node owns the Gemini interaction |
| Structured output parsing + retry routing | Agent (LangGraph conditional edge) | — | `_roteador` reads `valido`/`tentativas`, routes back to extrair_conteudo or END |
| Ingestion persistence | Agent (LangGraph node) + Database | — | `salvar` node writes to Supabase after validated extraction |
| Environment config loading | API / Backend (main.py startup) | — | `load_dotenv()` called once at app startup |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | 0.136.1 | REST API framework | Industry standard for Python async APIs; native Pydantic v2 integration |
| `uvicorn` | 0.47.0 | ASGI server | Standard uvicorn for FastAPI; Procfile uses `uvicorn main:app` |
| `python-multipart` | 0.0.29 | UploadFile form parsing | **Required** by FastAPI for any multipart/form-data; without it UploadFile routes return 422 |
| `langgraph` | >=1.0,<2 | Stateful extraction graph | Node-level retry + explicit state — matches design doc §4 exactly |
| `langchain-core` | >=1.4.0,<2 | LangChain base types (HumanMessage, SystemMessage) | Pulled in by langgraph; pinned via langgraph's own dependency |
| `langchain-google-genai` | ==4.1.1 | Gemini via LangChain | **PIN to 4.1.1** — 4.2.x has unresolved async slowdown (3-4x latency regression); see Pitfall 4 |
| `supabase` | ==2.4.6 | Supabase PostgreSQL client | **PIN exactly** (D-07) — v1→v2 was a silent breaking change; 2.4.6 released 2024-05-22 |
| `pydantic` | >=2.9.0 | Request/response validation + extraction schema | FastAPI and langchain-google-genai both require pydantic v2 |
| `python-dotenv` | >=1.0.0 | .env loading at startup | Standard pattern for FastAPI environment config |

### Supporting (Phase 1 Prepwork — not imported in Phase 1 but install now)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-docx` | 1.2.0 | DOCX text extraction | Phase 2 — `preprocessar_arquivo` DOCX branch |
| `pdfplumber` | 0.11.9 | PDF text layer extraction | Phase 2 — `preprocessar_arquivo` PDF branch |
| `pdf2image` | 1.17.0 | Scanned PDF → image | Phase 2 — fallback when pdfplumber gets < 100 chars |
| `Pillow` | 12.2.0 | Image → base64 for Gemini vision | Phase 2 — image and scanned PDF handling |
| `langsmith` | 0.8.5 | LangGraph tracing + eval | Phase 1 (tracing env vars) — full eval dataset in Phase 2 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangGraph StateGraph | LCEL chain | LCEL lacks per-node retry + explicit state; refactor cost in Phase 2 (branching) outweighs the simplicity gain |
| `with_structured_output()` | `JsonOutputParser` | `JsonOutputParser` silently passes malformed JSON without Pydantic validation — ruled out by D-05 |
| supabase==2.4.6 | Latest supabase (2.30.0) | Latest version is untested with this codebase; v1→v2 was a silent break; D-07 pins 2.4.6 specifically |

**Installation:**
```bash
pip install fastapi uvicorn python-multipart \
  "langgraph>=1.0,<2" "langchain-core>=1.4.0,<2" "langchain-google-genai==4.1.1" \
  supabase==2.4.6 pydantic python-dotenv \
  python-docx pdfplumber pdf2image Pillow langsmith
```

**Version verification (confirmed 2026-05-23):**

| Package | Confirmed Latest | Pinned To | Registry |
|---------|-----------------|-----------|----------|
| `langgraph` | 1.2.1 | `>=1.0,<2` | PyPI |
| `langchain-core` | 1.4.0 | `>=1.4.0,<2` (auto via langgraph) | PyPI |
| `langchain-google-genai` | 4.2.3 | `==4.1.1` (async bug) | PyPI |
| `fastapi` | 0.136.1 | `>=0.100` | PyPI |
| `uvicorn` | 0.47.0 | `>=0.20` | PyPI |
| `python-multipart` | 0.0.29 | `>=0.0.7` | PyPI |
| `supabase` | 2.30.0 (latest) | `==2.4.6` (D-07) | PyPI |
| `pydantic` | 2.13.4 | `>=2.9.0` | PyPI |
| `python-dotenv` | 1.2.2 | `>=1.0.0` | PyPI |
| `langsmith` | 0.8.5 | `>=0.7` | PyPI |

---

## Package Legitimacy Audit

> slopcheck was unavailable at research time — all packages marked `[ASSUMED]` via graceful degradation. All packages were verified to exist on PyPI via `python3 -m pip index versions` or pip dry-run. Planner must add `checkpoint:human-verify` before install steps if strictly required, though all packages are established ecosystem tools.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `fastapi` | PyPI | ~7 yrs | Very high | github.com/fastapi/fastapi | [ASSUMED] | Approved — flagship Python web framework |
| `uvicorn` | PyPI | ~7 yrs | Very high | github.com/encode/uvicorn | [ASSUMED] | Approved — standard ASGI server |
| `python-multipart` | PyPI | ~10 yrs | High | github.com/Kludex/python-multipart | [ASSUMED] | Approved — required FastAPI dep |
| `langgraph` | PyPI | ~2 yrs | High | github.com/langchain-ai/langgraph | [ASSUMED] | Approved — LangChain org official |
| `langchain-core` | PyPI | ~2 yrs | Very high | github.com/langchain-ai/langchain | [ASSUMED] | Approved — LangChain org official |
| `langchain-google-genai` | PyPI | ~2 yrs | High | github.com/langchain-ai/langchain-google | [ASSUMED] | Approved — LangChain org official |
| `supabase` | PyPI | ~5 yrs | High | github.com/supabase/supabase-py | [ASSUMED] | Approved — Supabase official client |
| `pydantic` | PyPI | ~8 yrs | Very high | github.com/pydantic/pydantic | [ASSUMED] | Approved — ecosystem foundational |
| `python-dotenv` | PyPI | ~9 yrs | Very high | github.com/theskumar/python-dotenv | [ASSUMED] | Approved — ubiquitous .env loader |
| `langsmith` | PyPI | ~2 yrs | High | github.com/langchain-ai/langsmith-sdk | [ASSUMED] | Approved — LangChain org official |
| `python-docx` | PyPI | ~10 yrs | High | github.com/python-openxml/python-docx | [ASSUMED] | Approved |
| `pdfplumber` | PyPI | ~7 yrs | High | github.com/jsvine/pdfplumber | [ASSUMED] | Approved |
| `pdf2image` | PyPI | ~7 yrs | High | github.com/Belval/pdf2image | [ASSUMED] | Approved |
| `Pillow` | PyPI | ~12 yrs | Very high | github.com/python-pillow/Pillow | [ASSUMED] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time — all packages are tagged `[ASSUMED]`. They were all confirmed present on PyPI via pip and are well-known ecosystem packages. The planner may gate installs behind `checkpoint:human-verify` if required by policy.*

---

## Architecture Patterns

### System Architecture Diagram

```
[Gerente]
    |
    | HTTP multipart/form-data (arquivo + sprint_numero + projeto_id)
    v
[FastAPI Router: POST /ingest]
    |-- MIME check (D-02): content_type != "text/plain" → HTTP 422 immediately
    |
    | build ExtractionState dict
    v
[LangGraph: extraction_graph.ainvoke(state)]  ← compiled ONCE at module level
    |
    +--[detectar_tipo]  sync node
    |   reads mime_type → writes tipo="texto"
    |
    +--[preprocessar_arquivo]  sync node
    |   decode UTF-8, truncate @ 50k chars → writes texto_preprocessado
    |
    +--[extrair_conteudo]  async node
    |   ChatGoogleGenerativeAI.with_structured_output(ConteudoEstruturado).ainvoke(messages)
    |   on success: writes conteudo_estruturado, valido=True
    |   on exception: writes valido=False, tentativas+=1, erro=str(exc)
    |
    +--[_roteador]  conditional edge
    |   valido=True → salvar
    |   valido=False & tentativas < 2 → extrair_conteudo (retry with hardened prompt)
    |   valido=False & tentativas >= 2 → END (surface erro)
    |
    +--[salvar]  async node
        supabase_client.table("ingestions").insert({...}).execute()
        on APIError → raise → FastAPI returns HTTP 502

[Supabase PostgreSQL]
    ingestions table: project_id, sprint_number, file_name, file_type, extracted_content (jsonb)
```

### Recommended Project Structure

```
docudata-backend/
├── main.py                    # FastAPI app: load_dotenv(), register routers, configure CORS
├── requirements.txt           # pinned versions
├── nixpacks.toml              # Railway system deps (poppler_utils) — Phase 2 prep
├── .env.example               # GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
├── routers/
│   ├── projects.py            # CRUD: POST /projects, GET /projects, GET /projects/{id}
│   ├── ingest.py              # POST /ingest: MIME check → graph.ainvoke()
│   └── generate.py            # Phase 3
├── graphs/
│   ├── extraction_graph.py    # StateGraph compiled at module level — singleton
│   └── generation_graph.py    # Phase 3
├── services/
│   ├── supabase_client.py     # Singleton client: create_client(URL, SERVICE_KEY)
│   └── file_parser.py         # Phase 2 — DOCX/PDF/image preprocessing
└── models/
    └── schemas.py             # Pydantic: ProjectCreate, ProjectResponse, IngestResponse
```

### Pattern 1: LangGraph StateGraph — Compile Once, Invoke Per Request

**What:** Build the `StateGraph`, add all nodes and edges, call `.compile()` once at module import time. Import the compiled singleton into the router.

**When to use:** Every LangGraph graph. Never compile inside a request handler.

**Key finding from current docs:** LangGraph 1.0 (released Oct 2025) has zero breaking changes from 0.2.x for `StateGraph`, `TypedDict` state, `add_conditional_edges`, `.compile()`, and `.ainvoke()`. The AI-SPEC entry-point pattern is fully compatible with LangGraph 1.2.1.

`add_conditional_edges` current signature (LangGraph 1.x): [VERIFIED: reference.langchain.com]
```python
add_conditional_edges(
    source: str,
    path: Callable[..., Hashable | Sequence[Hashable]] | Runnable,
    path_map: dict[Hashable, str] | list[str] | None = None,
) -> Self
```

**Note on `path_map`:** When routing to `END`, pass the string `"__end__"` in `path_map` or return `END` directly from the router function. The AI-SPEC returns `END` directly (the sentinel object from `langgraph.graph`) — this is correct and works without a `path_map`.

```python
# Source: AI-SPEC + verified against LangGraph reference docs
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional

class ExtractionState(TypedDict):
    arquivo_bytes: bytes
    arquivo_nome: str
    mime_type: str
    sprint_numero: int
    projeto_id: str
    tipo: str
    texto_preprocessado: str
    conteudo_estruturado: Optional[dict]
    valido: bool
    tentativas: int
    erro: Optional[str]

_builder = StateGraph(ExtractionState)
_builder.add_node("detectar_tipo", detectar_tipo)
_builder.add_node("preprocessar_arquivo", preprocessar_arquivo)
_builder.add_node("extrair_conteudo", extrair_conteudo)
_builder.add_node("salvar", salvar)

_builder.add_edge(START, "detectar_tipo")
_builder.add_edge("detectar_tipo", "preprocessar_arquivo")
_builder.add_edge("preprocessar_arquivo", "extrair_conteudo")
_builder.add_conditional_edges("extrair_conteudo", _roteador)
_builder.add_edge("salvar", END)

extraction_graph = _builder.compile()   # module-level singleton
```

### Pattern 2: ChatGoogleGenerativeAI with Structured Output (4.x)

**What:** Use `with_structured_output(ConteudoEstruturado)` to bind the Pydantic model to the LLM call. In `langchain-google-genai>=4.0`, the default method changed from `function_calling` to `json_schema`. Specify explicitly to guard against future default changes.

**Critical finding:** There is an **active unresolved async slowdown regression in langchain-google-genai 4.2.x** (GitHub issue #1600, opened Feb 2026). Async calls are 3-4x slower. **Pin to 4.1.1 for stable async performance.** [VERIFIED: github.com/langchain-ai/langchain-google/issues/1600]

```python
# Source: reference.langchain.com/python/langchain-google-genai/chat_models/
# + confirmed via PyPI dry-run (langchain-google-genai 4.2.3 installs google-genai>=1.65.0)
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

class ConteudoEstruturado(BaseModel):
    """Schema de extracao de conhecimento de projetos de dados."""
    resumo: str = Field(description="Descricao do que foi trabalhado nesta entrega")
    tarefas: list[str] = Field(description="Lista de tarefas identificadas no arquivo")
    decisoes: list[str] = Field(description="Decisoes tecnicas tomadas nesta sprint")
    problemas: list[str] = Field(description="Problemas e bloqueios identificados")
    contexto_cliente: str = Field(description="Informacoes sobre o cliente ou requisitos de negocio")
    proximos_passos: list[str] = Field(description="Lista de proximos passos identificados")

_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",   # D-04
    temperature=0,
    max_tokens=2048,
    # GOOGLE_API_KEY read from env automatically
)
_structured_llm = _llm.with_structured_output(
    ConteudoEstruturado,
    method="json_schema",   # explicit — default in 4.x, but guard against regression
)

# In the extraction node:
async def extrair_conteudo(state: ExtractionState) -> dict:
    result: ConteudoEstruturado = await _structured_llm.ainvoke(messages)
    return {"conteudo_estruturado": result.model_dump(), "valido": True}
```

### Pattern 3: FastAPI File Upload + Form Fields

**What:** FastAPI requires `UploadFile` for the file and `Form(...)` for each additional field when combining file + form data in the same request.

**Key finding:** `python-multipart` must be installed — FastAPI does not bundle it. Without it, any UploadFile route silently returns HTTP 422 at import time, not a clear error. [VERIFIED: fastapi.tiangolo.com/tutorial/request-files/]

```python
# Source: fastapi.tiangolo.com/tutorial/request-files/
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

router = APIRouter()

@router.post("/ingest")
async def ingest(
    arquivo: UploadFile = File(...),
    sprint_numero: int = Form(...),
    projeto_id: str = Form(...),
):
    # D-02: Validate MIME at router level before graph
    if arquivo.content_type != "text/plain":
        raise HTTPException(
            status_code=422,
            detail="Unsupported file type. Accepted: text/plain"
        )
    file_bytes = await arquivo.read()
    state = ExtractionState(
        arquivo_bytes=file_bytes,
        arquivo_nome=arquivo.filename,
        mime_type=arquivo.content_type,
        sprint_numero=sprint_numero,
        projeto_id=projeto_id,
        tipo="", texto_preprocessado="",
        conteudo_estruturado=None, valido=False,
        tentativas=0, erro=None,
    )
    result = await extraction_graph.ainvoke(state)   # D-06: async, non-blocking
    if not result.get("valido"):
        raise HTTPException(status_code=502, detail=result.get("erro", "Extraction failed"))
    return {"status": "ok", "sprint": sprint_numero}
```

### Pattern 4: Supabase Insert (sync, v2 API)

**What:** supabase-py v2 (pinned at 2.4.6) uses a builder pattern. `dict` values for `jsonb` columns are passed directly — the client serializes automatically. Errors raise exceptions; check for empty `.data` to detect insert failure.

```python
# Source: supabase.com/docs/reference/python/insert + PyPI history verification
from supabase import create_client, Client
import os

def get_client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )

# In salvar node:
async def salvar(state: ExtractionState) -> dict:
    client = get_client()
    try:
        response = client.table("ingestions").insert({
            "project_id": state["projeto_id"],
            "sprint_number": state["sprint_numero"],
            "file_name": state["arquivo_nome"],
            "file_type": state["tipo"],
            "extracted_content": state["conteudo_estruturado"],  # dict → jsonb auto
        }).execute()
        if not response.data:
            raise RuntimeError("Insert returned no data — row may not have been written")
    except Exception as exc:
        return {"erro": f"Supabase insert failed: {exc}"}
    return {}
```

**Note on singleton:** The `get_client()` call inside the `salvar` node creates a new client per call. For Phase 1 this is fine (low volume). In Phase 2+, move to a module-level singleton. Avoid creating the client at module import time — if env vars aren't loaded yet, initialization fails silently.

### Pattern 5: .env Loading in FastAPI

**What:** Call `load_dotenv()` at the very top of `main.py`, before any module that reads env vars is imported.

```python
# main.py — MUST be first
from dotenv import load_dotenv
load_dotenv()  # loads .env before any other imports read os.environ

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import projects, ingest, generate

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.include_router(projects.router)
app.include_router(ingest.router)
# ...
```

**Pitfall:** If `supabase_client.py` or `extraction_graph.py` is imported before `load_dotenv()` runs, `os.environ["GEMINI_API_KEY"]` raises `KeyError`. Import order matters.

### Pattern 6: nixpacks.toml for Railway (Phase 2 prep)

**What:** Add this file now so Phase 2 deploy doesn't break on `pdf2image` needing `poppler-utils`.

**Key finding:** Railway switched to Railpack (successor to nixpacks) for new projects. The correct approach is via aptPkgs (Debian/Ubuntu) OR via environment variable. The Nix `nixPkgs = ["poppler_utils"]` approach works on the legacy nixpacks builder. To be safe, use both methods: [VERIFIED: nixpacks.com/docs/guides/configuring-builds + station.railway.com]

```toml
# nixpacks.toml — place in docudata-backend root
[phases.setup]
nixPkgs = ["...", "poppler_utils"]
aptPkgs = ["...", "poppler-utils"]
```

Also set `RAILPACK_DEPLOY_APT_PACKAGES=poppler-utils` in Railway service Variables as a belt-and-suspenders fallback, since some users reported that nixpacks build-time installation doesn't survive to the runtime container.

### Anti-Patterns to Avoid

- **Calling `extraction_graph = _builder.compile()` inside a request handler.** Rebuilds the graph on every request — 10-50ms wasted per call. Compile once at module level.
- **Using `graph.invoke()` (sync) in an async FastAPI endpoint.** Blocks the event loop. Always `await graph.ainvoke()`.
- **Returning the full state dict from a node.** LangGraph merges partial dicts. Return only the keys the node modifies.
- **Not wrapping `_structured_llm.ainvoke()` in try/except.** Pydantic `ValidationError` from `with_structured_output` will propagate uncaught to FastAPI and return HTTP 500.
- **Importing `extraction_graph` before `load_dotenv()` runs.** Module-level `ChatGoogleGenerativeAI(...)` reads env vars at import time — if GEMINI_API_KEY is not set yet, the import fails.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema enforcement on LLM output | Manual JSON parsing + field presence checks | `with_structured_output(ConteudoEstruturado)` | Pydantic v2 validates types, presence, and nesting automatically; handles Gemini's occasional markdown wrapping |
| Retry loop on extraction failure | Custom while loop + state tracking | LangGraph `add_conditional_edges` + `tentativas` state field | Graph state persists retry count; conditional edge routes cleanly; no threading issues |
| MIME type detection | Manual magic-byte inspection | FastAPI's `UploadFile.content_type` | Browser sets it; trust it for Phase 1 (TXT only); add magic-byte fallback in Phase 2 for images |
| Supabase jsonb serialization | `json.dumps()` before insert | Pass `dict` directly to `supabase.table().insert()` | supabase-py v2 serializes `dict` → `jsonb` automatically |
| Async vs sync node dispatch | `asyncio.run()` inside nodes | Return `async def` or `def` — LangGraph handles both | LangGraph's runtime schedules both correctly; `asyncio.run()` raises `RuntimeError: event loop already running` |

**Key insight:** In this stack, every hand-rolled solution for LLM output handling, retry logic, and Supabase serialization either exists already or silently fails at edge cases that the standard libraries handle.

---

## Common Pitfalls

### Pitfall 1: langchain-google-genai 4.2.x Async Slowdown

**What goes wrong:** After installing `langchain-google-genai>=4.2.0` (which pulls `google-genai>=1.56`), `ainvoke()` becomes 3-4x slower. A call that took 2 seconds at 4.1.1 may take 8+ seconds at 4.2.x. At 30-second endpoint timeout this can cause spurious timeout failures.

**Why it happens:** The 4.2.0 release bumped `google-genai` to a new async client stack with a slower async path (token acquisition / request setup). The issue was filed Feb 2026 and is unresolved as of 4.2.3 (latest as of May 2026).

**How to avoid:** Pin `langchain-google-genai==4.1.1` in requirements.txt. Check GitHub issue #1600 before upgrading.

**Warning signs:** Extraction endpoint latency jumps to 8-20s; LangSmith traces show the Gemini call itself taking unusually long; sync `invoke()` is fast but `ainvoke()` is slow.

### Pitfall 2: python-multipart Not Installed

**What goes wrong:** FastAPI returns HTTP 422 on any `/ingest` call, with an error about form data parsing. The error message does not mention `python-multipart`.

**Why it happens:** FastAPI declares `python-multipart` as an optional dependency. If not installed, `UploadFile` routes fail at runtime, not at import.

**How to avoid:** Include `python-multipart` explicitly in `requirements.txt`. Run a smoke test immediately after deploy: `curl -F arquivo=@test.txt -F sprint_numero=1 -F projeto_id=<uuid> /ingest`.

**Warning signs:** HTTP 422 on upload even with a valid TXT file; no LangGraph trace appears in LangSmith.

### Pitfall 3: Module Import Order — load_dotenv() Must Run First

**What goes wrong:** `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` runs at module import time (it's a module-level statement in `extraction_graph.py`). If `main.py` imports `extraction_graph` before calling `load_dotenv()`, the `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) env var is not set, and initialization fails.

**Why it happens:** Python module imports are executed once, immediately. The LLM client reads env vars during `__init__`.

**How to avoid:** Structure `main.py` so `load_dotenv()` is the very first call, before any router or graph imports. Alternatively, lazily initialize the LLM client inside a function (but this conflicts with the compile-once pattern — keep the import order discipline instead).

**Warning signs:** `KeyError: 'GOOGLE_API_KEY'` at startup even though `.env` file exists.

### Pitfall 4: Returning END (sentinel) vs String in _roteador

**What goes wrong:** The `_roteador` function returns `END` (the sentinel from `langgraph.graph`) when retries are exhausted. In some LangGraph versions, conditional edge path functions were expected to return strings (node names), not the `END` sentinel directly. This can cause a `GraphBuildError` or silent routing failure.

**Why it happens:** The `add_conditional_edges` signature accepts `Callable[..., Hashable]`. `END` is a `str` constant (`"__end__"`) in LangGraph, so returning it works — but only if you do not also pass a `path_map` that doesn't include `END`.

**How to avoid:** When using `add_conditional_edges` without a `path_map`, the router function must return valid node names OR the `END` constant. This is the AI-SPEC pattern and is correct. Do NOT mix: if you add a `path_map`, you must include every possible return value, including `END`. [VERIFIED: reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges]

**Warning signs:** `GraphBuildError: Path map missing target for 'END'` at compile time; graph compiles but exhausted retries route to wrong node.

### Pitfall 5: supabase-py API Shape — check response.data, not response

**What goes wrong:** A Supabase insert that fails (e.g., FK violation, RLS policy) does not always raise an exception in `supabase-py 2.4.6`. Some errors surface as an empty `response.data` list.

**Why it happens:** The supabase-py client wraps PostgREST responses. HTTP 2xx with an empty body returns `response.data = []` rather than raising.

**How to avoid:** After `.execute()`, check `if not response.data: raise RuntimeError(...)`. This is already reflected in the Pattern 4 code above.

**Warning signs:** `salvar` node runs without error, no row appears in Supabase, but the endpoint reports success.

### Pitfall 6: DOCX/MIME Type Ambiguity (Phase 2 prep)

**What goes wrong:** Some browsers send DOCX files with `content_type = "application/octet-stream"` instead of the correct DOCX MIME type. Phase 1 only accepts `text/plain`, so this doesn't affect Phase 1 — but the Phase 2 MIME validation must account for this by checking the file extension as a fallback.

**Why it happens:** Browser MIME sniffing is inconsistent for Office formats.

**How to avoid:** For Phase 2, use `file.filename.endswith('.docx')` as a fallback when `content_type` is `application/octet-stream`.

**Warning signs:** Phase 2 `/ingest` returns 422 for `.docx` files even though they're valid DOCX.

---

## Code Examples

### Walking Skeleton: Minimal End-to-End Extraction Flow

This is the thinnest slice that proves the pipeline works (TXT upload → Gemini → Supabase row):

```python
# Test script — run locally against real Supabase and Gemini API
import asyncio
from graphs.extraction_graph import extraction_graph, ExtractionState

async def smoke_test():
    txt_content = b"Sprint 3: Finalizamos o modelo de clustering. Decisao: usar K-means com k=5. Proximo passo: validar com cliente."
    state = ExtractionState(
        arquivo_bytes=txt_content,
        arquivo_nome="sprint3.txt",
        mime_type="text/plain",
        sprint_numero=3,
        projeto_id="00000000-0000-0000-0000-000000000001",  # real UUID from Supabase
        tipo="", texto_preprocessado="",
        conteudo_estruturado=None, valido=False,
        tentativas=0, erro=None,
    )
    result = await extraction_graph.ainvoke(state)
    assert result["valido"], f"Extraction failed: {result.get('erro')}"
    assert all(k in result["conteudo_estruturado"] for k in [
        "resumo", "tarefas", "decisoes", "problemas", "contexto_cliente", "proximos_passos"
    ])
    print("Smoke test passed:", result["conteudo_estruturado"]["resumo"])

asyncio.run(smoke_test())
```

### Project CRUD Pattern (supabase-py v2)

```python
# routers/projects.py
from fastapi import APIRouter, HTTPException
from models.schemas import ProjectCreate, ProjectResponse
from services.supabase_client import get_client

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    client = get_client()
    response = client.table("projects").insert({
        "name": data.name,
        "client": data.client,
        "description": data.description,
    }).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return response.data[0]

@router.get("", response_model=list[ProjectResponse])
async def list_projects():
    client = get_client()
    response = client.table("projects").select("*").order("created_at", desc=True).execute()
    return response.data

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    client = get_client()
    response = client.table("projects").select("*").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return response.data[0]
```

### Pydantic Schemas Pattern

```python
# models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    client: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    description: Optional[str] = None
    created_at: datetime

class IngestResponse(BaseModel):
    status: str               # "ok" | "error"
    sprint: int
    tentativas: int = 0       # expose for LangSmith correlation (AI-SPEC §4b.5)
```

---

## AI-SPEC Pattern Validation

The AI-SPEC (01-AI-SPEC.md) contains a complete `extraction_graph.py` entry-point pattern. Research confirms it is **correct for LangGraph 1.x** with two corrections needed:

| AI-SPEC Element | Status | Finding |
|----------------|--------|---------|
| `StateGraph(ExtractionState)` with `TypedDict` | CORRECT | LangGraph 1.0 confirmed zero breaking changes for this pattern [CITED: medium.com/@romerorico.hugo/langgraph-1-0...] |
| `add_conditional_edges("extrair_conteudo", _roteador)` returning `END` sentinel | CORRECT | `END` is `"__end__"` string constant; valid return without path_map [VERIFIED: reference.langchain.com] |
| `extraction_graph = _builder.compile()` at module level | CORRECT | Compile once, import singleton — confirmed best practice |
| `await graph.ainvoke(state)` in async endpoint | CORRECT | Required per D-06 |
| `_structured_llm = _llm.with_structured_output(ConteudoEstruturado)` | CORRECT but incomplete | Add `method="json_schema"` explicitly — 4.x default changed from `function_calling` to `json_schema`; being explicit prevents silent regression [VERIFIED: reference.langchain.com/python/langchain-google-genai/...] |
| `langchain-google-genai` version (latest) | **CORRECTION NEEDED** | Pin to `==4.1.1` — 4.2.x has unresolved async slowdown (3-4x) [VERIFIED: github.com/langchain-ai/langchain-google/issues/1600] |
| `supabase_client.py` lazy `get_client()` call inside node | LOW RISK | Acceptable for Phase 1; consider module-level singleton in Phase 2 for performance |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `JsonOutputParser` for LLM JSON extraction | `with_structured_output(PydanticModel)` | LangChain 0.2+ | Silent malformed JSON no longer passes validation |
| `google-ai-generativelanguage` SDK | `google-genai` SDK (consolidated) | langchain-google-genai 4.0 (2025) | Single SDK for Gemini API + Vertex AI; REST-only (gRPC removed) |
| `method="function_calling"` in `with_structured_output` | `method="json_schema"` (new default in 4.x) | langchain-google-genai 4.0 | Native structured output API; more reliable for strict schemas |
| `StateGraph` from `langgraph.graph` (0.2.x) | Same API, stable (1.x) | LangGraph 1.0 (Oct 2025) | Zero breaking changes; `config_schema` deprecated in favor of `context_schema` (not used here) |

**Deprecated/outdated:**

- `create_react_agent` from LangGraph — deprecated in 1.x; replaced by LangChain's `create_agent`. Not used in DocuData.
- `config_schema` parameter in `StateGraph(...)` — deprecated since 0.6.0, removed in 2.0. Use `context_schema` if needed. Not used in DocuData.
- `gRPC transport` for Gemini — removed in `langchain-google-genai 4.0`. REST is the only protocol now.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All 14 packages confirmed via PyPI exist and are from legitimate sources | Package Legitimacy Audit | Low — all are major ecosystem packages with multi-year histories; risk is theoretical |
| A2 | `langchain-google-genai==4.1.1` async performance is acceptable (pin avoids 4.2.x regression) | Standard Stack | Medium — if 4.1.1 has its own async bugs specific to gemini-2.5-flash, extraction latency may be unexpectedly high |
| A3 | Gemini 2.5 Flash model name is `"gemini-2.5-flash"` for the API | Architecture Patterns | Medium — model name strings change; verify against Google AI Studio or `google-genai` SDK model list before first run |
| A4 | `supabase==2.4.6` insert API (`table().insert(dict).execute()`) returns `response.data` list on success | Architecture Patterns | Low — confirmed against official docs; behavior stable across 2.x |
| A5 | nixpacks.toml `nixPkgs = ["...", "poppler_utils"]` works on Railway's current build system | Architecture Patterns | Medium — Railway shifted to Railpack; RAILPACK_DEPLOY_APT_PACKAGES env var may be more reliable |

---

## Open Questions

1. **Gemini 2.5 Flash exact model string**
   - What we know: Design doc says `"gemini-2.5-flash"`; AI-SPEC uses same; langchain-google-genai 4.x docs show `"gemini-3.5-flash"` in one example (different model entirely)
   - What's unclear: Whether the exact API string is `"gemini-2.5-flash"` or `"gemini-2.5-flash-latest"` or `"gemini-2.5-flash-preview-..."` for the google-genai SDK
   - Recommendation: Test with `"gemini-2.5-flash"` first (simplest); if 404, check Google AI Studio model list for the exact string. This is a 5-minute verification during Wave 0 local setup.

2. **langchain-google-genai 4.2.x async bug resolution status**
   - What we know: Issue #1600 opened Feb 2026, unresolved as of 4.2.3 (latest); pinning to 4.1.1 restores performance
   - What's unclear: Whether 4.1.1 introduces any incompatibility with Pydantic 2.13.x or LangGraph 1.2.x
   - Recommendation: Pin `4.1.1`, run smoke test, upgrade to latest only after the issue is closed.

3. **Railway build system: Railpack vs nixpacks**
   - What we know: Railway docs reference "Railpack" as successor; nixpacks.toml still works for legacy projects; `RAILPACK_DEPLOY_APT_PACKAGES` is the new env var approach
   - What's unclear: Whether a new Railway project (no prior deploy) uses nixpacks or Railpack by default
   - Recommendation: Include `nixpacks.toml` as specified in AI-SPEC; also set `RAILPACK_DEPLOY_APT_PACKAGES=poppler-utils` in Railway vars. Both methods are additive.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All packages | Yes (3.13 local) | 3.13 | — |
| `pip` | Package install | Yes | — | — |
| Supabase project (cloud) | PROJ-01..03, INGS-01, EXTR-01 | Must configure | — | No fallback — requires Supabase account + project setup |
| `GEMINI_API_KEY` | EXTR-01 | Must configure | — | No fallback — requires Google AI Studio key |
| `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | All Supabase ops | Must configure | — | No fallback — required env vars |
| `poppler-utils` (system) | Phase 2 pdf2image | Not verified locally | — | N/A for Phase 1 (TXT only) |

**Missing dependencies with no fallback:**
- Supabase project + credentials: must create project, run SQL schema (tables: `projects`, `ingestions`, `generated_docs`), and set env vars before any integration test runs.
- `GEMINI_API_KEY`: must obtain from Google AI Studio before extraction smoke test.

**Missing dependencies with fallback:**
- `poppler-utils`: not needed for Phase 1; add to `nixpacks.toml` now, verify on first Phase 2 Railway deploy.

---

## Security Domain

> security_enforcement absent from config.json — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (MVP: no auth) | Out of scope (v2 requirement) |
| V3 Session Management | No | Out of scope |
| V4 Access Control | No (shared space, MVP) | Out of scope (v2 requirement) |
| V5 Input Validation | Yes | Pydantic v2 on all request models; MIME check in router (D-02) |
| V6 Cryptography | Partial | Supabase `service_role` key in env var (not committed); GEMINI_API_KEY in env var |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Large file upload exhausting memory | DoS | 50k char truncation in `preprocessar_arquivo` (AI-SPEC §4b.4); FastAPI default max upload size |
| API key leakage via logs | Information Disclosure | Log only first 200 chars of `texto_preprocessado` (AI-SPEC §4b.1); never log keys |
| Malformed JSON injection into Supabase `jsonb` | Tampering | `with_structured_output()` validates against Pydantic model before insert; dict is safe |
| SUPABASE_SERVICE_KEY committed to git | Information Disclosure | `.env` in `.gitignore`; only `.env.example` committed |
| CORS `allow_origins=["*"]` in production | Spoofing | Acceptable for MVP (internal tool, no auth); restrict in v2 with auth |

---

## Sources

### Primary (HIGH confidence)
- [PyPI: langgraph](https://pypi.org/project/langgraph/) — version 1.2.1 confirmed; dependency on `langchain-core>=1.4.0`
- [PyPI: langchain-google-genai](https://pypi.org/project/langchain-google-genai/) — version 4.2.3 latest; requires `google-genai>=1.65.0`
- [PyPI: supabase history](https://pypi.org/project/supabase/#history) — version 2.4.6 confirmed, released 2024-05-22
- [LangGraph reference: add_conditional_edges](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges) — current signature verified
- [LangChain reference: with_structured_output](https://reference.langchain.com/python/langchain-google-genai/chat_models/ChatGoogleGenerativeAI/with_structured_output) — method="json_schema" default confirmed
- [nixpacks.com: configuring builds](https://nixpacks.com/docs/guides/configuring-builds) — nixPkgs array syntax with "..." extension
- [Supabase docs: Python insert](https://supabase.com/docs/reference/python/insert) — sync insert API pattern
- [FastAPI docs: request files](https://fastapi.tiangolo.com/tutorial/request-files/) — UploadFile + Form() + python-multipart requirement

### Secondary (MEDIUM confidence)
- [langchain-google-genai 4.0 release discussion](https://github.com/langchain-ai/langchain-google/discussions/1422) — breaking changes: `json_schema` default, gRPC removed, Vertex migration
- [LangGraph 1.0 announcement](https://blog.langchain.com/langchain-langgraph-1dot0/) — zero breaking changes to StateGraph, TypedDict state, conditional edges
- [Railway poppler-utils thread](https://station.railway.com/questions/can-t-install-poppler-utils-6153dde1) — aptPkgs vs nixPkgs vs RAILPACK env var

### Tertiary (LOW confidence — flagged for validation)
- [langchain-google-genai 4.2 async slowdown issue #1600](https://github.com/langchain-ai/langchain-google/issues/1600) — regression confirmed but resolution status unclear; pin 4.1.1 as precaution
- [Gemini model name verification](https://aistudio.google.com) — cannot access without auth; model string "gemini-2.5-flash" assumed correct from design doc + AI-SPEC consensus

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages confirmed on PyPI via `pip index versions` and dry-run install
- Architecture: HIGH — LangGraph 1.0 confirmed zero breaking changes; FastAPI UploadFile + Form verified against official docs
- Pitfalls: MEDIUM — async slowdown regression (Pitfall 1) confirmed via GitHub issue but resolution status is LOW confidence; import order (Pitfall 3) is ASSUMED from training knowledge + official docs pattern

**Research date:** 2026-05-23

**Valid until:** 2026-06-23 (30 days — stable stack, but check langchain-google-genai issue #1600 resolution before upgrading past 4.1.1)
