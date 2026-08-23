---
phase: 10-composer-de-planning
plan: "03"
subsystem: backend
tags: [bug-fix, gap-closure, supabase, upsert, planning-wizard]
status: complete

dependency_graph:
  requires:
    - "10-02"
  provides:
    - "CR-01 fix — get_rascunho preserva progresso do wizard"
  affects:
    - docudata-backend/routers/composer.py

tech_stack:
  added: []
  patterns:
    - "upsert ignore_duplicates=True + SELECT explicito para operacao insert-or-read segura"

key_files:
  created: []
  modified:
    - docudata-backend/routers/composer.py

decisions:
  - "ignore_duplicates=True em vez de upsert destrutivo: garante que step_atual e dados_json do rascunho existente jamais sejam sobrescritos por um GET"
  - "SELECT explicito apos upsert: retorna sempre a linha real do banco (nova ou pre-existente), tornando o comportamento determinístico independente do retorno do upsert"

metrics:
  duration: "15min"
  completed: "2026-08-23"
  tasks_completed: 1
  commits: 1

actuals:
  tokens: 3750
  tasks: 1
  commits: 1
---

# Phase 10 Plan 03: CR-01 gap closure — upsert ignore_duplicates=True + SELECT explicito Summary

**One-liner:** Corrige bug destrutivo em `get_rascunho`: substitui upsert-on-conflict-overwrite por `ignore_duplicates=True` + SELECT explicito, preservando `step_atual` e `dados_json` do wizard em chamadas subsequentes.

## What Was Built

Single surgical fix in `docudata-backend/routers/composer.py`, funcao `get_rascunho` (linhas 113-129):

**Antes (bugado):** cada chamada ao `GET /composer/rascunho/{id}/{n}` sobrescrevia `step_atual` para 1 e `dados_json` para `{}` via upsert padrao — qualquer progresso salvo no wizard era destruido ao fechar e reabrir o browser.

**Depois (corrigido):**

- Step 1: `upsert(ignore_duplicates=True)` — insert-only; linha existente fica completamente intacta
- Step 2: SELECT explicito via `fetch_resp` — sempre retorna a linha real (nova ou pre-existente)
- Validacao de `fetch_resp.data` com HTTPException 500 se ausente

## Gaps Closed

| Gap | Status |
|-----|--------|
| SC-1: GET /rascunho nao redefine step_atual/dados_json quando rascunho ja existe | FECHADO |
| P1-1: GET /rascunho retorna rascunho existente intacto + throughput_ref + transbordos | FECHADO |

## Verification Results

```
grep -c 'ignore_duplicates=True' composer.py  => 1  PASS
grep -c 'fetch_resp' composer.py              => 3  PASS (>=2)
grep -c 'upsert_resp.data[0]' composer.py    => 0  PASS (old pattern gone)
AST parse + assertion script                  => OK: ignore_duplicates=True present, explicit SELECT present
```

## Commits

| Hash | Message |
|------|---------|
| 3c7cd1a | fix(10-03): CR-01 — upsert ignore_duplicates=True + SELECT explicito em get_rascunho |

## Deviations from Plan

None — plan executed exactly as written. The file did not exist in the worktree (plan 10-02 created it in a parallel worktree not yet merged to main); it was brought in from the main repo before applying the fix. No other functions or imports were changed.

## Known Stubs

None.

## Self-Check: PASSED

- `docudata-backend/routers/composer.py` committed in worktree: FOUND (3c7cd1a)
- `ignore_duplicates=True` count = 1: PASS
- `fetch_resp` count >= 2: PASS (3)
- Old pattern `upsert_resp.data[0]` in get_rascunho: GONE
- AST parse assertion: PASS
