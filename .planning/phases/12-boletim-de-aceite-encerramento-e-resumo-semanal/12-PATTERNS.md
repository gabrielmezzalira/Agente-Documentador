# Phase 12: Boletim de Aceite, Encerramento e Resumo Semanal - Pattern Map

**Mapped:** 2026-08-23
**Files analyzed:** 6 new/modified files
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `docudata-backend/routers/boletins.py` | router | CRUD + request-response | `docudata-backend/routers/composer.py` | exact |
| `docudata-backend/models/schemas.py` | model | transform | `docudata-backend/models/schemas.py` (existing, extend) | exact |
| `docudata-backend/main.py` | config | — | `docudata-backend/main.py` (existing, extend) | exact |
| `docudata-frontend/app/components/AceiteTab.tsx` | component | request-response | `docudata-frontend/app/components/PlanningTab.tsx` (implied by pattern) | role-match |
| `docudata-frontend/app/projects/[id]/page.tsx` | component | — | itself (existing, extend) | exact |
| `docudata-frontend/app/lib/api.ts` | utility | request-response | itself (existing, extend) | exact |

---

## Pattern Assignments

### `docudata-backend/routers/boletins.py` (router, CRUD + request-response)

**Analog:** `docudata-backend/routers/composer.py`

**Imports pattern** (composer.py lines 1-11):
```python
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, field_validator

from services.supabase_client import get_client

router = APIRouter(prefix="/boletins", tags=["boletins"])
```

**System prompt pattern** (composer.py lines 17-27):
```python
_BOLETIM_SYSTEM_PROMPT = """Você é um assistente especializado em comunicação com clientes de projetos de dados do CITi.
Sua tarefa é gerar um Boletim de Aceite em markdown, em português, de forma clara e acessível para um cliente não técnico.

O boletim deve conter:
1. **Título** — nome do projeto e identificação do lote de funcionalidades
2. **Funcionalidades para Aceite** — para cada funcionalidade: nome e critérios de aceite em linguagem de negócio (sem jargão técnico)
3. **Instruções para Aceite** — como o cliente deve registrar o retorno (aprovado ou ajuste pedido)

Reescreva os critérios de aceite em linguagem acessível ao cliente — sem termos técnicos como "endpoint", "payload", "UUID".
Retorne APENAS o markdown, sem texto antes ou depois, sem blocos de código, sem backticks."""
```

**Gemini call pattern** (composer.py lines 416-433):
```python
api_key = project.get("gemini_api_key") or ""
if not api_key:
    raise HTTPException(
        status_code=422,
        detail="Este projeto não tem uma chave de API do Gemini configurada.",
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",   # D-02 especifica gemini-1.5-flash — verificar disponibilidade com a chave
    max_tokens=2048,
    google_api_key=api_key,
)
try:
    result = await llm.ainvoke(
        [
            SystemMessage(content=_BOLETIM_SYSTEM_PROMPT),
            HumanMessage(content=contexto),
        ]
    )
    markdown: str = result.content  # type: ignore[assignment]
except Exception as exc:
    raise HTTPException(status_code=502, detail=f"Gemini failed: {exc}")
```

**TransicaoStatus batch pattern** (funcionalidades.py lines 279-307 — replicar por funcionalidade do lote):
```python
agora = datetime.now(timezone.utc)
for campo in ("status", "status_cliente"):
    novo_valor = getattr(data, campo, None)
    if novo_valor is None or novo_valor == func.get(campo):
        continue
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
        ts_anterior = datetime.fromisoformat(anterior.data[0]["timestamp"]).replace(tzinfo=timezone.utc)
    else:
        ts_anterior = datetime.fromisoformat(func["created_at"]).replace(tzinfo=timezone.utc)
    duracao = int((agora - ts_anterior).total_seconds())
    client.table("transicoes_status").insert({
        "funcionalidade_id": funcionalidade_id,
        "campo": campo,
        "de": func[campo],
        "para": novo_valor,
        "autor": None,
        "timestamp": agora.isoformat(),
        "motivo": None,
        "duracao_fase_anterior_segundos": duracao,
    }).execute()
```

**Resumo semanal — reutilização de painel.py** (painel.py lines 34-164):
```python
# Importar diretamente as funções de cálculo
from routers.painel import calcular_bloco_a, calcular_bloco_b

# Período da semana (D-09: dom–sáb)
from datetime import date, timedelta
hoje = date.today()
dias_desde_domingo = (hoje.weekday() + 1) % 7  # weekday(): 0=seg, 6=dom
inicio_semana = hoje - timedelta(days=dias_desde_domingo)
fim_semana = inicio_semana + timedelta(days=6)

# Salvar em generated_docs (D-10)
client.table("generated_docs").insert({
    "project_id": project_id,
    "doc_type": "resumo_semanal",
    "sprint_number": None,
    "content": markdown_gerado,
    "input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0.0,
}).execute()
```

**Status transition validation — PATCH handler:**
```python
# Transições válidas: rascunho → enviado, enviado → aprovado, enviado → ajuste
TRANSICOES_VALIDAS = {
    "rascunho": {"enviado"},
    "enviado": {"aprovado", "ajuste"},
}
if novo_status not in TRANSICOES_VALIDAS.get(boletim["status"], set()):
    raise HTTPException(status_code=422, detail=f"Transição inválida: {boletim['status']} → {novo_status}")

# Classificação obrigatória para ajuste (D-06)
if novo_status == "ajuste" and body.retorno_tipo not in ("bug", "mudanca_escopo"):
    raise HTTPException(
        status_code=422,
        detail="retorno_tipo é obrigatório quando status = ajuste (valores aceitos: bug, mudanca_escopo)",
    )
```

---

### `docudata-backend/models/schemas.py` (model, extend existing)

**Analog:** `docudata-backend/models/schemas.py` (existing patterns)

**Existing Pydantic pattern** (schemas.py lines 1-8, 33-58):
```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime

class BoletimCreate(BaseModel):
    project_id: str
    sprint_numero: Optional[int] = None
    funcionalidade_ids: list[str]  # UUIDs como strings — text[] no Supabase

class BoletimPatch(BaseModel):
    status: str  # enviado | aprovado | ajuste
    retorno_tipo: Optional[str] = None  # obrigatório se status=ajuste

class BoletimResponse(BaseModel):
    id: str
    project_id: str
    sprint_numero: Optional[int]
    funcionalidade_ids: list[str]
    status: str
    retorno_tipo: Optional[str]
    conteudo: str
    criado_em: datetime
    enviado_em: Optional[datetime]
    retorno_em: Optional[datetime]

class ResumoSemanalRequest(BaseModel):
    project_id: str
```

---

### `docudata-backend/main.py` (config, extend existing)

**Analog:** `docudata-backend/main.py` (lines 6, 30-31 — add boletins to import and include_router)

**Router registration pattern** (main.py lines 6 and 18-30):
```python
# Linha 6 — adicionar boletins ao import:
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich, funcionalidades, painel, revisao_ingest, composer, aceite_ingest, boletins

# Após os include_router existentes:
app.include_router(boletins.router)
```

---

### `docudata-frontend/app/components/AceiteTab.tsx` (component, request-response)

**Analog:** PlanningTab pattern (same project, same phase style: zero className, style={{}} only, ReactMarkdown preview, multi-step flow)

**Zero-className style pattern** (page.tsx lines 489-510 — representative inline style):
```tsx
<div style={{
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 16,
  marginTop: 4,
}}>
```

**ReactMarkdown usage** (page.tsx line 6 — already imported):
```tsx
import ReactMarkdown from "react-markdown";
// Usage:
<ReactMarkdown>{conteudoBoletim}</ReactMarkdown>
```

**Two-section structure for AceiteTab:**
```tsx
"use client";
import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import {
  listBoletins,
  createBoletim,
  patchBoletim,
  gerarResumoSemanal,
  listDocs,
  type BoletimResponse,
  type FuncionalidadeResponse,
  type GeneratedDoc,
} from "../lib/api";

// Props: project_id, funcionalidades (concluidas), geminiApiKey
// State: boletins[], resumos[], selectedFuncIds[], preview, activeBoletim, loading
// Sections: (1) Boletins — lista + Novo Boletim flow, (2) Resumo Semanal — histórico + botão
// Badge "Projeto encerrado" quando todas funcionalidades.status_cliente === "aprovado"
```

---

### `docudata-frontend/app/projects/[id]/page.tsx` (component, extend existing)

**Analog:** itself — extend at two points

**TabId extension** (page.tsx line 48):
```typescript
// DE:
type TabId = "sprints" | "painel" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config" | "planning";
// PARA:
type TabId = "sprints" | "painel" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config" | "planning" | "aceite";
```

**Tabs array extension** (page.tsx lines 470-483):
```tsx
<Tabs
  tabs={[
    { id: "sprints", label: "Sprints", badge: totalPendencias > 0 ? `${totalPendencias} pend.` : undefined },
    { id: "painel", label: "Painel" },
    { id: "tecnologias", label: "Tecnologias" },
    { id: "cross_sprint", label: "Cross-sprint" },
    { id: "documentos", label: "Documentos", badge: docs.length || undefined },
    { id: "custos", label: "Custos" },
    { id: "config", label: "Configurações" },
    { id: "planning", label: "Planning" },
    { id: "aceite", label: "Aceite" },   // ADICIONAR
  ]}
  active={activeTab}
  onChange={(t) => setActiveTab(t as TabId)}
/>
```

**Tab render pattern** (page.tsx lines 486-487):
```tsx
{activeTab === "aceite" && (
  <AceiteTab projectId={project.id} funcionalidades={funcionalidades} geminiApiKey={project.has_api_key} />
)}
```

---

### `docudata-frontend/app/lib/api.ts` (utility, extend existing)

**Analog:** itself — extend with new types and fetch functions

**FuncionalidadeResponse type update** (api.ts line 660 — CRITICAL):
```typescript
// DE:
status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado";
// PARA:
status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado" | "ajuste_pedido";
```

**New types to add:**
```typescript
export interface BoletimResponse {
  id: string;
  project_id: string;
  sprint_numero?: number | null;
  funcionalidade_ids: string[];
  status: "rascunho" | "enviado" | "aprovado" | "ajuste";
  retorno_tipo?: "bug" | "mudanca_escopo" | null;
  conteudo: string;
  criado_em: string;
  enviado_em?: string | null;
  retorno_em?: string | null;
}
```

**Fetch function pattern** (existing api.ts style — base URL + fetch):
```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function createBoletim(body: {
  project_id: string;
  sprint_numero?: number | null;
  funcionalidade_ids: string[];
}): Promise<BoletimResponse> {
  const res = await fetch(`${BASE}/boletins`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function patchBoletim(
  id: string,
  body: { status: string; retorno_tipo?: string }
): Promise<BoletimResponse> {
  const res = await fetch(`${BASE}/boletins/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listBoletins(projectId: string): Promise<BoletimResponse[]> {
  const res = await fetch(`${BASE}/boletins/${projectId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function gerarResumoSemanal(projectId: string): Promise<{ content: string }> {
  const res = await fetch(`${BASE}/boletins/resumo_semanal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

---

## Shared Patterns

### Supabase client
**Source:** `docudata-backend/services/supabase_client.py`
**Apply to:** `boletins.py`
```python
from services.supabase_client import get_client
client = get_client()
```

### Error handling (FastAPI)
**Source:** `docudata-backend/routers/composer.py` lines 421-430
**Apply to:** `boletins.py` — Gemini call wrapper + 404 guard
```python
try:
    result = await llm.ainvoke([...])
except Exception as exc:
    raise HTTPException(status_code=502, detail=f"Gemini failed: {exc}")

# 404 guard:
if not resp.data:
    raise HTTPException(status_code=404, detail="Boletim not found")
```

### Zero className rule
**Source:** Decisions D-14 (all phases 8–12)
**Apply to:** `AceiteTab.tsx` and any JSX changes in `page.tsx`
All styles via `style={{}}` — no Tailwind classes, no CSS modules, no className.

### painel.py calcular_bloco_b signature
**Source:** `docudata-backend/routers/painel.py` lines 69-164
**Apply to:** `boletins.py` (resumo semanal endpoint)
```python
def calcular_bloco_b(
    funcs: list[dict],
    transicoes: list[dict],
    revisao_recente: dict | None = None,
    execucoes_aceite: list[dict] | None = None
) -> dict:
    # Returns: travadas, aguardando_cliente, em_ajuste, achados_criticos,
    #          relatorio_gerente, relatorio_tecnico, data_revisao,
    #          funcionalidades_com_aceite_falhando
```

### generated_docs insert pattern
**Source:** `docudata-backend/routers/generate.py` (generation_graph saves to generated_docs)
**Apply to:** `boletins.py` (resumo_semanal endpoint only — NOT for boletim itself)
```python
client.table("generated_docs").insert({
    "project_id": project_id,
    "doc_type": "resumo_semanal",
    "sprint_number": None,
    "content": markdown_content,
    "input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0.0,
}).execute()
```

---

## No Analog Found

All files have close analogs. No entries needed.

---

## Metadata

**Analog search scope:** `docudata-backend/routers/`, `docudata-backend/models/`, `docudata-backend/main.py`, `docudata-frontend/app/projects/[id]/page.tsx`, `docudata-frontend/app/lib/api.ts`
**Files scanned:** 7 files read directly
**Pattern extraction date:** 2026-08-23
