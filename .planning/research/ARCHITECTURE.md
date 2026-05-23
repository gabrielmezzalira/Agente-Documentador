# Architecture Research: DocuData

**Project:** DocuData — Automated Data Project Documentation Agent
**Dimension:** Architecture
**Confidence:** HIGH

---

## Key Findings

- LangGraph graphs must be **compiled once at module level** and reused per request via `ainvoke()` — compiling per request wastes 10–50ms.
- FastAPI endpoints calling `ainvoke()` must be `async def`; mixing sync `invoke()` inside async endpoints blocks the event loop.
- The `base64_image:` prefix in `texto_preprocessado` is a critical coupling contract between `preprocessar_arquivo` and `extrair_conteudo` — document it explicitly.
- Supabase Python client (`supabase-py` v2) is synchronous by default — fine for MVP, needs singleton pattern to avoid connection leaks.
- JSON extraction retry node is the most brittle point — prompt engineering is the core work.
- Build order: `schemas.py` → `supabase_client.py` + `file_parser.py` → `extraction_graph.py` → `generation_graph.py` → routers → `main.py` → frontend.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Next.js Frontend (Vercel)                              │
│  page.tsx · projects/new · projects/[id]                │
│  lib/api.ts (all fetch calls centralized here)          │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP (multipart / JSON)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (Railway)                              │
│                                                         │
│  main.py ── CORS, router registration                   │
│  routers/                                               │
│    projects.py   — CRUD via supabase_client             │
│    ingest.py     — receives multipart, calls graph      │
│    generate.py   — receives JSON, calls graph           │
│                                                         │
│  services/                                              │
│    supabase_client.py  — singleton Supabase client      │
│    file_parser.py      — DOCX/PDF/TXT/image → bytes/str │
│                                                         │
│  graphs/                                                │
│    extraction_graph.py  — StateGraph (5 nodes)          │
│    generation_graph.py  — StateGraph (5 nodes)          │
│                                                         │
│  models/                                                │
│    schemas.py  — Pydantic request + response models     │
└──────────────┬──────────────────────────┬───────────────┘
               ▼                          ▼
┌──────────────────────┐   ┌─────────────────────────────┐
│  Gemini 1.5 Flash    │   │  Supabase (PostgreSQL)      │
│  via LangChain       │   │  projects                   │
│  ChatGoogleGenerAI   │   │  ingestions (jsonb)         │
└──────────────────────┘   │  generated_docs (text)      │
                           └─────────────────────────────┘
```

## Component Ownership

| Component | Owns | Does NOT Own |
|-----------|------|-------------|
| `routers/ingest.py` | HTTP boundary, request validation | File parsing, graph logic |
| `routers/generate.py` | HTTP boundary, request validation | Query logic, generation |
| `graphs/extraction_graph.py` | Full extraction pipeline, retry | HTTP concerns, Supabase init |
| `graphs/generation_graph.py` | Full generation pipeline | HTTP concerns, Supabase init |
| `services/supabase_client.py` | Supabase singleton, query helpers | Business logic |
| `services/file_parser.py` | Format-specific parsing | LLM calls, state management |
| `models/schemas.py` | Pydantic type contracts | Persistence, parsing |

---

## LangGraph Compilation Pattern

```python
# graphs/extraction_graph.py — compile ONCE at module level

from typing import TypedDict
from langgraph.graph import StateGraph, END

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

def should_retry(state) -> str:
    if not state["valido"] and state["tentativas"] < 2:
        return "extrair_conteudo"
    return "salvar"

builder = StateGraph(ExtractionState)
builder.add_node("detectar_tipo", detectar_tipo)
builder.add_node("preprocessar_arquivo", preprocessar_arquivo)
builder.add_node("extrair_conteudo", extrair_conteudo)
builder.add_node("estruturar_output", estruturar_output)
builder.add_node("salvar", salvar)
builder.set_entry_point("detectar_tipo")
builder.add_edge("detectar_tipo", "preprocessar_arquivo")
builder.add_edge("preprocessar_arquivo", "extrair_conteudo")
builder.add_edge("extrair_conteudo", "estruturar_output")
builder.add_conditional_edges(
    "estruturar_output",
    should_retry,
    {"extrair_conteudo": "extrair_conteudo", "salvar": "salvar"}
)
builder.add_edge("salvar", END)

extraction_graph = builder.compile()  # import this, never compile inside endpoint
```

---

## FastAPI + LangGraph Integration

```python
@router.post("/ingest")
async def ingest_file(
    arquivo: UploadFile,
    sprint_numero: int = Form(...),
    projeto_id: str = Form(...)
):
    arquivo_bytes = await arquivo.read()  # always await UploadFile.read()
    initial_state = {
        "arquivo_bytes": arquivo_bytes,
        "arquivo_nome": arquivo.filename,
        "mime_type": arquivo.content_type,
        "sprint_numero": sprint_numero,
        "projeto_id": projeto_id,
        "tentativas": 0,
        "valido": False,
        "erro": "",
    }
    final_state = await extraction_graph.ainvoke(initial_state)  # ainvoke, not invoke
    if final_state.get("erro"):
        raise HTTPException(status_code=422, detail=final_state["erro"])
    return {"status": "ok", "resumo": final_state["conteudo_estruturado"]["resumo"]}
```

## Async Rules Summary

| Concern | Decision | Rationale |
|---------|----------|-----------|
| `/ingest` and `/generate` | `async def` + `ainvoke()` | LLM calls are I/O-bound |
| `/projects` and `/ingestions` | `def` (sync) | Supabase sync; FastAPI dispatches to threadpool |
| Graph nodes with LLM calls | `async def` | Gemini HTTP call is async-capable |
| Graph nodes with Supabase | `def` (sync) | supabase-py v2 default client is sync |
| File reading | `await arquivo.read()` | UploadFile.read() is always awaitable |

---

## Data Flow: Extraction Graph

```
POST /ingest (multipart)
  │
  ▼ detectar_tipo
  │   mime_type → tipo ("texto" | "imagem" | "pdf")
  │
  ▼ preprocessar_arquivo
  │   DOCX  → python-docx → plain text string
  │   TXT   → UTF-8 decode → plain text string
  │   PDF   → pdfplumber → text; if < 100 chars → pdf2image → "base64_image:{b64}"
  │   image → Pillow → "base64_image:{b64}"
  │
  ▼ extrair_conteudo  [async — LLM call]
  │   starts with "base64_image:" → multimodal HumanMessage
  │   else → text HumanMessage
  │   → ChatGoogleGenerativeAI(model="gemini-1.5-flash")
  │
  ▼ estruturar_output
  │   JsonOutputParser → conteudo_estruturado
  │   on failure → tentativas+1, valido=False → back to extrair_conteudo (max 2)
  │   on success → valido=True
  │
  ▼ salvar  [async — DB call]
      INSERT INTO ingestions
```

## Data Flow: Generation Graph

```
POST /generate (JSON)
  │
  ▼ buscar_ingestions
  │   sprint_status/retro → WHERE project_id=? AND sprint_number=?
  │   decisoes/completo   → WHERE project_id=? ORDER BY sprint_number ASC
  │
  ▼ compilar_contexto
  │   ingestions → structured text block
  │   "--- Sprint {n} | {file_name} ---\nResumo: ...\nTarefas: ..."
  │
  ▼ selecionar_prompt
  │   tipo_doc → ChatPromptTemplate (one per doc type)
  │
  ▼ gerar_documento  [async — LLM call]
  │   prompt | ChatGoogleGenerativeAI | StrOutputParser()
  │
  ▼ salvar_documento  [async — DB call]
      INSERT INTO generated_docs → return documento
```

---

## Supabase Integration Patterns

```python
# services/supabase_client.py — singleton
_client = None

def get_supabase():
    global _client
    if _client is None:
        _client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    return _client

# Insert (in graph node)
def salvar(state):
    get_supabase().table("ingestions").insert({
        "project_id": state["projeto_id"],
        "sprint_number": state["sprint_numero"],
        "file_name": state["arquivo_nome"],
        "file_type": state["tipo"],
        "extracted_content": state["conteudo_estruturado"]  # auto-serialized to jsonb
    }).execute()
    return {}

# Query (in graph node)
def buscar_ingestions(state):
    q = get_supabase().table("ingestions").select("*").eq("project_id", state["projeto_id"])
    if state["tipo_doc"] in ("sprint_status", "sprint_retro"):
        q = q.eq("sprint_number", state["sprint_numero"])
    else:
        q = q.order("sprint_number", desc=False)
    return {"ingestions": q.execute().data}
```

---

## Prompt Engineering for JSON Extraction

```
You are a document analysis assistant.

Return ONLY a valid JSON object with exactly these keys:
- "resumo": string summarizing what was worked on
- "tarefas": array of task strings
- "decisoes": array of technical decision strings
- "problemas": array of problem/blocker strings
- "contexto_cliente": string with client context
- "proximos_passos": array of next step strings

Rules:
- Return ONLY the JSON object. No markdown, no backticks, no text before or after.
- Empty fields: use "" for strings, [] for arrays.
- Do not add extra fields.

Content: {content}
```

**Retry prompt** (when JsonOutputParser fails):
```
PREVIOUS ATTEMPT RETURNED INVALID JSON.
Return ONLY the raw JSON object — no markdown, no backticks, no text before or after.
[same prompt + content]
```

---

## Build Order

```
1. models/schemas.py           ← no deps; defines contracts used everywhere
2. services/supabase_client.py ← only needs .env
3. services/file_parser.py     ← only needs third-party libs
4. graphs/extraction_graph.py  ← needs supabase_client, file_parser, LangChain
5. graphs/generation_graph.py  ← needs supabase_client, LangChain [parallel with 4]
6. routers/projects.py         ← needs supabase_client, schemas
7. routers/ingest.py           ← needs extraction_graph, schemas
8. routers/generate.py         ← needs generation_graph, schemas
9. main.py                     ← needs all routers
10. frontend lib/api.ts         ← needs running FastAPI
11. frontend pages              ← needs api.ts
```

Steps 4 and 5 are independent and can be built in parallel. Steps 6–8 are independent once their graph dependencies exist.

---

## Anti-Patterns to Avoid

- **Compile graphs per request** — compile at module level.
- **Direct Supabase calls in routers** — all DB calls in graph nodes or `supabase_client.py`.
- **Returning full graph state as HTTP response** — shape responses explicitly in routers.
- **Sync `invoke()` inside `async def` endpoint** — always use `ainvoke()`.
- **Hardcoded prompt strings inline in nodes** — extract to constants/module top, retry logic references the same string.
