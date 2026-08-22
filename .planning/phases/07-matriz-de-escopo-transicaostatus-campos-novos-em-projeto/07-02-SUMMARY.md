# Plan 07-02 Summary — State Machine PATCH + /projects/{id}/contrato

**Status:** Complete  
**Commit:** 849c2f0

## What was built

**Task 1 — PATCH /funcionalidades/{id} with TransicaoStatus (already in 07-01 commit):**
- Implemented inline in `funcionalidades.py` during Plan 01 to ensure correct route ordering
- For each changed `status`/`status_cliente` field: reads previous transition timestamp (or `created_at` for first transition), calculates `duracao_fase_anterior_segundos`, inserts row into `transicoes_status`
- Auto-sets `data_aprovacao_cliente = date.today()` when `status_cliente = "aprovado"` and no explicit date provided (per D-03)
- Empty body (no changes) returns current row without any DB write

**Task 2 — PATCH /projects/{id}/contrato:**
- Added to `routers/projects.py` (new endpoint at file end)
- Imports `ContratoUpdate` from `models.schemas`
- 404 if project not found, 422 if body has no non-null fields
- Serializes Python `date` objects via `.isoformat()` for supabase-py compatibility
- Returns `ProjectResponse` via existing `_sanitize()` helper (strips gemini_api_key, injects has_api_key)

## Verification

- `python -c "from routers.projects import router; paths=[r.path for r in router.routes]; print(any('contrato' in p for p in paths))"` → True
- `python -c "from routers.funcionalidades import router; routes={r.path:getattr(r,'methods',set()) for r in router.routes}; print([k for k,v in routes.items() if 'PATCH' in (v or set())])"` → includes `/{funcionalidade_id}`
- `python -c "import main; print('OK')"` — no ImportError

## Self-Check: PASSED
