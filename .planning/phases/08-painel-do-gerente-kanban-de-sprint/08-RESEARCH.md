# Phase 8: Painel do Gerente + Kanban de Sprint - Research

**Researched:** 2026-08-22
**Domain:** FastAPI metrics endpoint + React inline-style dashboard (read-only panel + kanban)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Nova aba "Painel" — 7a aba no dashboard, inserida entre "Sprints" e "Tecnologias". Painel (4 blocos) + Kanban ficam juntos nessa aba. Sem alterar as 6 abas existentes.
- **D-02:** Layout da aba: grid 2×2 com os 4 blocos (A/B/C/D) no topo; kanban de sprint como seção full-width abaixo. Hierarquia: métricas primeiro, detalhe por funcionalidade depois.
- **D-03:** Bloco A sem dados de contrato (`data_inicio` ou `data_fim_contratada` nulos): card cinza com texto "Sem dados de contrato" + link para a aba Configurações. Grid permanece 2×2 — bloco não some.
- **D-04:** Detalhe do Bloco D: acordeom expansível inline. Clica em "ver detalhe" e uma lista expande abaixo do resumo agregado, listando cada funcionalidade com seus tempos por fase.
- **D-05:** Alerta de desvio (Bloco A): só visual — campo `desvio_detectado: bool` no response do endpoint. Não persiste no banco. Sem tabela nova, sem migration para alerta.
- **D-06:** Sprint selecionável via dropdown — ao abrir a aba Painel, o kanban pré-seleciona a sprint mais recente (maior número).
- **D-07:** 3 colunas: `Planejado` (nao_iniciada) / `Em andamento` (em_andamento + em_ajuste) / `Concluído` (concluida). Coluna "Transbordou" removida.
- **D-08:** Funcionalidades multi-sprint: badge no card mostrando as sprints em que a funcionalidade aparece (chips estilo existente).
- **D-09:** Filtro do kanban: funcionalidades com `sprint_alvo = sprint_selecionada`. Sem persistência de estado próprio.
- **D-10:** Endpoint dedicado: `GET /projects/{id}/painel` retorna JSON com os 4 blocos calculados. Cálculos de percentil, dias úteis e cycle time ficam em Python.
- **D-11:** Bloco B — funcionalidades travadas: `MAX(transicoes_status.timestamp)` por funcionalidade. Se `hoje − ultima_transicao > 7 dias` E `status = em_andamento` → travada.
- **D-12:** Bloco B — aguardando cliente: `status_cliente = enviado` E `tempo desde transição para enviado > 5 dias úteis`. Aproximar como `dias_corridos × 5/7`.
- **D-13:** Sem agrupamento por squad no Bloco C — projeto inteiro é o squad.
- **D-14:** Janela de tempo do Bloco C: projeto inteiro desde a primeira funcionalidade.
- **D-15:** Cycle time: de `em_andamento` até `concluida` — usa `transicoes_status`.

### Claude's Discretion

- **Fórmula de eficiência de fluxo (Bloco D):** `tempo_em_andamento / tempo_total_de_vida × 100%`. Tempo total de vida = criado_em até concluida (ou hoje se não concluída).
- **Throughput (Bloco C):** funcionalidades concluídas por semana, média sobre semanas com atividade.
- **p50/p85 de cycle time (Bloco C):** percentil da distribuição de cycle times de todas as concluídas. Se nenhuma concluída, retornar `null`.
- **Cálculo de dias úteis (Bloco B):** `dias_corridos × 5/7`.

### Deferred Ideas (OUT OF SCOPE)

- Coluna "Transbordou" no kanban — removida desta fase.
- Histórico de alertas de desvio — persistência no banco.
- Filtro de Bloco C por janela deslizante.
- Agrupamento por squad dentro de um projeto.
- Drag-and-drop no kanban para mudar status.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| M2-A | Bloco A: % prazo consumido, % escopo concluído, % aprovado pelo cliente; "sem dados" quando campos de contrato ausentes; alerta visual quando desvio excede tolerância | Endpoint calcula tudo com campos já em `projects` (data_inicio, data_fim_contratada, tolerancia_desvio_pontos) + contagem de funcionalidades |
| M2-B | Bloco B: lista funcionalidades travadas (>7 dias em_andamento), aguardando cliente (>5 dias úteis em enviado), em_ajuste | Query em `funcionalidades` + `transicoes_status`; lógica de dias úteis via `× 5/7` |
| M2-C | Bloco C: throughput, WIP, cycle time (p50, p85) agregados por projeto | `statistics.quantiles` do stdlib Python para percentis; cycle time de `transicoes_status` |
| M2-D | Bloco D: tempo médio e p85 por fase de status + eficiência de fluxo; detalhe por funcionalidade via acordeom | `duracao_fase_anterior_segundos` já gravado em `transicoes_status`; acordeom via `useState` React sem biblioteca |
| M3 | Kanban de sprint: 3 colunas (Planejado/Em andamento/Concluído) com funcionalidades filtradas por sprint selecionada; badge multi-sprint | Dados de `GET /funcionalidades?project_id=` já existentes; filtro no frontend |
</phase_requirements>

---

## Summary

Esta fase entrega duas capacidades read-only na aba "Painel" do dashboard do projeto. Do lado do backend, um único endpoint novo `GET /projects/{id}/painel` executa todas as consultas e cálculos — métricas de prazo/escopo (Bloco A), detecção de itens travados (Bloco B), métricas de fluxo agregadas (Bloco C) e tempos por fase com eficiência de fluxo (Bloco D). Do lado do frontend, uma nova aba "Painel" inserida como 7a aba renderiza um grid 2×2 de blocos no topo e um kanban com dropdown de sprint abaixo; o kanban consome os dados de funcionalidades já buscados por endpoints existentes e filtra no frontend sem nova chamada.

Toda a lógica de cálculo reside no backend Python, onde `statistics.quantiles` da stdlib (sem dependências extras) calcula p50/p85 em uma única linha. O modelo de dados (`transicoes_status.duracao_fase_anterior_segundos`) já foi projetado na Fase 7 para armazenar a duração de cada fase, tornando os cálculos do Bloco D diretos: é só agrupar por `campo` + `para` e calcular médias/percentis sobre os valores já persistidos.

**Primary recommendation:** Criar `routers/painel.py` com o endpoint GET, registrar em `main.py`, criar `PainelTab.tsx` como componente isolado seguindo o padrão de `TechnologiesTab.tsx`, e adicionar "painel" ao `TabId` union em `page.tsx`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cálculo de % prazo/escopo (Bloco A) | API / Backend | — | Requer acesso a `projects.data_inicio`, `data_fim_contratada`, contagem de `funcionalidades` — dados no Supabase; não enviar dados brutos ao frontend |
| Detecção de itens travados (Bloco B) | API / Backend | — | Requer `MAX(transicoes_status.timestamp)` por funcionalidade; lógica de limiar em dias — não expor tabela inteira ao cliente |
| Métricas de fluxo/percentis (Bloco C) | API / Backend | — | `statistics.quantiles` em Python; cálculo de cycle time exige joins entre funcionalidades e transicoes_status |
| Tempos por fase (Bloco D) | API / Backend | — | Agregação de `duracao_fase_anterior_segundos` agrupada por fase — computacionalmente trivial em Python mas requer dados do banco |
| Renderização Bloco D acordeom | Frontend | — | Estado de expansão (aberto/fechado) é UI-only — não persistir no banco |
| Filtro do kanban por sprint | Frontend | — | Funcionalidades já estão em memória no frontend após `GET /funcionalidades?project_id=`; filtrar por `sprint_alvo` no cliente sem nova requisição |
| Dropdown de sprint do kanban | Frontend | — | Lista de sprints já disponível no estado `sprints` de `page.tsx` |

---

## Standard Stack

### Core (sem dependências novas)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `statistics` (stdlib Python) | built-in | `quantiles(data, n=100)` para p50/p85 | Sem instalação; suficiente para N < 10.000 funcionalidades |
| `datetime` (stdlib Python) | built-in | Cálculo de delta de dias (`datetime.now(timezone.utc) - ts`) | Já em uso no projeto |
| React `useState` | já instalado | Acordeom expansível Bloco D + estado sprint selecionada no kanban | Padrão do projeto |
| React `useEffect` | já instalado | Fetch lazy ao ativar aba "Painel" | Padrão estabelecido (`custos`, `tecnologias`) |

**Nenhum pacote novo precisa ser instalado para esta fase.**

### Como calcular percentil com `statistics.quantiles`

```python
# [VERIFIED: docs.python.org/3/library/statistics.html#statistics.quantiles]
import statistics

# data = lista de cycle times em dias (floats), apenas funcionalidades concluídas
# Se menos de 2 pontos, quantiles() levanta StatisticsError
if len(cycle_times) >= 2:
    qs = statistics.quantiles(cycle_times, n=100)  # retorna 99 cortes
    p50 = qs[49]  # índice 49 = P50
    p85 = qs[84]  # índice 84 = P85
elif len(cycle_times) == 1:
    p50 = p85 = cycle_times[0]
else:
    p50 = p85 = None
```

`statistics.quantiles` requer Python 3.8+. O projeto já usa Python 3.x (FastAPI + type hints confirmam isso). [VERIFIED: docs.python.org]

---

## Architecture Patterns

### System Architecture Diagram

```
Frontend (PainelTab.tsx)
  |
  |-- ao ativar aba "painel" ---------> GET /projects/{id}/painel
  |                                          |
  |                                     routers/painel.py
  |                                          |
  |                                     Supabase:
  |                                       projects (1 row)
  |                                       funcionalidades (N rows)
  |                                       transicoes_status (M rows)
  |                                          |
  |                                     Python: calcula blocos A/B/C/D
  |                                          |
  |<-------- PainelResponse JSON  -----------+
  |
  |-- filtra sprint_alvo == selecionada --> kanban cols (frontend-only)
  |
  | (sprints list já em memória no page.tsx)
```

### Recommended File Structure — arquivos novos e modificados

```
docudata-backend/
├── routers/
│   └── painel.py          # NOVO — GET /projects/{id}/painel
└── main.py                # MODIFICAR — include_router(painel.router)

docudata-frontend/app/
├── components/
│   └── PainelTab.tsx      # NOVO — aba completa (blocos + kanban)
├── lib/
│   └── api.ts             # MODIFICAR — adicionar getPainel(), PainelData interface
└── projects/[id]/
    └── page.tsx           # MODIFICAR — TabId union, Tabs array, aba "painel" render
```

### Pattern 1: Aba isolada com fetch lazy (padrão do projeto)

O padrão estabelecido por `TechnologiesTab.tsx` e pela aba "custos" em `page.tsx` é: componente separado recebe `projectId` como prop, faz seu próprio `useEffect` que dispara quando o componente monta, gerencia `loading` / `error` / `data` localmente.

```typescript
// Padrão VERIFICADO em TechnologiesTab.tsx:14-76
"use client";
import { useEffect, useState } from "react";

export default function PainelTab({ projectId, sprints }: Props) {
  const [data, setData] = useState<PainelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getPainel(projectId)
      .then((d) => { setData(d); setError(null); })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [projectId]);
  // ...
}
```

O componente monta apenas quando `activeTab === "painel"` (pelo condicional `{activeTab === "painel" && <PainelTab ... />}` em `page.tsx`), garantindo fetch lazy sem `useEffect` dependendo de `activeTab` no pai.

### Pattern 2: Adicionar aba ao TabId union e ao array de Tabs

```typescript
// page.tsx linha 46 — ATUAL:
type TabId = "sprints" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config";

// APÓS MODIFICAÇÃO (inserir "painel" entre "sprints" e "tecnologias"):
type TabId = "sprints" | "painel" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config";
```

```typescript
// page.tsx linha 469-478 — array de tabs:
// Adicionar { id: "painel", label: "Painel" } na posição 2 (após "sprints"):
<Tabs
  tabs={[
    { id: "sprints", label: "Sprints", badge: ... },
    { id: "painel", label: "Painel" },      // NOVO
    { id: "tecnologias", label: "Tecnologias" },
    // ...
  ]}
/>
```

[VERIFIED: docudata-frontend/app/projects/[id]/page.tsx:46] — `type TabId = "sprints" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config"`

[VERIFIED: docudata-frontend/app/projects/[id]/page.tsx:469-478] — array de Tabs com 6 entradas.

### Pattern 3: Registro de router em main.py

```python
# main.py — ATUAL (linha 6-7):
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich, funcionalidades

# APÓS MODIFICAÇÃO:
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich, funcionalidades, painel

app.include_router(painel.router)  # adicionar após funcionalidades.router
```

[VERIFIED: docudata-backend/main.py:6-28] — import e `include_router` de todos os routers existentes.

### Pattern 4: Estrutura do router FastAPI (padrão existente)

```python
# routers/painel.py — seguir padrão de routers/projects.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.supabase_client import get_client
from datetime import datetime, timezone

router = APIRouter(prefix="/projects", tags=["painel"])

@router.get("/{project_id}/painel")
async def get_painel(project_id: str):
    client = get_client()
    # 1. Verificar projeto existe
    # 2. Buscar projeto (campos de contrato)
    # 3. Buscar funcionalidades do projeto
    # 4. Buscar transicoes_status de todas as funcionalidades
    # 5. Calcular blocos A, B, C, D
    # 6. Retornar PainelResponse
    ...
```

[VERIFIED: docudata-backend/routers/projects.py:21-28] — padrão de `APIRouter(prefix="/projects", tags=[...])` + `get_client()`.

### Pattern 5: Acordeom inline sem biblioteca (React + useState)

```typescript
// Padrão inline com useState — sem dependência de biblioteca
const [expandedBloco, setExpandedBloco] = useState<string | null>(null);

// Cada linha clicável do Bloco D:
<div
  onClick={() => setExpandedBloco(expandedBloco === fase ? null : fase)}
  style={{ cursor: "pointer", display: "flex", justifyContent: "space-between" }}
>
  <span>{faseLabel}</span>
  <span style={{ color: "#9696a0", fontSize: 12 }}>
    {expandedBloco === fase ? "▲ fechar" : "▼ ver detalhe"}
  </span>
</div>
{expandedBloco === fase && (
  <div style={{ marginTop: 8, paddingLeft: 12 }}>
    {/* lista de funcionalidades individuais */}
  </div>
)}
```

O projeto usa exclusivamente inline styles (sem Tailwind) — confirmado em `page.tsx` e `TechnologiesTab.tsx`. Este padrão não requer biblioteca externa.

### Pattern 6: Grid 2×2 para os 4 blocos

```typescript
// CSS Grid 2×2 com inline styles:
<div style={{
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 14,
  marginBottom: 20,
}}>
  <BlocoA data={data.bloco_a} />
  <BlocoB data={data.bloco_b} />
  <BlocoC data={data.bloco_c} />
  <BlocoD data={data.bloco_d} expandedFase={expandedFase} onToggle={...} />
</div>
```

### Anti-Patterns to Avoid

- **Calcular métricas no frontend:** Nunca. O CONTEXT.md (D-10) é explícito: toda lógica de cálculo fica no backend.
- **Nova busca de transições por funcionalidade individualmente (N+1):** Buscar todas as transições do projeto numa única query filtrando `funcionalidade_id IN (lista)` — não chamar `GET /funcionalidades/{id}/transicoes` por funcionalidade em loop.
- **`statistics.quantiles` com lista vazia ou 1 elemento:** Levanta `StatisticsError`. Sempre checar `len(data) >= 2` antes de chamar.
- **Usar Tailwind ou qualquer classe CSS:** O projeto usa inline styles exclusivamente. Não introduzir classes CSS.
- **Modificar TabId sem atualizar o array de Tabs:** As duas coisas devem ser atualizadas juntas em `page.tsx`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentil p50/p85 | Ordenação manual + índice | `statistics.quantiles(data, n=100)` | Stdlib Python — sem instalação, edge cases tratados |
| Dias úteis aproximados | Calendário de feriados | `dias_corridos * 5 / 7` | CONTEXT.md D-12 especifica esta aproximação |
| Acordeom expansível | Biblioteca de componentes | `useState<string|null>` com render condicional | Padrão inline do projeto |

---

## Data Model — Campos Relevantes (verificados no código)

### `FuncionalidadeResponse` — campos disponíveis

[VERIFIED: docudata-backend/models/schemas.py:234-248]

```python
class FuncionalidadeResponse(BaseModel):
    id: str
    project_id: str
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]
    prioridade: str
    status: str                           # nao_iniciada | em_andamento | em_ajuste | concluida
    status_cliente: str                   # nao_enviado | enviado | aprovado | rejeitado
    data_aprovacao_cliente: Optional[date] = None
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None     # usado pelo kanban para filtrar
    created_at: datetime
```

Valores de `status` e `status_cliente` — inferidos do código de patch (patch_funcionalidade valida implicitamente, mas os valores literais são gravados via PATCH direto do frontend). [ASSUMED] os valores exatos são: `status` = `nao_iniciada | em_andamento | em_ajuste | concluida`; `status_cliente` = `nao_enviado | enviado | aprovado | rejeitado` — os schemas.py não listam os valores enum diretamente, mas estão implícitos no CONTEXT.md e no código de lógica do router.

### `TransicaoStatusResponse` — campos disponíveis

[VERIFIED: docudata-backend/models/schemas.py:250-259]

```python
class TransicaoStatusResponse(BaseModel):
    id: str
    funcionalidade_id: str
    campo: str                               # "status" | "status_cliente"
    de: str
    para: str
    autor: Optional[str] = None
    timestamp: datetime
    motivo: Optional[str] = None
    duracao_fase_anterior_segundos: Optional[int] = None   # KEY: duração da fase anterior
```

`duracao_fase_anterior_segundos` é o campo central para Bloco D — já gravado pela lógica de PATCH em `funcionalidades.py:188-196`.

### `ProjectResponse` — campos de contrato

[VERIFIED: docudata-backend/models/schemas.py:28-42]

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
    data_inicio: Optional[date] = None           # KEY para Bloco A
    data_fim_contratada: Optional[date] = None   # KEY para Bloco A
    tolerancia_desvio_pontos: Optional[int] = None  # KEY para alerta de desvio
    periodo_garantia_dias: Optional[int] = None
```

---

## Backend — Lógica de Cálculo do Endpoint `/projects/{id}/painel`

### Queries necessárias (3 queries ao Supabase)

```python
# Query 1: projeto com campos de contrato
proj = client.table("projects").select("*").eq("id", project_id).execute()

# Query 2: todas as funcionalidades do projeto
funcs = client.table("funcionalidades").select("*").eq("project_id", project_id).execute()

# Query 3: todas as transições das funcionalidades do projeto
func_ids = [f["id"] for f in funcs.data]
# supabase-py v2: filtro IN via .in_()
transicoes = (
    client.table("transicoes_status")
    .select("*")
    .in_("funcionalidade_id", func_ids)
    .order("timestamp", desc=False)
    .execute()
)
```

**Nota sobre `.in_()` no supabase-py v2:** [ASSUMED] a sintaxe é `.in_("campo", lista)` — verificar no código se há outros usos de filtro IN no projeto. Se a lista `func_ids` estiver vazia (projeto sem funcionalidades), não executar a query 3 (evitar erro de sintaxe com lista vazia).

### Bloco A — Tempo × Escopo

```python
from datetime import date, datetime, timezone

def calcular_bloco_a(proj: dict, funcs: list[dict]) -> dict:
    data_inicio = proj.get("data_inicio")
    data_fim = proj.get("data_fim_contratada")
    tolerancia = proj.get("tolerancia_desvio_pontos") or 0

    if not data_inicio or not data_fim:
        return {"sem_dados": True}

    hoje = date.today()
    # parse strings ISO se necessário
    if isinstance(data_inicio, str): data_inicio = date.fromisoformat(data_inicio)
    if isinstance(data_fim, str): data_fim = date.fromisoformat(data_fim)

    total_dias = (data_fim - data_inicio).days
    dias_consumidos = (hoje - data_inicio).days
    pct_prazo = round(min(dias_consumidos / total_dias * 100, 100), 1) if total_dias > 0 else 0

    total_funcs = len(funcs)
    concluidas = sum(1 for f in funcs if f["status"] == "concluida")
    aprovadas = sum(1 for f in funcs if f["status_cliente"] == "aprovado")

    pct_escopo = round(concluidas / total_funcs * 100, 1) if total_funcs > 0 else 0
    pct_aprovado = round(aprovadas / total_funcs * 100, 1) if total_funcs > 0 else 0

    desvio = pct_prazo - pct_aprovado
    desvio_detectado = desvio > tolerancia

    return {
        "sem_dados": False,
        "pct_prazo_consumido": pct_prazo,
        "pct_escopo_concluido": pct_escopo,
        "pct_aprovado_cliente": pct_aprovado,
        "desvio_detectado": desvio_detectado,
        "desvio_pontos": round(desvio, 1),
    }
```

### Bloco B — Itens Travados

```python
from datetime import datetime, timezone, timedelta

def calcular_bloco_b(funcs: list[dict], transicoes: list[dict]) -> dict:
    hoje = datetime.now(timezone.utc)

    # Indexar última transição de "status" por funcionalidade
    ultima_transicao_status: dict[str, datetime] = {}
    primeira_transicao_enviado: dict[str, datetime] = {}

    for t in transicoes:
        fid = t["funcionalidade_id"]
        ts = datetime.fromisoformat(t["timestamp"]).replace(tzinfo=timezone.utc)
        if t["campo"] == "status":
            # transicoes ordenadas asc — última sobrescreve
            ultima_transicao_status[fid] = ts
        if t["campo"] == "status_cliente" and t["para"] == "enviado":
            # primeira ocorrência de "enviado" (pode ter voltado e ido de novo — pegar a mais recente)
            # DECISÃO: pegar a mais recente transição para "enviado" ativo
            # Como lista está ASC, qualquer sobrescrição pega a mais nova
            ultima_transicao_status_cli = primeira_transicao_enviado.get(fid)
            if ultima_transicao_status_cli is None or ts > ultima_transicao_status_cli:
                primeira_transicao_enviado[fid] = ts

    travadas = []
    aguardando_cliente = []
    em_ajuste = []

    for f in funcs:
        fid = f["id"]
        if f["status"] == "em_andamento":
            ultima = ultima_transicao_status.get(fid)
            if ultima is None:
                # sem transição registrada — usar created_at
                ultima = datetime.fromisoformat(f["created_at"]).replace(tzinfo=timezone.utc)
            delta_dias = (hoje - ultima).days
            if delta_dias > 7:
                travadas.append({"id": fid, "titulo": f["titulo"], "dias": delta_dias})

        if f["status_cliente"] == "enviado":
            ts_enviado = primeira_transicao_enviado.get(fid)
            if ts_enviado:
                dias_corridos = (hoje - ts_enviado).days
                dias_uteis_aprox = dias_corridos * 5 / 7
                if dias_uteis_aprox > 5:
                    aguardando_cliente.append({
                        "id": fid, "titulo": f["titulo"],
                        "dias_uteis": round(dias_uteis_aprox, 1)
                    })

        if f["status"] == "em_ajuste":
            em_ajuste.append({"id": fid, "titulo": f["titulo"]})

    return {
        "travadas": travadas,
        "aguardando_cliente": aguardando_cliente,
        "em_ajuste": em_ajuste,
    }
```

### Bloco C — Métricas de Fluxo

```python
import statistics

def calcular_bloco_c(funcs: list[dict], transicoes: list[dict]) -> dict:
    # Cycle time: de em_andamento até concluida (campo="status")
    # Indexar transições por funcionalidade
    trans_por_func: dict[str, list[dict]] = {}
    for t in transicoes:
        trans_por_func.setdefault(t["funcionalidade_id"], []).append(t)

    cycle_times_dias = []
    for f in funcs:
        if f["status"] != "concluida":
            continue
        trans = trans_por_func.get(f["id"], [])
        ts_inicio = None
        ts_fim = None
        for t in trans:
            if t["campo"] == "status" and t["para"] == "em_andamento" and ts_inicio is None:
                ts_inicio = datetime.fromisoformat(t["timestamp"]).replace(tzinfo=timezone.utc)
            if t["campo"] == "status" and t["para"] == "concluida":
                ts_fim = datetime.fromisoformat(t["timestamp"]).replace(tzinfo=timezone.utc)
        if ts_inicio and ts_fim and ts_fim > ts_inicio:
            cycle_times_dias.append((ts_fim - ts_inicio).total_seconds() / 86400)

    # WIP: funcionalidades com status em_andamento OU em_ajuste agora
    wip = sum(1 for f in funcs if f["status"] in ("em_andamento", "em_ajuste"))

    # Throughput: funcionalidades concluídas por semana desde o início do projeto
    concluidas_total = len(cycle_times_dias)
    throughput = None
    if funcs:
        primeira_criacao = min(
            datetime.fromisoformat(f["created_at"]).replace(tzinfo=timezone.utc)
            for f in funcs
        )
        semanas = max((datetime.now(timezone.utc) - primeira_criacao).days / 7, 1)
        throughput = round(concluidas_total / semanas, 2)

    # Percentis
    p50 = p85 = None
    if len(cycle_times_dias) >= 2:
        qs = statistics.quantiles(cycle_times_dias, n=100)
        p50 = round(qs[49], 1)
        p85 = round(qs[84], 1)
    elif len(cycle_times_dias) == 1:
        p50 = p85 = round(cycle_times_dias[0], 1)

    return {
        "throughput_por_semana": throughput,
        "wip": wip,
        "cycle_time_p50_dias": p50,
        "cycle_time_p85_dias": p85,
        "total_concluidas": concluidas_total,
    }
```

### Bloco D — Tempo por Fase

```python
def calcular_bloco_d(funcs: list[dict], transicoes: list[dict]) -> dict:
    # Usar duracao_fase_anterior_segundos já gravado em transicoes_status
    # Agrupar por campo="status" e por valor "para" (= a fase que começou)
    # "duracao_fase_anterior_segundos" = quanto tempo ficou na fase ANTERIOR (de)
    # Portanto, para saber duração em fase X: pegar transições onde "de" == X

    from collections import defaultdict
    duracoes_por_fase: dict[str, list[float]] = defaultdict(list)
    duracoes_por_func: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for t in transicoes:
        if t["campo"] != "status":
            continue
        fase_anterior = t["de"]   # fase que acabou
        duracao_s = t.get("duracao_fase_anterior_segundos")
        if duracao_s is not None and duracao_s >= 0:
            duracao_d = duracao_s / 86400
            duracoes_por_fase[fase_anterior].append(duracao_d)
            duracoes_por_func[t["funcionalidade_id"]][fase_anterior] += duracao_d

    # Eficiência de fluxo: tempo_em_andamento / tempo_total_de_vida
    hoje = datetime.now(timezone.utc)
    eficiencias = []
    for f in funcs:
        criado = datetime.fromisoformat(f["created_at"]).replace(tzinfo=timezone.utc)
        if f["status"] == "concluida":
            # tempo total = até a transição para concluida
            # aproximação: soma de todas as durações gravadas
            total_s = sum(
                t.get("duracao_fase_anterior_segundos") or 0
                for t in transicoes
                if t["funcionalidade_id"] == f["id"] and t["campo"] == "status"
            )
            tempo_total_d = total_s / 86400 if total_s > 0 else (hoje - criado).total_seconds() / 86400
        else:
            tempo_total_d = (hoje - criado).total_seconds() / 86400

        tempo_em_andamento_d = duracoes_por_func[f["id"]].get("em_andamento", 0.0)
        if tempo_total_d > 0:
            eficiencias.append(tempo_em_andamento_d / tempo_total_d * 100)

    eficiencia_media = round(sum(eficiencias) / len(eficiencias), 1) if eficiencias else None

    # Resumo por fase com média e p85
    fases_resumo = {}
    for fase, duracoes in duracoes_por_fase.items():
        media = round(sum(duracoes) / len(duracoes), 1)
        p85 = None
        if len(duracoes) >= 2:
            qs = statistics.quantiles(duracoes, n=100)
            p85 = round(qs[84], 1)
        elif len(duracoes) == 1:
            p85 = round(duracoes[0], 1)
        fases_resumo[fase] = {"media_dias": media, "p85_dias": p85, "amostras": len(duracoes)}

    # Detalhe por funcionalidade: dict { func_id -> { fase -> dias } }
    detalhe_por_func = []
    for f in funcs:
        tempos = {}
        for t in transicoes:
            if t["funcionalidade_id"] == f["id"] and t["campo"] == "status":
                fase = t["de"]
                d = (t.get("duracao_fase_anterior_segundos") or 0) / 86400
                tempos[fase] = round(tempos.get(fase, 0) + d, 1)
        if tempos:
            detalhe_por_func.append({
                "id": f["id"],
                "titulo": f["titulo"],
                "tempos_por_fase": tempos,
            })

    return {
        "fases_resumo": fases_resumo,
        "eficiencia_fluxo_pct": eficiencia_media,
        "detalhe_por_funcionalidade": detalhe_por_func,
    }
```

---

## Frontend — Estrutura de PainelTab.tsx

### Interface TypeScript para o response do endpoint

```typescript
// api.ts — novos tipos
export interface BlocoA {
  sem_dados: boolean;
  pct_prazo_consumido?: number;
  pct_escopo_concluido?: number;
  pct_aprovado_cliente?: number;
  desvio_detectado?: boolean;
  desvio_pontos?: number;
}

export interface BlocoB {
  travadas: { id: string; titulo: string; dias: number }[];
  aguardando_cliente: { id: string; titulo: string; dias_uteis: number }[];
  em_ajuste: { id: string; titulo: string }[];
}

export interface BlocoC {
  throughput_por_semana: number | null;
  wip: number;
  cycle_time_p50_dias: number | null;
  cycle_time_p85_dias: number | null;
  total_concluidas: number;
}

export interface FaseResumo {
  media_dias: number;
  p85_dias: number | null;
  amostras: number;
}

export interface BlocoD {
  fases_resumo: Record<string, FaseResumo>;
  eficiencia_fluxo_pct: number | null;
  detalhe_por_funcionalidade: {
    id: string;
    titulo: string;
    tempos_por_fase: Record<string, number>;
  }[];
}

export interface PainelData {
  bloco_a: BlocoA;
  bloco_b: BlocoB;
  bloco_c: BlocoC;
  bloco_d: BlocoD;
}

export async function getPainel(projectId: string): Promise<PainelData> {
  const res = await fetch(`${API}/projects/${projectId}/painel`);
  if (!res.ok) throw new Error("Erro ao buscar painel");
  return res.json();
}
```

### Kanban — filtro de sprint no frontend

O kanban não requer nova chamada de API. As funcionalidades já estão no estado de `page.tsx` via `GET /funcionalidades?project_id=` — mas CONTEXT.md especifica que o kanban deve ser parte de `PainelTab.tsx`. Portanto `PainelTab` precisa receber as funcionalidades e sprints como props de `page.tsx` (ou fazer seu próprio fetch).

**Decisão de implementação:** `PainelTab.tsx` recebe `funcionalidades: FuncionalidadeResponse[]` e `sprints: SprintWithStatus[]` como props. `page.tsx` já tem esses dados — só passar para baixo. Evita double-fetch.

**Nota:** O tipo `FuncionalidadeResponse` no frontend ainda não existe em `api.ts`. Precisa ser criado nesta fase. [VERIFIED: docudata-frontend/app/lib/api.ts:1-650] — não há interface `FuncionalidadeResponse` ainda.

```typescript
// api.ts — adicionar
export interface FuncionalidadeResponse {
  id: string;
  project_id: string;
  id_funcional: string;
  titulo: string;
  descricao?: string;
  criterios_aceite: string[];
  prioridade: string;
  status: "nao_iniciada" | "em_andamento" | "em_ajuste" | "concluida";
  status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado";
  data_aprovacao_cliente?: string | null;
  responsavel?: string | null;
  sprint_alvo?: string | null;
  created_at: string;
}

export async function listFuncionalidades(projectId: string): Promise<FuncionalidadeResponse[]> {
  const res = await fetch(`${API}/funcionalidades?project_id=${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar funcionalidades");
  return res.json();
}
```

**Filtro do kanban por sprint:**

```typescript
// PainelTab.tsx — filtro local
const [sprintSelecionada, setSprintSelecionada] = useState<number>(
  sprints.length > 0 ? sprints[sprints.length - 1].numero : 1
);

const funcsDaSprint = funcionalidades.filter(
  (f) => f.sprint_alvo === String(sprintSelecionada)
);

// Colunas:
const planejado = funcsDaSprint.filter((f) => f.status === "nao_iniciada");
const emAndamento = funcsDaSprint.filter((f) => ["em_andamento", "em_ajuste"].includes(f.status));
const concluido = funcsDaSprint.filter((f) => f.status === "concluida");
```

**Badge multi-sprint:** `sprint_alvo` é uma string simples (ex: "1", "2"). Para o badge multi-sprint mostrar "Sprint 1 · Sprint 2", precisamos identificar funcionalidades que também aparecem em outras sprints. Como cada funcionalidade tem um único `sprint_alvo`, a lógica de multi-sprint é: verificar se a mesma funcionalidade (por `id` ou `id_funcional`) aparece com diferentes `sprint_alvo` em todo o array de funcionalidades. [ASSUMED] — o badge multi-sprint pode ser simplificado para mostrar apenas o `sprint_alvo` atual da funcionalidade (uma funcionalidade tem um único sprint_alvo no modelo atual); a interpretação "multi-sprint" do CONTEXT.md (D-08) refere-se a funcionalidades que foram re-atribuídas e aparecem em múltiplas sprints via `sprint_alvo` diferente — mas no modelo atual cada funcionalidade tem um único `sprint_alvo`.

Implementação conservadora: mostrar `sprint_alvo` como chip simples no card. Se o gerente quiser ver carry-over entre sprints, é feature futura.

---

## Common Pitfalls

### Pitfall 1: `statistics.quantiles` com lista vazia ou unitária

**What goes wrong:** `StatisticsError: must have at least two data points` se a lista tiver 0 ou 1 elemento.

**Why it happens:** A função requer distribuição com pelo menos 2 pontos para dividir em quantis.

**How to avoid:** Sempre checar `len(data)` antes de chamar:
```python
if len(data) >= 2:
    qs = statistics.quantiles(data, n=100)
    p50, p85 = qs[49], qs[84]
elif len(data) == 1:
    p50 = p85 = data[0]
else:
    p50 = p85 = None
```

**Warning signs:** `StatisticsError` em projetos novos com poucas funcionalidades concluídas.

### Pitfall 2: `.in_()` com lista vazia no supabase-py

**What goes wrong:** Query com `.in_("funcionalidade_id", [])` pode falhar ou retornar SQL inválido.

**Why it happens:** SQL `WHERE campo IN ()` é inválido em muitos bancos.

**How to avoid:** Checar `if not func_ids: return []` antes de executar a query de transições.

### Pitfall 3: Datas do Supabase chegam como strings ISO, não como objetos `date`

**What goes wrong:** `(hoje - data_inicio).days` levanta `TypeError` se `data_inicio` é uma string.

**Why it happens:** `supabase-py` retorna datas de colunas `date` como strings `"YYYY-MM-DD"`.

**How to avoid:** Sempre converter: `date.fromisoformat(data_inicio)` antes de operar. Ver padrão em `funcionalidades.py:189-190` onde o mesmo cuidado é tomado com timestamps.

### Pitfall 4: `duracao_fase_anterior_segundos` pode ser `None`

**What goes wrong:** Transições antigas (antes da Fase 7) podem não ter o campo preenchido.

**Why it happens:** O campo foi adicionado na Fase 7; transições criadas antes serão `None`.

**How to avoid:** `duracao_s = t.get("duracao_fase_anterior_segundos") or 0` — tratar None como 0.

### Pitfall 5: `sprint_alvo` pode ser `None` para funcionalidades não atribuídas

**What goes wrong:** `f.sprint_alvo === String(sprintSelecionada)` inclui funcionalidades com `sprint_alvo = None` se a string for "null" ou similar.

**Why it happens:** Funcionalidades importadas do contrato podem não ter sprint atribuída.

**How to avoid:** Filtrar explicitamente: `f.sprint_alvo !== null && f.sprint_alvo !== undefined && f.sprint_alvo === String(sprintSelecionada)`.

### Pitfall 6: Bloco A com `data_fim_contratada` no passado

**What goes wrong:** `pct_prazo` ultrapassa 100% se o projeto está atrasado.

**Why it happens:** `min(dias_consumidos / total_dias * 100, 100)` — o `min(..., 100)` deve ser explícito.

**How to avoid:** Limitar `pct_prazo` a 100% com `min(...)` como mostrado na lógica acima. O desvio pode ser > 100 − tolerância mesmo assim, o que aciona o alerta.

---

## Integration Points — Checklist de Arquivos Modificados

| Arquivo | Tipo | Mudança |
|---------|------|---------|
| `docudata-backend/routers/painel.py` | CRIAR | Endpoint `GET /projects/{id}/painel` |
| `docudata-backend/main.py` | MODIFICAR | `import painel` + `app.include_router(painel.router)` |
| `docudata-frontend/app/lib/api.ts` | MODIFICAR | Interface `PainelData`, `FuncionalidadeResponse`, funções `getPainel()`, `listFuncionalidades()` |
| `docudata-frontend/app/components/PainelTab.tsx` | CRIAR | Componente completo: blocos + kanban |
| `docudata-frontend/app/projects/[id]/page.tsx` | MODIFICAR | `TabId` union + Tabs array + `{activeTab === "painel" && <PainelTab .../>}` |

**Dependências na ordem de implementação:**
1. `schemas.py` — Adicionar `PainelResponse` Pydantic (ou usar `dict` diretamente no router)
2. `routers/painel.py` — Endpoint com toda a lógica de cálculo
3. `main.py` — Registro do router
4. `api.ts` — Interfaces TypeScript + função fetch
5. `PainelTab.tsx` — Componente
6. `page.tsx` — Wiring da aba

---

## Validation Architecture

### Testes manuais (fase read-only sem lógica de escrita)

| Cenário | Como testar |
|---------|-------------|
| Projeto sem campos de contrato | Bloco A mostra "Sem dados de contrato" |
| Projeto com `data_fim_contratada` no passado | `pct_prazo = 100%`, alerta deve aparecer se desvio > tolerância |
| Nenhuma funcionalidade concluída | Bloco C: `cycle_time_p50_dias = null`, `total_concluidas = 0` |
| Funcionalidades com `sprint_alvo = null` | Não aparecem no kanban de nenhuma sprint |
| 1 única funcionalidade concluída | `p50 = p85 = cycle_time` dessa funcionalidade |
| `.in_()` com 0 funcionalidades | Endpoint retorna blocos vazios sem erro 500 |

### Smoke test de endpoint

```bash
# Com servidor FastAPI rodando:
curl http://localhost:8000/projects/{project_id}/painel | python3 -m json.tool
# Esperado: JSON com chaves bloco_a, bloco_b, bloco_c, bloco_d
```

---

## Environment Availability

Step 2.6: SKIPPED — fase é apenas código/lógica nova; sem dependências externas além do stack já em uso (FastAPI, Supabase, React). `statistics` é stdlib Python.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Valores de enum para `status`: `nao_iniciada`, `em_andamento`, `em_ajuste`, `concluida` | Data Model | Filtros do kanban e lógica do Bloco B quebram se os valores forem diferentes |
| A2 | Valores de enum para `status_cliente`: `nao_enviado`, `enviado`, `aprovado`, `rejeitado` | Data Model | Bloco B (aguardando_cliente) e Bloco A (pct_aprovado) quebram |
| A3 | `sprint_alvo` é armazenada como string numérica ("1", "2") no banco | Frontend kanban | Comparação `f.sprint_alvo === String(sprint)` falha silenciosamente se formato for diferente |
| A4 | supabase-py v2 usa `.in_("campo", lista)` para filtro IN | Backend query 3 | Erro de syntax na query se API for diferente |
| A5 | Funcionalidades não têm campo próprio para "histórico de sprints" — `sprint_alvo` é o único campo de sprint | Kanban badge multi-sprint | Badge multi-sprint não pode ser implementado conforme CONTEXT.md D-08; simplificar para chip único |
| A6 | `page.tsx` não faz fetch de funcionalidades no bootstrap — `listFuncionalidades` não existe ainda | page.tsx / PainelTab props | Se funcionalidades não estão no estado pai, PainelTab precisa fazer seu próprio fetch |

**Ação para A1/A2:** Antes de implementar, confirmar os valores lendo as migrações SQL da Fase 7 ou fazendo uma query direta no Supabase.

**Ação para A6:** Confirmar lendo `page.tsx` bootstrap (linha 144-160) — a lista de funcionalidades NÃO está no bootstrap atual. [VERIFIED: docudata-frontend/app/projects/[id]/page.tsx:144-160] — `Promise.all` do bootstrap busca apenas `getProject`, `listIngestions`, `listDocs`, `getProjectCost`, `listSprints`. Funcionalidades não são buscadas. Portanto `PainelTab` deve fazer seu próprio fetch via `listFuncionalidades(projectId)` no `useEffect` — não receber como prop.

---

## Open Questions

1. **Valores exatos dos enums de `status` e `status_cliente`**
   - O que sabemos: schemas.py usa `str` simples sem `Literal` ou `Enum`. Os valores são gravados pelo frontend via PATCH. CONTEXT.md e lógica do router implicam os 4 valores listados.
   - O que está incerto: se há valor adicional ou grafia diferente (ex: `nao_iniciado` vs `nao_iniciada`).
   - Recomendação: Confirmar via query SQL (`SELECT DISTINCT status FROM funcionalidades`) antes de escrever o código de filtragem.

2. **`sprint_alvo` como string vs. int**
   - O que sabemos: `FuncionalidadeCreate` define `sprint_alvo: Optional[str]` [VERIFIED: schemas.py:183].
   - O que está incerto: o frontend envia "1" ou 1? A comparação no kanban deve ser string-safe.
   - Recomendação: usar `String(sprintSelecionada)` no frontend para garantir que a comparação é string-to-string.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED] `docudata-backend/models/schemas.py:28-42` — campos `ProjectResponse` incluindo `data_inicio`, `data_fim_contratada`, `tolerancia_desvio_pontos`
- [VERIFIED] `docudata-backend/models/schemas.py:234-259` — `FuncionalidadeResponse` e `TransicaoStatusResponse` com todos os campos
- [VERIFIED] `docudata-backend/routers/funcionalidades.py:140-150` — padrão de busca de transicoes_status
- [VERIFIED] `docudata-backend/routers/projects.py:21-28` — padrão de router FastAPI
- [VERIFIED] `docudata-backend/main.py:6-28` — registro de routers
- [VERIFIED] `docudata-frontend/app/projects/[id]/page.tsx:46` — `type TabId` union
- [VERIFIED] `docudata-frontend/app/projects/[id]/page.tsx:144-160` — bootstrap sem funcionalidades
- [VERIFIED] `docudata-frontend/app/projects/[id]/page.tsx:469-478` — array Tabs atual
- [VERIFIED] `docudata-frontend/app/components/TechnologiesTab.tsx:62-76` — padrão de aba isolada com fetch lazy
- [VERIFIED] `docudata-frontend/app/lib/api.ts:1-650` — ausência de `FuncionalidadeResponse` e `listFuncionalidades`
- [CITED: docs.python.org/3/library/statistics.html#statistics.quantiles] — `statistics.quantiles(data, n=100)`, requer ≥2 pontos

### Secondary (MEDIUM confidence)
- [ASSUMED] Valores de enum de `status` e `status_cliente` — inferidos do CONTEXT.md e lógica do router, não lidos de migration SQL

---

## Metadata

**Confidence breakdown:**
- Backend endpoint structure: HIGH — código dos routers existentes lido diretamente
- Data model fields: HIGH — schemas.py lido diretamente
- Frontend tab pattern: HIGH — TechnologiesTab.tsx e page.tsx lidos diretamente
- Cálculos Python (percentis, dias úteis): HIGH — stdlib documentada, fórmulas do CONTEXT.md
- Enum values (status/status_cliente): MEDIUM — inferidos, não verificados via SQL
- Multi-sprint badge: LOW — modelo de dados tem campo único `sprint_alvo`; badge completo pode não ser implementável sem mudança de schema

**Research date:** 2026-08-22
**Valid until:** 2026-09-22 (stack estável)
