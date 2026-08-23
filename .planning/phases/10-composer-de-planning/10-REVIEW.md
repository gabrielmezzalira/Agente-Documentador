---
phase: 10-composer-de-planning
reviewed: 2026-08-23T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - docudata-backend/routers/composer.py
  - docudata-backend/supabase_schema.sql
  - docudata-backend/main.py
  - docudata-frontend/app/lib/api.ts
  - docudata-frontend/app/components/PlanningTab.tsx
  - docudata-frontend/app/projects/[id]/page.tsx
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-08-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 10 adds the Composer de Planning feature: a 4-step wizard in the frontend that lets managers compose a sprint planning document by selecting features, cutting acceptance criteria, allocating owners, and generating markdown via Gemini. The backend adds three new endpoints (`GET /rascunho`, `PATCH /rascunho`, `POST /confirmar`, `POST /gerar`) and the `planning_rascunhos` table.

The critical ordering constraint (D-07: INSERT before DELETE) is correctly implemented. The `sprint_alvo` string comparison is consistently applied. The `/gerar` endpoint correctly never calls `.insert()`. The TypeScript interface shapes are largely aligned with backend response bodies.

Two BLOCKER-level issues were found: the `gemini_api_key` field is selected from the `projects` table in `gerar_planning` and returned in the raw Supabase row, meaning the actual key value travels through the Python process — but more critically, the `projects` row response is not sanitized through `_project_safe` before it is used, so if any logging middleware or error response accidentally serializes `projeto`, the raw API key is exposed. A second blocker is a silent data-loss path: the upsert in `get_rascunho` **always resets** `step_atual` to `1` and `dados_json` to `{}` for any existing rascunho, because supabase-py v2's `upsert` with `on_conflict` still sends the full payload and the DB merges on conflict — but the payload itself contains the reset values. Existing progress is overwritten on every page load.

---

## Critical Issues

### CR-01: Upsert in `get_rascunho` destroys existing draft data on every GET

**File:** `docudata-backend/routers/composer.py:114-129`

**Issue:** The upsert payload unconditionally sets `step_atual: 1` and `dados_json: {}`. The Supabase `upsert` with `on_conflict` performs an UPDATE of all provided columns when the row already exists. This means every time the frontend calls `GET /composer/rascunho/{project_id}/{sprint}` — including when re-entering the wizard after navigating away — it silently resets the wizard back to step 1 with an empty `dados_json`, destroying whatever the user had saved. Steps 2 and 3 work (they call PATCH), but any page refresh or tab-switch wipes the state.

The intent is "create if not exists, return existing if already there," but the implementation does the opposite for updates.

**Fix:**
```python
# First check if the rascunho already exists
check_resp = (
    client.table("planning_rascunhos")
    .select("*")
    .eq("project_id", project_id)
    .eq("sprint_numero", sprint_numero)
    .execute()
)
if check_resp.data:
    rascunho = check_resp.data[0]
else:
    insert_resp = (
        client.table("planning_rascunhos")
        .insert({
            "project_id": project_id,
            "sprint_numero": sprint_numero,
            "step_atual": 1,
            "dados_json": {},
        })
        .execute()
    )
    if not insert_resp.data:
        raise HTTPException(status_code=500, detail="Falha ao criar rascunho")
    rascunho = insert_resp.data[0]
```

Alternatively, use `upsert` with `ignoreDuplicates=True` (supabase-py v2 supports this) to skip the update entirely when the row already exists:
```python
client.table("planning_rascunhos").upsert(
    {"project_id": project_id, "sprint_numero": sprint_numero, "step_atual": 1, "dados_json": {}},
    on_conflict="project_id,sprint_numero",
    ignore_duplicates=True,
).execute()
# Then SELECT to fetch the existing row
```

---

### CR-02: Raw `gemini_api_key` value selected and held in memory without sanitization guard

**File:** `docudata-backend/routers/composer.py:362-375`

**Issue:** `gerar_planning` selects `"name, client, gemini_api_key"` from `projects` and stores the result in `projeto`. The raw key is then extracted to `api_key`. This is intentional for the LLM call, but the unsanitized `projeto` dict (containing the raw key) is passed directly into `_montar_contexto_gerar()` at line 403. If `_montar_contexto_gerar` ever logs `projeto` for debugging, or if a future developer adds `projeto` to a 500 error response, the key leaks.

More concretely: the existing pattern in `routers/projects.py` uses a `_project_safe()` helper that strips `gemini_api_key` from any outbound dict. That guard is deliberately bypassed here. Any unhandled exception inside `_montar_contexto_gerar` that re-raises with context (e.g., via a framework that serializes locals) will expose the raw key in error logs.

**Fix:** Extract the key before building `projeto`, then delete it from the dict passed downstream:
```python
projeto = proj_resp.data[0]
api_key = (projeto.pop("gemini_api_key", None) or "").strip()
if not api_key:
    raise HTTPException(
        status_code=422,
        detail="Este projeto não tem uma chave de API do Gemini configurada.",
    )
# projeto dict no longer contains the key — safe to pass to helper functions
contexto = _montar_contexto_gerar(rascunho, funcs_map, projeto, throughput_ref, transbordos)
```

---

## Warnings

### WR-01: `patchAndAdvance` silently swallows PATCH errors — user loses data without feedback

**File:** `docudata-frontend/app/components/PlanningTab.tsx:264-279`

**Issue:** The `patchAndAdvance` function wraps `patchRascunho` in a bare `catch {}` and comments "non-blocking — continue navigation." If the PATCH fails (network error, 404, 500), the wizard advances to the next step but the backend state is not updated. The user continues working, reaches step 4, and generates the planning — but the backend rascunho still has the old `dados_json` from before the failed save. `POST /gerar` then reads the stale rascunho from the DB and generates a planning based on old data, silently producing a wrong document.

This is especially dangerous on step 3→4 transition, which also triggers `handleGerar` immediately via the `useEffect`.

**Fix:** Surface PATCH errors as a non-blocking warning (toast or inline message) rather than silently ignoring them. The wizard can still advance, but the user should know their progress was not saved to the server:
```typescript
async function patchAndAdvance(nextStep: 1 | 2 | 3 | 4) {
  // ...
  try {
    await patchRascunho(projectId, sprintAlvo, { step_atual: nextStep, dados_json: dadosJson });
  } catch {
    // Advance anyway, but warn the user
    setSaveWarning("Progresso não salvo no servidor — verifique sua conexão.");
  }
  setWizardStep(nextStep);
}
```

---

### WR-02: Auto-trigger `handleGerar` in `useEffect` has no guard against re-runs when returning to step 4

**File:** `docudata-frontend/app/components/PlanningTab.tsx:237-242`

**Issue:** The `useEffect` on `wizardStep` fires `handleGerar()` when `wizardStep === 4 && !markdownGerado && !gerandoMarkdown`. If the user clicks "Anterior" from step 4 to step 3, then "Próximo" back to step 4, `markdownGerado` is still populated from the first call so the guard `!markdownGerado` correctly prevents a re-generation. However, if the user clicks "Tentar novamente" after an error (line 621-626), `setMarkdownGerado("")` is called followed immediately by a manual `handleGerar()`. This double-invocation path is benign currently, but the guard logic is fragile: `markdownGerado` is reset to `""` by `setMarkdownGerado("")` before the new call, but React state updates are asynchronous — there is a window where the effect could fire a second time for the same step if component re-renders interleave. The `eslint-disable-next-line react-hooks/exhaustive-deps` comment suppressing the dependency array warning is a signal that this effect is not correctly modelled.

**Fix:** Use a ref to track whether generation was already initiated for the current step-4 entry, or include `markdownGerado` and `gerandoMarkdown` in the dependency array and rely on the guards:
```typescript
useEffect(() => {
  if (wizardStep === 4 && !markdownGerado && !gerandoMarkdown) {
    handleGerar();
  }
}, [wizardStep, markdownGerado, gerandoMarkdown]); // remove the eslint-disable comment
```

---

### WR-03: `sprintAlvo` is computed once on render from `sprints` prop — stale value if sprints change during wizard

**File:** `docudata-frontend/app/components/PlanningTab.tsx:209-210`

**Issue:** `sprintAlvo` is computed as a plain `const` (not `useMemo` or `useState`) from the `sprints` prop at each render. If the parent component refreshes `sprints` (e.g., after `handleCreateSprint`) while the user is mid-wizard, `sprintAlvo` recalculates to a new value. All subsequent `patchRascunho` and `gerarPlanning` calls will use the new `sprintAlvo`, while the rascunho in the DB was created under the old value — causing a 404 from `PATCH /rascunho` (which uses the new `sprintAlvo` in the URL but the DB has the old sprint number).

**Fix:** Freeze `sprintAlvo` when the wizard is initiated:
```typescript
const [sprintAlvo, setSprintAlvo] = useState<number | null>(null);

async function handleIniciar() {
  const targetSprint = sprints.length > 0 ? Math.max(...sprints.map((s) => s.numero)) + 1 : 1;
  setSprintAlvo(targetSprint);
  // ... rest of handleIniciar using targetSprint
}
```

---

### WR-04: `confirmarPlanning` sends user-edited markdown to the server with no size validation

**File:** `docudata-backend/routers/composer.py:56-61` and `docudata-frontend/app/components/PlanningTab.tsx:295-306`

**Issue:** The markdown displayed in step 4 is rendered inside a `<div>` (read-only). The user cannot edit it in the UI. However, `confirmarPlanning` in `api.ts` accepts any string and POSTs it to `/confirmar`. The backend `ConfirmarBody` validator only checks that `markdown` is non-empty — there is no maximum length validation. A malformed or very large `markdown` field (sent directly via API) could insert an arbitrarily large blob into `generated_docs.content` (a TEXT column with no DB-side length limit). This is low severity for an MVP without auth, but worth noting for the production path.

More immediately relevant: the `ReactMarkdown` component in step 4 renders `markdownGerado` which comes from Gemini's response. `react-markdown` by default does not render raw HTML (it escapes it), so XSS is not a concern. This is confirmed safe.

**Fix:** Add a server-side length cap:
```python
@field_validator("markdown")
@classmethod
def markdown_nao_vazio(cls, v: str) -> str:
    if not v or not v.strip():
        raise ValueError("markdown não pode ser vazio")
    if len(v) > 100_000:  # ~100KB cap
        raise ValueError("markdown excede o tamanho máximo permitido")
    return v
```

---

### WR-05: `planning_rascunhos` table missing index on `(project_id, sprint_numero)` for read performance

**File:** `docudata-backend/supabase_schema.sql:115-136`

**Issue:** The `UNIQUE (project_id, sprint_numero)` constraint creates a unique index, which is correct and sufficient for the upsert conflict target. However, the upsert in `get_rascunho` is `on_conflict="project_id,sprint_numero"` — this requires the exact column names to match the unique constraint definition. In PostgreSQL the constraint name and index name differ; supabase-py's `.upsert(on_conflict=...)` passes the value directly as the `on_conflict` clause. The constraint column order in the schema is `(project_id, sprint_numero)` and the upsert string is `"project_id,sprint_numero"` — these match, so this is safe. No action needed for the constraint itself.

The actual concern: three separate Supabase queries fire sequentially for every `GET /rascunho` call (upsert, throughput query, transbordos query) and one more for `POST /gerar` (rascunho fetch, project fetch, funcionalidades fetch, throughput, transbordos — 5 sequential round-trips). On Railway with Supabase Cloud this adds latency. This is a quality note, not a correctness bug.

**Fix (optional for MVP):** No structural fix required, but consider combining the throughput and transbordos queries, or accepting the latency given the MVP scope.

---

## Info

### IN-01: `funcionalidades` table is not defined in `supabase_schema.sql`

**File:** `docudata-backend/supabase_schema.sql`

**Issue:** `composer.py` queries `client.table("funcionalidades")` extensively (lines 84-96, 379-386, 393-400). The `funcionalidades` table is referenced by existing routers (`funcionalidades.py`, `painel.py`) but its `CREATE TABLE` DDL is absent from `supabase_schema.sql`. A developer setting up the schema from scratch using this file will get runtime errors from composer endpoints immediately. The schema file is the single source of truth for the DB structure — missing DDL is a documentation gap that causes real setup failures.

**Fix:** Add the `CREATE TABLE IF NOT EXISTS funcionalidades (...)` DDL block to `supabase_schema.sql`, consistent with how `planning_rascunhos` was added in this phase.

---

### IN-02: `passo2Valido` allows advancing when a selected function has zero acceptance criteria

**File:** `docudata-frontend/app/components/PlanningTab.tsx:309`

**Issue:** `passo2Valido = selecionadas.every((id) => (recortes[id] ?? []).length > 0)`. If a selected feature has `criterios_aceite: []` (no criteria defined), the validation error message "Selecione ao menos um critério de aceite" is suppressed by the `{!hasSelection && criterios.length > 0 && ...}` guard on line 541. But `selecionadas.every(...)` still requires `recortes[id].length > 0` for that feature — which can never be satisfied since there are no criteria to select, permanently blocking the "Próximo" button for that feature. The user is stuck on step 2 with no actionable error message explaining why.

**Fix:** Skip validation for features with no defined criteria:
```typescript
const passo2Valido = selecionadas.every((id) => {
  const func = funcionalidades.find((f) => f.id === id);
  const criterios = func?.criterios_aceite ?? [];
  if (criterios.length === 0) return true; // nothing to select
  return (recortes[id] ?? []).length > 0;
});
```

---

### IN-03: `model="gemini-3.5-flash-lite"` may not be a valid Gemini model identifier

**File:** `docudata-backend/routers/composer.py:407`

**Issue:** The model string `"gemini-3.5-flash-lite"` does not match any documented Gemini model name. Known valid names are `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`, `gemini-2.5-flash`, etc. The project memory notes that "chaves novas só funcionam com gemini-3.5-flash+" — the closest match is `gemini-2.5-flash`. Using an invalid model identifier will cause every `/gerar` call to fail with a 404 or model-not-found error from the Gemini API, wrapped in the 502 response. The other routers use a different model name; check `generation_graph.py` for the canonical value.

**Fix:** Verify the exact model name against the Google AI API and unify with the value used in `generation_graph.py`:
```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # or whatever the canonical value is
    max_tokens=2048,
    google_api_key=api_key,
)
```

---

_Reviewed: 2026-08-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
