---
phase: 05-content-type-validation-on-ingestion
verified: 2026-08-13T00:00:00Z
status: human_needed
score: 4/5 must-haves verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "Uploading an ML lecture PDF when creating a planning returns a 422 with a message indicating the content is unrelated to project management"
    test: "POST /sprint-docs/planning with an ML lecture PDF attached"
    expected: "HTTP 422 with detail.tipo_detectado='nao_relacionado' and detail.mensagem containing 'o sistema aceita documentos de projeto'"
    why_human: "Depends on Gemini classifying the file as nao_relacionado at runtime — no deterministic test exists and no integration test corpus is present in the repo. Code path is wired correctly but correctness of classification is model-dependent."
human_verification:
  - test: "Upload an unrelated file (e.g. an ML lecture PDF) to POST /sprint-docs/planning with a real Gemini API key"
    expected: "HTTP 422 with detail dict containing tipo_detectado='nao_relacionado', tipo_esperado='planning', mensagem citing 'o sistema aceita documentos de projeto', pode_forcar=True"
    why_human: "Gemini classification correctness cannot be tested without a live API key and a real file. The code path is fully wired; only runtime classification outcome is unverified."
---

# Phase 5: Content-Type Validation on Ingestion — Verification Report

**Phase Goal:** Every file-based ingestion endpoint (upload livre, planning, daily, ata, review, retrospectiva — when a file attachment is present) validates whether the content corresponds to the expected document type and returns a diagnostic error identifying what the content looks like instead. Commit ingestion is excluded (structured JSON payload, no free-form file).
**Verified:** 2026-08-13
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Uploading an ML lecture PDF to planning returns HTTP 422 indicating unrelated content | PRESENT_BEHAVIOR_UNVERIFIED | Code path wired: validar_tipo classifies -> nao_relacionado -> valido_tipo=False -> router raises 422 with "o sistema aceita documentos de projeto". Gemini classification correctness is runtime-only. |
| 2 | Uploading a review-like doc to planning returns 422 identifying the mismatch (e.g., "Conteudo parece ser uma Review, nao um(a) Planning") | VERIFIED | `_CATEGORY_LABELS` maps "review"->"Review", "planning"->"Planning". Message template at extraction_graph.py:220: `f"Esse arquivo parece ser uma {label_detectado}, nao um(a) {label_esperado}."` Wired end-to-end through _extract_anexo_to_content -> 422 in sprint_docs.py:83-92. |
| 3 | All 5 file-based endpoints have type validation; commit excluded | VERIFIED | planning: tipo_esperado="planning" via _extract_anexo_to_content (line 306). daily: tipo_esperado="daily" (line 377). review: tipo_esperado="review" (line 562). retrospectiva: tipo_esperado="retrospectiva" (line 665). ata: inline state tipo_esperado="ata_reuniao" (line 446). /ingest: tipo_esperado="upload_livre" (ingest.py:77). All have force: bool = Form(False). No commit endpoint in codebase. |
| 4 | Upload livre blocks only nao_relacionado; any project document passes | VERIFIED | extraction_graph.py:183-199: if tipo_esperado=="upload_livre" branch blocks only when tipo_detectado=="nao_relacionado". All other categories return valido_tipo=True immediately. |
| 5 | Validation runs before extraction; rejected content is never saved to Supabase | VERIFIED | Graph topology: START -> validar_tipo -> _roteador_validacao -> END (when valido_tipo=False). detectar_tipo, preprocessar_arquivo, extrair_conteudo, salvar are all bypassed. Router calls _insert_ingestion only after successful extraction. Confirmed by source analysis of both graph edges and router code flow. |

**Score:** 4/5 truths verified (1 present, behavior-unverified — SC-1 depends on live Gemini classification)

---

## Graph Topology Verification

**START -> validar_tipo:** extraction_graph.py:428 `_builder.add_edge(START, "validar_tipo")` — CONFIRMED

**Conditional edge from validar_tipo:** extraction_graph.py:429 `_builder.add_conditional_edges("validar_tipo", _roteador_validacao, {"detectar_tipo": "detectar_tipo", END: END})` — CONFIRMED

**_roteador_validacao logic:** extraction_graph.py:231-234:
```python
def _roteador_validacao(state: ExtractionState):
    if state.get("valido_tipo", True):
        return "detectar_tipo"
    return END
```
Correctly routes to END when `valido_tipo` is False (or missing, defaulting to True — safe-fail open). CONFIRMED.

**salvar node reachability:** salvar is only reachable via `_roteador` (from extrair_conteudo when `valido=True`). It is NOT reachable from the validar_tipo -> END path. CONFIRMED.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docudata-backend/graphs/extraction_graph.py` | validar_tipo node + ExtractionState fields + graph topology | VERIFIED | All 7 new ExtractionState fields present (lines 30-38). validar_tipo function (line 108). _roteador_validacao (line 231). _VALIDATION_SYSTEM_PROMPT with 8 categories (line 71). Graph compiled at module level (line 435). |
| `docudata-backend/routers/ingest.py` | force field, project context, tipo_esperado="upload_livre", 422 check | VERIFIED | force: bool = Form(False) at line 32. Project select expanded to include name/client/description (line 45). Full state dict with tipo_esperado/force/projeto_nome/cliente/projeto_descricao (lines 77-84). 422 check before 502 check (lines 88-97). |
| `docudata-backend/routers/sprint_docs.py` | All 5 endpoint signatures updated; _extract_anexo_to_content extended; 422 re-raised in review/retrospectiva | VERIFIED | _extract_anexo_to_content accepts tipo_esperado/force/project params (lines 37-39). 422 check inside helper (lines 83-92). All 5 endpoints have force: bool = Form(False). tipo_esperado hardcoded per endpoint. 422 re-raised in review (line 565) and retrospectiva (line 668). |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `submit_planning` | `_extract_anexo_to_content` | `tipo_esperado="planning"` kwarg | WIRED | sprint_docs.py:306 |
| `submit_daily` | `_extract_anexo_to_content` | `tipo_esperado="daily"` kwarg | WIRED | sprint_docs.py:377 |
| `submit_review` | `_extract_anexo_to_content` | `tipo_esperado="review"` kwarg | WIRED | sprint_docs.py:562 |
| `submit_retrospectiva` | `_extract_anexo_to_content` | `tipo_esperado="retrospectiva"` kwarg | WIRED | sprint_docs.py:665 |
| `submit_ata_with_upload` | `extraction_graph.ainvoke` | inline state `tipo_esperado="ata_reuniao"` | WIRED | sprint_docs.py:446 |
| `ingest` | `extraction_graph.ainvoke` | inline state `tipo_esperado="upload_livre"` | WIRED | ingest.py:77 |
| `_extract_anexo_to_content` | HTTP 422 | `result.get("valido_tipo") is False and not result.get("valido")` | WIRED | sprint_docs.py:83-92 |
| `submit_ata_with_upload` | HTTP 422 | same condition, inline | WIRED | sprint_docs.py:456-465 |
| `ingest` | HTTP 422 | same condition, inline | WIRED | ingest.py:88-97 |
| `validar_tipo` result | `salvar` (negative) | END path bypasses salvar node | WIRED | Graph edge analysis: salvar unreachable from END |

---

## Behavioral Spot-Checks

Step 7b: SKIPPED for SC-1 (requires live Gemini API + real file — routed to human verification).

All other SCs verified via static analysis with deterministic assertions (no server required).

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| extraction_graph.py | 64 | "TODOs" appears inside a string literal in _SYSTEM_PROMPT | Info | Not a debt marker — it is instructing Gemini to extract TODO comments from code files. Not a code debt marker. |

No unreferenced TBD/FIXME/XXX debt markers found in any of the three phase-modified files. No stub returns, no hardcoded empty responses, no orphaned implementations.

---

## Human Verification Required

### 1. Live Gemini Classification — Unrelated Content to Planning Endpoint

**Test:** Upload an ML lecture PDF (or any clearly non-project-management document) to `POST /sprint-docs/planning` with a real Gemini API key configured, `sprint_numero=1`, and a valid `projeto_id`. No `force` field (defaults to False).

**Expected:** HTTP 422 response with JSON body:
```json
{
  "tipo_detectado": "nao_relacionado",
  "tipo_esperado": "planning",
  "mensagem": "Conteudo parece ser <Gemini's explanation> — o sistema aceita documentos de projeto (atas, plannings, reviews, etc.).",
  "pode_forcar": true
}
```

**Why human:** Gemini must correctly classify the file as `nao_relacionado` for this scenario to work. The blocking logic, message construction, and HTTP 422 raise are all correctly wired in code. Only the runtime classification outcome (model behavior) cannot be verified statically.

---

## Gaps Summary

No implementation gaps found. All five success criteria have the correct code in place. The single human-needed item (SC-1) is a runtime behavior dependency on Gemini's classification quality — not a missing implementation.

**Note on the ata endpoint:** `submit_ata_with_upload` sets `tipo_esperado="ata_reuniao"` inline in its state dict (not via `_extract_anexo_to_content`) because ata always has a mandatory attachment and runs the graph directly. This is architecturally correct and consistent with the design — the validation 422 check at lines 456-465 is present and properly structured.

---

_Verified: 2026-08-13_
_Verifier: Claude (gsd-verifier)_
