# Phase 1: Backend Foundation + Extraction Proof - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 9 new files
**Analogs found:** 0 / 9 (greenfield — canonical source is CLAUDE.md + RESEARCH.md)

---

## Greenfield Notice

This is a greenfield project. No existing codebase analog exists for any file. The canonical
pattern source for every file is:

- `CLAUDE.md` — complete software design document (authoritative for architecture, API contract,
  graph nodes/edges, state schema, folder structure, and dependencies)
- `.planning/phases/01-backend-foundation-extraction-proof/01-RESEARCH.md` — verified stack
  patterns with exact code excerpts, pitfall list, and library version pins

All "Analog" entries below reference sections of those two documents, not existing source files.

---

## File Classification

| New File | Role | Data Flow | Canonical Reference | Match Quality |
|----------|------|-----------|---------------------|---------------|
| `docudata-backend/main.py` | config/entrypoint | request-response | CLAUDE.md §8.1 + RESEARCH.md Pattern 5 | canonical-spec |
| `docudata-backend/requirements.txt` | config | — | RESEARCH.md Standard Stack table | canonical-spec |
| `docudata-backend/nixpacks.toml` | config | — | RESEARCH.md Pattern 6 | canonical-spec |
| `docudata-backend/.env.example` | config | — | CLAUDE.md §9.2 | canonical-spec |
| `docudata-backend/models/schemas.py` | model | transform | RESEARCH.md Pydantic Schemas Pattern | canonical-spec |
| `docudata-backend/services/supabase_client.py` | service | CRUD | RESEARCH.md Pattern 4 | canonical-spec |
| `docudata-backend/routers/projects.py` | router | CRUD | RESEARCH.md Project CRUD Pattern | canonical-spec |
| `docudata-backend/routers/ingest.py` | router | request-response | RESEARCH.md Pattern 3 | canonical-spec |
| `docudata-backend/graphs/extraction_graph.py` | agent/graph | event-driven | RESEARCH.md Patterns 1 + 2 | canonical-spec |

---

## Pattern Assignments

### `docudata-backend/main.py` (config/entrypoint, request-response)

**Canonical reference:** CLAUDE.md §8.1 + RESEARCH.md Pattern 5

**Critical constraint:** `load_dotenv()` MUST be the very first call — before any router or graph
import. `extraction_graph.py` instantiates `ChatGoogleGenerativeAI` at module level, which reads
`GOOGLE_API_KEY` from `os.environ` at import time. Violating import order causes
`KeyError: 'GOOGLE_API_KEY'` at startup even when `.env` exists.

**Imports + dotenv pattern** (RESEARCH.md Pattern 5):
```python
# main.py — load_dotenv() FIRST, before all other imports
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import projects, ingest

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects.router)
app.include_router(ingest.router)
```

**Routers to register (Phase 1):** `projects`, `ingest`. `generate` is Phase 3 — create stub file
but do not import yet.

---

### `docudata-backend/requirements.txt` (config)

**Canonical reference:** RESEARCH.md Standard Stack table + Alternatives Considered

**Exact pin strategy:**

| Package | Pin | Reason |
|---------|-----|--------|
| `langchain-google-genai` | `==4.1.1` | 4.2.x has unresolved async slowdown 3-4x (issue #1600) |
| `supabase` | `==2.4.6` | D-07 — v1→v2 silent API break; 2.4.6 confirmed stable |
| `langgraph` | `>=1.0,<2` | Zero breaking changes across 1.x; upper bound prevents 2.0 surprise |
| `langchain-core` | `>=1.4.0,<2` | Pulled by langgraph; explicit pin for reproducibility |
| All others | floor pins (`>=`) | Stable packages; no known regression risk |

**Full requirements.txt content** (RESEARCH.md Standard Stack):
```
fastapi>=0.100
uvicorn>=0.20
python-multipart>=0.0.7
langgraph>=1.0,<2
langchain-core>=1.4.0,<2
langchain-google-genai==4.1.1
supabase==2.4.6
pydantic>=2.9.0
python-dotenv>=1.0.0
langsmith>=0.7
python-docx==1.2.0
pdfplumber==0.11.9
pdf2image==1.17.0
Pillow==12.2.0
```

Note: `python-docx`, `pdfplumber`, `pdf2image`, and `Pillow` are Phase 2 libs — install now to
avoid a Phase 2 requirements change breaking Railway's cached build layer.

---

### `docudata-backend/nixpacks.toml` (config)

**Canonical reference:** RESEARCH.md Pattern 6

**Purpose:** Phase 2 prep — `pdf2image` requires `poppler-utils` as a system package on Railway.
Adding this now avoids a Phase 2 deploy surprise.

**File content** (RESEARCH.md Pattern 6):
```toml
[phases.setup]
nixPkgs = ["...", "poppler_utils"]
aptPkgs = ["...", "poppler-utils"]
```

Belt-and-suspenders: also set `RAILPACK_DEPLOY_APT_PACKAGES=poppler-utils` in Railway service
Variables panel — Railway migrated to Railpack and the env var approach is more reliable than
nixpacks.toml alone on new projects.

---

### `docudata-backend/.env.example` (config)

**Canonical reference:** CLAUDE.md §9.2

**File content:**
```
GEMINI_API_KEY=your_google_ai_studio_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

Do NOT commit `.env`. Add `.env` to `.gitignore` — only `.env.example` is committed.

---

### `docudata-backend/models/schemas.py` (model, transform)

**Canonical reference:** RESEARCH.md Pydantic Schemas Pattern + CLAUDE.md §3

**Role:** Pydantic v2 models for (1) FastAPI request/response validation and (2) the
`ConteudoEstruturado` extraction schema consumed by `with_structured_output()`.

**Imports pattern** (RESEARCH.md Pydantic Schemas Pattern):
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
```

**ConteudoEstruturado** — extraction schema (RESEARCH.md Pattern 2 + CLAUDE.md §3.4):
```python
class ConteudoEstruturado(BaseModel):
    """Schema de extracao de conhecimento de projetos de dados."""
    resumo: str = Field(description="Descricao do que foi trabalhado nesta entrega")
    tarefas: list[str] = Field(description="Lista de tarefas identificadas no arquivo")
    decisoes: list[str] = Field(description="Decisoes tecnicas tomadas nesta sprint")
    problemas: list[str] = Field(description="Problemas e bloqueios identificados")
    contexto_cliente: str = Field(description="Informacoes sobre o cliente ou requisitos de negocio")
    proximos_passos: list[str] = Field(description="Lista de proximos passos identificados")
```

**ProjectCreate / ProjectResponse** (RESEARCH.md Pydantic Schemas Pattern):
```python
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
```

**IngestResponse** (RESEARCH.md Pydantic Schemas Pattern):
```python
class IngestResponse(BaseModel):
    status: str          # "ok" | "error"
    sprint: int
    tentativas: int = 0  # expose for LangSmith correlation
```

---

### `docudata-backend/services/supabase_client.py` (service, CRUD)

**Canonical reference:** RESEARCH.md Pattern 4

**Role:** Singleton Supabase client factory. Called from routers (project CRUD) and from the
`salvar` LangGraph node (ingestion write).

**Critical constraint:** Do NOT instantiate the client at module import time — env vars may not
be loaded yet. Use a `get_client()` function that reads env vars lazily.

**Core pattern** (RESEARCH.md Pattern 4):
```python
from supabase import create_client, Client
import os

def get_client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
```

**After every `.execute()` call, check `response.data`** (RESEARCH.md Pitfall 5):
```python
response = client.table("projects").insert({...}).execute()
if not response.data:
    raise RuntimeError("Insert returned no data — row may not have been written")
```

Supabase FK violations and RLS policy rejections can surface as `response.data = []` rather than
raising an exception. Always guard with `if not response.data`.

---

### `docudata-backend/routers/projects.py` (router, CRUD)

**Canonical reference:** RESEARCH.md Project CRUD Pattern + CLAUDE.md §6

**Role:** Three endpoints — POST /projects, GET /projects, GET /projects/{id}. Pure database
CRUD; no LangGraph, no LLM.

**Imports + router setup** (RESEARCH.md Project CRUD Pattern):
```python
from fastapi import APIRouter, HTTPException
from models.schemas import ProjectCreate, ProjectResponse
from services.supabase_client import get_client

router = APIRouter(prefix="/projects", tags=["projects"])
```

**POST /projects** (RESEARCH.md Project CRUD Pattern):
```python
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
```

**GET /projects** (RESEARCH.md Project CRUD Pattern):
```python
@router.get("", response_model=list[ProjectResponse])
async def list_projects():
    client = get_client()
    response = client.table("projects").select("*").order("created_at", desc=True).execute()
    return response.data
```

**GET /projects/{id}** (RESEARCH.md Project CRUD Pattern):
```python
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    client = get_client()
    response = client.table("projects").select("*").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return response.data[0]
```

---

### `docudata-backend/routers/ingest.py` (router, request-response)

**Canonical reference:** RESEARCH.md Pattern 3 + CLAUDE.md §6

**Role:** POST /ingest — receives multipart upload (arquivo + sprint_numero + projeto_id),
enforces MIME check (D-02), builds `ExtractionState`, calls `await extraction_graph.ainvoke()`.

**Critical constraints:**
- D-01: Phase 1 accepts ONLY `text/plain`. Any other MIME → HTTP 422 immediately.
- D-02: MIME check at router level, BEFORE graph is called. Graph is not invoked for unsupported types.
- D-06: Use `await graph.ainvoke()` — sync `invoke()` blocks the event loop.

**Imports + MIME validation + graph call** (RESEARCH.md Pattern 3):
```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from graphs.extraction_graph import extraction_graph, ExtractionState
from models.schemas import IngestResponse

router = APIRouter(tags=["ingest"])

@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    arquivo: UploadFile = File(...),
    sprint_numero: int = Form(...),
    projeto_id: str = Form(...),
):
    # D-02: validate MIME at router level before graph
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
    result = await extraction_graph.ainvoke(state)   # D-06: non-blocking async
    if not result.get("valido"):
        raise HTTPException(status_code=502, detail=result.get("erro", "Extraction failed"))
    return IngestResponse(status="ok", sprint=sprint_numero, tentativas=result.get("tentativas", 0))
```

**Error format** (D-03): FastAPI standard `detail` string — no custom error object.

---

### `docudata-backend/graphs/extraction_graph.py` (agent/graph, event-driven)

**Canonical reference:** RESEARCH.md Patterns 1 + 2 + CLAUDE.md §4

**Role:** LangGraph `StateGraph` — compile once at module level. Five nodes:
`detectar_tipo` → `preprocessar_arquivo` → `extrair_conteudo` → `_roteador` (conditional edge) →
`salvar` or retry back to `extrair_conteudo`.

**Critical constraints:**
- Compile `extraction_graph = _builder.compile()` at module level, NEVER inside a request handler.
- All nodes that call Gemini or Supabase are `async def` — LangGraph schedules both sync and async
  correctly; never use `asyncio.run()` inside a node.
- Return only the state keys the node modifies — LangGraph merges partial dicts.
- Wrap `_structured_llm.ainvoke()` in try/except — `ValidationError` propagates uncaught otherwise.

**State schema** (RESEARCH.md Pattern 1 + CLAUDE.md §4.1):
```python
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

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
```

**LLM + structured output setup** (RESEARCH.md Pattern 2 — module level):
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from models.schemas import ConteudoEstruturado

_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",   # D-04; verify exact string in Google AI Studio on first run
    temperature=0,
    max_tokens=2048,
)
_structured_llm = _llm.with_structured_output(
    ConteudoEstruturado,
    method="json_schema",       # explicit — default in 4.x, guards against future regression
)
```

**Node: detectar_tipo** (CLAUDE.md §4.2):
```python
def detectar_tipo(state: ExtractionState) -> dict:
    mime = state["mime_type"]
    if mime in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"):
        tipo = "texto"
    elif mime == "application/pdf":
        tipo = "pdf"
    elif mime in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        tipo = "imagem"
    else:
        tipo = "desconhecido"
    return {"tipo": tipo}
```

**Node: preprocessar_arquivo** (CLAUDE.md §4.2 + RESEARCH.md EXTR-02 — TXT only in Phase 1):
```python
def preprocessar_arquivo(state: ExtractionState) -> dict:
    # Phase 1: TXT only. DOCX/PDF/image branches added in Phase 2 (file_parser.py).
    texto = state["arquivo_bytes"].decode("utf-8", errors="replace")
    texto = texto[:50_000]   # truncate to avoid token overflow (RESEARCH.md DoS mitigation)
    return {"texto_preprocessado": texto}
```

**Node: extrair_conteudo** (RESEARCH.md Pattern 2):
```python
from langchain_core.messages import HumanMessage, SystemMessage

async def extrair_conteudo(state: ExtractionState) -> dict:
    tentativas = state["tentativas"]
    prompt_suffix = "" if tentativas == 0 else "\n\nRetorne APENAS JSON valido, sem texto antes ou depois, sem markdown, sem backticks."
    messages = [
        SystemMessage(content="Voce e um assistente que extrai conhecimento estruturado de documentos de projetos de dados."),
        HumanMessage(content=f"Extraia as informacoes do seguinte texto de projeto:\n\n{state['texto_preprocessado']}{prompt_suffix}"),
    ]
    try:
        result: ConteudoEstruturado = await _structured_llm.ainvoke(messages)
        return {"conteudo_estruturado": result.model_dump(), "valido": True}
    except Exception as exc:
        return {"valido": False, "tentativas": tentativas + 1, "erro": str(exc)}
```

**Conditional edge: _roteador** (RESEARCH.md Pattern 1 + CLAUDE.md §4.3):
```python
def _roteador(state: ExtractionState):
    if state["valido"]:
        return "salvar"
    if state["tentativas"] < 2:
        return "extrair_conteudo"   # retry with hardened prompt
    return END                      # END is the string "__end__" — valid without path_map
```

**Node: salvar** (RESEARCH.md Pattern 4):
```python
from services.supabase_client import get_client

async def salvar(state: ExtractionState) -> dict:
    client = get_client()
    try:
        response = client.table("ingestions").insert({
            "project_id": state["projeto_id"],
            "sprint_number": state["sprint_numero"],
            "file_name": state["arquivo_nome"],
            "file_type": state["tipo"],
            "extracted_content": state["conteudo_estruturado"],  # dict → jsonb auto-serialized
        }).execute()
        if not response.data:
            raise RuntimeError("Insert returned no data — row may not have been written")
    except Exception as exc:
        return {"erro": f"Supabase insert failed: {exc}", "valido": False}
    return {}
```

**Graph assembly** (RESEARCH.md Pattern 1 — compile at module level):
```python
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

extraction_graph = _builder.compile()   # module-level singleton — NEVER inside a request handler
```

---

## Shared Patterns

### Environment Loading
**Source:** RESEARCH.md Pattern 5
**Apply to:** `main.py` exclusively. `load_dotenv()` is the first statement in `main.py`, before
all other imports. All other modules read from `os.environ` (already populated by the time they
are imported).

```python
# main.py — first two lines, nothing above them
from dotenv import load_dotenv
load_dotenv()
```

### Supabase Response Guard
**Source:** RESEARCH.md Pattern 4 + Pitfall 5
**Apply to:** Every `.execute()` call in `routers/projects.py` and `graphs/extraction_graph.py`

```python
response = client.table(...).insert({...}).execute()
if not response.data:
    raise RuntimeError("Insert returned no data")
# For GET routes: return [] instead of raising when select returns empty
```

### FastAPI HTTPException Error Format
**Source:** RESEARCH.md Pattern 3 + CONTEXT.md D-03
**Apply to:** All routers (`projects.py`, `ingest.py`)

```python
# Standard FastAPI detail string — no structured error object in Phase 1
raise HTTPException(status_code=422, detail="Unsupported file type. Accepted: text/plain")
raise HTTPException(status_code=404, detail="Project not found")
raise HTTPException(status_code=502, detail=result.get("erro", "Extraction failed"))
```

### LangGraph Node Return Convention
**Source:** RESEARCH.md Anti-Patterns to Avoid
**Apply to:** All node functions in `extraction_graph.py`

Nodes return ONLY the keys they modify. LangGraph merges partial dicts into state.
Never return the entire state dict from a node.

```python
# Correct — return only what changed
return {"tipo": "texto"}

# Wrong — do not return full state
return {**state, "tipo": "texto"}
```

### Async Node Convention
**Source:** RESEARCH.md Anti-Patterns to Avoid + D-06
**Apply to:** `extrair_conteudo` (Gemini call) and `salvar` (Supabase insert) in `extraction_graph.py`

Nodes that call external services (`ainvoke`, Supabase) must be `async def`. LangGraph handles
both sync and async nodes correctly. Never call `asyncio.run()` inside a node — the event loop
is already running.

---

## No Analog Found

All Phase 1 files are new — this entire section applies to every file listed in File Classification.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `main.py` | config/entrypoint | request-response | Greenfield — no prior FastAPI app |
| `requirements.txt` | config | — | Greenfield |
| `nixpacks.toml` | config | — | Greenfield |
| `.env.example` | config | — | Greenfield |
| `models/schemas.py` | model | transform | Greenfield |
| `services/supabase_client.py` | service | CRUD | Greenfield |
| `routers/projects.py` | router | CRUD | Greenfield |
| `routers/ingest.py` | router | request-response | Greenfield |
| `graphs/extraction_graph.py` | agent/graph | event-driven | Greenfield |

Planner should use RESEARCH.md patterns directly (already reproduced as concrete excerpts above).

---

## Critical Pitfalls Summary (for planner)

| Pitfall | File(s) Affected | Guard |
|---------|-----------------|-------|
| `load_dotenv()` import order | `main.py` | Must be first statement before all imports |
| `python-multipart` not installed | `requirements.txt` | Include explicitly; without it UploadFile returns 422 |
| `langchain-google-genai 4.2.x` async slowdown | `requirements.txt` | Pin to `==4.1.1` |
| `graph.invoke()` (sync) in async endpoint | `routers/ingest.py` | Always `await graph.ainvoke()` |
| `_builder.compile()` inside request handler | `graphs/extraction_graph.py` | Module-level only |
| `response.data` not checked after Supabase insert | `routers/projects.py`, `salvar` node | Always `if not response.data: raise` |
| `ValidationError` uncaught from `with_structured_output` | `extrair_conteudo` node | Wrap `ainvoke` in try/except |
| `END` sentinel in `_roteador` without `path_map` | `extraction_graph.py` | Valid — `END == "__end__"` string; do not add path_map |

---

## Metadata

**Canonical pattern sources:**
- `CLAUDE.md` — design doc (authoritative spec)
- `.planning/phases/01-backend-foundation-extraction-proof/01-RESEARCH.md` — verified patterns

**Analog search scope:** N/A — greenfield project; no source files to scan
**Files scanned:** 2 (CLAUDE.md, 01-RESEARCH.md)
**Pattern extraction date:** 2026-05-23
