---
phase: 05-content-type-validation-on-ingestion
plan: "01"
subsystem: backend-extraction-graph
status: complete
tags:
  - langgraph
  - gemini
  - validation
  - extraction-graph
dependency_graph:
  requires: []
  provides:
    - extraction_graph.validar_tipo_node
    - extraction_graph.tipo_detectado_in_extracted_content
  affects:
    - docudata-backend/graphs/extraction_graph.py
tech_stack:
  added: []
  patterns:
    - "LangGraph conditional edge with router function (_roteador_validacao)"
    - "Gemini lightweight classification call (max_tokens=256, no structured output)"
    - "Safe fallback: json parse errors default to nao_bloquear=True — never block on uncertainty"
key_files:
  created: []
  modified:
    - docudata-backend/graphs/extraction_graph.py
decisions:
  - "validar_tipo is the first node in the graph (START -> validar_tipo -> conditional edge)"
  - "force=True bypasses validation entirely, registering override in _meta_force_override"
  - "upload_livre endpoint only blocks nao_relacionado; all DocuData categories pass through"
  - "JSON parse errors in validar_tipo default to nao_bloquear=True (safe fallback, T-05-01)"
  - "Preview capped at 3000 bytes with errors='replace' decode to bound processing cost (T-05-02)"
metrics:
  duration_minutes: 2
  completed_date: "2026-08-13"
  tasks_completed: 2
  commits: 2
estimate:
  tokens: 55000
actuals:
  tokens: 2476
  tasks: 2
  commits: 2
requirements:
  - VAL-01
  - VAL-02
---

# Phase 05 Plan 01: Validar Tipo Node — Summary

Adicionado nó `validar_tipo` como primeiro nó do grafo de extração, com classificacao Gemini de 8 categorias, logica de bloqueio suave, e anotacao de metadados de validacao no `extracted_content` de cada ingestao salva.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (tracer) | End-to-end validation path — validar_tipo node added | c649485 | docudata-backend/graphs/extraction_graph.py |
| 2 | Annotate tipo_detectado into extracted_content in salvar node | 05f96e8 | docudata-backend/graphs/extraction_graph.py |

## What Was Built

### Task 1 — validar_tipo node (tracer)

Extended `ExtractionState` TypedDict with 7 new fields:

- `tipo_esperado: Optional[str]` — document type expected by the endpoint
- `force: Optional[bool]` — bypass validation when True
- `projeto_nome: Optional[str]` — project name for Gemini context
- `cliente: Optional[str]` — client name for Gemini context
- `projeto_descricao: Optional[str]` — project description for Gemini context
- `tipo_detectado: Optional[str]` — classification output (one of 8 categories)
- `mensagem_validacao: Optional[str]` — diagnostic message in Portuguese
- `valido_tipo: Optional[bool]` — True if content passes validation or force=True

Added `_VALIDATION_SYSTEM_PROMPT` constant with:
- All 8 categories with descriptions (planning, daily, review, retrospectiva, ata_reuniao, commit, upload_livre, nao_relacionado)
- Project context placeholders ({projeto_nome}, {cliente}, {projeto_descricao})
- Explicit ambiguity instruction: "Em caso de duvida ou conteudo ambiguo, retorne nao_bloquear: true"

Added `async def validar_tipo(state)` node:
- Builds 3000-byte preview from arquivo_bytes (UTF-8 decode with errors='replace')
- Lightweight Gemini call: model=gemini-flash-latest, temperature=0, max_tokens=256
- JSON parse with safe fallback: parse errors -> nao_bloquear=True (T-05-01 mitigation)
- Blocking logic per D-08: upload_livre only blocks nao_relacionado; specific types block mismatch
- force=True short-circuits all validation, sets mensagem_validacao="Override forcado pelo gerente"

Added `_roteador_validacao(state)` router function.

Updated graph topology:
- START -> validar_tipo (was START -> detectar_tipo)
- add_conditional_edges("validar_tipo", _roteador_validacao, {"detectar_tipo": "detectar_tipo", END: END})
- All downstream edges unchanged

### Task 2 — _meta_tipo_detectado annotation in salvar

Modified `salvar` node to enrich `extracted_content` before Supabase insert:
- `content_to_save = dict(state["conteudo_estruturado"])` (copy, not mutate)
- Always sets `content_to_save["_meta_tipo_detectado"] = state.get("tipo_detectado") or ""`
- Conditionally sets `content_to_save["_meta_force_override"] = True` when `force` is True
- `conteudo_estruturado` state field itself is not mutated

## Verification Results

Task 1 automated check:
- All 7 new ExtractionState fields confirmed present via `__annotations__`
- Graph nodes list: `['__start__', 'validar_tipo', 'detectar_tipo', 'preprocessar_arquivo', 'extrair_conteudo', 'salvar']`
- All 8 categories and ambiguity instruction confirmed present in `_VALIDATION_SYSTEM_PROMPT`
- Module imports cleanly: `from graphs.extraction_graph import extraction_graph, ExtractionState`

Task 2 automated check:
- `_meta_tipo_detectado`, `_meta_force_override`, and `content_to_save` all present in source
- AST parse confirms no syntax errors

## Deviations from Plan

None — plan executed exactly as written. The `import json` addition at the top of the file was required by `validar_tipo`'s use of `json.loads`; this is a dependency of the implementation, not a deviation.

## Threat Model Coverage

| Threat ID | Mitigation | Implemented |
|-----------|------------|-------------|
| T-05-01 | json.loads parse errors default to nao_bloquear=True | Yes — except block sets nao_bloquear=True |
| T-05-02 | Preview capped at 3000 bytes; decode with errors='replace' | Yes — in validar_tipo preview build |
| T-05-03 | force override logged as _meta_force_override in extracted_content | Yes — Task 2 |
| T-05-04 | Gemini explicacao used only in diagnostic message | Accepted — no action required |

## Known Stubs

None. All fields are wired — routers (Plan 02) must pass tipo_esperado, force, projeto_nome, cliente, projeto_descricao in the initial state dict before invoking the graph. Until Plan 02 is complete, those fields default to None/empty, causing validar_tipo to use defaults (tipo_esperado="upload_livre", force=False) and skip blocking for all content.

## Self-Check: PASSED

- extraction_graph.py: FOUND
- 05-01-SUMMARY.md: FOUND
- Commit c649485 (Task 1): FOUND
- Commit 05f96e8 (Task 2): FOUND
