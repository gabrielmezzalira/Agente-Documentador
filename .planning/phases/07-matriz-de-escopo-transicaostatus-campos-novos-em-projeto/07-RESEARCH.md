# Phase 07: Matriz de Escopo + TransicaoStatus + Campos Novos em Projeto — Research

**Researched:** 2026-08-22
**Domain:** FastAPI + LangGraph + Supabase — nova entidade `funcionalidades`, grafo de importação, machine de estados, rastreabilidade temporal
**Confidence:** HIGH (codebase lido diretamente; sem dependências externas novas)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Importação em massa entra na Fase 7** junto com CRUD manual — não deferida
- **Arquitetura de importação:** LangGraph — grafo novo em `graphs/import_graph.py`, padrão do `extraction_graph.py` (StateGraph + TypedDict, nós retornando partial dicts, retry JSON). Nós: `receber_texto → gerar_proposta → estruturar_json → (retry se inválido) → retornar_proposta`. Proposta **nunca salva automaticamente**.
- **Revisão:** item a item com checkbox — gerente marca quais confirmar antes de salvar
- **Endpoints de importação:**
  - `POST /funcionalidades/importar` — retorna lista proposta (sem salvar)
  - `POST /funcionalidades/importar/confirmar` — cria confirmadas, descarta rejeitadas
- **Critérios EARS:** texto livre no backend — sem validação de formato. Backend exige apenas ≥1 critério por funcionalidade.
- **TransicaoStatus calculado no Python**, no handler do PATCH de status — não em trigger SQL
- **Endpoint separado:** `PATCH /projects/{id}/contrato` para campos novos de projeto
- **Campos novos:** `data_inicio` (date), `data_fim_contratada` (date), `tolerancia_desvio_pontos` (int, default 20), `periodo_garantia_dias` (int, default 30)
- **Migration:** ALTER TABLE com DEFAULT null — compatibilidade retroativa garantida
- **Sem transaction explícita no MVP** para TransicaoStatus (race condition improvável)
- **Sem auth:** campo `autor` em TransicaoStatus é string livre ou null

### Claude's Discretion

- Estrutura interna do grafo `import_graph.py` (nomes de nós intermediários, prompt exato)
- Validação de campos enum (`prioridade`, `status`, `status_cliente`) — se via Pydantic ou CHECK constraint no Supabase, ou ambos
- Ordem de criação dos planos / ondas de execução

### Deferred Ideas (OUT OF SCOPE)

- Vínculo automático funcionalidade ↔ branch/commit por convenção de nome
- Validação de formato EARS (começar com "Quando")
- Transação explícita para evitar race condition em TransicaoStatus
- RLS (Row Level Security) nas tabelas novas
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| M1 (§5) | Matriz de Escopo — funcionalidade com ≥1 critério de aceite | Pydantic validator + supabase insert |
| §4.1 | Entidade Funcionalidade — campos id_funcional, titulo, criterios_aceite[], prioridade, status, status_cliente | Modelo de dados mapeado; padrão Pydantic do codebase |
| §4.2 | Máquina de estados manual: nao_iniciada → em_andamento → concluida / em_ajuste; status_cliente: nao_enviado → enviado → aprovado / ajuste_pedido | PATCH handler com enum validation |
| §4.3 | TransicaoStatus — cada mudança de status grava registro com autor, timestamp, duracao_fase_anterior_segundos | Cálculo Python no handler; padrão ORDER BY timestamp DESC LIMIT 1 |
| §4.6 | Campos novos em Projeto: data_inicio, data_fim_contratada, tolerancia_desvio_pontos, periodo_garantia_dias | PATCH /projects/{id}/contrato + ALTER TABLE |
| Import (§5 M1) | POST /funcionalidades/importar + confirmar via LangGraph | Grafo `import_graph.py` seguindo padrão extraction_graph |
</phase_requirements>

---

## Summary

Esta fase adiciona três grupos de código ao backend FastAPI existente sem tocar em nenhum endpoint ou rota existente. O risco maior é o grafo de importação (`import_graph.py`) — novo LangGraph que produz JSON estruturado, seguindo o mesmo padrão de retry do `extraction_graph.py` já em produção. O segundo risco é a lógica de TransicaoStatus: o cálculo de `duracao_fase_anterior_segundos` depende de uma query Supabase correta (ORDER BY timestamp DESC LIMIT 1 por campo), e a inserção deve ocorrer atomicamente com o PATCH de status dentro do mesmo handler Python — sem trigger SQL.

O terceiro grupo (campos novos em Projeto e o endpoint `PATCH /projects/{id}/contrato`) é o mais simples: migration DDL + novo endpoint seguindo o padrão já existente em `routers/projects.py`.

Todos os projetos existentes sem funcionalidades cadastradas continuam funcionando: as novas tabelas são isoladas com FK referenciando `projects(id)`, e nenhum dos endpoints existentes consulta `funcionalidades` ou `transicoes_status`.

**Primary recommendation:** Construir em 3 ondas — (1) Migration + schemas + router CRUD básico; (2) PATCH de status + TransicaoStatus; (3) grafo de importação + endpoints de importar/confirmar. Cada onda é testável isoladamente.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CRUD de funcionalidades | API / Backend (FastAPI) | Database (Supabase) | Lógica de negócio no Python, persistência no Supabase |
| Validação de critérios (≥1) | API / Backend (Pydantic) | — | Pydantic `@field_validator` ou `model_validator` na camada de schema |
| Máquina de estados | API / Backend (handler) | Database (CHECK constraint opcional) | Handler verifica transição válida; enum no Pydantic garante valores |
| TransicaoStatus — cálculo de duração | API / Backend (handler) | Database (query) | Cálculo Python; query Supabase traz timestamp anterior |
| Importação via IA | API / Backend (LangGraph) | Gemini (externo) | Grafo `import_graph.py` orquestra chamada Gemini e retry |
| Revisão humana pré-salvamento | API / Backend (endpoint confirmar) | — | Dois endpoints separados — proposta nunca é persistida automaticamente |
| Campos novos de contrato | API / Backend (FastAPI) | Database (Supabase) | Novo endpoint PATCH + ALTER TABLE migration |

---

## Standard Stack

### Core (sem mudanças — reutiliza o que já existe)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | ≥0.100 | Router para funcionalidades e PATCH contrato | Padrão do projeto [VERIFIED: docudata-backend/requirements.txt:1] |
| langgraph | ≥1.0,<2 | StateGraph para import_graph | Padrão do projeto [VERIFIED: docudata-backend/requirements.txt:4] |
| langchain-core | ≥1.4.0,<2 | Messages, prompts | Padrão do projeto [VERIFIED: docudata-backend/requirements.txt:5] |
| langchain-google-genai | 4.1.1 | ChatGoogleGenerativeAI para proposta de importação | Padrão do projeto [VERIFIED: docudata-backend/requirements.txt:6] |
| supabase | ≥2.9.0,<3 | Persistência via supabase-py | Padrão do projeto [VERIFIED: docudata-backend/requirements.txt:7] |
| pydantic | ≥2.9.0 | Schemas de request/response | Padrão do projeto [VERIFIED: docudata-backend/requirements.txt:8] |

Nenhuma dependência nova é necessária para esta fase.

**Installation:** Nenhum `pip install` adicional — todas as dependências já estão em `requirements.txt`.

---

## Package Legitimacy Audit

Nenhum pacote novo é instalado nesta fase. Todas as bibliotecas utilizadas já estão em `requirements.txt` com versões fixadas e em produção nas fases anteriores.

| Package | Verdict | Disposition |
|---------|---------|-------------|
| fastapi | OK (existente) | Aprovado — já em uso |
| langgraph | OK (existente) | Aprovado — já em uso |
| langchain-google-genai | OK (existente) | Aprovado — já em uso |
| supabase | OK (existente) | Aprovado — já em uso |
| pydantic | OK (existente) | Aprovado — já em uso |

**Packages removed due to SLOP verdict:** nenhum
**Packages flagged as suspicious:** nenhum

---

## Architecture Patterns

### System Architecture Diagram

```
Gerente → POST /funcionalidades
            ↓
         [Pydantic: FuncionalidadeCreate]
            ↓ validar: criterios_aceite ≥ 1 item
            ↓
         Supabase INSERT funcionalidades
            ↓
         201 FuncionalidadeResponse

Gerente → PATCH /funcionalidades/{id}
            ↓
         [handler busca funcionalidade atual]
            ↓
         [valida transição de status/status_cliente]
            ↓
         Supabase: query transicoes_status ORDER BY timestamp DESC LIMIT 1
            ↓ calcula duracao_fase_anterior_segundos = now - timestamp_anterior
            ↓
         Supabase: UPDATE funcionalidades
         Supabase: INSERT transicoes_status
            ↓
         200 FuncionalidadeResponse

Gerente → POST /funcionalidades/importar
            ↓
         [texto_contrato no body]
            ↓
         import_graph.invoke()
            ├── gerar_proposta (Gemini: texto → lista JSON)
            ├── estruturar_json (JsonOutputParser / with_structured_output)
            └── (retry ≤2x se JSON inválido)
            ↓
         200 ImportPropostaResponse (NÃO salva nada)

Gerente → POST /funcionalidades/importar/confirmar
            ↓
         [lista de itens com confirmed: true/false]
            ↓
         [filtra confirmed=true, itera e insere cada uma]
            ↓
         Supabase: INSERT funcionalidades (confirmadas)
            ↓
         201 lista de FuncionalidadeResponse

Gerente → PATCH /projects/{id}/contrato
            ↓
         [Pydantic: ContratoUpdate]
            ↓
         Supabase: UPDATE projects SET data_inicio=..., etc.
            ↓
         200 ProjectResponse
```

### Recommended Project Structure

```
docudata-backend/
├── graphs/
│   └── import_graph.py       # NOVO — grafo de importação via IA
├── routers/
│   └── funcionalidades.py    # NOVO — CRUD + importar + importar/confirmar
├── models/
│   └── schemas.py            # ATUALIZAR — FuncionalidadeCreate, FuncionalidadeResponse,
│                             #              TransicaoStatusResponse, ImportPropostaResponse,
│                             #              ImportConfirmarRequest, ContratoUpdate
└── main.py                   # ATUALIZAR — app.include_router(funcionalidades.router)
```

### Pattern 1: Pydantic Field Validator para criterios_aceite ≥ 1

**What:** Validação em tempo de parse do request body — rejeita antes de tocar no banco.
**When to use:** Regras de negócio simples que não dependem de estado do banco.

```python
# Source: padrão Pydantic v2 — model_validator / field_validator
from pydantic import BaseModel, field_validator
from typing import Optional
import uuid
from datetime import date

class FuncionalidadeCreate(BaseModel):
    project_id: str
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]          # lista de strings — texto livre
    prioridade: str = "should"           # must | should | could | wont
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None    # UUID da sprint (FK)

    @field_validator("criterios_aceite")
    @classmethod
    def criterios_nao_vazios(cls, v: list[str]) -> list[str]:
        if not v or all(s.strip() == "" for s in v):
            raise ValueError("Ao menos um critério de aceite é obrigatório")
        return [s.strip() for s in v if s.strip()]

    @field_validator("prioridade")
    @classmethod
    def prioridade_valida(cls, v: str) -> str:
        validas = {"must", "should", "could", "wont"}
        if v not in validas:
            raise ValueError(f"prioridade deve ser um de {sorted(validas)}")
        return v
```

[VERIFIED: docudata-backend/models/schemas.py:1-17] — padrão de BaseModel + Field já usado no projeto

### Pattern 2: TransicaoStatus — cálculo de duração no handler Python

**What:** Ao receber PATCH com mudança de `status` ou `status_cliente`, o handler (1) busca a transição anterior, (2) calcula duração, (3) insere a nova transição — tudo no mesmo request.
**When to use:** Toda chamada a `PATCH /funcionalidades/{id}` que muda `status` ou `status_cliente`.

```python
# Source: padrão observado em routers/projects.py + routers/sprints.py
from datetime import datetime, timezone

async def patch_funcionalidade(funcionalidade_id: str, data: FuncionalidadeUpdate):
    client = get_client()

    # 1. Busca estado atual
    atual = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not atual.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    func = atual.data[0]

    agora = datetime.now(timezone.utc)
    updates = {}

    # 2. Para cada campo de status que mudou, registra transição
    for campo in ("status", "status_cliente"):
        novo_valor = getattr(data, campo, None)
        if novo_valor is None or novo_valor == func.get(campo):
            continue

        updates[campo] = novo_valor

        # Busca timestamp da transição anterior para esse campo
        anterior = (
            client.table("transicoes_status")
            .select("timestamp")
            .eq("funcionalidade_id", funcionalidade_id)
            .eq("campo", campo)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        if anterior.data:
            ts_anterior = datetime.fromisoformat(anterior.data[0]["timestamp"])
        else:
            # Primeira transição — usa created_at da funcionalidade
            ts_anterior = datetime.fromisoformat(func["created_at"])

        duracao = int((agora - ts_anterior.replace(tzinfo=timezone.utc)).total_seconds())

        client.table("transicoes_status").insert({
            "funcionalidade_id": funcionalidade_id,
            "campo": campo,
            "de": func[campo],
            "para": novo_valor,
            "autor": data.autor,
            "timestamp": agora.isoformat(),
            "motivo": data.motivo,
            "duracao_fase_anterior_segundos": duracao,
        }).execute()

    if not updates:
        return func  # nada mudou

    resp = client.table("funcionalidades").update(updates).eq("id", funcionalidade_id).execute()
    return resp.data[0]
```

[VERIFIED: docudata-backend/routers/projects.py:83-98] — padrão de PATCH com select-then-update

### Pattern 3: Import Graph — LangGraph seguindo padrão extraction_graph.py

**What:** StateGraph com TypedDict, nós retornando dicts parciais, retry para JSON inválido, compilado uma vez no nível do módulo.
**When to use:** `POST /funcionalidades/importar`.

```python
# Source: docudata-backend/graphs/extraction_graph.py — padrão reutilizado
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

class ImportState(TypedDict):
    texto_contrato: str
    projeto_id: str
    gemini_api_key: str
    proposta: Optional[list]   # lista de dicts de funcionalidade proposta
    valido: bool
    tentativas: int
    erro: Optional[str]

# Compilado uma vez no nível do módulo — não dentro de request handler
_builder = StateGraph(ImportState)
# ... add_node, add_edge, add_conditional_edges ...
import_graph = _builder.compile()
```

[VERIFIED: docudata-backend/graphs/extraction_graph.py:420-434] — `_builder.compile()` no nível do módulo

### Pattern 4: PATCH /projects/{id}/contrato — endpoint separado

**What:** Endpoint novo em `routers/projects.py` — mesma classe do router existente, nova rota.
**When to use:** Campos de contrato do projeto sem afetar outros endpoints.

```python
# Source: padrão de routers/projects.py:83-98 (update_api_key)
class ContratoUpdate(BaseModel):
    data_inicio: Optional[date] = None
    data_fim_contratada: Optional[date] = None
    tolerancia_desvio_pontos: Optional[int] = None
    periodo_garantia_dias: Optional[int] = None

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

[VERIFIED: docudata-backend/routers/projects.py:29-45] — padrão `_sanitize` e structure de PATCH

### Anti-Patterns to Avoid

- **Calcular duração em trigger SQL:** decisão explícita do usuário — cálculo DEVE ser em Python no handler (testável com monkeypatch). Não adicionar trigger.
- **Salvar proposta de importação automaticamente:** `POST /funcionalidades/importar` é read-only. Nunca chamar INSERT antes de `confirmar`.
- **Compilar o grafo dentro do request handler:** causa recriação do grafo a cada request. Compilar uma vez no escopo do módulo, como `extraction_graph.py` e `generation_graph.py` fazem. [VERIFIED: docudata-backend/graphs/extraction_graph.py:420-434]
- **Alterar endpoints existentes:** A fase 7 adiciona novos arquivos e rotas — nenhum endpoint existente é modificado. `routers/projects.py` recebe apenas um novo `@router.patch("/{project_id}/contrato", ...)` na classe do router existente.
- **Referenciar `sprint_alvo` como int:** O campo `sprint_alvo` na tabela `funcionalidades` é `uuid REFERENCES sprints(id)` — não o número da sprint. [VERIFIED: docudata-backend/models/schemas.py — ver padrão SprintResponse com id uuid]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parse de JSON do Gemini com retry | Loop manual de try/except | `with_structured_output` do LangChain + `_roteador` condicional existente | Padrão já testado em produção no extraction_graph |
| Validação de enum no Python | `if status not in {...}: raise` espalhado | `@field_validator` Pydantic no schema | Erro é gerado na camada de parsing com HTTP 422 automático |
| Serialização de `date` para Supabase | `str(date_obj)` manual | `pydantic.date` — supabase-py aceita ISO string diretamente | Supabase-py serializa dicts Python automaticamente |
| Cálculo de timestamps | `time.time()` ou `datetime.utcnow()` | `datetime.now(timezone.utc)` | `utcnow()` é deprecated no Python 3.12; o codebase já usa `timezone.utc` [VERIFIED: docudata-backend/routers/sprints.py:200] |

---

## Runtime State Inventory

Esta fase é **greenfield parcial** — adiciona novas tabelas e endpoints sem renomear ou migrar nada existente. Não se aplica runtime state inventory de rename/refactor.

Impacto em estado existente:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Tabelas `projects`, `ingestions`, `generated_docs`, `sprints` — sem alteração de dados | Nenhuma migration destrutiva; ALTER TABLE ADD COLUMN apenas |
| Live service config | Nenhum — nenhum endpoint existente muda | Nenhuma |
| OS-registered state | Nenhum | Nenhuma |
| Secrets/env vars | Nenhum novo — reutiliza `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Nenhuma |
| Build artifacts | Nenhum — sem build step no Railway | Nenhuma |

---

## Common Pitfalls

### Pitfall 1: `datetime.fromisoformat()` com timezone-aware strings do Supabase

**What goes wrong:** Supabase retorna timestamps como `"2026-08-22T10:00:00+00:00"`. `datetime.fromisoformat()` lida com isso no Python 3.11+, mas ao subtrair dois datetimes, um deve ser timezone-aware e o outro não pode ser naive — senão `TypeError`.

**Why it happens:** `func["created_at"]` vem como string ISO do Supabase. Se convertido sem `.replace(tzinfo=timezone.utc)` e `agora` tem tzinfo, a subtração falha.

**How to avoid:** Sempre chamar `.replace(tzinfo=timezone.utc)` no datetime parseado do banco, ou usar `datetime.fromisoformat(ts).astimezone(timezone.utc)`. O `agora` deve ser `datetime.now(timezone.utc)`.

**Warning signs:** `TypeError: can't subtract offset-naive and offset-aware datetimes` nos logs do Railway.

### Pitfall 2: `sprint_alvo` é UUID da sprint, não número

**What goes wrong:** Frontend ou testes enviam `sprint_alvo: 3` (int) esperando o número da sprint. O banco espera UUID da sprint.

**Why it happens:** A tabela `sprints` tem `id uuid` e `numero int`. O relacionamento `funcionalidades.sprint_alvo → sprints.id` usa UUID, não `numero`.

**How to avoid:** Pydantic schema declara `sprint_alvo: Optional[str] = None` (UUID como string). Documentar claramente no endpoint que o frontend deve enviar o `id` da sprint, não o número.

**Warning signs:** Erro de FK violation no Supabase — `insert or update on table "funcionalidades" violates foreign key constraint`.

### Pitfall 3: Proposta de importação vaza para o banco em caso de erro de rota

**What goes wrong:** Se o roteador de `import_graph` tiver uma edge incorreta, o nó `salvar` (se existir por acidente) pode ser executado.

**Why it happens:** O grafo de importação NÃO deve ter nó de salvar. A proposta deve terminar em `END` sem inserção no banco.

**How to avoid:** O grafo `import_graph.py` não tem nó `salvar`. O retorno do `graph.invoke()` é o estado final — o handler extrai `state["proposta"]` e retorna diretamente ao cliente. Inserção só acontece no endpoint `confirmar`.

**Warning signs:** Linhas aparecendo em `funcionalidades` após chamada a `POST /funcionalidades/importar`.

### Pitfall 4: Gemini API key vem do projeto, não do env global

**What goes wrong:** O handler de importação usa a API key do env (`os.environ["GEMINI_API_KEY"]`) mas os outros grafos buscam a key por projeto (`gemini_api_key` do projeto no Supabase).

**Why it happens:** O `extraction_graph.py` recebe `gemini_api_key` no estado, buscada pelo router de ingestão a partir do projeto. O `import_graph.py` deve seguir o mesmo padrão.

**How to avoid:** O router de funcionalidades, ao invocar `import_graph`, deve buscar a API key do projeto no Supabase (campo `gemini_api_key`) e injetar no estado — com fallback para `GEMINI_API_KEY` do env se o projeto não tiver key própria. [VERIFIED: docudata-backend/graphs/extraction_graph.py:17-19] — campo `gemini_api_key` no ExtractionState.

**Warning signs:** `AuthenticationError: API key not valid` para projetos sem key própria, ou vazamento da key global para projetos que deveriam usar key própria.

### Pitfall 5: `ProjectResponse` schema não inclui campos novos de contrato

**What goes wrong:** Após `PATCH /projects/{id}/contrato`, o response retorna `ProjectResponse` sem `data_inicio`, `data_fim_contratada`, etc. Frontend não vê os dados.

**Why it happens:** `ProjectResponse` em `schemas.py` precisa ser atualizado para incluir os 4 novos campos como `Optional`.

**How to avoid:** Atualizar `ProjectResponse` com os 4 campos opcionais antes de implementar o endpoint. [VERIFIED: docudata-backend/models/schemas.py:28-38] — definição atual de `ProjectResponse`.

---

## Code Examples

### Schema completo de FuncionalidadeCreate e FuncionalidadeResponse

```python
# Adicionar a models/schemas.py
from datetime import date, datetime
from pydantic import BaseModel, field_validator
from typing import Optional

class FuncionalidadeCreate(BaseModel):
    project_id: str
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]
    prioridade: str = "should"         # must | should | could | wont
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None  # UUID da sprint

    @field_validator("criterios_aceite")
    @classmethod
    def criterios_nao_vazios(cls, v: list[str]) -> list[str]:
        filtrados = [s.strip() for s in v if s.strip()]
        if not filtrados:
            raise ValueError("Ao menos um critério de aceite é obrigatório")
        return filtrados

    @field_validator("prioridade")
    @classmethod
    def prioridade_valida(cls, v: str) -> str:
        if v not in {"must", "should", "could", "wont"}:
            raise ValueError("prioridade deve ser must | should | could | wont")
        return v

class FuncionalidadeUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    criterios_aceite: Optional[list[str]] = None
    prioridade: Optional[str] = None
    status: Optional[str] = None          # nao_iniciada | em_andamento | concluida | em_ajuste
    status_cliente: Optional[str] = None  # nao_enviado | enviado | aprovado | ajuste_pedido
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None
    data_aprovacao_cliente: Optional[date] = None
    autor: Optional[str] = None           # para TransicaoStatus
    motivo: Optional[str] = None          # para TransicaoStatus

class FuncionalidadeResponse(BaseModel):
    id: str
    project_id: str
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]
    prioridade: str
    status: str
    status_cliente: str
    data_aprovacao_cliente: Optional[date] = None
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None
    created_at: datetime

class TransicaoStatusResponse(BaseModel):
    id: str
    funcionalidade_id: str
    campo: str
    de: str
    para: str
    autor: Optional[str] = None
    timestamp: datetime
    motivo: Optional[str] = None
    duracao_fase_anterior_segundos: Optional[int] = None

# Schemas de importação
class FuncionalidadeProposta(BaseModel):
    """Item proposto pelo Gemini — não persistido."""
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]
    prioridade: str = "should"

class ImportPropostaResponse(BaseModel):
    propostas: list[FuncionalidadeProposta]

class ImportConfirmarItem(BaseModel):
    proposta: FuncionalidadeProposta
    confirmed: bool

class ImportConfirmarRequest(BaseModel):
    project_id: str
    itens: list[ImportConfirmarItem]

# Campos novos de contrato
class ContratoUpdate(BaseModel):
    data_inicio: Optional[date] = None
    data_fim_contratada: Optional[date] = None
    tolerancia_desvio_pontos: Optional[int] = None
    periodo_garantia_dias: Optional[int] = None
```

### Migration SQL para Supabase

```sql
-- Rodar no Supabase SQL Editor

-- Tabela funcionalidades
CREATE TABLE IF NOT EXISTS funcionalidades (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  id_funcional text NOT NULL,
  titulo text NOT NULL,
  descricao text,
  criterios_aceite text[] NOT NULL,
  prioridade text NOT NULL DEFAULT 'should',
  status text NOT NULL DEFAULT 'nao_iniciada',
  status_cliente text NOT NULL DEFAULT 'nao_enviado',
  data_aprovacao_cliente date,
  responsavel text,
  sprint_alvo uuid REFERENCES sprints(id),
  created_at timestamptz DEFAULT now()
);

-- Tabela transicoes_status
CREATE TABLE IF NOT EXISTS transicoes_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  funcionalidade_id uuid REFERENCES funcionalidades(id) ON DELETE CASCADE,
  campo text NOT NULL,
  de text NOT NULL,
  para text NOT NULL,
  autor text,
  timestamp timestamptz DEFAULT now(),
  motivo text,
  duracao_fase_anterior_segundos integer
);

-- Campos novos na tabela projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS data_inicio date;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS data_fim_contratada date;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tolerancia_desvio_pontos integer DEFAULT 20;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS periodo_garantia_dias integer DEFAULT 30;
```

[VERIFIED: docudata-backend/models/schemas.py — padrão de tipos date/timestamptz mapeados como Python date/datetime]

### import_graph.py — estrutura do grafo

```python
# graphs/import_graph.py
# Source: padrão de docudata-backend/graphs/extraction_graph.py
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

class ImportState(TypedDict):
    texto_contrato: str
    projeto_id: str
    gemini_api_key: str
    proposta: Optional[list]
    valido: bool
    tentativas: int
    erro: Optional[str]

_IMPORT_SYSTEM_PROMPT = (
    "Você é um assistente especializado em quebrar o escopo de um contrato de projeto de dados "
    "em funcionalidades discretas com critérios de aceite no formato EARS "
    "(Quando [evento], o sistema deve [resposta]). "
    "Retorne APENAS um JSON com a chave 'funcionalidades' contendo uma lista de objetos com: "
    "id_funcional (string curta tipo F01, F02...), titulo, descricao (opcional), "
    "criterios_aceite (lista de strings), prioridade (must/should/could/wont)."
)
_HARDENED_SUFFIX = "\n\nRetorne APENAS JSON válido, sem texto antes ou depois, sem markdown, sem backticks."

async def gerar_proposta(state: ImportState) -> dict:
    tentativas = state["tentativas"]
    suffix = _HARDENED_SUFFIX if tentativas > 0 else ""
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        max_tokens=4096,
        google_api_key=state["gemini_api_key"],
    )
    messages = [
        SystemMessage(content=_IMPORT_SYSTEM_PROMPT),
        HumanMessage(content=f"Texto do contrato:\n\n{state['texto_contrato']}{suffix}"),
    ]
    try:
        response = await llm.ainvoke(messages)
        raw = response.content
        if isinstance(raw, list):
            raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)
        parsed = json.loads(raw.strip())
        funcionalidades = parsed.get("funcionalidades", [])
        if not funcionalidades:
            return {"valido": False, "tentativas": tentativas + 1, "erro": "Lista vazia"}
        return {"proposta": funcionalidades, "valido": True}
    except Exception as exc:
        return {"valido": False, "tentativas": tentativas + 1, "erro": str(exc)}

def _roteador(state: ImportState):
    if state["valido"]:
        return END
    if state["tentativas"] < 2:
        return "gerar_proposta"
    return END

_builder = StateGraph(ImportState)
_builder.add_node("gerar_proposta", gerar_proposta)
_builder.add_edge(START, "gerar_proposta")
_builder.add_conditional_edges("gerar_proposta", _roteador)

import_graph = _builder.compile()
```

[VERIFIED: docudata-backend/graphs/extraction_graph.py:412-434] — padrão idêntico de builder + compile

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 deprecation | `utcnow()` gera warning — usar `timezone.utc` [VERIFIED: docudata-backend/routers/sprints.py:200] |
| Pydantic v1 `@validator` | Pydantic v2 `@field_validator` com `@classmethod` | Pydantic 2.0 | O projeto usa Pydantic v2 [VERIFIED: docudata-backend/requirements.txt:8] |
| `StateGraph` com `ChannelWrite` explícito | Nós retornando dicts parciais | LangGraph 0.1+ | API estável — cada nó retorna apenas os campos que altera [VERIFIED: docudata-backend/graphs/extraction_graph.py:235-249] |

**Deprecated/outdated:**
- `dict()` em Pydantic v2: use `.model_dump()` — já correto no codebase [VERIFIED: docudata-backend/graphs/extraction_graph.py:351]
- `datetime.utcnow()`: já corrigido para `datetime.now(timezone.utc)` no codebase [VERIFIED: docudata-backend/routers/sprints.py:200]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | O frontend irá enviar `sprint_alvo` como UUID (id da sprint), não como número inteiro | Architecture Patterns — Pattern 2 | Se o frontend enviar número, o insert vai falhar com FK violation — precisaria de lookup intermediário no router |
| A2 | O Supabase aceita `date` Python serializado diretamente pelo supabase-py v2 ao fazer insert/update | Code Examples — Migration SQL | Se não aceitar, é necessário converter para `str` ISO antes do insert |
| A3 | O modelo `gemini-3.5-flash-lite` (em uso em todos os grafos) é adequado para quebrar texto de contrato em funcionalidades | import_graph.py | Se a qualidade for insuficiente, pode ser necessário usar `gemini-3.5-flash` (sem lite) — testável localmente antes do deploy |

---

## Open Questions

1. **Validação de transições de estado no backend**
   - What we know: A decisão é máquina de estados manual — o gerente é soberano
   - What's unclear: O backend deve rejeitar transições inválidas (ex: `concluida → nao_iniciada`)? Ou aceita qualquer transição?
   - Recommendation: Para o MVP, aceitar qualquer transição (gerente é soberano). A `TransicaoStatus` registra de qualquer forma. Se quiser validação, adicionar `@field_validator` em `FuncionalidadeUpdate` depois.

2. **Formato da `id_funcional` proposta pelo Gemini**
   - What we know: O Gemini vai gerar algo como `F01`, `F02`... conforme o prompt
   - What's unclear: Se o gerente precisa editar esse id antes de confirmar (pode já existir uma funcionalidade `F01` no projeto)
   - Recommendation: Para o MVP, o endpoint `confirmar` não valida unicidade de `id_funcional` por projeto. Adicionar unique constraint depois se necessário.

3. **`status_cliente = 'aprovado'` deve preencher `data_aprovacao_cliente` automaticamente?**
   - What we know: `data_aprovacao_cliente` é um campo separado na tabela
   - What's unclear: Se transição para `aprovado` deve setar `data_aprovacao_cliente = today` automaticamente no handler
   - Recommendation: Sim — ao detectar `status_cliente = 'aprovado'` no PATCH, o handler deve setar `data_aprovacao_cliente = date.today()` no update se não vier explicitamente no body.

---

## Environment Availability

Esta fase não adiciona dependências externas novas. Todos os serviços já estão em uso.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Supabase (Cloud) | Persistência de funcionalidades e transicoes_status | Sim | — | — |
| Gemini API | import_graph — gerar proposta | Sim | gemini-3.5-flash-lite | — |
| FastAPI/uvicorn | Novos endpoints | Sim | ≥0.100 | — |
| LangGraph | import_graph | Sim | ≥1.0,<2 | — |

---

## Validation Architecture

> `nyquist_validation` está explicitamente `false` em `.planning/config.json` [VERIFIED: .planning/config.json:19]. Seção omitida conforme instrução.

---

## Security Domain

> `security_enforcement` não está configurado explicitamente (ausente = habilitado).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Não (sem auth no MVP) | — (decisão de escopo) |
| V3 Session Management | Não | — |
| V4 Access Control | Não (sem isolamento por usuário no MVP) | — |
| V5 Input Validation | Sim | Pydantic `@field_validator` — criterios_aceite, prioridade, status, status_cliente |
| V6 Cryptography | Não | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Texto de contrato muito grande enviado ao Gemini | Tampering / DoS | Truncar input em `import_graph` antes de invocar LLM (ex: primeiros 50.000 chars, padrão do `preprocessar_arquivo`) |
| Injeção de SQL via id_funcional | Tampering | supabase-py usa queries parametrizadas — sem risco de SQL injection |
| Vazamento de gemini_api_key do projeto no response de funcionalidades | Information Disclosure | O campo `gemini_api_key` nunca retorna na resposta — padrão `_sanitize` já em projects.py [VERIFIED: docudata-backend/routers/projects.py:23-26] |

---

## Sources

### Primary (HIGH confidence)

- `docudata-backend/graphs/extraction_graph.py` — padrão LangGraph StateGraph completo lido e verificado
- `docudata-backend/graphs/generation_graph.py` — padrão de grafo simples sem multimodal
- `docudata-backend/routers/projects.py` — padrão de router FastAPI + supabase-py
- `docudata-backend/routers/sprints.py` — padrão de PATCH com datetime.now(timezone.utc)
- `docudata-backend/models/schemas.py` — padrões Pydantic v2 existentes
- `docudata-backend/requirements.txt` — versões fixadas de todas as dependências
- `docudata-backend/supabase_schema.sql` — schema atual do banco
- `.planning/phases/07-matriz-de-escopo-transicaostatus-campos-novos-em-projeto/07-CONTEXT.md` — decisões locked

### Secondary (MEDIUM confidence)

- `.planning/ROADMAP.md` — success criteria da fase 7
- `docudata-backend/tests/test_project_usage.py` — padrão de teste com monkeypatch

### Tertiary (LOW confidence)

- Nenhuma fonte de baixa confiança usada — toda pesquisa foi no codebase real.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — lido diretamente de `requirements.txt`
- Architecture: HIGH — padrões verificados no codebase real
- Pitfalls: HIGH — derivados de comportamentos reais observados no código
- SQL migration: HIGH — lido de `07-CONTEXT.md` e verificado contra `supabase_schema.sql`

**Research date:** 2026-08-22
**Valid until:** 2026-09-22 (stack estável — sem atualização de dependências prevista)
