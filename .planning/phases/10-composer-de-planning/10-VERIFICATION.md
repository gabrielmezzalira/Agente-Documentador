---
phase: 10-composer-de-planning
verified: 2026-08-23T00:00:00Z
status: gaps_found
score: 12/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Gerente pode sair e voltar ao composer sem perder o progresso — estado salvo após cada passo (SC-1 / D-01)"
    status: failed
    reason: "CR-01: GET /composer/rascunho upsert always sends step_atual=1 and dados_json={} in the upsert body. Supabase upsert with on_conflict updates all provided columns on conflict — so every GET call on an existing rascunho resets step_atual to 1 and clears dados_json. Session resume is broken at the database layer."
    artifacts:
      - path: "docudata-backend/routers/composer.py"
        issue: "Lines 114-126: upsert payload hardcodes step_atual=1 and dados_json={} with no ignore_duplicates flag. On conflict this overwrites existing state."
    missing:
      - "Add ignore_duplicates=True to the upsert call (supabase-py v2 supports it), then always SELECT the row after upsert. Or: SELECT first; INSERT only if not found; return whichever row exists."
  - truth: "GET /composer/rascunho retorna rascunho (criado via upsert), throughput_ref e lista de transbordos (P1-1)"
    status: partial
    reason: "Throughput_ref and transbordos logic is correct. Upsert is present. But the upsert resets step_atual/dados_json on every call (CR-01), so the 'retrieves existing' part of this truth fails."
    artifacts:
      - path: "docudata-backend/routers/composer.py"
        issue: "Lines 114-126: upsert overwrites existing rascunho with default values on every GET"
    missing:
      - "Same fix as SC-1 gap above — single root cause"
---

# Phase 10: Composer de Planning — Verification Report

**Phase Goal:** Wizard de 4 passos que permite ao gerente compor o planning da sprint de forma estruturada — persistindo rascunho entre sessões, validando critérios de aceite, chamando Gemini para gerar markdown e confirmando oficialmente para generated_docs.
**Verified:** 2026-08-23
**Status:** gaps_found — 1 blocker (CR-01: upsert resets rascunho state on every GET call, 2 truths affected)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Gerente pode sair e voltar ao composer sem perder o progresso — estado salvo após cada passo | FAILED (BLOCKER) | GET /rascunho upsert always writes step_atual=1, dados_json={} on conflict — overwrites existing state. composer.py lines 114-126. |
| SC-2 | Funcionalidades transbordadas da sprint anterior aparecem no topo marcadas como tal | VERIFIED | Backend filters sprint_alvo=str(N-1) AND status!='concluida' (composer.py lines 135-145). PlanningTab renders transbordos first with borderLeft orange and "Transbordado" badge. |
| SC-3 | Sistema exibe throughput das últimas 3 sprints — como informação, nunca como bloqueio | VERIFIED | calcular_throughput_ref (composer.py lines 69-96) queries funcionalidades with sprint_alvo IN [str(N-1), str(N-2), str(N-3)] and status='concluida'. PlanningTab shows value as text only; no blocking logic. |
| SC-4 | Recorte é campo obrigatório por funcionalidade; gerente pode marcar quais critérios entram nesta sprint | VERIFIED | PlanningTab.tsx line 309: passo2Valido = selecionadas.every((id) => (recortes[id] ?? []).length > 0). Line 554: disabled={!passo2Valido}. Step 2 "Próximo" blocked when any selected funcionalidade has no criteria. |
| SC-5 | Template de Planning preenchido automaticamente com itens, recortes, responsáveis, transbordos e throughput | VERIFIED | POST /gerar calls _montar_contexto_gerar (composer.py lines 263-328) building structured context with all 5 required fields, sends to Gemini gemini-3.5-flash-lite. Returns {markdown} only. |
| SC-6 | Rascunho nunca vira Planning oficial sem confirmação humana explícita | VERIFIED | POST /gerar returns {markdown} without any DB insert. POST /confirmar is separate. Step 4 shows preview with distinct "Confirmar Planning" button before any persist. D-06/D-07 respected. |

**Roadmap score: 5/6 truths verified** (SC-1 FAILED)

### Must-Have Truths (PLAN frontmatter)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| P1-1 | GET /rascunho returns rascunho (via upsert), throughput_ref, transbordos | PARTIAL (BLOCKER) | Upsert present, throughput_ref and transbordos correct — but upsert resets existing state (same root cause as SC-1) |
| P1-2 | PATCH /rascunho updates step_atual and dados_json | VERIFIED | composer.py lines 154-194: SELECT check + UPDATE with step_atual, dados_json, updated_at. 404 on missing. |
| P1-3 | POST /confirmar inserts in generated_docs with doc_type='planning' AND deletes rascunho (D-07 order) | VERIFIED | Lines 223-249: INSERT first, check success, THEN DELETE. doc_type='planning' at line 228. Order confirmed. |
| P1-4 | planning_rascunhos table in supabase_schema.sql with UNIQUE(project_id, sprint_numero) | VERIFIED | supabase_schema.sql lines 115-124: all 7 fields + UNIQUE constraint present. |
| P1-5 | composer.router registered in main.py | VERIFIED | main.py line 6 import list includes 'composer'; line 31: app.include_router(composer.router). |
| P2-1 | POST /composer/gerar calls Gemini, returns {markdown} without persisting (D-05/D-06) | VERIFIED | composer.py lines 336-423: ChatGoogleGenerativeAI(model='gemini-3.5-flash-lite'), returns {"markdown": result.content}, zero .insert() calls. |
| P2-2 | PlanningTab.tsx exists with zero className (all inline styles) | VERIFIED | File exists. grep -v '^//' \| grep -c 'className' returns 0. Line 23 has 'className' inside a comment only, not as an attribute. All styles are CSSProperties constants. |
| P2-3 | 4-step wizard with horizontal step indicator | VERIFIED | wizardStep state typed as 1\|2\|3\|4. Horizontal step bar at top with display:flex, 4 labels: Seleção, Recorte, Alocação, Composição. |
| P2-4 | Step 1 lists funcionalidades with transbordos on top (orange badge) | VERIFIED | Transbordos rendered before other funcionalidades with borderLeft: "3px solid #c2410c" and badge with background #ffedd5, color #c2410c. |
| P2-5 | Step 2 "Próximo" disabled when no criteria selected (D-04) | VERIFIED | passo2Valido computed at line 309; button disabled={!passo2Valido} at line 554. |
| P2-6 | Step 3 responsável input per funcionalidade | VERIFIED | Step 3 renders a text input per selected funcionalidade for alocacoes (optional per spec). |
| P2-7 | Step 4 auto-calls gerarPlanning, shows ReactMarkdown preview, "Confirmar Planning" button | VERIFIED | useEffect (lines 237-238) fires on wizardStep===4 when !markdownGerado && !gerandoMarkdown. ReactMarkdown renders preview. "Confirmar Planning" button calls confirmarPlanning(). |
| P2-8 | getRascunho, patchRascunho, gerarPlanning, confirmarPlanning in api.ts | VERIFIED | api.ts lines 782+: all 4 functions exported. Interfaces DadosJson, RascunhoData, GetRascunhoResponse, TransbordoItem present. |
| P2-9 | page.tsx TabId includes 'planning', tab in array, conditional render | VERIFIED | Line 48: TabId union includes 'planning'. Line 479: tab entry present. Lines 930-932: conditional render wired. |

**Plan must-have score: 12/14 verified** (P1-1 partial from same CR-01 root cause as SC-1)

---

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `docudata-backend/routers/composer.py` | VERIFIED | 424 lines; GET/PATCH/POST confirmar/POST gerar endpoints; Pydantic schemas; calcular_throughput_ref; _montar_contexto_gerar; _PLANNING_SYSTEM_PROMPT |
| `docudata-backend/supabase_schema.sql` | VERIFIED | planning_rascunhos with 7 fields + UNIQUE(project_id, sprint_numero) at lines 115-124 |
| `docudata-frontend/app/components/PlanningTab.tsx` | VERIFIED | Full 4-step wizard; welcome screen; transbordos marked; recorte validation; step 4 auto-generation |
| `docudata-frontend/app/lib/api.ts` | VERIFIED | 4 composer async functions + 4 TypeScript interfaces |
| `docudata-frontend/app/projects/[id]/page.tsx` | VERIFIED | TabId extended; tab added; PlanningTab import; conditional render |

---

## Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| main.py | composer.router | `from routers import ..., composer` + `app.include_router(composer.router)` line 31 | VERIFIED |
| GET /rascunho | planning_rascunhos upsert | upsert on_conflict="project_id,sprint_numero" — present but resets state on conflict | PARTIAL (CR-01) |
| POST /confirmar | generated_docs THEN planning_rascunhos delete | INSERT at line 223, check, DELETE at line 247 | VERIFIED |
| PlanningTab step 4 | POST /composer/gerar | useEffect on wizardStep===4 calls gerarPlanning() | VERIFIED |
| page.tsx | PlanningTab | import + activeTab==="planning" conditional render | VERIFIED |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docudata-backend/routers/composer.py` | 114-126 | Upsert payload always includes step_atual=1 and dados_json={} — on conflict these values overwrite the existing rascunho, destroying saved wizard progress | BLOCKER | Session resume broken: SC-1 and P1-1 fail |

No TBD, FIXME, or XXX debt markers found in phase-modified files.

---

## Gaps Summary

### Root Cause: CR-01 — Upsert Destroys Existing Rascunho State

**Affected truths:** SC-1 (Gerente pode sair e voltar), P1-1 (GET retorna rascunho via upsert)

The GET `/composer/rascunho/{project_id}/{sprint_numero}` endpoint (composer.py lines 114-126) uses:

```python
client.table("planning_rascunhos").upsert(
    {
        "project_id": project_id,
        "sprint_numero": sprint_numero,
        "step_atual": 1,       # <-- hardcoded default
        "dados_json": {},      # <-- hardcoded default
    },
    on_conflict="project_id,sprint_numero",
).execute()
```

Supabase's default upsert behavior on conflict is an UPDATE with all provided values. This means every time the frontend calls GET (including when resuming a session), `step_atual` is reset to `1` and `dados_json` is cleared. A manager who reaches step 3, closes the browser, and returns will lose all selections.

**Fix — option A (recommended, minimal change):**

```python
# INSERT only if the row does not exist; return existing row unchanged on conflict
upsert_resp = (
    client.table("planning_rascunhos")
    .upsert(
        {
            "project_id": project_id,
            "sprint_numero": sprint_numero,
            "step_atual": 1,
            "dados_json": {},
        },
        on_conflict="project_id,sprint_numero",
        ignore_duplicates=True,   # <-- add this
    )
    .execute()
)
# After upsert (which may have returned nothing on ignore), fetch the actual row
fetch_resp = (
    client.table("planning_rascunhos")
    .select("*")
    .eq("project_id", project_id)
    .eq("sprint_numero", sprint_numero)
    .execute()
)
if not fetch_resp.data:
    raise HTTPException(status_code=500, detail="Falha ao criar/buscar rascunho")
rascunho = fetch_resp.data[0]
```

**Fix — option B (explicit SELECT-then-INSERT):**

```python
existing = (
    client.table("planning_rascunhos")
    .select("*")
    .eq("project_id", project_id)
    .eq("sprint_numero", sprint_numero)
    .execute()
)
if existing.data:
    rascunho = existing.data[0]
else:
    insert_resp = (
        client.table("planning_rascunhos")
        .insert({"project_id": project_id, "sprint_numero": sprint_numero,
                 "step_atual": 1, "dados_json": {}})
        .execute()
    )
    if not insert_resp.data:
        raise HTTPException(status_code=500, detail="Falha ao criar rascunho")
    rascunho = insert_resp.data[0]
```

This is a single-endpoint fix. All other phase deliverables are correctly implemented.

---

_Verified: 2026-08-23_
_Verifier: Claude (gsd-verifier)_
