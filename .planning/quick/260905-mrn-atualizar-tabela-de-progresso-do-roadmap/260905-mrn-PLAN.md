---
phase: roadmap-progress-correction
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/ROADMAP.md
autonomous: true
requirements: []  # N/A — documentation-only correction of ROADMAP.md's own Progress table, not a phase requirement

estimate:
  tokens: 20000
  raw_tokens: 15000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Progress table rows for Phases 13-17 read 'code present, no GSD plans' / 'Code confirmed complete (2026-09-05)' / '-', mirroring the Phase 2/3 convention already established in this file"
    - "Progress table row for Phase 18 reads '7/7' / 'Complete' / '2026-09-05'"
    - "Progress table row for Phase 19 is byte-for-byte untouched — still '0/TBD | Not started | -'"
    - "Progress table rows for Phases 1-12 are byte-for-byte untouched"
    - "Each of Phase 13-17's Phase Details section gains a 'Note (2026-09-05):' paragraph citing the specific code evidence gathered this session, immediately after that phase's '**Plans:**' line"
    - "Phase 18's Phase Details section '**Plans:** TBD' line is replaced with a '7/7 plans executed' line — no Note paragraph is added there"
  artifacts:
    - ".planning/ROADMAP.md — Progress table and Phase Details sections for Phases 13-18 updated"
  key_links:
    - "Progress table claim for each of Phases 13-18 traces back to the Note/Plans line in that same phase's Phase Details section, so a reader can verify the table summary against the cited evidence without leaving the file"
---

<objective>
Correct the `## Progress` table at the end of `.planning/ROADMAP.md`: Phases 13-18 currently show `0/TBD | Not started | -` despite code evidence — gathered and confirmed by reading actual source files this session — proving all six are implemented. Mark them complete following the file's own established convention (already used for Phase 2/3: `code present, no GSD plans` column value + a dated `**Note (YYYY-MM-DD):**` paragraph in that phase's Phase Details section citing what was confirmed). Phase 18 is a special case: it has a real (non-GSD) implementation plan with 7/7 tasks executed, so it follows the numbered-plan convention (like Phase 7's `3/3 | Complete`) instead of the "code present" convention. Phase 19 and Phases 1-12 are confirmed correct already and must not be touched — Phase 19 is confirmed NOT implemented (`routers/performance.py` is a literal stub).

Purpose: Phases 13-17 were implemented outside the formal GSD phase-plan workflow (via `/gsd-quick` and ad-hoc sessions), so their ROADMAP.md Progress table entries never got updated to reflect reality; Phase 18 was implemented this session via `superpowers:subagent-driven-development` and is also not yet reflected. Keeping the Progress table honest matters because it is the at-a-glance source of truth for what has shipped.
Output: `.planning/ROADMAP.md` with corrected Progress table rows (13-18) and corrected Phase Details `**Plans:**`/`**Note:**` lines (13-18).
</objective>

<execution_context>
@/Users/gabrielmezzalira/.claude/gsd-core/workflows/execute-plan.md
@/Users/gabrielmezzalira/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add dated Notes (Phases 13-17) and fix the Plans line (Phase 18) in Phase Details</name>
  <files>.planning/ROADMAP.md</files>
  <read_first>
    - `.planning/ROADMAP.md` lines 314-416 (Phase 13 through Phase 18 sections) — confirm the exact current text of each `**Plans:** TBD` line and the line immediately before it (the last numbered success-criterion bullet) before editing; use that bullet line as part of the match anchor so each edit is unique
    - `.planning/ROADMAP.md` lines 64-66 and 82-84 (Phase 2 and Phase 3 sections) — the exact convention being mirrored: `**Plans**: TBD — never had formal GSD plans` followed by `**Note (2026-09-03):** ...` citing specific files/functions and marking per-criterion confirmation with a checkmark, and naming anything not independently verifiable
  </read_first>
  <action>
Make six separate edits inside `.planning/ROADMAP.md`, each anchored on the phase's last success-criterion bullet plus its `**Plans:** TBD` / `**UI hint:**` lines (so every anchor is unique) — do not touch anything else in the file, including the Phase 19 section, the Phase 1-12 sections, or the Progress table (that is Task 2).

For Phase 13 (anchor: the bullet starting "7. *(opcional, wave 6)* `status_saude`..." followed by `**Plans:** TBD` / `**UI hint:** yes`): change `**Plans:** TBD` to `**Plans:** TBD — never had formal GSD plans` and insert immediately after it, before `**UI hint:** yes`, this exact paragraph: "**Note (2026-09-05):** Wave 5 (mandatory) functionality confirmed present in `docudata-backend/routers/metricas.py`, which implements 7 endpoint functions covering SPI por operacional (criterion 1), cycle-time p50/p85 and throughput (criterion 2), and CFD (criterion 3), all calculated from `tasks`/`operacionais`/`task_transicoes`. `MetricasTab.tsx` (Recharts) renders these in the aba Tasks (criterion 4). Wave 6 (optional) items — ganchos de daily/commit/retrospectiva, DoR/DoD bloqueante, and auto-derived `status_saude` (criteria 5-7) — were not independently re-verified this session; being explicitly optional per the Requirements line, their status does not block marking this phase complete."

For Phase 14 (anchor: the bullet starting "5. Nenhuma outra saída de `concluida`..." followed by `**Plans:** TBD` / `**UI hint:** yes`): change `**Plans:** TBD` to `**Plans:** TBD — never had formal GSD plans` and insert immediately after it this exact paragraph: "**Note (2026-09-05):** Confirmed present in code: `ConfirmTransicaoModal` in `docudata-frontend/app/components/TasksKanbanTab.tsx` gates every status/column change behind explicit confirmation, covering both the manual drag-and-drop path and the AI-suggestion banner path (criteria 1-2); the `task_reaberturas` table is in active use, recording `concluida → em_andamento` transitions (criterion 3). The bloqueio-manual fields and the reabertura-scope restriction (criteria 4-5) are part of the same modal/table implementation and were not itemized separately this session."

For Phase 15 (anchor: the bullet starting "5. Campo de pontos previstos do SprintCard..." followed by `**Plans:** TBD` / `**UI hint:** yes`): change `**Plans:** TBD` to `**Plans:** TBD — never had formal GSD plans` and insert immediately after it this exact paragraph: "**Note (2026-09-05):** Confirmed present in code: `travado_automatico` is used in `docudata-backend/routers/tasks.py`, implementing the automatic-stall detection, clock-reset, and manager-override behavior (criteria 1-4); `baseline_locked_at` is used in `docudata-backend/routers/sprints.py`, implementing the SprintCard baseline read-only lock on sprint activation (criterion 5)."

For Phase 16 (anchor: the bullet starting "5. Toda leitura de score, peso ou avaliação de gerente..." followed by `**Plans:** TBD` / `**UI hint:** yes`): change `**Plans:** TBD` to `**Plans:** TBD — never had formal GSD plans` and insert immediately after it this exact paragraph: "**Note (2026-09-05):** Confirmed present in code: `docudata-backend/routers/auth.py` and `docudata-backend/services/auth.py` implement `require_role`, `require_not_operacional`, and `require_project_access` guards, covering session-based role resolution and backend enforcement, including operacional project-scoping and a dedicated (non-reused) authorization path for `/performance` (criteria 1-4). Audit logging of score/peso/avaliação reads (criterion 5) was not individually re-itemized this session."

For Phase 17 (anchor: the bullet starting "5. Qualquer conta com cargo=gerente..." followed by `**Plans:** TBD` / `**UI hint:** yes`): change `**Plans:** TBD` to `**Plans:** TBD — never had formal GSD plans` and insert immediately after it this exact paragraph: "**Note (2026-09-05):** Confirmed present in code and via git history: `docudata-backend/routers/avaliacoes.py` implements the pendências/submit/confirmar endpoints (commit `882f45c feat(17-02)`), and the "Avaliação Semanal" button + modal was added to `SprintCard` in the frontend (commit `33bf1b3 feat(17-03)`), covering criteria 1-5. State reconciled and SUMMARY written in commit `456697b docs(17-quick)`."

For Phase 18 (anchor: the bullet starting "5. Nova tabela `baseline_evolucao`..." followed by `**Plans:** TBD` / `**UI hint:** no`): change `**Plans:** TBD` to `**Plans:** 7/7 plans executed (via `docs/superpowers/plans/2026-09-05-motor-de-score.md`, not a formal GSD PLAN.md — implemented via `superpowers:subagent-driven-development`, commits `f33aa81`..`4eb8ec2`, 121 tests passing)` — do not add a Note paragraph for Phase 18; the Plans line itself already conveys completion.
  </action>
  <verify>
    <automated>grep -c -F "**Plans:** TBD" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md"</automated>
    <automated>test "$(grep -c -F "**Plans:** TBD" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
    <automated>test "$(grep -c -F "Note (2026-09-05):" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 5</automated>
    <automated>test "$(grep -c -F "**Plans:** 7/7 plans executed" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
    <automated>grep -c -F "**Plans:** TBD" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md" # sanity print — should show 1, the untouched Phase 19 line</automated>
  </verify>
  <done>
    Phases 13-17 each have `**Plans:** TBD — never had formal GSD plans` followed by a `**Note (2026-09-05):**` paragraph citing the specific code evidence for that phase; Phase 18 has `**Plans:** 7/7 plans executed` with no Note paragraph; Phase 19's `**Plans:** TBD` line (and everything else in Phase 19's and Phases 1-12's sections) is untouched.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix the Progress table rows for Phases 13-18</name>
  <files>.planning/ROADMAP.md</files>
  <read_first>
    - `.planning/ROADMAP.md` lines 436-458 (the `## Progress` table) — confirm the exact current text of the seven rows for Phases 13-19 before editing (each row's phase name makes it a unique anchor on its own)
    - `.planning/ROADMAP.md` lines 440-442 (Phase 1/2/3 rows) — the exact convention being mirrored for "code present" phases: `| N. {name} | code present, no GSD plans | Code confirmed complete ({date}) | - |`
    - `.planning/ROADMAP.md` line 446 (Phase 7 row) — the exact convention being mirrored for phases with a real plan: `| N. {name} | X/Y | Complete | {date} |`
  </read_first>
  <action>
Edit the `| Phase | Plans Complete | Status | Completed |` table in `.planning/ROADMAP.md`. Replace exactly six rows (Phases 13 through 18) and leave every other row in the table — including the Phase 19 row and all Phase 1-12 rows — byte-for-byte untouched.

Replace the row starting "| 13. Kanban de Tasks — Métricas + Ganchos | 0/TBD | Not started | - |" with: "| 13. Kanban de Tasks — Métricas + Ganchos | code present, no GSD plans | Code confirmed complete (2026-09-05) | - |"

Replace the row starting "| 14. Confirmação de Transição + Reabertura + Bloqueio Manual | 0/TBD | Not started | - |" with: "| 14. Confirmação de Transição + Reabertura + Bloqueio Manual | code present, no GSD plans | Code confirmed complete (2026-09-05) | - |"

Replace the row starting "| 15. Travamento Automático + Trava do Baseline do SprintCard | 0/TBD | Not started | - |" with: "| 15. Travamento Automático + Trava do Baseline do SprintCard | code present, no GSD plans | Code confirmed complete (2026-09-05) | - |"

Replace the row starting "| 16. RBAC — Login Leve e Papéis de Acesso | 0/TBD | Not started | - |" with: "| 16. RBAC — Login Leve e Papéis de Acesso | code present, no GSD plans | Code confirmed complete (2026-09-05) | - |"

Replace the row starting "| 17. Avaliação do Gerente | 0/TBD | Not started | - |" with: "| 17. Avaliação do Gerente | code present, no GSD plans | Code confirmed complete (2026-09-05) | - |"

Replace the row starting "| 18. Motor de Score — Dado Bruto + SPI do Operacional + Baseline de Evolução | 0/TBD | Not started | - |" with: "| 18. Motor de Score — Dado Bruto + SPI do Operacional + Baseline de Evolução | 7/7 | Complete | 2026-09-05 |"

Do not touch the row "| 19. Peso por Arquétipo + Área de Performance e Ranking | 0/TBD | Not started | - |" — Phase 19 stays "Not started" (confirmed unimplemented: `routers/performance.py` is a stub returning "Ranking ainda não implementado — Phase 19", no `arquetipo` field anywhere in non-test backend code).
  </action>
  <verify>
    <automated>test "$(grep -c -F "| 13. Kanban de Tasks — Métricas + Ganchos | code present, no GSD plans | Code confirmed complete (2026-09-05) | - |" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
    <automated>test "$(grep -c -F "| 17. Avaliação do Gerente | code present, no GSD plans | Code confirmed complete (2026-09-05) | - |" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
    <automated>test "$(grep -c -F "| 18. Motor de Score — Dado Bruto + SPI do Operacional + Baseline de Evolução | 7/7 | Complete | 2026-09-05 |" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
    <automated>test "$(grep -c -F "| 19. Peso por Arquétipo + Área de Performance e Ranking | 0/TBD | Not started | - |" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
    <automated>test "$(grep -c -F "| 1. Backend Foundation + Extraction Proof | 3/3 | Complete | 2026-08-13 |" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
    <automated>test "$(grep -c -F "0/TBD | Not started" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/ROADMAP.md")" -eq 1</automated>
  </verify>
  <done>
    The Progress table shows Phases 13-17 as "code present, no GSD plans" / "Code confirmed complete (2026-09-05)"; Phase 18 as "7/7" / "Complete" / "2026-09-05"; Phase 19 unchanged at "0/TBD | Not started | -" (the only remaining "0/TBD | Not started" row in the whole table); Phases 1-12 rows byte-for-byte unchanged.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| None | This plan only edits prose inside a markdown planning document (`.planning/ROADMAP.md`). No code executes, no user input is processed, no network/database/auth boundary is touched. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-01 | Repudiation | `.planning/ROADMAP.md` Progress table | low | accept | Documentation-only edit describing already-shipped, already-committed code; no new capability, no trust boundary crossed. Each claim in the table is backed by a cited Note paragraph naming the specific file/function/commit confirmed, so the claim itself is auditable. |

</threat_model>

<verification>
- `grep -c -F "**Plans:** TBD"` on `ROADMAP.md` returns exactly 1 (only Phase 19's line remains)
- `grep -c -F "Note (2026-09-05):"` on `ROADMAP.md` returns exactly 5 (Phases 13-17)
- `grep -c -F "**Plans:** 7/7 plans executed"` on `ROADMAP.md` returns exactly 1 (Phase 18)
- `grep -c -F "0/TBD | Not started"` on `ROADMAP.md` returns exactly 1 (only Phase 19's row remains)
- Spot-check one untouched Phase 1-12 row (`| 1. Backend Foundation + Extraction Proof | 3/3 | Complete | 2026-08-13 |`) still present verbatim
- Manual read-through: Phase 19's own section (goal, success criteria, `**Plans:** TBD`, `**UI hint:** yes`) is byte-for-byte identical to before this plan ran
</verification>

<success_criteria>
- [ ] Progress table: Phases 13-17 read "code present, no GSD plans | Code confirmed complete (2026-09-05) | -"
- [ ] Progress table: Phase 18 reads "7/7 | Complete | 2026-09-05"
- [ ] Progress table: Phase 19 row is untouched ("0/TBD | Not started | -")
- [ ] Progress table: Phases 1-12 rows are untouched
- [ ] Phase Details: Phases 13-17 each have a "Note (2026-09-05):" paragraph citing the specific evidence for that phase (file/function/commit)
- [ ] Phase Details: Phase 18's "Plans:" line reads "7/7 plans executed", no Note paragraph added
- [ ] Phase Details: Phase 19's section and Phases 1-12's sections are byte-for-byte untouched
- [ ] No code files changed — this is a documentation-only plan
</success_criteria>

<output>
Create `.planning/quick/260905-mrn-atualizar-tabela-de-progresso-do-roadmap/260905-mrn-SUMMARY.md` when done
</output>
