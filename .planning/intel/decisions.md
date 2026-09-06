# Decisions (from ADR-type documents)

No ADR-type documents were present in this ingestion batch (`CLASSIFICATIONS_DIR` contained one classified document, type `SPEC`). No entries extracted from documents.

## Decisions from Gabriel (Líder), resolving INGEST-CONFLICTS.md warnings — 2026-09-02

These three decisions were given directly by Gabriel in response to the two WARNINGs raised after v3 synthesis (see `.planning/INGEST-CONFLICTS.md`). They are locked and should be treated as ADR-equivalent for downstream planning (`gsd-roadmapper`, `gsd-plan-phase`).

1. **Rename (SDD Parte 0) — DEFERRED, not rejected.**
   Decision: do not apply the DocuData/Agente Documentador → Hub de Projetos rename now. Proceed with Partes 1-12 of the SDD under the current name. Plan a dedicated future phase for the rename (folder renames `docudata-backend/`/`docudata-frontend/`, ~117 files, `package.json`, PROJECT.md identity) once the rest of the SDD has shipped and stabilized.
   Applies to: `.planning/ROADMAP.md` phase planning — do not create a rename phase in this ingest's phase additions; note it as a deferred/backlog item instead.

2. **Task reassignment mid-period (v2 Parte 9 open item, unaddressed in v3) — RESOLVED.**
   Decision, Gabriel's exact words: "os pontos previstos daquele operacional é recalculado."
   Interpretation for implementation: when a task is reassigned from one operacional to another mid-sprint, `entrega_pontos_alocados` (allocated/previsto points, Parte 11's `pontuacao_operacional_sprint` table) is recalculated for the affected operacional(s) at the time of reassignment — not left as "todos os pontos vão para quem está com a task no fechamento" (the ambiguous default v2 had flagged as an open question). This must be reflected in the SPI/Entrega raw-data-layer design (Parte 9 + Parte 11) when planning/implementing that phase — confirm the exact recalculation mechanics (e.g., does the original assignee's `entrega_pontos_alocados` decrease by the task's points, and the new assignee's increase by the same amount, at the moment of reassignment) during phase planning, since Gabriel's answer establishes the *principle* (recalculate, don't leave stale) but not the full mechanical spec.
   Applies to: Parte 9/11 phase — SPI do Operacional + `pontuacao_operacional_sprint`.

3. **Peso diferenciado por arquétipo (SDD Parte 10 open item) — RESOLVED, closed permanently.**
   Decision, Gabriel's exact words: "pesos iguais, nao precisa ter essa divisao."
   Interpretation: no objective data will differentiate weights between Dev/Consultoria/Agente IA archetypes — this is not "keep equal for now, revisit later," it is a closed decision that archetype-based weight differentiation is not needed. The `pesos_arquetipo` table and `arquetipo` field remain implemented as designed (for extensibility / to match the SDD's data model) but no further design work is needed to find a CSAT replacement or other differentiator. Phase planning for Parte 10/12 should not block on this question.
   Applies to: Parte 10/12 phase — Peso por Arquétipo + Área de Performance e Ranking.

## Decisions from Gabriel (Líder), resolving ROUTE-MERGE-DRAFT.md risks R1/R6/R5 — 2026-09-02

4. **RBAC identity mechanism (ROUTE-MERGE-DRAFT.md risk R1) — RESOLVED.**
   Decision, Gabriel's exact words: "Login leve por papel/pessoa. Usuário+senha simples: uma conta por Líder/Gerente/Operacional. Eu vou falar qual email é pra cada pessoa e sua função, então quando ela for logar, vai ser relacionado o seu cargo, que vai ter os acessos, independente se ele é gerente de algum projeto ou não. A única restrição de projeto é de operacional, só vão ter acesso aos projetos que estão vinculados."
   Interpretation for implementation (orchestrator's best reading — flagged for the RBAC phase planner to re-confirm with Gabriel if it looks wrong once planned in detail): a `pessoa` table (email, nome, cargo ∈ {lider, gerente, operacional}) is populated manually by Gabriel; login is simple email+password; **cargo alone** determines access level (role-based, not project-scoped) for Líder and Gerente — **any** account with cargo=gerente sees manager-level data (score inputs, evaluations, etc.) on **any** project, not just ones it "manages." The **only** project-level restriction applies to Operacional: an account with cargo=operacional only accesses projects it is linked to as an operacional (this already exists today — operacional is already a per-project entity per `.continue-here.md`). **This resolves ROUTE-MERGE-DRAFT.md risk R2 without needing a squad↔gerente link — do not build that.** This also loosens the SDD's original Parte 5/6 wording ("gerente só vê e preenche avaliação dos operacionais do próprio squad"): treat it as — any gerente account can evaluate operacionais on any project it has access to (no "own squad" backend enforcement), unless detailed planning of the RBAC phase (Phase 16) surfaces a reason to reconfirm with Gabriel before implementing.
   Applies to: Phase 16 (RBAC — Login Leve e Papéis de Acesso), Phase 17 (Avaliação do Gerente — squad restriction removed from success criteria).

5. **Reconciling the loose `.continue-here.md` "Kanban de Tasks/SPI" thread (ROUTE-MERGE-DRAFT.md risk R6) — RESOLVED.**
   Decision, Gabriel's exact words: "Criar fase para o continue-here.md primeiro."
   Interpretation: the pending waves 5-6 of `.planning/.continue-here.md` (waves 1-4b already complete and committed) get their own phase in `ROADMAP.md`, **placed before** the SDD v3 phases. This became **Phase 13** ("Kanban de Tasks: Métricas + Ganchos"), pushing the SDD v3 phases to **14-19** (Confirmação/Reabertura/Bloqueio, Alertas, RBAC, Avaliação do Gerente, Motor de Score, Performance/Ranking — see `.planning/ROADMAP.md`).
   Applies to: `.planning/ROADMAP.md` phase numbering (Phases 13-19 applied 2026-09-02).

**Granularity (ROUTE-MERGE-DRAFT.md risk R5):** Gabriel confirmed "Manter as 6 fases (recomendado)" — the SDD v3 phases keep the 6-phase granularity from the draft (only the numbering shifted by +1 to make room for Phase 13).

---
*Synthesized by gsd-doc-synthesizer — merge run (re-synthesis, v3 supersedes v2). Gabriel decisions appended by orchestrator after the conflict gate — 2026-09-02. Decisions #4-#5 appended after ROUTE-MERGE-DRAFT.md review — 2026-09-02, applied to ROADMAP.md/REQUIREMENTS.md/PROJECT.md same day.*
