# Walking Skeleton — DocuData Phase 1

**Created:** 2026-05-23
**Phase:** 1 — Backend Foundation + Extraction Proof

## What the Walking Skeleton Proves

The thinnest possible end-to-end stack: a **TXT file upload travels through every layer of the system and lands as a structured 6-field JSON row in the database.**

```
TXT upload  ->  POST /ingest (FastAPI)  ->  extraction_graph (LangGraph)
                                              detectar_tipo
                                              preprocessar_arquivo
                                              extrair_conteudo (Gemini 2.5 Flash, structured output)
                                              _roteador (retry edge)
                                              salvar
                                          ->  Supabase ingestions row (6-field jsonb)
```

If this single flow works, the architecture is proven: FastAPI multipart handling, LangGraph state + conditional retry, Gemini structured extraction, and Supabase persistence all integrate correctly. Every Phase 2 (more file types, generation graph, Railway deploy) and Phase 3 (frontend) capability is an additive extension of this skeleton — not a re-architecture.

## Architectural Decisions (locked for downstream phases)

| Concern | Decision | Source |
|---------|----------|--------|
| Backend framework | FastAPI (async), `main.py` entry point | CLAUDE.MD section 2.1 |
| Agent orchestration | LangGraph `StateGraph`, compiled once at module level, `await ainvoke()` per request | RESEARCH.md Pattern 1; D-06 |
| LLM | Gemini 2.5 Flash via `langchain-google-genai==4.1.1`, `with_structured_output(..., method="json_schema")` | D-04, D-05; RESEARCH.md Pitfall 1 |
| Database | Supabase (PostgreSQL), `supabase==2.4.6` pinned, lazy `get_client()` | D-07; RESEARCH.md Pattern 4 |
| Extraction schema | `ConteudoEstruturado` — 6 fields (resumo, tarefas, decisoes, problemas, contexto_cliente, proximos_passos) | CLAUDE.MD section 3.4 |
| Config loading | `load_dotenv()` is the first statement in `main.py`, before all imports | RESEARCH.md Pitfall 3 |
| Directory layout | `docudata-backend/{main.py, models/, services/, routers/, graphs/, evals/}` | CLAUDE.MD section 8.1 |
| Deploy target (prepared, not done in Phase 1) | Railway; `nixpacks.toml` with poppler_utils + `Procfile` committed now | RESEARCH.md Pattern 6; STATE.md |

## Entry Point — How to Run It

```bash
cd docudata-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# .env must contain GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
uvicorn main:app --reload
```

Health check (no DB/LLM): `curl http://localhost:8000/health` -> `{"status":"ok"}`

## Real DB Call

- **Table:** `ingestions` (Supabase PostgreSQL)
- **Operation:** `INSERT` of `{project_id, sprint_number, file_name, file_type, extracted_content(jsonb)}` in the `salvar` LangGraph node.
- **Schema setup:** run `docudata-backend/supabase_schema.sql` in the Supabase SQL Editor once (creates `projects`, `ingestions`, `generated_docs`).
- **Prerequisite row:** a `projects` row (created via `POST /projects`) provides the `project_id` foreign key.

## Real API/Pipeline Interaction

The endpoint that proves the skeleton:

```bash
# 1. Create a project, capture its UUID
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Projeto Teste","client":"Cliente X","description":"MVP"}'

# 2. Ingest a TXT against that project + sprint
curl -X POST http://localhost:8000/ingest \
  -F "arquivo=@sprint3.txt;type=text/plain" \
  -F "sprint_numero=3" \
  -F "projeto_id=<UUID-from-step-1>"
# -> 200 {"status":"ok","sprint":3,"tentativas":0}
# -> one new row in Supabase `ingestions` with all 6 extracted_content fields
```

Negative path (also part of the proof): uploading a non-`text/plain` file returns HTTP 422 with `detail: "Unsupported file type. Accepted: text/plain"` and writes no row (D-01/D-02 router-level validation).

## Dev Verification Before Railway

Phase 1 is **local-only** — no Railway deploy (that is Phase 2). Verify the skeleton locally before any deploy:

1. `uvicorn main:app --reload` boots with no `KeyError` (proves `load_dotenv()` ordering).
2. `GET /health` returns ok (proves app wiring).
3. `POST /projects` -> 201 + UUID, `GET /projects` lists it (proves DB write/read).
4. `POST /ingest` with a TXT -> 200 + a row in `ingestions` with 6 populated fields (proves the full pipeline).
5. `POST /ingest` with an image -> 422, no row (proves router-level validation).
6. `pytest evals/` green (proves schema validity, retry-edge termination, and write integrity offline).
7. (Optional) Set `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` to see the full graph trace in LangSmith project `docudata-extraction-phase1`.

`nixpacks.toml` (poppler_utils) and `Procfile` are committed in Phase 1 so the Phase 2 Railway deploy needs no last-minute build changes.
