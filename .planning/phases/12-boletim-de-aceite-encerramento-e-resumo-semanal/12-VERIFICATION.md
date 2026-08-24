---
phase: 12-boletim-de-aceite-encerramento-e-resumo-semanal
verified: 2026-08-24T00:00:00Z
status: human_needed
score: 5/6 must-haves verified
behavior_unverified: 2
overrides_applied: 0
overrides:
  - must_have: "Gerente seleciona funcionalidades em concluida e gera boletim com título, critérios em linguagem de negócio, link de deploy preview e espaço para evidência visual"
    reason: "link de deploy preview and evidência visual were explicitly removed from scope by the user (D-03, D-04 in 12-CONTEXT.md). Core boletim generation with Gemini, título, and critérios in business language is fully implemented."
    accepted_by: "user (via 12-CONTEXT.md decisions D-03, D-04)"
    accepted_at: "2026-08-23"
  - must_have: "Quando 100% das funcionalidades estiverem aprovado, o sistema habilita geração do Termo de Encerramento com todas as funcionalidades, critérios, datas de aprovação e período de garantia"
    reason: "Geração do Termo de Encerramento was removed from scope by the user (D-04, D-13 in 12-CONTEXT.md). Replaced with badge sinalização: 'Projeto encerrado — todas as funcionalidades aprovadas' displayed in AceiteTab when todasAprovadas === true."
    accepted_by: "user (via 12-CONTEXT.md decisions D-04, D-13)"
    accepted_at: "2026-08-23"
gaps: []
behavior_unverified_items:
  - truth: "Ao marcar boletim como enviado, funcionalidades movem para status_cliente=enviado com data registrada"
    test: "PATCH /boletins/{id} com status=enviado deve (1) inserir registro em transicoes_status com campo=status_cliente e (2) atualizar funcionalidades.status_cliente para 'enviado'"
    expected: "Supabase recebe INSERT em transicoes_status com duracao_fase_anterior_segundos calculado + UPDATE em funcionalidades — ambas operações na mesma chamada"
    why_human: "Comportamento depende de estado real no Supabase. O código _registrar_transicao_status_cliente está presente e wired, mas a sequência de INSERT + UPDATE e o cálculo de duracao requerem execução real para confirmar"
  - truth: "PATCH /boletins/{id} com status=ajuste sem retorno_tipo retorna 422 e sequência rascunho→aprovado também retorna 422"
    test: "Chamar PATCH /boletins/{id} com {status: 'ajuste'} sem retorno_tipo e depois com {status: 'aprovado'} a partir de rascunho; ambos devem retornar HTTP 422"
    expected: "Status 422 com mensagens descritivas em ambos os casos"
    why_human: "Validação de sequência enforced via TRANSICOES_VALIDAS e retorno_tipo check estão no código, mas os caminhos de erro são state-dependent (dependem do status atual do boletim)"
human_verification:
  - test: "Fluxo completo boletim: seleção de funcionalidades → POST /boletins → preview markdown → PATCH enviado → PATCH aprovado"
    expected: "Gerente consegue percorrer todo o fluxo na aba Aceite; boletim aparece na lista com status correto; status_cliente das funcionalidades muda correspondentemente"
    why_human: "Fluxo multi-step com fetch real ao Supabase e Gemini — não verificável com grep"
  - test: "PATCH /boletins/{id} com transição inválida (rascunho→aprovado) retorna 422"
    expected: "HTTP 422 com mensagem 'Transição inválida: rascunho → aprovado'"
    why_human: "Behavior-dependent — requer estado real de boletim em rascunho no Supabase"
  - test: "PATCH /boletins/{id} com status=ajuste sem retorno_tipo retorna 422"
    expected: "HTTP 422 com 'retorno_tipo é obrigatório quando status = ajuste'"
    why_human: "Behavior-dependent — requer estado real de boletim em enviado no Supabase"
  - test: "Badge 'Projeto encerrado' aparece quando todas as funcionalidades têm status_cliente=aprovado"
    expected: "div com texto 'Projeto encerrado — todas as funcionalidades aprovadas' visível no topo da aba Aceite"
    why_human: "Computed value depende de dados reais de funcionalidades — verificável apenas na UI com dados reais"
  - test: "POST /boletins/resumo_semanal retorna markdown estruturado com seções corretas"
    expected: "Markdown com cabeçalho de período dom-sáb, seções de anomalias ou 'Nenhuma anomalia identificada nesta semana.', e salvo em generated_docs"
    why_human: "Integração com Supabase e calcular_bloco_a/b de painel.py — requer dados reais"
---

# Phase 12: Boletim de Aceite, Encerramento e Resumo Semanal — Verification Report

**Phase Goal:** O gerente gera boletins de aceite para envio ao cliente, registra o retorno (aprovado / ajuste pedido com categorização bug vs mudança de escopo), e quando 100% das funcionalidades estiverem aprovadas pode gerar o Termo de Encerramento; o resumo semanal de anomalias é gerado automaticamente.
**Verified:** 2026-08-24
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Gerente seleciona funcionalidades em `concluida` e gera boletim com título, critérios em linguagem de negócio | PASSED (override) | POST /boletins implementado em boletins.py:118-246; ownership check, Gemini call, INSERT em boletins_aceite. Deploy preview + evidência visual removidos do escopo (D-03, D-04) |
| SC2 | Ao marcar boletim como enviado, funcionalidades movem para `status_cliente=enviado` com data registrada | PRESENT_BEHAVIOR_UNVERIFIED | PATCH /boletins/{id} em linha 447; _registrar_transicao_status_cliente presente e wired; estado do Supabase não verificável sem execução real |
| SC3 | Ao registrar retorno como "ajuste pedido", sistema exige classificação: bug ou mudança de escopo | PRESENT_BEHAVIOR_UNVERIFIED | TRANSICOES_VALIDAS e validação retorno_tipo em boletins.py:479-483 presentes; caminhos de erro são state-dependent |
| SC4 | Quando 100% aprovado, sistema habilita geração do Termo de Encerramento | PASSED (override) | Termo de Encerramento removido do escopo (D-04, D-13). Substituído por badge sinalização: `todasAprovadas` em AceiteTab.tsx:247-248; JSX em linha 384-388 |
| SC5 | Resumo de exceções semanal gerado por projeto (travadas, aguardando cliente, suíte falhando, achados críticos, decisões pendentes, leitura tempo × escopo) | VERIFIED | POST /boletins/resumo_semanal em boletins.py:279-444; chama calcular_bloco_a + calcular_bloco_b de painel.py; seções todas presentes no código; sem Gemini |
| SC6 | Quando não houver anomalia, o resumo declara explicitamente | VERIFIED | boletins.py:380-383: `if not tem_anomalia: linhas.append("Nenhuma anomalia identificada nesta semana.")` |

**Score:** 4/6 truths verified (2 present, behavior-unverified; 2 PASSED via override — both overrides are user-authorized scope reductions documented in 12-CONTEXT.md)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docudata-backend/routers/boletins.py` | Router FastAPI com 4 endpoints | VERIFIED | 548 linhas; POST, GET, POST /resumo_semanal, PATCH presentes; imports wired |
| `docudata-backend/models/schemas.py` | BoletimCreate, BoletimPatch, BoletimResponse, ResumoSemanalRequest | VERIFIED | Linhas 324, 330, 335, 348 confirmadas |
| `docudata-backend/main.py` | boletins router registrado | VERIFIED | `from routers import ..., boletins` e `app.include_router(boletins.router)` — linha 6 e 33 |
| `docudata-frontend/app/components/AceiteTab.tsx` | Componente React zero className | VERIFIED | 593 linhas; zero `className=` attributes (apenas comentário de texto); 16 constantes CSSProperties |
| `docudata-frontend/app/lib/api.ts` | BoletimResponse + 4 funções + ajuste_pedido | VERIFIED | Linhas 660, 868, 881, 887, 901, 904, 914 confirmadas |
| `docudata-frontend/app/projects/[id]/page.tsx` | Aba Aceite wired | VERIFIED | TabId inclui "aceite" (linha 51); AceiteTab importado (linha 44); renderizado condicionalmente (linha 942) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| POST /boletins | ChatGoogleGenerativeAI → boletins_aceite INSERT | boletins.py:199-246 | VERIFIED | llm.ainvoke com SystemMessage+HumanMessage; INSERT em boletins_aceite com status=rascunho |
| GET /boletins/{project_id} | boletins_aceite SELECT WHERE project_id | boletins.py:249-276 | VERIFIED | .eq("project_id") + ORDER criado_em DESC |
| PATCH /boletins/{id} | TRANSICOES_VALIDAS → batch funcionalidades UPDATE → transicoes_status INSERT | boletins.py:447-547 | VERIFIED | loop sobre funcionalidade_ids; _registrar_transicao_status_cliente chamado; campos_update corretos |
| POST /boletins/resumo_semanal | calcular_bloco_a + calcular_bloco_b → generated_docs INSERT | boletins.py:279-444 | VERIFIED | from routers.painel import calcular_bloco_a, calcular_bloco_b (linha 9); INSERT em generated_docs com doc_type=resumo_semanal |
| main.py include_router | boletins router acessível | main.py:6+33 | VERIFIED | import + include_router confirmados |
| AceiteTab → listBoletins | GET /boletins/{project_id} | AceiteTab.tsx:235 | VERIFIED | useEffect chama listBoletins(projectId) |
| AceiteTab → createBoletim | POST /boletins | AceiteTab.tsx:268 | VERIFIED | handleGerarBoletim → createBoletim |
| AceiteTab → patchBoletim | PATCH /boletins/{id} | AceiteTab.tsx:283,295,309,322 | VERIFIED | 4 handlers chamam patchBoletim |
| AceiteTab → gerarResumoSemanal | POST /boletins/resumo_semanal | AceiteTab.tsx:341 | VERIFIED | handleGerarResumo → gerarResumoSemanal(projectId) |
| page.tsx → AceiteTab | aba Aceite renderizada | page.tsx:942-944 | VERIFIED | activeTab === "aceite" renderiza AceiteTab |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| AceiteTab.tsx boletins list | `boletins` state | `listBoletins(projectId)` → GET /boletins/{project_id} → Supabase | Yes | FLOWING |
| AceiteTab.tsx preview | `boletimPreview.conteudo` | `createBoletim()` → POST /boletins → Gemini → boletins_aceite | Yes (Gemini) | FLOWING |
| AceiteTab.tsx badge encerramento | `todasAprovadas` | `funcs` state ← `listFuncionalidades(projectId)` real fetch | Yes | FLOWING |
| boletins.py resumo markdown | `markdown_content` | calcular_bloco_a/b ← Supabase funcionalidades/transicoes/revisoes | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| boletins.py syntax | `python3 -c "import ast; ast.parse(...)"` | OK — todas as 3 files | PASS |
| Schemas importam | `from models.schemas import BoletimCreate, BoletimPatch, BoletimResponse, ResumoSemanalRequest` | OK (verificado via grep confirming class definitions at lines 324, 330, 335, 348) | PASS |
| main.py registra router | `grep "include_router(boletins" main.py` | count = 1 (linha 33) | PASS |
| TypeScript compila | `npx tsc --noEmit` | zero erros | PASS |
| AceiteTab zero className= | `grep -n "className=" AceiteTab.tsx` | empty output (zero JSX className attributes) | PASS |
| Route ordering | Routes listed: POST /boletins, GET /{project_id}, POST /resumo_semanal, PATCH /{id} | POST /resumo_semanal precede PATCH /{id}; GET vs POST = no conflict | PASS |
| Commits existem | `git log --oneline \| grep hash` | 0faf006, 332113a, ce4cb1f, 3d1325d, d40b99d confirmados | PASS |

### Requirements Coverage

| Requirement ID | Source Plan | Description | Status | Evidence |
|---------------|-------------|-------------|--------|---------|
| M6 (§5) | 12-01, 12-02, 12-03 | Boletins de aceite — geração, ciclo de vida, retorno do cliente | SATISFIED | POST/GET/PATCH /boletins implementados; AceiteTab wired |
| M8 (§5) | 12-02, 12-03 | Resumo semanal de anomalias por projeto | SATISFIED | POST /boletins/resumo_semanal determinístico; AceiteTab Seção 2 |
| §4.5 (RevisaoDiaria) | 12-02 | Achados críticos de revisoes_diarias no resumo semanal | SATISFIED | boletins.py:336-344 busca revisao_recente; calcular_bloco_b recebe e processa achados_criticos |

**Note on REQUIREMENTS.md:** The IDs M6, M8, §4.5 do NOT appear in `.planning/REQUIREMENTS.md` (last updated 2026-05-22, covers only phases 1-3). These are ROADMAP-level requirement references for phases added after the initial REQUIREMENTS.md was written. REQUIREMENTS.md is stale and does not cover this phase — this is an orphaned requirements documentation gap, not an implementation gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `routers/boletins.py` | 9 | `from routers.painel import calcular_bloco_a, calcular_bloco_b` — circular import risk if painel.py ever imports boletins | INFO | No circular import currently present (confirmed by Python import test passing) |

No TBD, FIXME, XXX, or HACK markers found in any phase-modified files.

### Human Verification Required

#### 1. Status Transition Enforcement (Behavior-Dependent)

**Test:** Call PATCH /boletins/{id} with `{status: "aprovado"}` on a boletim whose current status is "rascunho"
**Expected:** HTTP 422 with message "Transição inválida: rascunho → aprovado. Transições válidas: rascunho→enviado, enviado→aprovado, enviado→ajuste"
**Why human:** Requires a real boletim record in Supabase with status="rascunho" to exercise the transition guard

#### 2. retorno_tipo Validation (Behavior-Dependent)

**Test:** Call PATCH /boletins/{id} with `{status: "ajuste"}` (no retorno_tipo) on a boletim with status="enviado"
**Expected:** HTTP 422 with "retorno_tipo é obrigatório quando status = ajuste (valores aceitos: bug, mudanca_escopo)"
**Why human:** Requires a real boletim in "enviado" state in Supabase

#### 3. Batch status_cliente Update with TransicaoStatus

**Test:** After PATCH /boletins/{id} with status="enviado", query Supabase: (a) `transicoes_status` WHERE campo="status_cliente" AND funcionalidade_id IN boletim.funcionalidade_ids; (b) `funcionalidades` WHERE id IN boletim.funcionalidade_ids
**Expected:** (a) new transicao records with de=previous_status, para="enviado", duracao_fase_anterior_segundos > 0; (b) funcionalidades.status_cliente = "enviado"
**Why human:** State transition across two tables — requires real Supabase data to confirm both writes succeeded

#### 4. Full Boletim Creation Flow (End-to-End)

**Test:** In the Aceite tab, select concluida funcionalidades, click "Gerar Boletim", wait for Gemini response, verify preview appears, click "Marcar como Enviado"
**Expected:** Preview markdown renders with business language (no jargon); boletim appears in list with status "Enviado"; funcionalidades status_cliente updates visible
**Why human:** Requires Gemini API key configured in project, real Supabase data, and browser UI interaction

#### 5. Badge "Projeto Encerrado" Trigger

**Test:** Set all project funcionalidades to status_cliente="aprovado" in Supabase, reload the Aceite tab
**Expected:** Green badge "Projeto encerrado — todas as funcionalidades aprovadas" appears at top of Aceite tab
**Why human:** Computed from real funcionalidades data; requires controlled state setup

#### 6. Resumo Semanal End-to-End

**Test:** Click "Gerar Resumo desta Semana" in the Aceite tab for a project with mixed funcionalidades states
**Expected:** Markdown rendered with correct dom-sáb period header; sections for each anomaly type present; saved to generated_docs table
**Why human:** Depends on real Supabase data for calcular_bloco_a/b inputs and generated_docs INSERT

### Gaps Summary

No blocking gaps. All 6 key artifacts exist and are wired. The two ROADMAP SCs that appear not met (SC1: deploy preview + evidência visual; SC4: Termo de Encerramento) are documented user-authorized scope reductions captured in 12-CONTEXT.md before implementation began — these are overrides, not gaps.

The `human_needed` status is driven by 2 behavior-dependent truths (SC2 and SC3) that require runtime Supabase state to verify the state-transition invariants, plus 4 UX/integration items that require the running application.

**REQUIREMENTS.md is stale** — it was last updated 2026-05-22 and covers only phases 1-3. Requirement IDs M6, M8, §4.5 appear only in ROADMAP.md (which is the authoritative contract for phases 4-12). This is a documentation gap, not an implementation gap.

---

_Verified: 2026-08-24_
_Verifier: Claude (gsd-verifier)_
