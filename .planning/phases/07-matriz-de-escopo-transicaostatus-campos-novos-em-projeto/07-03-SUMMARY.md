# Plan 07-03 Summary — import_graph.py + importar endpoints

**Status:** Complete  
**Commit:** 3dcd903

## What was built

**Task 1 — `graphs/import_graph.py`:**
- `ImportState` TypedDict: `texto_contrato`, `projeto_id`, `gemini_api_key`, `proposta`, `valido`, `tentativas`, `erro`
- `gerar_proposta` async node: calls `ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")`, parses JSON response, extracts `funcionalidades` list
- Retry: `_roteador` returns to `gerar_proposta` with hardened suffix (`_HARDENED_SUFFIX`) when `valido=False` and `tentativas < 2`; falls to END after max retries
- Module-level compile: `import_graph = _builder.compile()` — NOT inside any function
- **No `salvar` node** — confirmed by grep: all "funcionalidades" references are in prompt string/JSON parsing, no Supabase calls

**Task 2 — `/importar` and `/importar/confirmar` endpoints (already in 07-01 commit):**
- `POST /funcionalidades/importar`: lazy-imports `import_graph`, truncates text at 50000 chars, fetches project's `gemini_api_key` (with `GEMINI_API_KEY` env fallback), invokes `import_graph.ainvoke()`, converts raw dicts to `FuncionalidadeProposta`, returns `ImportPropostaResponse` — zero DB writes
- `POST /funcionalidades/importar/confirmar`: filters `confirmed=True` items, inserts each into `funcionalidades` table, returns `list[FuncionalidadeResponse]`
- Route order: `/importar` and `/importar/confirmar` declared before `/{funcionalidade_id}` (index 0, 1 vs 4+)

## Verification

- `python -c "from graphs.import_graph import import_graph; print(type(import_graph))"` → CompiledStateGraph
- Graph nodes: `['__start__', 'gerar_proposta', '__end__']` — no `salvar`
- `_roteador({'valido': True, ...})` → `__end__`
- `_roteador({'valido': False, 'tentativas': 0, ...})` → `gerar_proposta`
- `_roteador({'valido': False, 'tentativas': 2, ...})` → `__end__`
- `python -c "import main; print('OK')"` — full app loads cleanly

## Phase 7 coverage

All 6 ROADMAP success criteria now met:
1. POST /funcionalidades with ≥1 criterion → 201; without → 422 ✓
2. POST /funcionalidades/importar returns proposal without DB write ✓
3. POST /funcionalidades/importar/confirmar creates confirmed items ✓
4. PATCH /funcionalidades/{id} writes TransicaoStatus with autor, timestamp, duracao ✓
5. PATCH /projects/{id}/contrato accepts 4 contract fields ✓
6. GET /projects still works — zero regression ✓

## Self-Check: PASSED
