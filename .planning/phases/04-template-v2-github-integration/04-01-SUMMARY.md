---
phase: "04"
plan: "04-01"
subsystem: backend
tags: [sprint-docs, campos-estruturados, planning, review, retrospectiva, supabase]
dependency_graph:
  requires: []
  provides:
    - campos_planning sub-dict in extracted_content for planning ingestions
    - campos_review sub-dict in extracted_content for review ingestions
    - campos_retrospectiva sub-dict in extracted_content for retrospectiva ingestions
    - POST /sprint-docs/retrospectiva endpoint
    - supabase_schema.sql CHECK constraint with retrospectiva and commit
  affects:
    - docudata-backend/routers/sprint_docs.py
    - docudata-backend/supabase_schema.sql
tech_stack:
  added: []
  patterns:
    - campos_daily pattern extended to campos_planning, campos_review, campos_retrospectiva
key_files:
  modified:
    - docudata-backend/supabase_schema.sql
    - docudata-backend/routers/sprint_docs.py
decisions:
  - campos_planning/campos_review/campos_retrospectiva follow the existing campos_daily sub-dict pattern for consistency
  - All new Form params are Optional so existing endpoints do not break without them
  - submit_retrospectiva passes ingestion_id=None to _run_generation (same as review — generation graph fetches all sprint ingestions)
  - tipo_documentacao="retrospectiva" stored in ingestion for constraint-compliant filtering
metrics:
  duration: "~15min"
  completed_date: "2026-07-28"
  tasks_completed: 5
  tasks_total: 5
  files_modified: 2
---

# Phase 04 Plan 01: Backend — Novos Campos Estruturados Summary

**One-liner:** Novos Form fields armazenados como sub-dicts campos_planning (7 campos), campos_review (3 campos) e campos_retrospectiva em extracted_content JSONB, com endpoint /sprint-docs/retrospectiva e CHECK constraint atualizada no SQL.

## What Was Built

### Task 1 — CHECK constraint atualizada (f977c8c)
`supabase_schema.sql` linha 21: adicionados `'retrospectiva'` e `'commit'` ao IN list do CHECK constraint de `tipo_documentacao`. Bloco de migration comentado (v2) adicionado ao final do arquivo com as instruções ALTER TABLE para banco já em produção.

### Task 2 — campos_planning em submit_planning (497de77)
`submit_planning` recebe agora 7 novos Form params opcionais: `squad`, `periodo_inicio`, `periodo_fim`, `horas_disponiveis`, `horas_estimadas`, `dependencias_cliente`, `carry_over`. Todos armazenados no sub-dict `campos_planning` dentro de `extracted_content` no JSONB.

### Task 3 — campos_review em submit_review (de5be90)
`submit_review` recebe agora 3 novos Form params opcionais: `percepcao_cliente`, `sinal_satisfacao`, `pedidos_fora_escopo`. Todos armazenados no sub-dict `campos_review` dentro de `extracted_content`.

### Task 4 — Endpoint POST /sprint-docs/retrospectiva (cecf7b8)
Novo endpoint `submit_retrospectiva` seguindo o padrão de `submit_review`. Recebe `pedido_fora_escopo_status` e `observacoes` opcionais, mais `anexo` opcional. Armazena `campos_retrospectiva.pedido_fora_escopo_status` no JSONB. Insere com `tipo_documentacao="retrospectiva"` e chama `_run_generation` com `tipo_doc="retrospectiva"` e `ingestion_id=None`.

### Task 5 — Checkpoint (APROVADO)
Verificacao manual no Supabase SQL Editor e testes de curl realizados pelo usuario. Migration SQL executada no banco de producao. Campos confirmados no Supabase.

## Commits

| Hash | Task | Description |
|------|------|-------------|
| f977c8c | 1 | feat(04-01): atualizar CHECK constraint tipo_documentacao com retrospectiva e commit |
| 497de77 | 2 | feat(04-01): adicionar campos_planning ao submit_planning com 7 novos Form fields |
| de5be90 | 3 | feat(04-01): adicionar campos_review ao submit_review com 3 novos Form fields |
| cecf7b8 | 4 | feat(04-01): criar endpoint POST /sprint-docs/retrospectiva com campos_retrospectiva |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All fields are wired to real Form inputs and stored in JSONB. The generation graph (`tipo_doc="retrospectiva"`) does not yet have a prompt template — this will be resolved when the generation graph is updated in a subsequent plan to handle the "retrospectiva" doc type.

## Threat Flags

None. No new network endpoints beyond what is described in the plan. The new `/sprint-docs/retrospectiva` endpoint follows the same auth pattern (project-level gemini_api_key gate) as existing sprint-docs endpoints.

## Self-Check

- [x] `docudata-backend/supabase_schema.sql` contains `'retrospectiva'` in CHECK constraint — FOUND
- [x] `docudata-backend/routers/sprint_docs.py` contains `campos_planning` sub-dict — FOUND
- [x] `docudata-backend/routers/sprint_docs.py` contains `campos_review` sub-dict — FOUND
- [x] `docudata-backend/routers/sprint_docs.py` contains `@router.post("/retrospectiva"` — FOUND
- [x] Commits f977c8c, 497de77, de5be90, cecf7b8 — all present in git log

## Self-Check: PASSED
