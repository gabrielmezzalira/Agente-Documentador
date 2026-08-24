---
phase: 12-boletim-de-aceite-encerramento-e-resumo-semanal
plan: "02"
subsystem: backend/boletins
status: complete
tags:
  - fastapi
  - boletins
  - status-lifecycle
  - resumo-semanal
  - deterministic
dependency_graph:
  requires:
    - "12-01"
  provides:
    - PATCH /boletins/{id}
    - POST /boletins/resumo_semanal
  affects:
    - docudata-backend/routers/boletins.py
    - funcionalidades (status_cliente field)
    - transicoes_status (batch inserts)
    - generated_docs (doc_type=resumo_semanal)
tech_stack:
  added: []
  patterns:
    - TransicaoStatus batch pattern (replicated from funcionalidades.py)
    - Deterministic markdown generation without LLM
    - FastAPI static-before-parametric route ordering
key_files:
  modified:
    - docudata-backend/routers/boletins.py
decisions:
  - "Route POST /boletins/resumo_semanal registered before PATCH /boletins/{id} to prevent path capture"
  - "resumo_semanal reuses calcular_bloco_a + calcular_bloco_b from painel.py — no hand-rolling"
  - "No Gemini call in gerar_resumo_semanal — deterministic, zero token cost (D-08/Pitfall 6)"
  - "Bloco Tempo x Escopo always appended, with graceful fallback when dates not configured"
metrics:
  duration_minutes: 35
  completed_date: "2026-08-24"
  tasks_completed: 2
  commits: 2
actuals:
  tokens: 18000
  tasks: 2
  commits: 2
---

# Phase 12 Plan 02: Expansion Boletins — PATCH + Resumo Semanal Summary

PATCH /boletins/{id} with enforced status sequence and batch TransicaoStatus, plus POST /boletins/resumo_semanal delivering M8 via deterministic markdown without Gemini.

## What Was Built

### Task 1 — PATCH /boletins/{id} (commit `332113a`)

Added status lifecycle management to the boletins router:

- `TRANSICOES_VALIDAS` dict enforces rascunho→enviado, enviado→aprovado/ajuste (T-12-05)
- 422 on invalid sequence with descriptive message including valid transitions
- 422 when `status=ajuste` and `retorno_tipo` is absent or not in `{bug, mudanca_escopo}` (T-12-06)
- `_registrar_transicao_status_cliente()` helper replicates funcionalidades.py:280-307 pattern: fetches prior transition timestamp, calculates `duracao_fase_anterior_segundos`, inserts into `transicoes_status`, then updates `funcionalidades.status_cliente`
- Batch update over all `funcionalidade_ids` in the boletim
- `enviado_em` set on `status=enviado`; `retorno_em + retorno_tipo` set on `status=aprovado|ajuste`
- Mapping: enviado→enviado, aprovado→aprovado, ajuste→ajuste_pedido (D-05)

### Task 2 — POST /boletins/resumo_semanal (commit `ce4cb1f`)

Deterministic weekly anomaly summary — zero token cost, zero hallucination risk:

- Period calculation: `(hoje.weekday() + 1) % 7` days since Sunday → dom–sáb range (D-09/Pitfall 5)
- Queries: funcionalidades, transicoes_status, revisoes_diarias (most recent), execucoes_aceite
- Calls `calcular_bloco_a(projeto, funcs)` and `calcular_bloco_b(funcs, transicoes, revisao_recente, execucoes_aceite)` from painel.py — no hand-rolling
- Markdown sections: Funcionalidades Travadas / Aguardando Cliente / Concluídas com Suíte Falhando / Achados Críticos (Revisão de Código) / Leitura Tempo x Escopo
- When all lists empty: `## Status\nNenhuma anomalia identificada nesta semana.`
- `achados_criticos` from `calcular_bloco_b` includes items from `revisoes_diarias.achados` where severidade in (CRITICA, ALTA) and confianca=ALTA (§4.5)
- Saves to `generated_docs`: `doc_type=resumo_semanal`, `sprint_number=None`, `input_tokens=0`, `output_tokens=0`, `cost_usd=0.0` (D-10)
- Route registered BEFORE `PATCH /{id}` to prevent path capture by parametric route

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Route ordering fix for /resumo_semanal vs /{id}**
- **Found during:** Task 2 verification
- **Issue:** `POST /boletins/resumo_semanal` was initially appended after `PATCH /boletins/{id}`. While HTTP methods differ (no immediate conflict), the plan explicitly requires static routes to be registered before parametric ones to avoid edge cases, and `GET /boletins/{project_id}` would capture any GET to `/boletins/resumo_semanal`.
- **Fix:** Moved `gerar_resumo_semanal` function block before `atualizar_status_boletim`. Route order confirmed: resumo_semanal (index 2) < /{id} (index 3).
- **Files modified:** docudata-backend/routers/boletins.py
- **Commit:** ce4cb1f (included in Task 2 commit)

## Self-Check

```
PASS: resumo_semanal registered before /{id}
PASS: no Gemini call in gerar_resumo_semanal
PASS: dom-sab period calculation present
PASS: no-anomaly message present
PASS: calcular_bloco_a and calcular_bloco_b called
PASS: generated_docs insert with resumo_semanal doc_type
PASS: PATCH validations intact
ALL CHECKS PASSED
```

**Files exist:**
- docudata-backend/routers/boletins.py: FOUND

**Commits exist:**
- 332113a: FOUND (Task 1)
- ce4cb1f: FOUND (Task 2)

## Self-Check: PASSED
