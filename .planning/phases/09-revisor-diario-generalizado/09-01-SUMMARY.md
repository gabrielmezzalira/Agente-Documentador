---
id: "09-01"
phase: "09-revisor-diario-generalizado"
plan: "01"
status: complete
completed_at: "2026-08-23T00:00:00Z"
---

# Plan 09-01 Summary — Backend Tracer: ingestão + painel expandido

## What Was Built

**Migration SQL (`docudata-backend/supabase_schema.sql`):**
- `CREATE TABLE IF NOT EXISTS revisoes_diarias` com todas as colunas do D-05: id, project_id (FK→projects), data_revisao, achados (jsonb), relatorio_gerente, relatorio_tecnico, commits_analisados, diff_chars_total, created_at
- `CREATE INDEX IF NOT EXISTS idx_revisoes_diarias_project_created ON revisoes_diarias (project_id, created_at DESC)`

**Pydantic Schemas (`docudata-backend/models/schemas.py`):**
- `Achado`: severidade, confianca, referencia, descricao_tecnica, descricao_gerente
- `RevisaoEstruturada`: achados (list[Achado]), relatorio_gerente, relatorio_tecnico

**Router (`docudata-backend/routers/revisao_ingest.py`):**
- `POST /ingest/revisao` status_code=201
- Verifica project existe e tem gemini_api_key configurada (404/422 idiomático)
- Gemini `gemini-3.5-flash-lite` com `with_structured_output(RevisaoEstruturada)` max_tokens=4096
- Cap de 20 achados, ordenados CRITICA > ALTA > MEDIA > BAIXA via `_PRIORIDADE` dict
- Insert em `revisoes_diarias`, retorna `{status, revisao_id, achados_count}`

**Painel expandido (`docudata-backend/routers/painel.py`):**
- `calcular_bloco_b` agora aceita `revisao_recente: dict | None = None` como terceiro parâmetro
- Filtra achados com `severidade IN ("CRITICA", "ALTA") AND confianca == "ALTA"` para `achados_criticos`
- `get_painel` busca revisão mais recente em `revisoes_diarias` e passa a `calcular_bloco_b`
- `bloco_b` retorna 4 campos novos: `achados_criticos`, `relatorio_gerente`, `relatorio_tecnico`, `data_revisao`
- Campos existentes (`travadas`, `aguardando_cliente`, `em_ajuste`) inalterados

**main.py:**
- `revisao_ingest` importado e `revisao_ingest.router` registrado após `painel.router`

## Self-Check: PASSED

- `python -c "from routers import revisao_ingest; from models.schemas import Achado, RevisaoEstruturada; print('ok')"` → imports ok
- `calcular_bloco_b([], [], None)` → `achados_criticos=[]`, sem erro
- Filtro mock: achado CRITICA/ALTA + ALTA → 1 passa; ALTA/MEDIA → não passa
- OpenAPI schema: `/ingest/revisao` e `/projects/{project_id}/painel` confirmados

## Artifacts Modified

- `docudata-backend/supabase_schema.sql` — Phase 9 migration block adicionado
- `docudata-backend/models/schemas.py` — Achado e RevisaoEstruturada adicionados
- `docudata-backend/routers/revisao_ingest.py` — criado (novo arquivo)
- `docudata-backend/routers/painel.py` — calcular_bloco_b expandido, query revisoes_diarias adicionada
- `docudata-backend/main.py` — revisao_ingest importado e registrado
