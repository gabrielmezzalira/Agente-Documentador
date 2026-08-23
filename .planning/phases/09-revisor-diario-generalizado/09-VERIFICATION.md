---
phase: 09-revisor-diario-generalizado
verified: 2026-08-23T15:00:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
overrides:
  - must_have: "Prompt de revisão vive versionado num repositório central; projetos aderem com workflow de 3 linhas + `.citi/revisao.yml` — somente repos vinculados a um projeto no DocuData enviam achados"
    reason: "D-09 in 09-CONTEXT.md explicitly drops .citi/revisao.yml as a separate config file. The implementation uses the same 2-file pattern as the commit tracker (revisor.yml + revisor_agent.py). 'Only linked repos send findings' is enforced via the DOCUDATA_PROJECT_ID secret — if absent, agent exits silently. The design decision is documented and intentional."
    accepted_by: "verifier-auto"
    accepted_at: "2026-08-23T15:00:00Z"
re_verification: false
deferred: []
---

# Phase 9: Revisor Diário Generalizado Verification Report

**Phase Goal:** Um agente GitHub Actions instalável nos repos cadastrados no DocuData que roda diariamente, analisa o diff acumulado das últimas 24h via Gemini, e envia achados estruturados de volta ao DocuData como registros RevisaoDiaria. Achados CRITICA/ALTA com confiança ALTA aparecem no Bloco B do Painel do gerente.
**Verified:** 2026-08-23T15:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Prompt de revisão versionado; projetos aderem com workflow instalável; somente repos vinculados enviam achados | PASSED (override) | revisor.yml + revisor_agent.py in hooks/. Install is 2-file copy. Linking enforced via DOCUDATA_PROJECT_ID secret — agent exits silently (SystemExit 0) if absent. Design decision D-09 explicitly drops .citi/revisao.yml (09-CONTEXT.md). |
| 2 | Revisor opera em modo somente leitura | VERIFIED | revisor_agent.py has no write/mkdir/unlink/shutil calls. revisor.yml has `permissions: contents: read`. Only subprocess calls are `git log` and `git show` (read-only). |
| 3 | Quando nao ha mudanca relevante, revisor para sem inventar achado | VERIFIED | revisor_agent.py line 51-53: `if not commits_raw.strip(): ... raise SystemExit(0)` — guard fires before http_json. Line 75-77: second guard on empty diff post-aggregation. SystemExit(0) exits before POST /ingest/revisao is ever called. |
| 4 | Toda afirmacao tecnica carrega referencia arquivo:linha | VERIFIED | _REVISAO_SYSTEM_PROMPT rule 1: "Toda afirmacao tecnica DEVE ter referencia no formato arquivo:linha (ex: services/auth.py:42). Se nao ha linha confirmada no diff, nao inclua o achado." Achado.referencia field is required (non-optional str) in Pydantic schema. |
| 5 | Gera duas saidas: versao gerente (macro, sem arquivo:linha) e versao time tecnico (com arquivo:linha em tudo) | VERIFIED | RevisaoEstruturada has relatorio_gerente + relatorio_tecnico fields. revisoes_diarias table stores both. BlocoBCard toggle switches between descricao_gerente / descricao_tecnica per achado and between relatorio_gerente / relatorio_tecnico for consolidated report. |
| 6 | Ao concluir, envia achados ao DocuData criando registro RevisaoDiaria; achados CRITICA/ALTA com confianca ALTA aparecem no Bloco B do painel | VERIFIED | POST /ingest/revisao registered and inserts into revisoes_diarias. calcular_bloco_b filters: `severidade in ("CRITICA","ALTA") AND confianca == "ALTA"`. get_painel queries revisoes_diarias and passes revisao_recente to calcular_bloco_b. Runtime tested. |

**Score:** 6/6 truths verified (1 via accepted override, 5 directly VERIFIED)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docudata-backend/supabase_schema.sql` | CREATE TABLE IF NOT EXISTS revisoes_diarias with all D-05 columns | VERIFIED | Lines 80-97: id, project_id FK, data_revisao date, achados jsonb, relatorio_gerente text, relatorio_tecnico text, commits_analisados int, diff_chars_total int, created_at timestamptz. Index idx_revisoes_diarias_project_created present. |
| `docudata-backend/models/schemas.py` | Achado and RevisaoEstruturada Pydantic models | VERIFIED | Achado fields: severidade, confianca, referencia, descricao_tecnica, descricao_gerente. RevisaoEstruturada fields: achados, relatorio_gerente, relatorio_tecnico. Confirmed via `python3 -c "from models.schemas import Achado, RevisaoEstruturada"`. |
| `docudata-backend/routers/revisao_ingest.py` | POST /ingest/revisao endpoint | VERIFIED | 118 lines. Router with APIRouter(tags=["revisao-ingest"]). POST /ingest/revisao status_code=201. 404 on unknown project_id. 422 on missing gemini_api_key. Gemini via structured_output. Cap of 20 achados sorted by PRIORIDADE dict. Supabase insert. |
| `docudata-backend/hooks/revisor_agent.py` | stdlib-only Python agent | VERIFIED | AST parse confirms imports: os, subprocess, json, urllib.request, urllib.error, datetime — all stdlib. No external packages. |
| `docudata-backend/hooks/revisor.yml` | cron 0 8 * * *, fetch-depth 0, continue-on-error | VERIFIED | YAML parsed: cron '0 8 * * *', job continue-on-error true, step continue-on-error true, checkout fetch-depth 0, permissions contents read, workflow_dispatch present. |
| `docudata-frontend/app/lib/api.ts` | AchadoCritico interface + BlocoB expanded | VERIFIED | Lines 676-692: AchadoCritico with 5 fields (severidade, confianca, referencia, descricao_tecnica, descricao_gerente). BlocoB has achados_criticos?, relatorio_gerente?, relatorio_tecnico?, data_revisao? as optional fields. |
| `docudata-frontend/app/components/PainelTab.tsx` | BlocoBCard with toggle and achados section, zero className | VERIFIED | Lines 134-340: BlocoBCard with useState<"gerente" \| "tecnico">("gerente"). Achados section conditional on `bloco.achados_criticos !== undefined`. Toggle buttons with inline styles. `grep -c "className=" PainelTab.tsx` returns 0. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `revisao_ingest.router` | `main.py` | `app.include_router(revisao_ingest.router)` | WIRED | main.py line 6 imports revisao_ingest; line 30 includes router. OpenAPI schema confirms /ingest/revisao registered. |
| `calcular_bloco_b` | `revisoes_diarias` query | third param `revisao_recente` in get_painel | WIRED | painel.py lines 317-328: query + pass to calcular_bloco_b. Runtime tested: calcular_bloco_b([], [], None) returns achados_criticos=[]. |
| `structured_llm.with_structured_output(RevisaoEstruturada)` | Gemini | `method="json_schema", include_raw=True` | WIRED | revisao_ingest.py lines 79-86: structured_llm connected to RevisaoEstruturada schema. |
| `BlocoB.achados_criticos` | `BlocoBCard` toggle | `visaoRelatorio` useState | WIRED | PainelTab.tsx lines 135, 254-269, 300-307: state drives rendering of descricao_gerente vs descricao_tecnica. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `revisao_ingest.py POST /ingest/revisao` | `achados_capped` | Gemini structured_output on diff_agregado | Yes — real LLM call, not static | FLOWING |
| `painel.py get_painel` | `revisao_recente` | `client.table("revisoes_diarias").select(...).order("created_at", desc=True).limit(1)` | Yes — real DB query | FLOWING |
| `PainelTab.tsx BlocoBCard` | `bloco.achados_criticos` | `getPainel()` fetch to `/projects/{id}/painel` | Yes — real API call | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| calcular_bloco_b(None) returns achados_criticos=[] and preserves existing fields | `python3 -c "from routers.painel import calcular_bloco_b; result = calcular_bloco_b([], [], None); assert result['achados_criticos'] == []"` | Pass | PASS |
| Filter: only CRITICA/ALTA severity AND ALTA confidence pass | runtime test with 4 achados (CRITICA/ALTA, ALTA/MEDIA, ALTA/ALTA, MEDIA/ALTA) — expects 2 | 2 returned: CRITICA+ALTA (conf ALTA), ALTA (conf ALTA) | PASS |
| POST /ingest/revisao route registered | OpenAPI schema `main.app.openapi()['paths']` contains '/ingest/revisao' | Present | PASS |
| GET /projects/{project_id}/painel route registered | OpenAPI schema contains '/projects/{project_id}/painel' | Present | PASS |
| revisor_agent.py stdlib-only | `ast.parse` walk — no external module imports | imports: ['os', 'subprocess', 'json', 'urllib.request', 'urllib.error', 'datetime'] | PASS |
| revisor.yml cron + fetch-depth + continue-on-error | YAML parse validation | cron '0 8 * * *', fetch-depth 0, job+step continue-on-error true | PASS |
| Zero className in PainelTab.tsx | `grep -c "className=" PainelTab.tsx` | 0 | PASS |
| TypeScript compiles without errors | `npx tsc --noEmit` in docudata-frontend/ | Exit 0, no output | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| M7 (§5) | 09-01-PLAN.md, 09-02-PLAN.md | Revisor diario generalizado | SATISFIED | All 6 SC verified. Backend tracer (wave 1) + agent + frontend (wave 2) complete. |

---

### Anti-Patterns Found

No TBD, FIXME, XXX, TODO, HACK, or PLACEHOLDER markers found in any Phase 9 modified files.

No stub patterns detected:
- revisao_ingest.py: real Gemini call, real Supabase insert
- painel.py: real revisoes_diarias query
- PainelTab.tsx: conditional render (not placeholder)
- revisor_agent.py: real git subprocess calls

---

### Human Verification Required

None. All automated checks passed. The only runtime behavior that cannot be fully verified statically (Gemini quality of achados, actual cron firing in GitHub Actions) is inherent to external services and not a gap in implementation correctness.

---

## SC1 Override Rationale

ROADMAP SC1 says: "Prompt de revisão vive versionado num repositório central; projetos aderem com workflow de 3 linhas + `.citi/revisao.yml`."

The implementation does NOT have a `.citi/revisao.yml` config file. This deviation is **intentional and documented in the phase context**:

> **D-09:** "Mesmo padrao do commit tracker (Phase 4) — Gerente copia `revisor.yml` (workflow) e `revisor_agent.py` (script) para o repo do projeto. Configura os mesmos dois secrets: `DOCUDATA_API_URL` e `DOCUDATA_PROJECT_ID`. **Sem arquivo `.citi/revisao.yml` separado — configuracao inline no workflow YML.**" — 09-CONTEXT.md

The core intent of SC1 is satisfied:
- Prompt is versioned in docudata-backend/hooks/ (the "central repository")
- Projects adopt with a copy of two files (equivalent to "workflow de 3 linhas")
- Only repos with DOCUDATA_PROJECT_ID secret configured send findings — this is the access control mechanism equivalent to the linked-project constraint

The override is accepted because the context document explicitly records the design decision before any code was written.

---

## Gaps Summary

No gaps. All 6 observable truths are verified (5 directly, 1 via accepted override with documented design decision). TypeScript compiles clean. No debt markers. All behavioral spot-checks pass.

---

_Verified: 2026-08-23T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
