# Plan 07-01 Summary — Migration + Schemas + CRUD Router

**Status:** Complete  
**Commit:** 06c572d

## What was built

- **9 new Pydantic models** in `models/schemas.py`:
  - `FuncionalidadeCreate` — with `@field_validator` for `criterios_aceite` (≥1, strips whitespace) and `prioridade` (enum must/should/could/wont)
  - `FuncionalidadeUpdate` — same validators, all fields Optional
  - `FuncionalidadeResponse` — full entity response
  - `TransicaoStatusResponse` — state machine audit trail row
  - `FuncionalidadeProposta`, `ImportPropostaResponse`, `ImportConfirmarItem`, `ImportConfirmarRequest` — for AI import flow
  - `ContratoUpdate` — 4 contract fields with `ge=0` constraint on numeric fields

- **`ProjectResponse` updated** with 4 new Optional fields: `data_inicio`, `data_fim_contratada`, `tolerancia_desvio_pontos`, `periodo_garantia_dias`

- **`routers/funcionalidades.py`** (new file):
  - `POST /funcionalidades/importar` — lazy-imports `import_graph`; proposes funcionalidades from contract text, never writes to DB
  - `POST /funcionalidades/importar/confirmar` — creates only confirmed items
  - `POST /funcionalidades` → 201 with default `status="nao_iniciada"`
  - `GET /funcionalidades?project_id=<id>` — list
  - `GET /funcionalidades/{id}` — single or 404
  - `GET /funcionalidades/{id}/transicoes` — state machine history
  - `PATCH /funcionalidades/{id}` — partial update with TransicaoStatus recording + auto-set `data_aprovacao_cliente`
  - `DELETE /funcionalidades/{id}` → 204
  - Route order: `/importar` and `/importar/confirmar` declared before `/{funcionalidade_id}` (FastAPI catch-all safety)

- **`main.py`** — `funcionalidades.router` registered

## Supabase DDL (run by user)

```sql
CREATE TABLE IF NOT EXISTS funcionalidades (...);
CREATE TABLE IF NOT EXISTS transicoes_status (...);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS data_inicio date;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS data_fim_contratada date;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tolerancia_desvio_pontos integer DEFAULT 20;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS periodo_garantia_dias integer DEFAULT 30;
```

## Verification

- `python -c "from models.schemas import FuncionalidadeCreate"` — OK
- `FuncionalidadeCreate(criterios_aceite=[])` raises ValidationError with "critério" — OK
- `FuncionalidadeCreate(criterios_aceite=['  '])` raises same error — OK
- `FuncionalidadeCreate(prioridade='invalid')` raises ValidationError with "prioridade" — OK
- OpenAPI spec includes all `/funcionalidades/*` routes — OK
- `python -c "import main"` — no ImportError — OK

## Key files

- `docudata-backend/models/schemas.py`
- `docudata-backend/routers/funcionalidades.py`
- `docudata-backend/main.py`

## Self-Check: PASSED
