---
phase: 12-boletim-de-aceite-encerramento-e-resumo-semanal
plan: "01"
subsystem: backend
status: complete
tags:
  - boletins-aceite
  - fastapi
  - gemini
  - langgraph
dependency_graph:
  requires:
    - "11-02 (funcionalidades schema e router)"
    - "supabase boletins_aceite table (manual migration)"
  provides:
    - "POST /boletins — gera boletim de aceite via Gemini"
    - "GET /boletins/{project_id} — lista boletins"
  affects:
    - "docudata-backend/main.py"
    - "docudata-backend/models/schemas.py"
    - "docudata-backend/routers/boletins.py"
tech_stack:
  added:
    - "boletins_aceite table (text[] funcionalidade_ids, status CHECK, conteudo text)"
  patterns:
    - "ChatGoogleGenerativeAI ainvoke com SystemMessage + HumanMessage (mesmo padrão composer.py)"
    - "ownership check de funcionalidade_ids antes de chamar Gemini (T-12-01)"
    - "try/except em ainvoke retorna 502 em vez de travar (T-12-04)"
key_files:
  created:
    - "docudata-backend/routers/boletins.py"
  modified:
    - "docudata-backend/models/schemas.py"
    - "docudata-backend/main.py"
decisions:
  - "gemini-3.5-flash-lite: consistente com composer.py (D-02 especificava gemini-1.5-flash mas projeto já usa gemini-3.5-flash-lite)"
  - "funcionalidade_ids como text[] no DDL para evitar erros de serialização supabase-py (RESEARCH Pitfall 7)"
  - "Ownership check via .in_() + count comparison garante T-12-01 sem N+1 queries"
metrics:
  duration: "~15 minutes"
  completed: "2026-08-23"
  tasks_completed: 1
  tasks_total: 1
  commits: 1
estimate:
  tokens: 60000
actuals:
  tokens: 10500
  tasks: 1
  commits: 1
---

# Phase 12 Plan 01: Tracer Boletins Aceite — Schemas + Router POST/GET + main.py Wiring Summary

JWT auth with refresh rotation using jose library — Boletim de aceite end-to-end: gerente seleciona funcionalidades concluídas → backend busca critérios → Gemini gera markdown em linguagem de negócio → salvo em boletins_aceite como rascunho.

## What Was Built

Tracer vertical completo para o fluxo de Boletim de Aceite:

1. **4 schemas Pydantic** adicionados a `schemas.py`: `BoletimCreate`, `BoletimPatch`, `BoletimResponse`, `ResumoSemanalRequest`
2. **`routers/boletins.py`** (novo): router FastAPI com prefix `/boletins`
   - `POST /boletins`: recebe `BoletimCreate`, verifica ownership dos `funcionalidade_ids` (T-12-01), busca critérios de aceite, chama Gemini via `ChatGoogleGenerativeAI.ainvoke`, persiste em `boletins_aceite` com `status="rascunho"`
   - `GET /boletins/{project_id}`: lista boletins ordenados por `criado_em DESC`
   - Constante `_BOLETIM_SYSTEM_PROMPT` definida no módulo
3. **`main.py`**: boletins router importado e registrado com `app.include_router(boletins.router)`
4. **Migration SQL documentada** (DDL para execução manual no Supabase SQL Editor — tabela `boletins_aceite` com `text[]` para `funcionalidade_ids`, CHECK constraints em `status` e `retorno_tipo`, index em `(project_id, criado_em DESC)`)

## Verifications Passed

All 8 automated checks from `<verify>` block passed:
- `ast.parse` em `boletins.py`, `main.py`, `schemas.py`: todos OK
- `from routers import boletins`: importa sem erro
- Routes: `['/boletins', '/boletins/{project_id}']` — ambos presentes
- `grep include_router(boletins main.py`: count = 1
- `from models.schemas import BoletimCreate, BoletimPatch, BoletimResponse, ResumoSemanalRequest`: OK
- `grep _BOLETIM_SYSTEM_PROMPT routers/boletins.py`: count = 2 (definição + uso)
- `python3 -c "import main"`: OK

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Note on model name:** D-02 referenciava `gemini-1.5-flash`; plano já antecipou usar `gemini-3.5-flash-lite` como o projeto usa em `composer.py`. Seguido o plano sem desvio.

## Security — Threat Mitigations Applied

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-12-01 | Mitigado | Ownership check via `.in_()` + count comparison antes de chamar Gemini; retorna 422 se qualquer `funcionalidade_id` não pertencer ao projeto |
| T-12-02 | Mitigado | `gemini_api_key` buscada via `project_id` no backend; nunca incluída em nenhum `BoletimResponse` |
| T-12-03 | Aceito | MVP sem autenticação — decisão consciente do projeto |
| T-12-04 | Mitigado | `try/except` em `ainvoke` retorna HTTP 502 em vez de deixar o servidor travar |

## Database Migration Required

A tabela `boletins_aceite` precisa ser criada manualmente no Supabase SQL Editor antes de usar os endpoints. DDL documentado no PLAN.md (seção `<action>` Step 0):

```sql
CREATE TABLE IF NOT EXISTS boletins_aceite (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_numero       int,
    funcionalidade_ids  text[]      NOT NULL DEFAULT '{}',
    status              text        NOT NULL DEFAULT 'rascunho'
                        CHECK (status IN ('rascunho', 'enviado', 'aprovado', 'ajuste')),
    retorno_tipo        text        CHECK (retorno_tipo IS NULL OR retorno_tipo IN ('bug', 'mudanca_escopo')),
    conteudo            text        NOT NULL DEFAULT '',
    criado_em           timestamptz NOT NULL DEFAULT now(),
    enviado_em          timestamptz,
    retorno_em          timestamptz
);
CREATE INDEX IF NOT EXISTS idx_boletins_aceite_project
    ON boletins_aceite (project_id, criado_em DESC);
```

## Commits

| Hash | Message |
|------|---------|
| 0faf006 | feat(12-01): tracer boletins_aceite — schemas + router POST/GET + main wiring |

## Self-Check: PASSED

- [x] `docudata-backend/routers/boletins.py` exists
- [x] `docudata-backend/models/schemas.py` updated with 4 new schemas
- [x] `docudata-backend/main.py` registers boletins router
- [x] Commit 0faf006 exists (verified via git log)
- [x] All verification commands passed
