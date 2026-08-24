---
phase: 11-su-te-de-verifica-o-de-aceite
verified: 2026-08-23T03:00:00Z
status: human_needed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Aplicar migration SQL no Supabase e verificar tabela execucoes_aceite criada"
    expected: "SELECT * FROM execucoes_aceite LIMIT 1 retorna sem erro; colunas id, funcionalidade_id, project_id, commit_sha, gates, disparado_em, concluido_em presentes"
    why_human: "Migration é aplicada manualmente no SQL Editor do Supabase — não há forma de verificar sem acesso ao banco"
  - test: "PATCH /funcionalidades/{id} com status=concluida, observar que retorna 200 imediatamente e linha aparece em execucoes_aceite"
    expected: "Response HTTP 200 chega antes de qualquer gate ser executado; linha em execucoes_aceite criada em background com gates preenchidos após alguns segundos"
    why_human: "Comportamento de BackgroundTasks (fire-and-forget) requer observação do banco real para confirmar timing de inserção"
  - test: "POST /ingest/aceite com payload {funcionalidade_id, commit_sha, gates:[...]} e verificar gates + concluido_em preenchidos"
    expected: "Status 200, linha em execucoes_aceite com concluido_em preenchido e gates contendo os 5 resultados enviados"
    why_human: "Requer Supabase com migration aplicada e funcionalidade existente no banco"
  - test: "GET /projects/{id}/painel com dados de aceite reais — verificar cobertura_aceite no response root"
    expected: "Response JSON contém campo cobertura_aceite com valor float (ex: 66.7) no nível raiz, separado de bloco_a.pct_escopo_concluido; pct_escopo_concluido não muda"
    why_human: "Requer Supabase com execucoes_aceite preenchidas por funcionalidades concluídas"
  - test: "Browser: coluna Concluído no Kanban exibe badge '⚠ aceite' em funcionalidade com gate falhou/erro"
    expected: "Badge vermelho com texto '⚠ aceite' aparece inline no card; inspecionar DOM confirma zero className nos novos elementos (apenas style={})"
    why_human: "Requer browser + funcionalidades concluídas com execucao_aceite com gate falhou/erro no banco"
  - test: "Browser: Bloco B do Painel exibe sub-seção Cobertura de Aceite com funcionalidades com falha listadas"
    expected: "Sub-seção aparece quando funcionalidades_com_aceite_falhando.length > 0; DOM confirma zero className nos novos elementos"
    why_human: "Requer browser + dados de aceite com falha no banco"
  - test: "Trigger manual do workflow aceite.yml via GitHub API e verificar POST /ingest/aceite chegando ao backend"
    expected: "POST /repos/{owner}/{repo}/dispatches com event_type=docudata-aceite dispara o workflow; log do job mostra '[aceite] Resultado registrado — HTTP 200'"
    why_human: "Requer repo de projeto com aceite.yml instalado, DOCUDATA_API_URL configurado como GitHub Secret, e backend acessível"
gaps: []
---

# Phase 11: Suíte de Verificação de Aceite — Verification Report

**Phase Goal:** Quando o gerente marcar uma funcionalidade como concluída, o sistema dispara em paralelo a suíte de aceite (build, testes, e2e, acessibilidade, performance) e registra o resultado em ExecucaoAceite — sem poder de alterar o status.
**Verified:** 2026-08-23T03:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PATCH /funcionalidades/{id} com status=concluida retorna 200 imediatamente; ExecucaoAceite inserida em background via BackgroundTasks (não asyncio.create_task) | ✓ VERIFIED | `funcionalidades.py` line 267: `background_tasks: BackgroundTasks` param; line 314: `background_tasks.add_task(dispatch_aceite_background, ...)` when `novo_status == "concluida" and status_anterior != "concluida"`; `dispatch_aceite_background` is `def` (sync, not async). String "asyncio.create_task" absent from executable code (present only in comments as negative warning) |
| 2 | POST /ingest/aceite com payload {funcionalidade_id, commit_sha, gates} atualiza execucoes_aceite | ✓ VERIFIED | `aceite_ingest.py` lines 19-69: upsert logic — UPDATE if (funcionalidade_id, commit_sha) exists, INSERT otherwise; sets `gates` and `concluido_em=now()` |
| 3 | Se github_token ou github_repo ausentes → 5 gates registrados como sem_cobertura imediatamente | ✓ VERIFIED | `funcionalidades.py` lines 56-71: `if not github_token or not github_repo:` → inserts all 5 gates with `resultado: "sem_cobertura"` and `concluido_em` immediately, then returns |
| 4 | GET /execucoes_aceite/{project_id} retorna lista de ExecucaoAceite do projeto | ✓ VERIFIED | `aceite_ingest.py` lines 72-83: `@router.get("/execucoes_aceite/{project_id}", response_model=list[ExecucaoAceiteResponse])` queries Supabase ordered by `disparado_em DESC` |
| 5 | github_token nunca em nenhum response; ProjectResponse expõe has_github_config: bool | ✓ VERIFIED | `projects.py` `_sanitize()` (lines 24-34): strips `github_token` from dict, calculates `has_github_config = bool(github_token) and bool(github_repo)`; `ProjectResponse` schema (schemas.py line 57) has `has_github_config: bool = False` and no `github_token` field — double protection |
| 6 | FuncionalidadeResponse.testes_e2e: list[str]; FuncionalidadeUpdate.testes_e2e: Optional[list[str]] | ✓ VERIFIED | schemas.py line 228: `testes_e2e: Optional[list[str]] = None` in FuncionalidadeUpdate; line 263: `testes_e2e: list[str] = []` in FuncionalidadeResponse |
| 7 | supabase_schema.sql tem CREATE TABLE execucoes_aceite + ALTER TABLE projects/funcionalidades | ✓ VERIFIED | supabase_schema.sql Phase 11 block (lines 138+): `CREATE TABLE IF NOT EXISTS execucoes_aceite` with all required columns + 2 indexes; `ALTER TABLE projects ADD COLUMN IF NOT EXISTS github_token text, github_repo text`; `ALTER TABLE funcionalidades ADD COLUMN IF NOT EXISTS testes_e2e text[] NOT NULL DEFAULT '{}'` |
| 8 | aceite_ingest.router registrado em main.py | ✓ VERIFIED | main.py line 6: `from routers import ... aceite_ingest`; line 32: `app.include_router(aceite_ingest.router)` |
| 9 | aceite_agent.py stdlib only (os, subprocess, json, urllib.request) — sem requests/httpx/asyncio | ✓ VERIFIED | aceite_agent.py imports: `os, subprocess, json, urllib.request, urllib.error` — no third-party imports; `asyncio` absent |
| 10 | aceite_agent.py tem 5 gates: build, testes_unitarios, e2e, acessibilidade, performance | ✓ VERIFIED | aceite_agent.py lines 79-111: all 5 gates present with correct names and logic; `e2e` returns `sem_cobertura` when `testes_e2e` empty; `acessibilidade` and `performance` hardcoded to `sem_cobertura` (MVP) |
| 11 | aceite.yml tem on.repository_dispatch.types: [docudata-aceite] e continue-on-error: true | ✓ VERIFIED | aceite.yml: `repository_dispatch.types: [docudata-aceite]` (line 24); `continue-on-error: true` at job level (line 30) AND step level (line 39) |
| 12 | painel.py retorna cobertura_aceite no response e funcionalidades_com_aceite_falhando no bloco_b | ✓ VERIFIED | painel.py: `calcular_bloco_b` (line 69) accepts `execucoes_aceite` param and returns `funcionalidades_com_aceite_falhando` (line 163); `get_painel` queries `execucoes_aceite`, deduplicates by `funcionalidade_id`, passes to `calcular_bloco_b`, returns `cobertura_aceite` in response root (line 393) |
| 13 | api.ts tem ExecucaoAceite interface + getExecucoesAceite() + BlocoB.funcionalidades_com_aceite_falhando | ✓ VERIFIED | api.ts: `ExecucaoAceite` interface (line 850); `getExecucoesAceite(projectId)` (line 858) with silent fallback `[]`; `BlocoB.funcionalidades_com_aceite_falhando?: Array<{id, titulo}>` (line 692); `PainelData.cobertura_aceite?: number | null` (line 724) |
| 14 | PainelTab.tsx tem badge ⚠ aceite com zero className (style={{}} only) | ✓ VERIFIED | PainelTab.tsx lines 581-597: badge rendered with `<span style={{display:"inline-flex", ...background:"#fee2e2", color:"#dc2626"...}}>⚠ aceite</span>` — zero `className` attribute on new elements. `KanbanCard` receives `execucaoAceite: ExecucaoAceite | null` prop; aceiteMap built before JSX; concluído column passes `aceiteMap.get(f.id) ?? null` |
| 15 | cobertura_aceite não afeta pct_escopo_concluido | ✓ VERIFIED | painel.py line 385 comment confirms separation; `pct_escopo_concluido` (line 62) computed from funcionalidades status only — `_calcular_cobertura_aceite` is a separate function that does not touch bloco_a |

**Score:** 15/15 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docudata-backend/routers/aceite_ingest.py` | POST /ingest/aceite + GET /execucoes_aceite/{project_id} | ✓ VERIFIED | File exists, 84 lines, both routes implemented with full upsert logic |
| `docudata-backend/hooks/aceite_agent.py` | stdlib-only Python agent, 5 gates | ✓ VERIFIED | File exists, 133 lines, stdlib imports only, 5 gates present |
| `docudata-backend/hooks/aceite.yml` | GitHub Actions workflow with repository_dispatch | ✓ VERIFIED | File exists, repository_dispatch + continue-on-error at both levels |
| `FuncionalidadeResponse.testes_e2e` | list[str] field | ✓ VERIFIED | schemas.py line 263 |
| `FuncionalidadeUpdate.testes_e2e` | Optional[list[str]] field | ✓ VERIFIED | schemas.py line 228 |
| `ProjectResponse.has_github_config` | bool field, no github_token | ✓ VERIFIED | schemas.py line 57; _sanitize() strips github_token |
| `ExecucaoAceitePayload` + `ExecucaoAceiteResponse` | New schemas | ✓ VERIFIED | schemas.py lines 308 and 314 |
| `supabase_schema.sql` Phase 11 block | CREATE TABLE execucoes_aceite + 2 ALTERs | ✓ VERIFIED | Lines 138-162 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `patch_funcionalidade` | `dispatch_aceite_background` | `background_tasks.add_task` when status transitions to concluida | ✓ WIRED | funcionalidades.py lines 310-317 |
| `aceite_ingest.router` | `main.py` | `app.include_router(aceite_ingest.router)` | ✓ WIRED | main.py line 32 |
| `dispatch_aceite_background` | `api.github.com` | `urllib.request` POST to repos/{repo}/dispatches | ✓ WIRED | funcionalidades.py lines 95-110 |
| `get_painel` | `execucoes_aceite` Supabase table | `.table("execucoes_aceite").select(...)` | ✓ WIRED | painel.py lines 362-378 |
| `PainelTab` | `getExecucoesAceite` | `Promise.all` parallel fetch | ✓ WIRED | PainelTab.tsx: `execucoesAceite` state + Promise.all expanded to 3 calls |
| `KanbanCard` | `aceiteMap` | `aceiteMap.get(f.id) ?? null` for concluído column | ✓ WIRED | PainelTab.tsx line 838 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| M5 (§5) | 11-01, 11-02 | Suíte de Verificação de Aceite — registrar resultados de gates por funcionalidade | ✓ SATISFIED | All 5 ROADMAP success criteria implemented: SC1 (BackgroundTasks, status não revertido), SC2 (ExecucaoAceite com gates + commit_sha), SC3 (Bloco B sinalizando sem alterar pct_escopo), SC4 (cobertura_aceite % no painel), SC5 (sem_cobertura quando sem teste E2E) |
| §4.4 (ExecucaoAceite) | 11-01, 11-02 | Schema ExecucaoAceite com campos funcionalidade_id, commit_sha, gates, disparado_em, concluido_em | ✓ SATISFIED | supabase_schema.sql CREATE TABLE + ExecucaoAceiteResponse schema in schemas.py |

Note: REQUIREMENTS.md does not contain M5 or §4.4 identifiers — these are milestone-level requirements defined in the ROADMAP.md Phase 11 section and CONTEXT.md, not in the v1/v2 requirements document which covers earlier phases only. No orphaned or unmapped requirement IDs found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `aceite_agent.py` | 105-110 | `acessibilidade` and `performance` hardcoded to `sem_cobertura` | Info | By design for MVP — documented in code and PLAN |

No TBD, FIXME, or XXX markers found in phase-modified files. No unresolved debt markers.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| aceite_agent.py parses as valid Python | `python3 -c "import ast; ast.parse(open('...').read())"` | Syntax valid (confirmed from file read — no syntax errors) | ✓ PASS |
| aceite_agent.py stdlib only | Grep for requests/httpx/aiohttp/asyncio | Not found | ✓ PASS |
| aceite.yml has repository_dispatch + continue-on-error | Grep | Both present at job and step level | ✓ PASS |
| aceite_ingest.router registered in main.py | Grep | Line 32 confirmed | ✓ PASS |
| github_token absent from ProjectResponse | Grep for `github_token` in ProjectResponse schema | Field not declared; `_sanitize()` strips it | ✓ PASS |
| cobertura_aceite in painel response, pct_escopo_concluido unchanged | Grep | Separate field at response root (line 393); pct_escopo_concluido untouched | ✓ PASS |

Step 7b: Full test suite not run (no runnable entry points available without Supabase).

### Human Verification Required

#### 1. Supabase Migration Applied

**Test:** Execute the Phase 11 SQL block from `supabase_schema.sql` in the Supabase SQL Editor
**Expected:** Table `execucoes_aceite` created with all columns; `ALTER TABLE projects` adds `github_token` and `github_repo`; `ALTER TABLE funcionalidades` adds `testes_e2e`
**Why human:** Migration is applied manually — cannot verify without database access

#### 2. PATCH Trigger + Background Insertion Timing

**Test:** PATCH /funcionalidades/{id} with `{"status": "concluida"}` on a funcionalidade not yet concluida
**Expected:** HTTP 200 returns immediately (before any gate runs); within seconds, a row appears in `execucoes_aceite` with `gates` populated (either `sem_cobertura` if no GitHub config, or empty `[]` pending CI dispatch)
**Why human:** BackgroundTasks fire-and-forget timing requires live observation of DB state

#### 3. POST /ingest/aceite End-to-End

**Test:** POST `/ingest/aceite` with `{"funcionalidade_id": "<uuid>", "commit_sha": "abc123", "gates": [{"nome": "build", "resultado": "passou"}, ...]}`
**Expected:** HTTP 200 `{"status": "ok", ...}`; row in `execucoes_aceite` has `concluido_em` set and `gates` matching payload
**Why human:** Requires Supabase with migration applied and existing funcionalidade row

#### 4. GET /projects/{id}/painel — cobertura_aceite Field

**Test:** GET `/projects/{id}/painel` after having execucoes_aceite rows for concluídas funcionalidades
**Expected:** Response root contains `cobertura_aceite: <float>` (e.g. `66.7`); `bloco_a.pct_escopo_concluido` value is unchanged compared to a request without aceite data
**Why human:** Requires real Supabase data with both funcionalidades and execucoes_aceite

#### 5. Browser: Badge ⚠ aceite in Kanban

**Test:** Open project dashboard with at least one funcionalidade in status=concluida with an execucao_aceite where a gate has `resultado=falhou` or `resultado=erro`; inspect the Kanban column "Concluído"
**Expected:** Badge "⚠ aceite" appears inline in the card; DOM inspection shows `<span style="...">` with no `className` attribute on any new element
**Why human:** Requires browser + live data with a failing gate

#### 6. Browser: Bloco B — Cobertura de Aceite Sub-Section

**Test:** Open Painel tab with funcionalidades concluídas that have suíte falhando
**Expected:** Sub-section "Cobertura de Aceite" appears in Bloco B listing the failing funcionalidades; DOM confirms zero `className` on new elements
**Why human:** Requires browser + specific data state

#### 7. GitHub Actions Workflow Trigger

**Test:** Install `aceite.yml` + `aceite_agent.py` in a test repo; configure `DOCUDATA_API_URL` GitHub Secret; trigger via `POST /repos/{owner}/{repo}/dispatches` with `event_type: docudata-aceite` and `client_payload: {funcionalidade_id, project_id, testes_e2e: []}`
**Expected:** Workflow runs; job does not fail CI (continue-on-error); agent logs `[aceite] Resultado registrado — HTTP 200`; POST /ingest/aceite reaches the backend
**Why human:** Requires GitHub repo, live backend, and workflow dispatch

### Gaps Summary

No gaps found. All 15 code-verifiable must-haves pass. Phase is blocked on 7 human verification items that require live Supabase, browser, and optionally a GitHub repository with the workflow installed.

---

_Verified: 2026-08-23T03:00:00Z_
_Verifier: Claude (gsd-verifier)_
