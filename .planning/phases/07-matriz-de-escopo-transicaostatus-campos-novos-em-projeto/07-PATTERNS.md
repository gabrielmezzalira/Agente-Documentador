# Phase 07: Matriz de Escopo + TransicaoStatus + Campos Novos em Projeto — Pattern Map

**Mapped:** 2026-08-22
**Files analyzed:** 4 new/modified files
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docudata-backend/models/schemas.py` | model | transform | `docudata-backend/models/schemas.py` (existing) | exact — additive |
| `docudata-backend/graphs/import_graph.py` | service/graph | request-response + retry | `docudata-backend/graphs/extraction_graph.py` | exact |
| `docudata-backend/routers/funcionalidades.py` | controller | CRUD + event-driven (TransicaoStatus) | `docudata-backend/routers/projects.py` + `docudata-backend/routers/sprints.py` | exact |
| `docudata-backend/main.py` | config | — | `docudata-backend/main.py` (existing) | exact — additive |

---

## Pattern Assignments

### `docudata-backend/models/schemas.py` (model, transform) — ATUALIZAR

**Analog:** `docudata-backend/models/schemas.py` (arquivo existente, linhas 1–167)

**Imports pattern** (lines 1–4):
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
```

Adicionar ao topo:
```python
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
```

**Pydantic v2 field_validator pattern** (padrão observado no codebase — schemas.py usa Field; `@field_validator` é Pydantic v2 padrão do projeto per requirements.txt):
```python
@field_validator("criterios_aceite")
@classmethod
def criterios_nao_vazios(cls, v: list[str]) -> list[str]:
    filtrados = [s.strip() for s in v if s.strip()]
    if not filtrados:
        raise ValueError("Ao menos um critério de aceite é obrigatório")
    return filtrados
```

**Optional fields pattern** (lines 28–39 — ProjectResponse):
```python
class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    description: Optional[str] = None
    squad: Optional[str] = None
    budget_usd: Optional[float] = None
    has_api_key: bool = False
    is_delivered: bool = False
    created_at: datetime
    last_ingestion_at: Optional[datetime] = None
```

**Novos schemas a adicionar** (seguindo padrão acima):
- `FuncionalidadeCreate` — com `@field_validator` em `criterios_aceite` e `prioridade`
- `FuncionalidadeUpdate` — todos Optional, inclui `autor` e `motivo` para TransicaoStatus
- `FuncionalidadeResponse` — espelho da tabela com `created_at: datetime`
- `TransicaoStatusResponse` — campos: id, funcionalidade_id, campo, de, para, autor, timestamp, motivo, duracao_fase_anterior_segundos
- `FuncionalidadeProposta`, `ImportPropostaResponse`, `ImportConfirmarItem`, `ImportConfirmarRequest` — schemas de importação (proposta nunca é um BaseModel persistível)
- `ContratoUpdate` — 4 campos Optional[date/int]
- Atualizar `ProjectResponse` — adicionar os 4 campos novos como `Optional` (data_inicio, data_fim_contratada, tolerancia_desvio_pontos, periodo_garantia_dias)

---

### `docudata-backend/graphs/import_graph.py` (service/graph, request-response) — NOVO

**Analog:** `docudata-backend/graphs/extraction_graph.py`

**Imports pattern** (lines 1–10):
```python
import os
import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
```

**TypedDict state pattern** (lines 13–38 do extraction_graph):
```python
class ExtractionState(TypedDict):
    arquivo_bytes: bytes
    arquivo_nome: str
    mime_type: str
    sprint_numero: int
    projeto_id: str
    gemini_api_key: str          # key buscada do projeto no Supabase pelo router
    tipo: str
    texto_preprocessado: str
    conteudo_estruturado: Optional[dict]
    valido: bool
    tentativas: int
    erro: Optional[str]
    input_tokens: int
    output_tokens: int
```

Adaptar para ImportState:
```python
class ImportState(TypedDict):
    texto_contrato: str
    projeto_id: str
    gemini_api_key: str          # mesmo padrão — buscada do projeto pelo router
    proposta: Optional[list]
    valido: bool
    tentativas: int
    erro: Optional[str]
```

**LLM construction pattern** (lines 45–51 do extraction_graph):
```python
def _make_structured_llm(api_key: str):
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        max_tokens=2048,
        google_api_key=api_key,
    )
    return llm.with_structured_output(ConteudoEstruturado, method="json_schema", include_raw=True)
```

Para import_graph, usar `ChatGoogleGenerativeAI` sem `with_structured_output` — fazer parse manual com `json.loads` (proposta é lista, não schema Pydantic fixo).

**Hardened suffix pattern** (line 68 do extraction_graph):
```python
_HARDENED_SUFFIX = "\n\nRetorne APENAS JSON valido, sem texto antes ou depois, sem markdown, sem backticks."
```

Aplicar o mesmo `_HARDENED_SUFFIX` em retry (tentativas > 0).

**Retry router pattern** (lines 412–417 do extraction_graph):
```python
def _roteador(state: ExtractionState):
    if state["valido"]:
        return "salvar"
    if state["tentativas"] < 2:
        return "extrair_conteudo"
    return END
```

Adaptar para import_graph (sem nó salvar — termina em END):
```python
def _roteador(state: ImportState):
    if state["valido"]:
        return END
    if state["tentativas"] < 2:
        return "gerar_proposta"
    return END
```

**Module-level compile pattern** (lines 420–434 do extraction_graph):
```python
_builder = StateGraph(ExtractionState)
_builder.add_node("validar_tipo", validar_tipo)
_builder.add_node("detectar_tipo", detectar_tipo)
_builder.add_node("preprocessar_arquivo", preprocessar_arquivo)
_builder.add_node("extrair_conteudo", extrair_conteudo)
_builder.add_node("salvar", salvar)

_builder.add_edge(START, "validar_tipo")
_builder.add_conditional_edges("validar_tipo", _roteador_validacao, {"detectar_tipo": "detectar_tipo", END: END})
_builder.add_edge("detectar_tipo", "preprocessar_arquivo")
_builder.add_edge("preprocessar_arquivo", "extrair_conteudo")
_builder.add_conditional_edges("extrair_conteudo", _roteador)
_builder.add_edge("salvar", END)

extraction_graph = _builder.compile()
```

Adaptar para import_graph (apenas 1 nó + conditional_edges):
```python
_builder = StateGraph(ImportState)
_builder.add_node("gerar_proposta", gerar_proposta)
_builder.add_edge(START, "gerar_proposta")
_builder.add_conditional_edges("gerar_proposta", _roteador)

import_graph = _builder.compile()
```

**CRITICO:** `_builder.compile()` DEVE estar no escopo do módulo, NUNCA dentro de um request handler. Violation causa recriação do grafo a cada request.

**CRITICO:** `import_graph` NÃO tem nó `salvar`. O handler extrai `state["proposta"]` do resultado do `invoke()` e retorna ao cliente — sem INSERT no banco.

---

### `docudata-backend/routers/funcionalidades.py` (controller, CRUD + event-driven) — NOVO

**Analog primário:** `docudata-backend/routers/projects.py`
**Analog secundário:** `docudata-backend/routers/sprints.py` (PATCH com datetime + validation)

**Imports pattern** (lines 1–18 do projects.py):
```python
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from models.schemas import (
    FuncionalidadeCreate,
    FuncionalidadeUpdate,
    FuncionalidadeResponse,
    TransicaoStatusResponse,
    ImportPropostaResponse,
    ImportConfirmarRequest,
)
from services.supabase_client import get_client
from graphs.import_graph import import_graph
```

**Router declaration pattern** (line 20 do projects.py):
```python
router = APIRouter(prefix="/projects", tags=["projects"])
```

Adaptar:
```python
router = APIRouter(prefix="/funcionalidades", tags=["funcionalidades"])
```

**GET single + 404 pattern** (lines 73–80 do projects.py):
```python
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    client = get_client()
    response = client.table("projects").select("*").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return _sanitize(response.data[0])
```

**POST + INSERT + 201 pattern** (lines 33–45 do projects.py):
```python
@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    client = get_client()
    payload = {"name": data.name, "client": data.client, ...}
    response = client.table("projects").insert(payload).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return _sanitize(response.data[0])
```

**PATCH select-then-update pattern** (lines 83–98 do projects.py):
```python
@router.patch("/{project_id}/api-key", response_model=ProjectResponse)
async def update_api_key(project_id: str, data: ApiKeyUpdate):
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    response = (
        client.table("projects")
        .update({"gemini_api_key": data.gemini_api_key or None})
        .eq("id", project_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update API key")
    return _sanitize(response.data[0])
```

**PATCH com datetime.now(timezone.utc) pattern** (lines 183–205 do sprints.py):
```python
@router.patch("/sprints/{sprint_id}/health", response_model=SprintResponse)
async def update_health(sprint_id: str, data: SprintHealthUpdate):
    if data.status_saude is not None and data.status_saude not in _VALID_HEALTH:
        raise HTTPException(
            status_code=400,
            detail=f"status_saude deve ser um de {sorted(_VALID_HEALTH)} ou null",
        )
    client = get_client()
    check = client.table("sprints").select("id").eq("id", sprint_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Sprint not found")
    payload = {
        "status_saude": data.status_saude,
        "plano_correcao": data.plano_correcao,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.table("sprints").update(payload).eq("id", sprint_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update sprint health")
    return response.data[0]
```

**TransicaoStatus — lógica completa no handler PATCH** (padrão definido em RESEARCH.md Pattern 2):

O handler de `PATCH /funcionalidades/{id}` deve, para cada campo de status que mudou:
1. Buscar funcionalidade atual (select *)
2. Para cada campo em `("status", "status_cliente")` que mudou:
   a. Buscar timestamp da transição anterior: `.table("transicoes_status").select("timestamp").eq("funcionalidade_id", id).eq("campo", campo).order("timestamp", desc=True).limit(1).execute()`
   b. Se não há anterior: usar `func["created_at"]` como base
   c. Calcular `duracao = int((agora - ts_anterior.replace(tzinfo=timezone.utc)).total_seconds())`
   d. Inserir em `transicoes_status` com todos os campos
3. Se `status_cliente` mudou para `"aprovado"` e `data_aprovacao_cliente` não veio no body: setar `data_aprovacao_cliente = date.today()` no update
4. Executar UPDATE em `funcionalidades` com os campos que mudaram

**Pitfall critico de timezone** (RESEARCH.md Pitfall 1):
```python
# CERTO — ambos timezone-aware
agora = datetime.now(timezone.utc)
ts_anterior = datetime.fromisoformat(anterior.data[0]["timestamp"]).replace(tzinfo=timezone.utc)
duracao = int((agora - ts_anterior).total_seconds())

# ERRADO — TypeError: can't subtract offset-naive and offset-aware
ts_anterior = datetime.fromisoformat(anterior.data[0]["timestamp"])  # naive se string sem offset
duracao = int((agora - ts_anterior).total_seconds())
```

**DELETE + cascade pattern** (lines 307–314 do projects.py):
```python
@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    client = get_client()
    response = client.table("projects").select("id").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    client.table("projects").delete().eq("id", project_id).execute()
```

**Endpoints de importação:**
- `POST /funcionalidades/importar` — invocar `import_graph`, retornar `state["proposta"]` sem INSERT
- `POST /funcionalidades/importar/confirmar` — filtrar `confirmed=True`, iterar e fazer INSERT de cada funcionalidade confirmada, retornar lista de `FuncionalidadeResponse`

**PATCH /projects/{id}/contrato — adicionar em routers/projects.py** (seguindo RESEARCH.md Pattern 4):
```python
@router.patch("/{project_id}/contrato", response_model=ProjectResponse)
async def update_contrato(project_id: str, data: ContratoUpdate):
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=422, detail="Nenhum campo fornecido")
    response = client.table("projects").update(payload).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update contract fields")
    return _sanitize(response.data[0])
```

Nota: `model_dump()` — não `dict()` — padrão Pydantic v2 já usado no codebase.

---

### `docudata-backend/main.py` (config) — ATUALIZAR

**Analog:** `docudata-backend/main.py` (arquivo existente, linhas 1–33)

**Router registration pattern** (lines 6–27):
```python
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich

app.include_router(projects.router)
app.include_router(sprints.router)
# ... demais routers ...
```

Adicionar:
```python
from routers import funcionalidades  # novo

app.include_router(funcionalidades.router)
```

Inserir após `app.include_router(sprints.router)` para manter ordem lógica (entidades de projeto juntas).

---

## Shared Patterns

### supabase-py v2 query chain
**Source:** `docudata-backend/routers/projects.py` (linhas 42, 52, 77, 87–95)
**Apply to:** Todos os handlers em `routers/funcionalidades.py` e o novo endpoint em `projects.py`
```python
# INSERT
response = client.table("funcionalidades").insert(payload).execute()
if not response.data:
    raise HTTPException(status_code=500, detail="Failed to create funcionalidade")

# SELECT com filtro
response = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
if not response.data:
    raise HTTPException(status_code=404, detail="Funcionalidade not found")

# UPDATE
response = client.table("funcionalidades").update(updates).eq("id", funcionalidade_id).execute()

# ORDER + LIMIT (para buscar última transição)
anterior = (
    client.table("transicoes_status")
    .select("timestamp")
    .eq("funcionalidade_id", funcionalidade_id)
    .eq("campo", campo)
    .order("timestamp", desc=True)
    .limit(1)
    .execute()
)
```

### datetime timezone-aware
**Source:** `docudata-backend/routers/sprints.py` (line 200)
**Apply to:** Handler PATCH de funcionalidades (cálculo de duracao_fase_anterior_segundos)
```python
from datetime import datetime, timezone

agora = datetime.now(timezone.utc)
# Sempre usar .replace(tzinfo=timezone.utc) ao parsear strings do Supabase
ts = datetime.fromisoformat(row["timestamp"]).replace(tzinfo=timezone.utc)
```

### model_dump() para payload parcial
**Source:** Pydantic v2 padrão do projeto (requirements.txt confirma Pydantic ≥2.9.0)
**Apply to:** PATCH /projects/{id}/contrato e PATCH /funcionalidades/{id}
```python
payload = {k: v for k, v in data.model_dump().items() if v is not None}
```

### gemini_api_key buscada do projeto pelo router
**Source:** `docudata-backend/graphs/extraction_graph.py` (lines 17–19 — campo `gemini_api_key` no estado)
**Apply to:** Handler `POST /funcionalidades/importar` ao invocar `import_graph`

O router deve buscar a key do projeto no Supabase antes de invocar o grafo:
```python
proj = client.table("projects").select("gemini_api_key").eq("id", projeto_id).execute()
api_key = (proj.data[0].get("gemini_api_key") or "") if proj.data else ""
if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY", "")

state = import_graph.invoke({
    "texto_contrato": data.texto_contrato,
    "projeto_id": data.projeto_id,
    "gemini_api_key": api_key,
    "proposta": None,
    "valido": False,
    "tentativas": 0,
    "erro": None,
})
```

---

## No Analog Found

Nenhum arquivo desta fase ficou sem analog — todos os padrões existem no codebase atual.

---

## Metadata

**Analog search scope:** `docudata-backend/graphs/`, `docudata-backend/routers/`, `docudata-backend/models/`, `docudata-backend/main.py`
**Files scanned:** 6 (extraction_graph.py, generation_graph.py, projects.py, sprints.py, schemas.py, main.py)
**Pattern extraction date:** 2026-08-22
