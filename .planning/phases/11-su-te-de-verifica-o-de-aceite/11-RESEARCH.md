# Phase 11: Suíte de Verificação de Aceite — Research

**Researched:** 2026-08-23
**Domain:** GitHub Actions repository_dispatch + FastAPI async background tasks + Supabase jsonb + frontend badge
**Confidence:** HIGH (backend patterns) / MEDIUM (aceite_agent.py gate detection in generic repos)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Gates rodam via GitHub Actions no repo do projeto (repository_dispatch). Mesmo padrão dos Phases 4 e 9.
- **D-02:** O status muda imediatamente — a suíte NÃO bloqueia a transição. `PATCH /funcionalidades/{id}` retorna 200 imediatamente; dispatch é assíncrono.
- **D-03:** Dispatch via GitHub repository_dispatch (`POST /repos/{owner}/{repo}/dispatches`). `GITHUB_TOKEN` armazenado em `projects.github_token`. Se ausente, todos os gates = `sem_cobertura`.
- **D-04:** 5 gates fixos: `build`, `testes_unitarios`, `e2e`, `acessibilidade`, `performance`. Resultado: `passou | falhou | erro | sem_cobertura`.
- **D-05:** `POST /ingest/aceite` recebe payload `{ funcionalidade_id, commit_sha, gates: [{nome, resultado}] }`. Backend atualiza `execucoes_aceite`.
- **D-06:** Campo `testes_e2e: list[str]` em `funcionalidades`. Gerente define manualmente. Se lista vazia → gate E2E = `sem_cobertura`.
- **D-07:** Sem UI de gestão de testes E2E nesta fase. Campo editável via `PATCH /funcionalidades/{id}`.
- **D-08:** Badge visual no Kanban (coluna Concluído) quando existe `execucao_aceite` com gate `falhou` ou `erro`.
- **D-09:** Sub-seção "Cobertura de Aceite" no Bloco B do Painel. Lista funcionalidades concluídas com suíte falhando.
- **D-10:** Campo `cobertura_aceite: float` adicionado ao response de `GET /projects/{id}/painel`.

### Claude's Discretion

- Trigger do dispatch: adicionar ao handler `patch_funcionalidade` quando `status=concluida`.
- Token GitHub: campo `github_token: text` em `projects`.
- Repo: campo `github_repo: text` (formato `owner/repo`) em `projects`.
- Falha no dispatch sem configuração → registrar `sem_cobertura` imediatamente.
- `aceite_agent.py`: Python stdlib apenas. Roda gates via subprocess.

### Deferred Ideas (OUT OF SCOPE)

- Interface de gestão de testes E2E no frontend.
- Histórico paginado de ExecucaoAceite.
- Suporte a CIs além do GitHub Actions.
- Re-disparo manual da suíte.
- Notificações (Slack/email).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| M5 (§5) | Suíte de Verificação de Aceite — disparo em paralelo quando status=concluida, sem bloquear transição | D-02 + asyncio.create_task pattern |
| §4.4 (ExecucaoAceite) | Tabela execucoes_aceite com id, funcionalidade_id, project_id, commit_sha, gates (jsonb), disparado_em, concluido_em | Supabase jsonb insert pattern |
</phase_requirements>

---

## Summary

Esta fase conecta a transição de status `concluida` a um pipeline de CI externo via GitHub Actions `repository_dispatch`. O backend dispara o workflow assincronamente (sem bloquear o response 200) e registra uma `ExecucaoAceite` pendente imediatamente. O CI executa os 5 gates, coleta resultados e faz POST de volta ao DocuData. O frontend exibe badges e sub-seção no Painel.

A maior complexidade técnica está em dois pontos: (1) o `asyncio.create_task` dentro de um handler FastAPI precisa ser feito com cuidado para não perder a task quando o request termina; e (2) o `aceite_agent.py` precisa detectar e rodar gates em repos genéricos de forma best-effort, sem falhar o CI do projeto.

O padrão de integração GitHub Actions já foi estabelecido em Phases 4 (docudata_agent.py / docudata.yml) e 9 (revisor_agent.py / revisor.yml). Esta fase segue exatamente o mesmo padrão: script Python stdlib + workflow yml + secrets no repo do projeto.

**Primary recommendation:** Use `FastAPI BackgroundTasks` (não `asyncio.create_task` raw) para o dispatch — é a API idiomática do FastAPI, evita o pitfall de task garbage-collection, e o comportamento é idêntico para operações fire-and-forget curtas. Registre a `ExecucaoAceite` com `gates=[]` (ou gates todos `sem_cobertura`) ANTES do dispatch, depois atualize via `POST /ingest/aceite`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Detectar transição status=concluida | API / Backend | — | Lógica já existe em patch_funcionalidade |
| Disparar repository_dispatch | API / Backend | — | Requer github_token — nunca expor no frontend |
| Registrar ExecucaoAceite pendente | Database / Storage | API Backend | Supabase insert imediato pré-dispatch |
| Executar gates (build/test/e2e/etc.) | GitHub Actions CI | — | Roda no repo do projeto, fora do DocuData |
| Reportar resultado dos gates | API / Backend | — | POST /ingest/aceite recebe e atualiza Supabase |
| Badge no Kanban | Browser / Client | — | Consulta execucoes_aceite via API; renderiza badge |
| Sub-seção Bloco B | API / Backend + Browser | — | Backend calcula; frontend renderiza |
| % cobertura de aceite | API / Backend | — | Calculado em get_painel, adicionado ao response |

---

## Standard Stack

### Core (já instalado no projeto)
| Library | Purpose | Provenance |
|---------|---------|------------|
| FastAPI + `BackgroundTasks` | Fire-and-forget dispatch sem bloquear response | [VERIFIED: routers/revisao_ingest.py — padrão existente] |
| `urllib.request` (stdlib) | HTTP no aceite_agent.py — zero dependências | [VERIFIED: docudata-backend/hooks/revisor_agent.py:19] |
| `subprocess` (stdlib) | Rodar gates (build/test/e2e) no repo do projeto | [VERIFIED: docudata-backend/hooks/revisor_agent.py:28] |
| `supabase-py` (já instalado) | Insert/update execucoes_aceite | [VERIFIED: docudata-backend/services/supabase_client.py — em uso] |

### Novos campos / tabelas (sem nova lib)
| Item | Tipo | Onde |
|------|------|------|
| `execucoes_aceite` | nova tabela Supabase | Supabase SQL migration |
| `github_token` | text em `projects` | ALTER TABLE |
| `github_repo` | text em `projects` | ALTER TABLE |
| `testes_e2e` | text[] em `funcionalidades` | ALTER TABLE |

**Nenhuma nova dependência Python ou npm é necessária para esta fase.**

---

## Architecture Patterns

### System Architecture Diagram

```
PATCH /funcionalidades/{id} (status=concluida)
  │
  ├─► [1] Salva no banco + retorna 200 imediatamente
  │
  └─► [2] BackgroundTask: dispatch_aceite_task(funcionalidade_id, project_id)
              │
              ├─► Busca github_token + github_repo de projects
              │
              ├─► [se sem token/repo] → insert execucoes_aceite com todos gates=sem_cobertura
              │
              └─► [se configurado]
                    ├─► git rev-parse HEAD → commit_sha
                    ├─► insert execucoes_aceite (gates=[], disparado_em=now)  ← registro pendente
                    └─► POST api.github.com/repos/{owner}/{repo}/dispatches
                            event_type: "docudata-aceite"
                            client_payload: {funcionalidade_id, project_id, commit_sha,
                                            testes_e2e: [...], api_url: DOCUDATA_API_URL}

                          ↓ (GitHub Actions roda no repo do projeto)

aceite.yml → checkout → python scripts/aceite_agent.py
  aceite_agent.py:
    ├─► gate build: subprocess("npm run build" ou "pip install") → passou/falhou/erro
    ├─► gate testes_unitarios: subprocess("pytest" ou "npm test") → passou/falhou/erro
    ├─► gate e2e: se testes_e2e lista vazia → sem_cobertura; senão subprocess(testes)
    ├─► gate acessibilidade: sem_cobertura (MVP — sem ferramenta detectada)
    ├─► gate performance: sem_cobertura (MVP — sem ferramenta detectada)
    └─► POST /ingest/aceite {funcionalidade_id, commit_sha, gates: [{nome, resultado}]}

POST /ingest/aceite (novo endpoint)
  └─► UPDATE execucoes_aceite SET gates=?, concluido_em=now() WHERE funcionalidade_id=? AND commit_sha=?

GET /projects/{id}/painel
  └─► busca execucoes_aceite do projeto
  └─► calcula cobertura_aceite + funcionalidades_com_falha para bloco_b

Frontend KanbanCard (coluna Concluído):
  └─► se execucao_aceite com gate falhou/erro → exibe badge ⚠ vermelho/âmbar

Frontend BlocoBCard:
  └─► nova sub-seção "Cobertura de Aceite" com lista de funcionalidades com falha
```

### Recommended Project Structure (novos arquivos)

```
docudata-backend/
├── routers/
│   └── aceite_ingest.py          # POST /ingest/aceite
├── hooks/
│   ├── aceite_agent.py           # script Python stdlib para o CI
│   └── aceite.yml                # workflow GitHub Actions
docudata-frontend/app/
├── components/
│   └── AceiteBadge.tsx           # badge ⚠ para KanbanCard (zero className)
└── lib/
    └── api.ts                    # adicionar ExecucaoAceite interface + getExecucoesAceite()
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background task no FastAPI | `asyncio.create_task` raw no handler | `BackgroundTasks` (FastAPI nativo) | create_task raw pode ser garbage-collected antes de terminar se não houver referência; BackgroundTasks garante execução até o fim |
| Dispatch HTTP para GitHub | lib externa (httpx, requests) | `urllib.request` (stdlib) | Consistência com revisor_agent.py; sem nova dep; funciona no Railway |
| Detecção de runtime no aceite_agent | lógica complexa de auto-detect | subprocess best-effort com `continue-on-error: true` | O agente é best-effort por design; falhas não devem quebrar CI |

---

## Critical Patterns

### Pattern 1: GitHub repository_dispatch (Python stdlib)

```python
# Source: https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event
import urllib.request, json

def dispatch_github_aceite(github_token: str, github_repo: str, payload: dict):
    """Dispara repository_dispatch. Retorna True se sucesso (204), False caso contrário."""
    url = f"https://api.github.com/repos/{github_repo}/dispatches"
    body = json.dumps({
        "event_type": "docudata-aceite",
        "client_payload": payload   # max 10 top-level keys, max 64KB total
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 204
    except Exception:
        return False
```

[CITED: https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#create-a-repository-dispatch-event]

**Campos do client_payload para esta fase:**
```json
{
  "funcionalidade_id": "<uuid>",
  "project_id": "<uuid>",
  "commit_sha": "<sha do HEAD no momento do dispatch>",
  "testes_e2e": ["test_login.py", "test_checkout.spec.ts"],
  "api_url": "https://docudata-backend.railway.app"
}
```

### Pattern 2: FastAPI BackgroundTasks (preferir sobre asyncio.create_task)

```python
# Source: [VERIFIED: docudata-backend/routers/funcionalidades.py — padrão existente]
from fastapi import APIRouter, BackgroundTasks

@router.patch("/{funcionalidade_id}", response_model=FuncionalidadeResponse)
async def patch_funcionalidade(
    funcionalidade_id: str,
    data: FuncionalidadeUpdate,
    background_tasks: BackgroundTasks,   # injetar como parâmetro
):
    # ... lógica existente de transição de status ...

    # Adicionar após o update no banco:
    if data.status == "concluida" and func.get("status") != "concluida":
        background_tasks.add_task(
            dispatch_aceite_background,
            funcionalidade_id=funcionalidade_id,
            project_id=func["project_id"],
        )

    return result.data[0]
```

**Por que BackgroundTasks e não asyncio.create_task:**
- `asyncio.create_task` dentro de um handler pode ser garbage-collected se não houver referência externa — a task morre silenciosamente quando o request termina
- `BackgroundTasks` é o padrão idiomático do FastAPI para fire-and-forget: garante execução, mas ainda no mesmo processo (sem Celery)
- Para esta fase (dispatch HTTP curto, ~1-2s), BackgroundTasks é exatamente o nível certo

[CITED: https://dev.to/kaushikcoderpy/python-background-tasks-asyncio-traps-fastapi-celery-2026-381i]

### Pattern 3: Commit SHA no repository_dispatch

O `GITHUB_SHA` padrão do Actions **não está disponível** em eventos `repository_dispatch` — ele aponta para o SHA do último commit no default branch do DocuData, não do repo do projeto.

**Solução correta:** o DocuData passa o `commit_sha` no `client_payload`. O `aceite_agent.py` no repo do projeto obtém o SHA do HEAD atual via:

```bash
git rev-parse HEAD
```

Ou via `subprocess` no Python:
```python
import subprocess
commit_sha = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    capture_output=True, text=True
).stdout.strip()
```

O aceite_agent.py deve usar o SHA do HEAD do repo onde está rodando (o repo do projeto), não o SHA passado no payload. O payload SHA serve apenas como referência de "qual versão o DocuData sabia quando disparou".

[CITED: https://oneuptime.com/blog/post/2025-12-20-repository-dispatch-github-actions/view]

### Pattern 4: Supabase jsonb para lista de gates

```python
# Source: [VERIFIED: docudata-backend/routers/revisao_ingest.py:95-105 — padrão jsonb existente]
# Insert com lista de gates (jsonb aceita list[dict] diretamente)
client.table("execucoes_aceite").insert({
    "funcionalidade_id": funcionalidade_id,
    "project_id": project_id,
    "commit_sha": commit_sha,
    "gates": [],            # lista vazia enquanto aguarda resultado
    "disparado_em": datetime.now(timezone.utc).isoformat(),
}).execute()

# Update quando o resultado chega (POST /ingest/aceite)
client.table("execucoes_aceite").update({
    "gates": [
        {"nome": "build", "resultado": "passou"},
        {"nome": "testes_unitarios", "resultado": "falhou"},
        {"nome": "e2e", "resultado": "sem_cobertura"},
        {"nome": "acessibilidade", "resultado": "sem_cobertura"},
        {"nome": "performance", "resultado": "sem_cobertura"},
    ],
    "concluido_em": datetime.now(timezone.utc).isoformat(),
}).eq("funcionalidade_id", funcionalidade_id).eq("commit_sha", commit_sha).execute()
```

### Pattern 5: aceite.yml — Workflow GitHub Actions

```yaml
# Segue o mesmo padrão de revisor.yml [VERIFIED: docudata-backend/hooks/revisor.yml]
name: DocuData Aceite

on:
  repository_dispatch:
    types: [docudata-aceite]   # filtra por event_type

jobs:
  aceite:
    runs-on: ubuntu-latest
    continue-on-error: true    # best-effort: nunca quebra CI do projeto
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Executar suíte de aceite
        continue-on-error: true
        env:
          DOCUDATA_API_URL:       ${{ secrets.DOCUDATA_API_URL }}
          FUNCIONALIDADE_ID:      ${{ github.event.client_payload.funcionalidade_id }}
          PROJECT_ID:             ${{ github.event.client_payload.project_id }}
          TESTES_E2E:             ${{ toJson(github.event.client_payload.testes_e2e) }}
        run: python scripts/aceite_agent.py
```

**Nota crítica:** `repository_dispatch` workflows só são acionados se o workflow estiver **no default branch** do repo do projeto.

### Pattern 6: aceite_agent.py — Estrutura de gates

```python
#!/usr/bin/env python3
"""
DocuData Aceite Agent — roda gates e reporta resultados.
Python stdlib apenas. Best-effort: nunca falha o CI.
"""
import os, subprocess, json
import urllib.request, urllib.error

API_URL          = os.environ.get("DOCUDATA_API_URL", "").rstrip("/")
FUNCIONALIDADE_ID = os.environ.get("FUNCIONALIDADE_ID", "")
PROJECT_ID        = os.environ.get("PROJECT_ID", "")
TESTES_E2E_JSON   = os.environ.get("TESTES_E2E", "[]")

def run_cmd(cmd: list[str]) -> tuple[int, str]:
    """Roda comando, retorna (returncode, stdout+stderr)."""
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr

def gate_resultado(cmd: list[str] | None) -> str:
    """Executa gate e mapeia para passou|falhou|erro|sem_cobertura."""
    if cmd is None:
        return "sem_cobertura"
    try:
        rc, _ = run_cmd(cmd)
        return "passou" if rc == 0 else "falhou"
    except Exception:
        return "erro"

# Detectar commit SHA do HEAD atual (repo do projeto)
commit_sha = subprocess.run(
    ["git", "rev-parse", "HEAD"], capture_output=True, text=True
).stdout.strip() or "unknown"

# Detectar runtime (heurística best-effort)
has_package_json = os.path.exists("package.json")
has_requirements = os.path.exists("requirements.txt") or os.path.exists("pyproject.toml")

testes_e2e: list[str] = json.loads(TESTES_E2E_JSON) if TESTES_E2E_JSON else []

gates = [
    {"nome": "build",           "resultado": gate_resultado(
        ["npm", "run", "build"] if has_package_json else
        ["pip", "install", "-e", "."] if has_requirements else None
    )},
    {"nome": "testes_unitarios", "resultado": gate_resultado(
        ["npm", "test", "--", "--watchAll=false"] if has_package_json else
        ["pytest", "--tb=short", "-q"] if has_requirements else None
    )},
    {"nome": "e2e",             "resultado": "sem_cobertura" if not testes_e2e else
        gate_resultado(["python", "-m", "pytest"] + testes_e2e)},
    {"nome": "acessibilidade",  "resultado": "sem_cobertura"},  # MVP
    {"nome": "performance",     "resultado": "sem_cobertura"},  # MVP
]

# Reportar ao DocuData
payload = {"funcionalidade_id": FUNCIONALIDADE_ID, "commit_sha": commit_sha, "gates": gates}
body = json.dumps(payload).encode()
req = urllib.request.Request(
    f"{API_URL}/ingest/aceite", data=body,
    headers={"Content-Type": "application/json"}, method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[aceite] Resultado registrado — {r.status}")
except Exception as e:
    print(f"[aceite] Aviso: falha ao registrar ({e}) — continuando")
```

### Pattern 7: Badge no KanbanCard (zero className)

```tsx
// Adicionar ao KanbanCard em PainelTab.tsx
// Source: [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:473-510 — padrão existente]

interface ExecucaoAceite {
  funcionalidade_id: string;
  gates: { nome: string; resultado: string }[];
  concluido_em: string | null;
}

function AceiteBadge({ execucao }: { execucao: ExecucaoAceite | null }) {
  if (!execucao || !execucao.concluido_em) return null;
  const temFalha = execucao.gates.some(
    (g) => g.resultado === "falhou" || g.resultado === "erro"
  );
  if (!temFalha) return null;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 7px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        background: "#fee2e2",
        color: "#dc2626",
        marginLeft: 4,
      }}
    >
      ⚠ aceite
    </span>
  );
}
```

---

## Common Pitfalls

### Pitfall 1: asyncio.create_task garbage-collection silenciosa

**What goes wrong:** `asyncio.create_task(dispatch())` dentro de um handler FastAPI — a task pode ser coletada pelo GC quando o request termina antes da task completar.

**How to avoid:** Usar `BackgroundTasks` do FastAPI. É injetado como parâmetro no handler e garante execução.

**Warning signs:** Dispatch que "funciona em dev mas falha em produção intermitentemente" sem log de erro.

### Pitfall 2: repository_dispatch não dispara

**What goes wrong:** O workflow `aceite.yml` existe no repo mas não é acionado.

**Root cause:** `repository_dispatch` workflows **só rodam se o arquivo estiver no default branch** do repo. Se o gerente commitar em uma branch, o dispatch não funciona.

**How to avoid:** Documentar na instrução de instalação que `aceite.yml` deve estar na branch default (main/master).

### Pitfall 3: GITHUB_SHA errado no repository_dispatch

**What goes wrong:** Usar `${{ github.sha }}` no workflow de aceite retorna o SHA do DocuData, não do repo do projeto.

**How to avoid:** O aceite_agent.py deve obter o SHA via `git rev-parse HEAD` no próprio checkout. O `commit_sha` no client_payload do dispatch é apenas referência informativa de quando o DocuData disparou.

[CITED: https://www.codegenes.net/blog/get-commit-sha-in-github-actions/]

### Pitfall 4: Race condition no update de execucoes_aceite

**What goes wrong:** Se o gerente marcar duas funcionalidades como `concluida` rapidamente, dois dispatches podem chegar ao `POST /ingest/aceite` em ordem invertida, atualizando o registro errado.

**How to avoid:** O update deve filtrar por `funcionalidade_id` AND `commit_sha` (não apenas funcionalidade_id). O schema do D-04 já inclui `commit_sha NOT NULL` — usar ambos como chave de update.

### Pitfall 5: Campo `testes_e2e` em FuncionalidadeResponse não retornado

**What goes wrong:** Adicionar `testes_e2e` à tabela `funcionalidades` mas não ao schema Pydantic → o campo não aparece no response do PATCH.

**How to avoid:** Atualizar `FuncionalidadeResponse`, `FuncionalidadeUpdate`, e `FuncionalidadeCreate` em `schemas.py` simultaneamente à migration SQL.

[VERIFIED: docudata-backend/models/schemas.py:248-262 — FuncionalidadeResponse existente, precisa de testes_e2e adicionado]

### Pitfall 6: 422 do GitHub API — client_payload muito grande

**What goes wrong:** GitHub retorna 422 se `client_payload` tiver mais de 10 propriedades top-level OU ultrapassar 64KB.

**How to avoid:** Manter client_payload com ≤ 6 campos. Se `testes_e2e` for uma lista muito longa, truncar para os primeiros 50 itens.

[CITED: https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#create-a-repository-dispatch-event]

---

## Supabase Migration SQL

```sql
-- Tabela execucoes_aceite (D-04)
CREATE TABLE execucoes_aceite (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  funcionalidade_id uuid NOT NULL REFERENCES funcionalidades(id) ON DELETE CASCADE,
  project_id       uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  commit_sha       text NOT NULL,
  gates            jsonb NOT NULL DEFAULT '[]'::jsonb,
  disparado_em     timestamptz NOT NULL DEFAULT now(),
  concluido_em     timestamptz
);

-- Campos novos em projects (D-Discretion)
ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS github_token text,
  ADD COLUMN IF NOT EXISTS github_repo  text;

-- Campo novo em funcionalidades (D-06)
ALTER TABLE funcionalidades
  ADD COLUMN IF NOT EXISTS testes_e2e text[] NOT NULL DEFAULT '{}';
```

---

## Integration Points (Canonical References)

| File | Change | Source Verified |
|------|--------|-----------------|
| `routers/funcionalidades.py` | Adicionar `BackgroundTasks` param + call a `dispatch_aceite_background` quando status→concluida | [VERIFIED: docudata-backend/routers/funcionalidades.py:162-229] |
| `routers/aceite_ingest.py` | Novo arquivo — POST /ingest/aceite, padrão de revisao_ingest.py | [VERIFIED: docudata-backend/routers/revisao_ingest.py] |
| `main.py` | `app.include_router(aceite_ingest.router)` | [VERIFIED: docudata-backend/main.py:6,31] |
| `models/schemas.py` | Adicionar `testes_e2e: list[str]` a FuncionalidadeResponse + FuncionalidadeUpdate | [VERIFIED: docudata-backend/models/schemas.py:215-261] |
| `routers/painel.py` | `calcular_bloco_b` + `get_painel`: adicionar `cobertura_aceite` e `funcionalidades_com_aceite_falhando` | [VERIFIED: docudata-backend/routers/painel.py:69-144, 293-337] |
| `hooks/aceite_agent.py` | Novo script Python stdlib | — |
| `hooks/aceite.yml` | Novo workflow GitHub Actions | [VERIFIED: docudata-backend/hooks/revisor.yml — template] |
| `app/components/PainelTab.tsx` | Badge no KanbanCard + sub-seção Bloco B | [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:473-728] |
| `app/lib/api.ts` | Adicionar interface ExecucaoAceite + funções fetch | [VERIFIED: docudata-frontend/app/lib/api.ts:1-100] |

---

## Environment Availability

Step 2.6: Verificado — nenhuma dependência nova de sistema é necessária. Todo o stack já está instalado. O `aceite_agent.py` usa stdlib Python e subprocess (git já disponível no ubuntu-latest do GitHub Actions).

| Dependency | Required By | Available | Fallback |
|------------|------------|-----------|---------|
| GitHub API (api.github.com) | Dispatch do aceite | ✓ (external) | Se token ausente → sem_cobertura |
| Python stdlib (urllib, subprocess) | aceite_agent.py | ✓ (python3 no ubuntu-latest) | — |
| git | commit SHA no aceite_agent.py | ✓ (ubuntu-latest tem git) | hardcode "unknown" |

---

## Validation Architecture

O projeto não tem `nyquist_validation` explicitamente desativado em config.json, mas esta fase não tem requirements numerados com IDs de teste. Os success criteria são funcionais e testáveis manualmente.

**Per-task verification (manual):**
1. PATCH com status=concluida → checar Supabase: `execucoes_aceite` tem registro criado
2. Simular POST /ingest/aceite → checar: `gates` atualizado, `concluido_em` preenchido
3. GET /painel → checar: `cobertura_aceite` presente no response, bloco_b tem sub-seção
4. Kanban com funcionalidade concluída com falha → checar: badge ⚠ aparece no card

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `aceite_agent.py` detecta runtime por presença de `package.json` ou `requirements.txt` | aceite_agent.py Pattern | Repo com estrutura diferente → gate retorna `erro` ao invés de `passou/falhou` — aceitável (best-effort) |
| A2 | Gates `acessibilidade` e `performance` registram `sem_cobertura` no MVP | gates fixos | Se o gerente espera dados reais desses gates no MVP → refactor necessário |
| A3 | `BackgroundTasks` do FastAPI suporta funções async (não apenas sync) | Pattern 2 | Se BackgroundTasks exigir sync wrapper → trocar para `asyncio.create_task` com `asyncio.shield` |

---

## Open Questions

1. **Coluna Concluído no Kanban carrega execucoes_aceite?**
   - O que sabemos: `PainelTab.tsx` carrega funcionalidades via `listFuncionalidades`. Não carrega `execucoes_aceite`.
   - Gap: Precisamos de um endpoint `GET /execucoes_aceite?project_id=...` ou enriquecer `FuncionalidadeResponse` com o `execucao_aceite` mais recente.
   - Recomendação: Adicionar endpoint `GET /execucoes_aceite/{project_id}` (retorna lista, mapeado por funcionalidade_id) e chamar em paralelo com `listFuncionalidades` no PainelTab.

2. **`ProjectResponse` em schemas.py precisa de `github_repo` e `github_token` expostos?**
   - `github_token` NUNCA deve aparecer em response de API (segurança). Adicionar campo `has_github_config: bool` ao `ProjectResponse` para o frontend saber se o dispatch vai funcionar.

---

## Sources

### Primary (HIGH confidence)
- GitHub REST API docs (fetched diretamente) — endpoint POST /repos/{owner}/{repo}/dispatches, payload format, response codes
- `docudata-backend/hooks/revisor_agent.py` (lido nesta sessão) — padrão stdlib Python para agente CI
- `docudata-backend/hooks/revisor.yml` (lido nesta sessão) — template workflow GitHub Actions
- `docudata-backend/routers/revisao_ingest.py` (lido nesta sessão) — padrão POST /ingest/*
- `docudata-backend/routers/funcionalidades.py` (lido nesta sessão) — handler patch_funcionalidade existente
- `docudata-backend/routers/painel.py` (lido nesta sessão) — calcular_bloco_b e get_painel
- `docudata-backend/models/schemas.py` (lido nesta sessão) — schemas Pydantic existentes
- `docudata-frontend/app/components/PainelTab.tsx` (lido nesta sessão) — padrão zero className

### Secondary (MEDIUM confidence)
- WebSearch: FastAPI BackgroundTasks vs asyncio.create_task — padrão confirmado por múltiplas fontes
- WebSearch: GitHub repository_dispatch + commit SHA via client_payload — padrão confirmado

### Tertiary (LOW confidence)
- `aceite_agent.py` gate detection heuristics — [ASSUMED] baseado no padrão revisor_agent.py + conhecimento de runtime detection

---

## Metadata

**Confidence breakdown:**
- GitHub repository_dispatch API: HIGH — documentação oficial lida diretamente
- FastAPI BackgroundTasks pattern: HIGH — padrão estabelecido no projeto + WebSearch
- aceite_agent.py gate detection: MEDIUM — heurística best-effort, aceitável para MVP
- Supabase jsonb: HIGH — padrão já em uso no projeto (revisao_ingest.py)
- Frontend badge (zero className): HIGH — padrão lido em PainelTab.tsx

**Research date:** 2026-08-23
**Valid until:** 2026-09-23 (stack estável)
