# Phase 10: Composer de Planning — Research

**Researched:** 2026-08-23
**Domain:** FastAPI + Next.js — wizard de 4 passos com estado persistido por sessão no Supabase
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Nova tabela `planning_rascunhos` no Supabase — campos: id uuid PK, project_id uuid FK→projects, sprint_numero int NOT NULL, step_atual int NOT NULL DEFAULT 1, dados_json jsonb NOT NULL DEFAULT '{}', created_at timestamptz, updated_at timestamptz. UNIQUE (project_id, sprint_numero).
- **D-02:** Rascunho deletado ao confirmar o planning oficial (POST /composer/confirmar bem-sucedido).
- **D-03:** Recorte = lista de índices. `dados_json.recortes: { [funcionalidade_id]: number[] }`. Ex: `{"abc-123": [0, 2]}`.
- **D-04:** Recorte obrigatório — botão "Próximo" do passo 2 desabilitado enquanto alguma funcionalidade selecionada não tiver nenhum índice marcado.
- **D-05:** Gemini (`gemini-3.5-flash-lite`) gera o texto do planning.
- **D-06:** Preview via react-markdown no passo 4 + botão "Confirmar Planning".
- **D-07:** POST /composer/confirmar — salva em `generated_docs` com `doc_type='planning'` + deleta rascunho.
- **D-08:** Nova aba "Planning" no Tabs.tsx existente.
- **D-09:** Steps horizontais no topo + painel de conteúdo abaixo. Zero className — todos os estilos via `style={{...}}` objects.
- **D-10:** Tela de boas-vindas quando não há rascunho ativo — exibe throughput das últimas 3 sprints + botão "Iniciar Planning da Sprint N".

### Claude's Discretion

- Estrutura completa do `dados_json`: `{ funcionalidades_selecionadas: string[], recortes: Record<string, number[]>, alocacoes: Record<string, string>, transbordos: string[] }`. `transbordos` = funcionalidade_ids com `sprint_alvo == sprint_numero - 1` e `status != 'concluida'`.
- Throughput das últimas 3 sprints: calculado no endpoint `GET /composer/rascunho/{project_id}/{sprint_numero}` retornando também `throughput_ref`.
- Endpoints: `GET /composer/rascunho/{project_id}/{sprint_numero}`, `PATCH /composer/rascunho/{project_id}/{sprint_numero}`, `POST /composer/gerar`, `POST /composer/confirmar`.
- Funcionalidades transbordadas: `sprint_alvo == sprint_numero - 1 AND status != 'concluida'`.

### Deferred Ideas (OUT OF SCOPE)

- Histórico de plannings anteriores na aba Planning.
- Edição inline do markdown no preview.
- Múltiplos rascunhos por sprint.
- Notificação quando planning é confirmado.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| M4 (§5) | Composer de Planning — wizard 4 passos com estado persistido, transbordos, throughput de referência, recorte de critérios, template preenchido automaticamente, confirmação humana explícita | Coberto pela tabela `planning_rascunhos` (D-01), endpoints /composer/*, PlanningTab.tsx wizard, lógica de throughput via `calcular_bloco_c` adaptada para janela de 3 sprints |
</phase_requirements>

---

## Summary

A Phase 10 adiciona um wizard de 4 passos ao dashboard do projeto para compor o planning de uma sprint. O estado do rascunho é persistido em uma nova tabela Supabase (`planning_rascunhos`) entre sessões, permitindo ao gerente sair e voltar sem perder progresso. Quatro endpoints FastAPI em `/composer/*` gerenciam o ciclo de vida do rascunho. O frontend adiciona uma aba "Planning" ao `Tabs.tsx` existente e renderiza o wizard com o padrão de zero-className/inline-style estabelecido em `PainelTab.tsx`. O Gemini (`gemini-3.5-flash-lite`) gera o texto final do planning a partir dos dados estruturados do rascunho; o gerente confirma explicitamente antes de oficializar.

A principal reutilização de código existente é: `calcular_bloco_c` em `painel.py` para throughput de referência (calculado sobre as últimas 3 sprints como janela temporal), `FuncionalidadeResponse` do `schemas.py` (campo `criterios_aceite: list[str]` com índices simples), e o padrão de chamada Gemini de `commit_ingest.py` (linha 129–146). O `generated_docs` recebe o planning com `doc_type='planning'`, mesmo campo já existente na tabela — nenhuma alteração de schema em tabelas existentes.

**Primary recommendation:** Implementar os 4 endpoints `/composer/*` como um único router FastAPI (`routers/composer.py`), registrá-lo em `main.py`, criar `planning_rascunhos` via migration SQL, e o componente `PlanningTab.tsx` seguindo byte-a-byte o padrão de `PainelTab.tsx`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Persistência do rascunho entre sessões | API/Backend (Supabase) | — | Estado deve sobreviver a troca de browser/máquina — não pode ser localStorage |
| Cálculo de throughput de referência | API/Backend | — | Dados em `transicoes_status` — lógica Python já existe em `calcular_bloco_c` |
| Detecção de transbordos | API/Backend (GET rascunho) | — | Query em `funcionalidades` com filtros `sprint_alvo` e `status` |
| Wizard de 4 passos (UI) | Frontend (Next.js) | — | Estado local do step ativo, renderização condicional por step |
| Validação do recorte (D-04) | Frontend | — | Regra de UI — botão desabilitado, não é validação de negócio no backend |
| Geração do markdown via Gemini | API/Backend (POST /composer/gerar) | — | Gemini API key está no projeto (backend) — não exposta ao frontend |
| Confirmação e oficialização | API/Backend (POST /composer/confirmar) | — | Atomicidade: insert generated_docs + delete rascunho numa transação lógica |
| Renderização do markdown de preview | Frontend (react-markdown) | — | Já presente no projeto: `"react-markdown": "^9.0.1"` em package.json |

---

## Standard Stack

### Core (já presente no projeto — sem instalação necessária)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `react-markdown` | `^9.0.1` | Renderizar markdown do Gemini no preview (passo 4) | Já presente em `package.json` [VERIFIED: docudata-frontend/package.json:14] |
| `langchain-google-genai` | projeto atual | Chamar Gemini com `ChatGoogleGenerativeAI` | Padrão estabelecido em `commit_ingest.py` e `revisao_ingest.py` |
| `supabase-py` | projeto atual | CRUD em `planning_rascunhos` via `get_client()` | Padrão em todos os routers |
| `fastapi` | projeto atual | Router `/composer` com 4 endpoints | Stack definida |

### Sem novas dependências

Todos os packages necessários já estão instalados. A Phase 10 não adiciona nenhum novo `pip install` ou `npm install`.

---

## Package Legitimacy Audit

> Nenhum pacote novo a instalar nesta fase. Todos os pacotes utilizados são do stack existente do projeto.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious SUS:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Frontend (Next.js)
  PlanningTab.tsx
    ├── Tela de boas-vindas
    │     └── GET /composer/rascunho/{project_id}/{sprint_numero}
    │           → cria rascunho se não existe, retorna {rascunho, throughput_ref, transbordos}
    │
    ├── Step 1: Seleção
    │     ├── lista funcionalidades do projeto
    │     ├── transbordos marcados no topo (badge "Transbordado")
    │     └── PATCH /composer/rascunho/{project_id}/{sprint_numero}
    │           {step_atual: 1, dados_json: {funcionalidades_selecionadas: [...], transbordos: [...]}}
    │
    ├── Step 2: Recorte
    │     ├── por funcionalidade selecionada: checkboxes nos criterios_aceite (por índice)
    │     ├── validação: nenhum "Próximo" se alguma func sem índice marcado
    │     └── PATCH /composer/rascunho (step_atual: 2, dados_json.recortes: {...})
    │
    ├── Step 3: Alocação
    │     ├── input de responsável por funcionalidade
    │     └── PATCH /composer/rascunho (step_atual: 3, dados_json.alocacoes: {...})
    │
    └── Step 4: Composição
          ├── POST /composer/gerar → {markdown: "..."}   (Gemini, não salva)
          ├── <ReactMarkdown>{markdown}</ReactMarkdown>
          └── POST /composer/confirmar → {doc_id, content}
                → insert generated_docs (doc_type='planning')
                → delete planning_rascunhos

Backend (FastAPI)
  routers/composer.py
    GET  /composer/rascunho/{project_id}/{sprint_numero}
         → upsert planning_rascunhos
         → calcular throughput das últimas 3 sprints (via calcular_bloco_c adaptado)
         → detectar transbordos (funcionalidades com sprint_alvo=N-1 AND status!='concluida')
         → return {rascunho, throughput_ref, transbordos}

    PATCH /composer/rascunho/{project_id}/{sprint_numero}
         → update planning_rascunhos SET step_atual=?, dados_json=?, updated_at=now()

    POST /composer/gerar
         → monta prompt com dados_json do rascunho + funcionalidades completas
         → ChatGoogleGenerativeAI(gemini-3.5-flash-lite).ainvoke(...)
         → return {markdown: "..."}   ← NÃO persiste

    POST /composer/confirmar
         → insert generated_docs (doc_type='planning', sprint_number=N, content=markdown)
         → delete planning_rascunhos WHERE project_id=? AND sprint_numero=?
         → return {doc_id, content}

Supabase
  planning_rascunhos   ← nova tabela (migration SQL Phase 10)
  generated_docs       ← tabela existente, recebe doc_type='planning'
  funcionalidades      ← tabela existente, lida em GET rascunho e POST gerar
  transicoes_status    ← tabela existente, usada para calcular throughput_ref
```

### Recommended Project Structure

```
docudata-backend/
└── routers/
    └── composer.py          # novo — 4 endpoints /composer/*

docudata-frontend/app/
└── components/
    └── PlanningTab.tsx      # novo — wizard 4 passos (zero className, inline style)

docudata-backend/
└── supabase_schema.sql      # atualizado — CREATE TABLE planning_rascunhos + migration comment
```

---

## Exact Existing Patterns (VERIFIED — ler antes de implementar)

### Pattern 1: Router FastAPI com prefix e tags

[VERIFIED: docudata-backend/routers/funcionalidades.py:18]

```python
router = APIRouter(prefix="/funcionalidades", tags=["funcionalidades"])
```

O composer deve seguir exatamente:

```python
router = APIRouter(prefix="/composer", tags=["composer"])
```

Registrar em `main.py` seguindo o padrão da linha 6 e 29:

```python
# main.py linha 6 — import
from routers import ..., composer

# main.py linha ~31 — registro
app.include_router(composer.router)
```

[VERIFIED: docudata-backend/main.py:6-30]

### Pattern 2: get_client() e query Supabase

[VERIFIED: docudata-backend/services/supabase_client.py:1-14]

```python
from services.supabase_client import get_client

client = get_client()
resp = client.table("planning_rascunhos").select("*").eq("project_id", project_id).eq("sprint_numero", sprint_numero).execute()
```

`get_client()` cria um novo client a cada chamada (lazy factory). O padrão é chamar dentro do handler, não no módulo.

### Pattern 3: Chamada Gemini (padrão de commit_ingest.py)

[VERIFIED: docudata-backend/routers/commit_ingest.py:129-146]

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    max_tokens=2048,
    google_api_key=api_key,
)

try:
    result = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])
    markdown = result.content
except Exception as exc:
    raise HTTPException(status_code=502, detail=f"Gemini failed: {exc}")
```

Para o `/composer/gerar`, não usar `with_structured_output` — queremos texto livre (markdown). Usar `StrOutputParser` ou acessar `result.content` diretamente.

Buscar `api_key` do projeto antes de invocar:

```python
proj = client.table("projects").select("gemini_api_key").eq("id", project_id).execute()
if not proj.data:
    raise HTTPException(status_code=404, detail="Project not found")
api_key = (proj.data[0].get("gemini_api_key") or "").strip()
if not api_key:
    raise HTTPException(status_code=422, detail="Este projeto não tem uma chave de API do Gemini configurada.")
```

### Pattern 4: Insert em generated_docs (padrão de sprint_docs.py)

[VERIFIED: docudata-backend/routers/sprint_docs.py:198-223]

O `generated_docs` tem os campos (verificado em supabase_schema.sql:51-60):
`id, project_id, doc_type, sprint_number, content, input_tokens, output_tokens, cost_usd, created_at`

Para o `/composer/confirmar`:

```python
client = get_client()
resp = client.table("generated_docs").insert({
    "project_id": project_id,
    "doc_type": "planning",
    "sprint_number": sprint_numero,
    "content": markdown,
    "input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0,
}).execute()
if not resp.data:
    raise HTTPException(status_code=500, detail="Failed to save planning doc")
doc_id = resp.data[0]["id"]

# Depois deletar o rascunho
client.table("planning_rascunhos").delete().eq("project_id", project_id).eq("sprint_numero", sprint_numero).execute()
```

### Pattern 5: Tabs.tsx — como adicionar nova aba

[VERIFIED: docudata-frontend/app/components/Tabs.tsx:3-6 e app/projects/[id]/page.tsx:47,470-481]

O `Tabs` recebe `tabs: TabItem[]` onde `TabItem = { id: string; label: string; badge?: number | string }`. A aba "Planning" deve ser adicionada como:

```typescript
// page.tsx linha 47 — ampliar o tipo
type TabId = "sprints" | "painel" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config" | "planning";

// page.tsx no array de tabs (linha 470-478)
{ id: "planning", label: "Planning" },

// page.tsx — renderização condicional (mesma estrutura das outras abas)
{activeTab === "planning" && (
  <PlanningTab projectId={id} sprints={sprints} />
)}
```

### Pattern 6: PainelTab.tsx — padrão zero-className, inline style

[VERIFIED: docudata-frontend/app/components/PainelTab.tsx:1-728]

Regras extraídas do arquivo:
- Nunca usar `className`. Todos os estilos são objetos `React.CSSProperties` atribuídos à prop `style`.
- Constantes de estilo declaradas fora do componente (ex: `cardStyle`, `cardTitleStyle`).
- Loading state: `if (loading) return (<section style={cardStyle}><p style={{color: "#9696a0", fontSize: 14, margin: 0}}>Carregando…</p></section>)`.
- Error state: `if (error) return (<section style={cardStyle}><p style={{color: "#dc2626", ...}}>{error}</p></section>)`.
- Paleta de cores do projeto:
  - background principal: `#f7f7fa`
  - cards: `background: "#ffffff", border: "1px solid #e8e8ed", borderRadius: 14`
  - texto primário: `#111116`
  - texto secundário: `#9696a0`
  - verde (ativo, badge): `#4ade80` / `#16a34a` / `#dcfce7`
  - amarelo (aviso): `#fef9c3` / `#a16207`
  - vermelho (erro): `#fee2e2` / `#dc2626`
  - laranja (alerta): `#ffedd5` / `#c2410c`
  - roxo (sprint): `#ede9fe` / `#7c3aed`

Badge "Transbordado" deve usar a paleta laranja: `background: "#ffedd5", color: "#c2410c"`.

### Pattern 7: api.ts — estrutura de função fetch

[VERIFIED: docudata-frontend/app/lib/api.ts:1-2, 158-162]

```typescript
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Exemplo: GET com path params
export async function getRascunho(projectId: string, sprintNumero: number): Promise<RascunhoData> {
  const res = await fetch(`${API}/composer/rascunho/${projectId}/${sprintNumero}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao buscar rascunho");
  }
  return res.json();
}

// Exemplo: PATCH com JSON body
export async function patchRascunho(projectId: string, sprintNumero: number, payload: {
  step_atual: number;
  dados_json: DadosJson;
}): Promise<RascunhoData> {
  const res = await fetch(`${API}/composer/rascunho/${projectId}/${sprintNumero}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao salvar rascunho");
  }
  return res.json();
}
```

---

## SQL para a Tabela Nova

[VERIFIED: docudata-backend/supabase_schema.sql:1-113]

A tabela deve ser adicionada ao `supabase_schema.sql` com o padrão de formatação existente (linha 80-97 como referência):

```sql
-- Phase 10: Composer de Planning
CREATE TABLE IF NOT EXISTS planning_rascunhos (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_numero int         NOT NULL,
    step_atual    int         NOT NULL DEFAULT 1,
    dados_json    jsonb       NOT NULL DEFAULT '{}',
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now(),
    UNIQUE (project_id, sprint_numero)
);

-- Se a tabela já existe, rode apenas:
-- CREATE TABLE IF NOT EXISTS planning_rascunhos (...);
```

---

## Endpoint Structure Completo

### GET /composer/rascunho/{project_id}/{sprint_numero}

**Comportamento:** Upsert — cria rascunho se não existe, retorna se existe. Retorna também `throughput_ref` e `transbordos` para evitar chamadas extras do frontend.

**Response:**
```json
{
  "rascunho": {
    "id": "uuid",
    "project_id": "uuid",
    "sprint_numero": 3,
    "step_atual": 2,
    "dados_json": {
      "funcionalidades_selecionadas": ["uuid1", "uuid2"],
      "recortes": {"uuid1": [0, 2]},
      "alocacoes": {"uuid1": "Gabriel"},
      "transbordos": ["uuid3"]
    },
    "created_at": "...",
    "updated_at": "..."
  },
  "throughput_ref": 2.5,
  "transbordos": [
    {"id": "uuid3", "titulo": "Análise exploratória", "sprint_alvo": "2", "status": "em_andamento", "criterios_aceite": [...]}
  ]
}
```

**Lógica de throughput_ref:** Calcular throughput médio das últimas 3 sprints anteriores à `sprint_numero` (sprints N-1, N-2, N-3). Reutilizar `calcular_bloco_c` de `painel.py` passando apenas as funcionalidades e transições dessas sprints. Ver seção "Throughput de Referência" abaixo.

### PATCH /composer/rascunho/{project_id}/{sprint_numero}

**Body:**
```json
{
  "step_atual": 2,
  "dados_json": {
    "funcionalidades_selecionadas": ["uuid1"],
    "recortes": {"uuid1": [0, 1]},
    "alocacoes": {},
    "transbordos": []
  }
}
```

**Comportamento:** UPDATE SET step_atual, dados_json, updated_at=now(). 404 se rascunho não existe (o frontend sempre chama GET antes de PATCH).

### POST /composer/gerar

**Body:**
```json
{
  "project_id": "uuid",
  "sprint_numero": 3
}
```

**Comportamento:** Lê rascunho e funcionalidades do Supabase, monta prompt, chama Gemini. NÃO persiste. Retorna markdown.

**Response:**
```json
{
  "markdown": "# Planning — Sprint 3\n\n## Funcionalidades\n..."
}
```

**Erro:** HTTPException 502 se Gemini falhar (padrão de `commit_ingest.py:146`).

### POST /composer/confirmar

**Body:**
```json
{
  "project_id": "uuid",
  "sprint_numero": 3,
  "markdown": "# Planning — Sprint 3\n..."
}
```

**Comportamento:** Insere em `generated_docs` (doc_type='planning') + deleta rascunho. Retorna o doc criado.

**Response:**
```json
{
  "doc_id": "uuid",
  "content": "# Planning...",
  "created_at": "..."
}
```

---

## Throughput de Referência — Estratégia de Implementação

**O que `calcular_bloco_c` faz:**
[VERIFIED: docudata-backend/routers/painel.py:147-202]

A função recebe `funcs: list[dict]` e `transicoes: list[dict]` e retorna `{"throughput_por_semana": float, "wip": int, "cycle_time_p50_dias": float|None, "cycle_time_p85_dias": float|None, "total_concluidas": int}`.

O `throughput_por_semana` é calculado como `total_concluidas / weeks` onde `weeks` é o tempo desde a criação da funcionalidade mais antiga. Esse cálculo usa todo o histórico do projeto — não por sprint.

**Adaptação necessária para throughput_ref (últimas 3 sprints):**

No endpoint `GET /composer/rascunho`, implementar uma função auxiliar:

```python
def calcular_throughput_ref(project_id: str, sprint_numero: int, client) -> float | None:
    """Throughput médio das últimas 3 sprints anteriores (N-1, N-2, N-3)."""
    sprints_ref = [sprint_numero - 1, sprint_numero - 2, sprint_numero - 3]
    sprints_ref = [s for s in sprints_ref if s > 0]
    if not sprints_ref:
        return None

    # Funcionalidades com sprint_alvo nas sprints de referência que foram concluídas
    funcs_resp = (
        client.table("funcionalidades")
        .select("*")
        .eq("project_id", project_id)
        .in_("sprint_alvo", [str(s) for s in sprints_ref])
        .eq("status", "concluida")
        .execute()
    )
    funcs = funcs_resp.data or []
    if not funcs:
        return None

    # Total concluídas / número de sprints de referência = média por sprint
    # Convertemos para "por semana" assumindo sprint de 2 semanas (padrão CITi)
    # Alternativa mais simples: throughput = len(funcs) / len(sprints_ref) (funcionalidades/sprint)
    # A CONTEXT.md diz "throughput médio das 3 sprints" — retornar como funcionalidades/sprint
    return round(len(funcs) / len(sprints_ref), 1)
```

**Nota:** `calcular_bloco_c` calcula throughput por semana sobre o ciclo de vida inteiro do projeto. Para o "throughput de referência" do planning, o mais intuitivo para o gerente é "quantas funcionalidades foram concluídas nas últimas 3 sprints, em média por sprint" — não por semana. A CONTEXT.md especifica "throughput das últimas 3 sprints" sem definir a unidade. O planner deve decidir a unidade; a sugestão da pesquisa é `funcionalidades/sprint` por ser mais intuitivo em contexto de planning. Marcar como [ASSUMED] pois a CONTEXT.md não especifica.

[ASSUMED] Unidade do throughput_ref é funcionalidades/sprint (não por semana).

---

## FuncionalidadeResponse — Campos Relevantes

[VERIFIED: docudata-backend/models/schemas.py:248-262]

```python
class FuncionalidadeResponse(BaseModel):
    id: str
    project_id: str
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]           # lista de strings — índice = posição na lista
    prioridade: str                        # "must" | "should" | "could" | "wont"
    status: str                            # "nao_iniciada" | "em_andamento" | "em_ajuste" | "concluida"
    status_cliente: str
    data_aprovacao_cliente: Optional[date] = None
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None     # string (ex: "2"), não int
    created_at: datetime
```

**Ponto crítico:** `sprint_alvo` é `Optional[str]`, não int. A query de transbordos deve comparar com string: `sprint_alvo == str(sprint_numero - 1)`.

[VERIFIED: docudata-frontend/app/lib/api.ts:651-665]

```typescript
export interface FuncionalidadeResponse {
  id: string;
  project_id: string;
  id_funcional: string;
  titulo: string;
  descricao?: string;
  criterios_aceite: string[];              // array de strings — recorte por índice
  prioridade: string;
  status: "nao_iniciada" | "em_andamento" | "em_ajuste" | "concluida";
  status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado";
  data_aprovacao_cliente?: string | null;
  responsavel?: string | null;
  sprint_alvo?: string | null;             // string (ex: "2")
  created_at: string;
}
```

---

## Frontend Wizard — Estrutura do Componente

```typescript
// docudata-frontend/app/components/PlanningTab.tsx

"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { listFuncionalidades, type FuncionalidadeResponse } from "../lib/api";
// + funções novas de api.ts: getRascunho, patchRascunho, gerarPlanning, confirmarPlanning

// Estilos declarados fora do componente (padrão PainelTab)
const cardStyle: React.CSSProperties = { background: "#ffffff", border: "1px solid #e8e8ed", borderRadius: 14, padding: "20px 22px" };
// ... etc

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
}

// Estado local do wizard
interface WizardState {
  sprintNumero: number;
  step: 1 | 2 | 3 | 4;
  funcionalidadesSelecionadas: string[];   // IDs
  recortes: Record<string, number[]>;      // funcId -> índices de criterios_aceite
  alocacoes: Record<string, string>;       // funcId -> nome do responsável
  transbordos: string[];                   // IDs detectados pelo backend
  markdownGerado: string;                  // resultado do POST /composer/gerar
}

export default function PlanningTab({ projectId, sprints }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rascunho, setRascunho] = useState<...>(null);
  const [funcionalidades, setFuncionalidades] = useState<FuncionalidadeResponse[]>([]);
  const [throughputRef, setThroughputRef] = useState<number | null>(null);
  const [wizard, setWizard] = useState<WizardState | null>(null);
  // ...

  // Tela de boas-vindas (sem rascunho ativo) → botão iniciar
  // Step 1: lista funcionalidades com transbordos no topo
  // Step 2: checkboxes de criterios_aceite por funcionalidade selecionada
  // Step 3: inputs de responsável por funcionalidade selecionada
  // Step 4: preview markdown + botão confirmar
}
```

**Regra D-04 implementada no frontend:**

```typescript
const passo2Valido = wizard.funcionalidadesSelecionadas.every(
  (id) => (wizard.recortes[id] ?? []).length > 0
);
// Botão "Próximo" do step 2 recebe disabled={!passo2Valido}
```

---

## Prompt do Gemini para POST /composer/gerar

Montar contexto a partir dos dados do rascunho + funcionalidades completas:

```python
_PLANNING_SYSTEM_PROMPT = (
    "Você é um assistente especializado em documentação de projetos de dados do CITi. "
    "A partir dos dados estruturados de um planning de sprint fornecidos, gere um documento "
    "de Planning em markdown com as seções: Objetivo da Sprint, Funcionalidades Selecionadas "
    "(com critérios de aceite recortados), Responsabilidades, Transbordos da Sprint Anterior, "
    "e Throughput de Referência. "
    "Escreva em português, de forma objetiva e estruturada. "
    "Retorne APENAS o markdown do documento, sem texto antes ou depois."
)

def _montar_contexto_gerar(rascunho: dict, funcs_map: dict[str, dict], projeto: dict) -> str:
    dados = rascunho["dados_json"]
    sprint_n = rascunho["sprint_numero"]
    linhas = [
        f"Projeto: {projeto['name']} | Cliente: {projeto['client']}",
        f"Sprint: {sprint_n}",
        "",
        "## Funcionalidades Selecionadas",
    ]
    for fid in dados.get("funcionalidades_selecionadas", []):
        func = funcs_map.get(fid)
        if not func:
            continue
        eh_transborde = fid in dados.get("transbordos", [])
        tag = " [TRANSBORDADO]" if eh_transborde else ""
        responsavel = dados.get("alocacoes", {}).get(fid, "—")
        criterios = func.get("criterios_aceite", [])
        indices = dados.get("recortes", {}).get(fid, [])
        criterios_sprint = [criterios[i] for i in indices if i < len(criterios)]
        linhas.append(f"\n### {func['titulo']}{tag}")
        linhas.append(f"Responsável: {responsavel}")
        linhas.append("Critérios de aceite desta sprint:")
        for c in criterios_sprint:
            linhas.append(f"  - {c}")
    transbordos = dados.get("transbordos", [])
    if transbordos:
        linhas.append("\n## Transbordos da Sprint Anterior")
        for tid in transbordos:
            f = funcs_map.get(tid)
            if f:
                linhas.append(f"  - {f['titulo']}")
    linhas.append(f"\n## Throughput de Referência")
    # throughput_ref vem do rascunho ou do GET — incluir se disponível
    return "\n".join(linhas)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Renderizar markdown | Parser manual | `react-markdown` (já presente) | Edge cases de listas aninhadas, links, tabelas |
| Calcular throughput histórico | Loop custom em Python | Adaptar `calcular_bloco_c` de `painel.py` | Lógica já testada, inclui edge cases de cycle time |
| Chamada Gemini com retry | Lógica própria de backoff | `ChatGoogleGenerativeAI.ainvoke` + try/except 502 | Padrão estabelecido em `commit_ingest.py` |
| Persistência de estado wizard | localStorage | Tabela `planning_rascunhos` no Supabase | Sobrevive troca de browser/máquina (D-01) |
| Upsert no Supabase | INSERT + catch + UPDATE | `.upsert()` com `on_conflict="project_id,sprint_numero"` | Supabase-py v2 tem suporte nativo |

**Key insight:** O padrão de upsert do Supabase para a tabela `planning_rascunhos` usa a constraint UNIQUE — o `GET /composer/rascunho` pode usar `.upsert(default_row, on_conflict="project_id,sprint_numero")` para criar-se-não-existe em uma única chamada.

---

## Common Pitfalls

### Pitfall 1: sprint_alvo é string, não int

**What goes wrong:** Query `funcionalidades.sprint_alvo == sprint_numero - 1` retorna zero resultados porque `sprint_alvo` é `text` no banco e na API Python.
**Why it happens:** O campo foi modelado como `Optional[str]` em `FuncionalidadeResponse` [VERIFIED: schemas.py:260].
**How to avoid:** Sempre comparar com `str(sprint_numero - 1)` no backend e `String(sprintNumero - 1)` no frontend.
**Warning signs:** GET rascunho retorna `transbordos: []` mesmo com funcionalidades da sprint anterior.

### Pitfall 2: Confirmação sem verificar que rascunho existe

**What goes wrong:** POST /composer/confirmar com markdown vazio ou sem rascunho gera doc inválido em `generated_docs`.
**Why it happens:** Sem validação do rascunho antes do insert.
**How to avoid:** No `/composer/confirmar`, buscar o rascunho primeiro: se não existe, retornar 404. Só persistir se rascunho existe e markdown não é vazio.

### Pitfall 3: Delete do rascunho antes do insert no generated_docs

**What goes wrong:** Erro no insert de `generated_docs` após delete do rascunho perde o rascunho permanentemente sem criar o doc.
**Why it happens:** Supabase-py não suporta transações multi-tabela na camada cliente.
**How to avoid:** Ordem: (1) INSERT generated_docs → (2) se sucesso, DELETE rascunho. Se insert falhar, rascunho permanece.

### Pitfall 4: Gemini chamado para cada PATCH (lentidão)

**What goes wrong:** Frontend que chama POST /composer/gerar a cada mudança de step trava o wizard com 2-5s de latência.
**Why it happens:** Confundir "salvar rascunho" com "gerar documento".
**How to avoid:** PATCH salva dados estruturados (sem Gemini). POST /gerar é chamado apenas quando o gerente clica em "Gerar Planning" no step 4.

### Pitfall 5: Índices de recorte out-of-bounds

**What goes wrong:** `criterios[i]` lança IndexError se rascunho salvo tem índice maior que o array atual.
**Why it happens:** `criterios_aceite` pode ter sido editado entre salvar o rascunho e gerar o doc.
**How to avoid:** Em `/composer/gerar`, filtrar índices: `indices = [i for i in indices if i < len(criterios)]`.

### Pitfall 6: Adicionar "planning" ao TabId sem atualizar o tipo

**What goes wrong:** TypeScript error em `page.tsx` ao fazer `setActiveTab("planning")`.
**Why it happens:** O tipo `TabId` na linha 47 lista explicitamente os IDs válidos.
**How to avoid:** Ao adicionar a aba, atualizar o tipo: `type TabId = "sprints" | "painel" | ... | "planning"`. [VERIFIED: docudata-frontend/app/projects/[id]/page.tsx:47]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `doc_type = 'planning'` via `/sprint-docs/planning` (form-based) | `/composer/confirmar` (JSON-based, sem ingestion intermediária) | Phase 10 | O planning via composer não cria ingestion — só generated_docs |
| Throughput global do projeto | Throughput das últimas 3 sprints (janela temporal) | Phase 10 | Mais relevante para planning de curto prazo |

**Atenção:** Já existe um endpoint `POST /sprint-docs/planning` (sprint_docs.py:231) que gera um planning via upload/form com ingestion intermediária. O composer é um fluxo alternativo e mais estruturado — ele NÃO substitui o endpoint existente. O `doc_type='planning'` em `generated_docs` será usado por ambos.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Nenhum framework de test detectado no projeto (sem pytest.ini, jest.config) |
| Config file | Nenhum |
| Quick run command | Não aplicável |
| Full suite command | Não aplicável |

### Wave 0 Gaps

Nenhum framework de testes instalado. Testes desta fase são manuais (end-to-end via browser) conforme padrão do projeto.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | MVP sem auth |
| V4 Access Control | no | MVP sem isolamento por usuário |
| V5 Input Validation | yes | Pydantic schemas no backend; validação de índices out-of-bounds |
| V6 Cryptography | no | Gemini API key lida de env/banco, não exposta |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Markdown injection no preview | Spoofing | react-markdown renderiza safe por default (sem dangerouslySetInnerHTML) |
| UUID manipulation (acessar rascunho de outro projeto) | Elevation of Privilege | Backend sempre filtra por project_id — não confiar no UUID do rascunho sozinho |
| Gemini API key exposta no response | Info Disclosure | API key nunca retornada nos endpoints; project response já filtra isso (has_api_key bool) |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `react-markdown` | Preview do markdown no passo 4 | YES | `^9.0.1` | — |
| `langchain-google-genai` | POST /composer/gerar | YES (projeto usa) | projeto atual | — |
| `supabase-py` | Todos os endpoints | YES (projeto usa) | projeto atual | — |
| Gemini API key por projeto | POST /composer/gerar | Configurada por projeto | — | HTTPException 422 se ausente |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Unidade do throughput_ref é funcionalidades/sprint (não por semana) | Throughput de Referência | Número exibido diferente do esperado; baixo impacto funcional |
| A2 | POST /composer/gerar retorna markdown sem salvar — correto per D-05 e D-06 | Endpoint Structure | Se salvar prematuro, gerente não tem oportunidade de cancelar |
| A3 | `calcular_bloco_c` pode ser chamada com lista vazia sem erro | Throughput | Erro de runtime se a função não tratar lista vazia (verificar linha 184) |

Sobre A3: verificado que linha 184 de painel.py retorna `throughput = 0.0` se `weeks > 0` e `total_concluidas = 0`, e `weeks` tem `max(..., 1)` na linha 182 — logo não divide por zero. [VERIFIED: docudata-backend/routers/painel.py:180-185]

---

## Open Questions

1. **Throughput exibido: funcionalidades/sprint ou funcionalidades/semana?**
   - O que sabemos: a CONTEXT.md diz "throughput médio das últimas 3 sprints" sem especificar unidade
   - O que não está claro: `calcular_bloco_c` usa semanas; planning usa sprints como unidade natural
   - Recomendação: usar funcionalidades/sprint (mais intuitivo para o gerente durante planning)

2. **O passo de Composição (step 4) gera automaticamente ou só ao clicar?**
   - O que sabemos: D-06 diz "o passo 4 exibe o markdown gerado pelo Gemini" — implica que ao entrar no passo 4 o markdown já está gerado
   - O que não está claro: se POST /composer/gerar é chamado ao avançar do step 3 para o 4, ou ao entrar no step 4
   - Recomendação: chamar POST /composer/gerar com `loading spinner` ao entrar no step 4 (melhor UX — o gerente não precisa clicar em um botão "Gerar" antes de ver o preview)

---

## Sources

### Primary (HIGH confidence)
- `docudata-backend/routers/painel.py` — `calcular_bloco_c` signature e lógica completa (lido nesta sessão)
- `docudata-backend/routers/commit_ingest.py` — padrão de chamada Gemini com `ChatGoogleGenerativeAI` + erro 502 (lido nesta sessão)
- `docudata-backend/models/schemas.py` — `FuncionalidadeResponse` campos exactos incluindo `criterios_aceite: list[str]` e `sprint_alvo: Optional[str]` (lido nesta sessão)
- `docudata-backend/supabase_schema.sql` — schema completo de tabelas existentes + padrão de migration (lido nesta sessão)
- `docudata-frontend/app/components/Tabs.tsx` — `TabItem` interface e estilo de aba ativa (lido nesta sessão)
- `docudata-frontend/app/components/PainelTab.tsx` — padrão zero-className, paleta de cores, loading/error states (lido nesta sessão)
- `docudata-frontend/app/lib/api.ts` — estrutura de funções fetch, interfaces TypeScript, base URL (lido nesta sessão)
- `docudata-frontend/app/projects/[id]/page.tsx` — `TabId` type, array de tabs, renderização condicional (lido nesta sessão)
- `docudata-frontend/package.json` — confirma `react-markdown: ^9.0.1` presente (lido nesta sessão)
- `docudata-backend/main.py` — padrão de registro de routers (lido nesta sessão)
- `docudata-backend/services/supabase_client.py` — `get_client()` lazy factory (lido nesta sessão)
- `docudata-backend/routers/sprint_docs.py` — padrão de insert em generated_docs (lido nesta sessão)
- `.planning/phases/10-composer-de-planning/10-CONTEXT.md` — decisões D-01 a D-10 (lido nesta sessão)

### Secondary (MEDIUM confidence)
- [ASSUMED] Unidade throughput_ref = funcionalidades/sprint (derivado por raciocínio, não especificado em CONTEXT.md)

---

## Metadata

**Confidence breakdown:**
- Schema da tabela nova (planning_rascunhos): HIGH — derivado diretamente de D-01 do CONTEXT.md
- Endpoints /composer/*: HIGH — D-10, "Claude's Discretion" do CONTEXT.md + padrões verificados no código
- Padrão de chamada Gemini: HIGH — lido commit_ingest.py:129-146 nesta sessão
- Padrão zero-className frontend: HIGH — lido PainelTab.tsx completo nesta sessão
- Throughput_ref lógica: MEDIUM — adaptação de calcular_bloco_c, unidade [ASSUMED]
- sprint_alvo como string: HIGH — lido schemas.py:260 e api.ts:662 nesta sessão

**Research date:** 2026-08-23
**Valid until:** 2026-09-23 (stack estável, sem dependências novas)

---

## RESEARCH COMPLETE
