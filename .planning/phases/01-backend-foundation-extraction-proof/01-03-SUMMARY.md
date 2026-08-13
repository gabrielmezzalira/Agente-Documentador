# Plan 01-03 Summary — Code-based Eval Gates

**Phase:** 01-backend-foundation-extraction-proof
**Plan:** 01-03
**Status:** Complete
**Completed:** 2026-08-13

## What was built

pytest eval suite (`evals/`) gating AI-SPEC dimensions 1, 5, and 6 against the extraction graph. Files were already present from an earlier session but had 5 failures due to schema drift (phases 4 and 5 evolved `ConteudoEstruturado` and `salvar`). Fixed and all 21 tests now pass.

## Key files

- `docudata-backend/evals/test_schema_validity.py` — AI-SPEC dim 1: ConteudoEstruturado validates all 8 required fields (7 original + `tecnologias` added in phase 4); rejects missing fields and wrong types
- `docudata-backend/evals/test_retry_edge.py` — AI-SPEC dim 5: `_roteador` routes correctly for all (valido, tentativas) combinations; terminates at tentativas≥2 (no infinite loop)
- `docudata-backend/evals/test_supabase_write.py` — AI-SPEC dim 6: `salvar` persists correct payload and reports failure (not success) when response.data is empty; no live Supabase dependency
- `docudata-backend/pytest.ini` — `asyncio_mode = auto` for pytest-asyncio 1.4+
- `docudata-backend/requirements-dev.txt` — `pytest>=8`, `pytest-asyncio>=0.23`

## Fixes applied

| Issue | Root cause | Fix |
|-------|-----------|-----|
| `test_valid_payload_constructs` failed | `tecnologias` field added to `ConteudoEstruturado` in phase 4 | Added `tecnologias: ["Python", "FastAPI"]` to `VALID_PAYLOAD`; updated key assertion to use `issubset` |
| `test_missing_field_raises` didn't cover `tecnologias` | Schema drift | Added `tecnologias` to parametrize list |
| Async tests failed (`Failed: async def`) | `pytest-asyncio` not installed in environment | Installed `pytest-asyncio==1.4.0`; added `pytest.ini` with `asyncio_mode = auto` |
| `test_salvar_success` payload assertion failed | `salvar` now adds `_meta_tipo_detectado` (phase 5) and `input_tokens/output_tokens/cost_usd` | Changed from strict equality to field-by-field check + `_meta_tipo_detectado` presence assertion |

## Self-Check: PASSED

- `python3 -m pytest evals/ -q` → 21 passed, 0 failed, 1 warning
- No live Gemini or Supabase dependency — runs fully offline
- AI-SPEC dims 1, 5, 6 gated as CI merge gates
