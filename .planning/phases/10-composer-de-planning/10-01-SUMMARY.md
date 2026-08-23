---
phase: 10-composer-de-planning
plan: 01
subsystem: api
tags: [fastapi, supabase, postgresql, langgraph]

requires:
  - phase: prior phases
    provides: supabase_client, schemas patterns, existing routers as reference

provides:
  - planning_rascunhos SQL table with UNIQUE(project_id, sprint_numero)
  - composer.router with GET /rascunho, PATCH /rascunho, POST /confirmar endpoints
  - calcular_throughput_ref function (funcionalidades/sprint, últimas 3 sprints)
  - composer.router registered in main.py

affects: [10-02]

actuals:
  tokens: 2545
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - upsert for idempotent create-or-get (on_conflict parameter in supabase-py)
    - insert-before-delete order for confirmar (D-07)
    - sprint_alvo always compared as str(N), never int

key-files:
  created:
    - docudata-backend/routers/composer.py
  modified:
    - docudata-backend/supabase_schema.sql
    - docudata-backend/main.py

key-decisions:
  - "POST /confirmar: insert generated_docs BEFORE delete planning_rascunhos (D-07/Pitfall 3)"
  - "GET /rascunho uses upsert on_conflict='project_id,sprint_numero' to create-if-not-exists atomically"
  - "sprint_alvo compared as str(N-1), str(N-2), str(N-3) — never int (Pitfall 1 from RESEARCH.md)"
  - "calcular_throughput_ref returns funcionalidades/sprint (not per week) — matches planning mental model"

patterns-established:
  - "Upsert pattern: supabase.table().upsert({...}, on_conflict='project_id,sprint_numero').execute()"
  - "get_client() called inside each handler, not at module level (lazy factory pattern)"
  - "Confirmar order: INSERT generated_docs → check resp.data → DELETE planning_rascunhos"

requirements-completed:
  - "M4 (§5)"

coverage:
  - id: D1
    description: "planning_rascunhos table in supabase_schema.sql with UNIQUE constraint"
    requirement: "M4 (§5)"
    verification:
      - kind: automated
        ref: "grep -c planning_rascunhos docudata-backend/supabase_schema.sql → 2"
        status: pass
    human_judgment: false
  - id: D2
    description: "composer.py with GET/PATCH/POST confirmar endpoints"
    requirement: "M4 (§5)"
    verification:
      - kind: automated
        ref: "python -c 'from routers import composer; print(len(composer.router.routes))' → 3"
        status: pass
    human_judgment: false
  - id: D3
    description: "composer.router registered in main.py"
    requirement: "M4 (§5)"
    verification:
      - kind: automated
        ref: "python -c 'import main' → no errors"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /confirmar inserts in generated_docs BEFORE deleting rascunho (D-07)"
    verification:
      - kind: code-inspection
        ref: "composer.py lines 199-224: INSERT at line 200, DELETE at line 224 — insert first, delete after resp.data check"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-08-23
status: complete
---

# Phase 10 Plan 01: Tracer backend composer — planning_rascunhos + 3 endpoints

**One-liner:** Nova tabela `planning_rascunhos` no Supabase + router FastAPI `/composer` com GET/PATCH/POST confirmar, implementando o ciclo completo de rascunho → planning oficial sem camada Gemini.

## What Was Built

### 1. `docudata-backend/supabase_schema.sql` — Bloco Phase 10

Adicionado ao final do arquivo (após seção Phase 9), seguindo o estilo de formatação estabelecido:

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
```

Inclui comentário de migration para tabela existente.

### 2. `docudata-backend/routers/composer.py` — Router com 3 endpoints

**GET /composer/rascunho/{project_id}/{sprint_numero}**
- Upsert atômico via `supabase.upsert(on_conflict="project_id,sprint_numero")` — cria se não existe, retorna existente
- Calcula `throughput_ref` (funcionalidades/sprint das últimas 3 sprints) via `calcular_throughput_ref()`
- Detecta transbordos: funcionalidades com `sprint_alvo == str(sprint_numero - 1)` e `status != 'concluida'`
- Retorna `{rascunho, throughput_ref, transbordos}`

**PATCH /composer/rascunho/{project_id}/{sprint_numero}**
- Body: `{step_atual: int, dados_json: dict}`
- Verifica existência do rascunho antes de atualizar (404 se não existe)
- Atualiza `step_atual`, `dados_json`, `updated_at`

**POST /composer/confirmar**
- Body: `{project_id, sprint_numero, markdown}` — Pydantic valida markdown não-vazio (422 se vazio)
- Verifica existência do rascunho (404 se não existe — Pitfall 2)
- Ordem obrigatória D-07: INSERT `generated_docs` com `doc_type='planning'` → DELETE `planning_rascunhos`
- Se INSERT falhar: HTTPException 500, rascunho preservado (Pitfall 3)

### 3. `docudata-backend/main.py` — Registro do router

```python
from routers import ..., revisao_ingest, composer
app.include_router(composer.router)
```

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Import composer | `python -c "from routers import composer; print(composer.router.prefix)"` | `/composer` — PASS |
| 3 rotas registradas | `len(composer.router.routes)` | `3` — PASS |
| main.py importa sem erro | `python -c "import main"` | OK — PASS |
| planning_rascunhos no SQL | `grep -c planning_rascunhos supabase_schema.sql` | `2` — PASS |
| Markdown vazio → 422 | `ConfirmarBody(markdown='')` → ValidationError | PASS |
| Markdown whitespace → 422 | `ConfirmarBody(markdown='   ')` → ValidationError | PASS |
| sprint_alvo como str | `str(sprint_numero - 1)` e `[str(s) for s in sprints_ref]` | PASS |
| INSERT antes de DELETE | Linhas 200 e 224 de composer.py | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-10-02 | `field_validator("markdown")` em `ConfirmarBody` rejeita markdown vazio/whitespace com ValidationError (422) |
| T-10-04 | Todos os endpoints filtram por `project_id` nas queries Supabase — não confiam no UUID do rascunho isoladamente |

## Self-Check: PASSED

- [x] `docudata-backend/routers/composer.py` — FOUND
- [x] `docudata-backend/supabase_schema.sql` — FOUND (with planning_rascunhos)
- [x] `docudata-backend/main.py` — FOUND (with composer import and include_router)
- [x] Commit `3018c2c` — FOUND
