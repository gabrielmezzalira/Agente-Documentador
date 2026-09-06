# Synthesis Summary — Doc Ingest (merge mode, RE-SYNTHESIS run)

**Run scope:** `.planning/intel/classifications/` (1 active classification file — v3 revision; prior v2 classification moved to `classifications/superseded/` and excluded from this run entirely)

**This run fully overwrites** the stale v2-derived content in `decisions.md`, `requirements.md`, `constraints.md`, `context.md`, and this file — v3 supersedes v2 for the "Hub de Projetos" SDD lineage. No v2 content was merged or averaged with v3 content.

## Doc counts by type

| Type | Count | Files |
|---|---|---|
| ADR | 0 | — |
| SPEC | 1 | SDD-hub-de-projetos-v3.md |
| PRD | 0 | — |
| DOC | 0 | — |
| UNKNOWN | 0 | — |

## Decisions locked

0 — no ADR-type documents in this batch. `decisions.md` has no entries.

## Requirements extracted

0 — no PRD-type documents in this batch. `requirements.md` has no entries. (The incoming SPEC's own "Definition of Done" section was preserved as a constraint, not split into REQ- entries — see `constraints.md`.)

## Constraints

16 entries, all from the single active SPEC document (v3), all type SPEC source:

- **schema** (6): Parte 2 (task_reaberturas), Parte 3 (bloqueado_manual fields), Parte 5 (avaliacoes_gerente), Parte 7 (baseline_evolucao), Parte 10 (pesos_arquetipo — narrowed scope in v3), Parte 11 (pontuacao_operacional_sprint — new raw-data layer in v3)
- **protocol** (3): Parte 1 (confirmação de transição), Parte 4 (travamento automático), Parte 8 (trava do baseline do SprintCard)
- **nfr** (7): Parte 0 (rename), Parte 6 (RBAC — expanded in v3 with /performance route), Parte 9 (SPI do Operacional — method changed in v3), Parte 12 (Área de Performance e Ranking — new section in v3), Requisitos não funcionais, Critérios de aceite (DoD — SPI line overwritten), Decisões em aberto (4 of 5 resolved in v3, 1 new carry-over flag)

Full detail in `.planning/intel/constraints.md`. Every entry that changed from v2 carries an explicit `change from v2:` line documenting what moved, was resolved, or was overwritten.

## Context topics

0 — no DOC-type documents in this batch. `context.md` has no entries.

## Conflicts

- **Blockers:** 0
- **Competing variants:** 0 (v2 vs v3 is NOT treated as competing — v3 supersedes v2 per explicit instruction; only v3 is synthesized)
- **Warnings requiring explicit user decision:** 2
  1. Rename scope — "DocuData" → "Hub de Projetos" vs. current PROJECT.md identity, re-verified: now 117 files affected (up from 105), still unresolved
  2. Two open-decision items needing Gabriel's explicit sign-off: (a) v2's mid-period task-reassignment point-attribution question, absent from v3 with unclear status; (b) v3's own still-open item on archetype weight differentiation post-CSAT
- **Auto-resolved / info:** 3
  1. SPI do Operacional method change (v2→v3) — explicit author decision, overwritten not merged
  2. Archetype selection rule relocated from Parte 10 to Parte 12 with a different criterion (most sprint-rows vs. most points)
  3. Parte 1 / Parte 4 re-verified compatible with the Phase 7 "marcação manual soberana" principle — unchanged from prior report

See `.planning/INGEST-CONFLICTS.md` for full detail with sources.

## Pointers

- Decisions: `.planning/intel/decisions.md`
- Requirements: `.planning/intel/requirements.md`
- Constraints: `.planning/intel/constraints.md`
- Context: `.planning/intel/context.md`
- Conflicts report: `.planning/INGEST-CONFLICTS.md`

## Note for gsd-roadmapper

This batch contains **no PRD/ADR content** — it is a pure technical SPEC, now at v3. Key points carried forward from v3 that affect roadmap/requirements generation:

1. **SPI do Operacional calculation method changed** (Parte 9/11/12) — sum within project across sprints, then simple average across projects. Do NOT use the old v2 method (sum across all projects, divide once) anywhere downstream.
2. **New raw-data layer** — `pontuacao_operacional_sprint`, one row per operacional per sprint per project, locked at sprint close. This did not exist in v2 and needs its own migration/implementation step.
3. **New ranking module scope** — Parte 12 "Área de Performance e Ranking" is substantial new surface area: `/performance` route, count-based windows (1/2/4 sprint-rows), per-window two-layer aggregation, archetype-by-window selection with tie-break, top-performer announcement. Size this as real scope, not a rename of v2's old Parte 11.
4. **4 of 5 v2 open items are now resolved** in v3 — see `constraints.md` → "Decisões em aberto" for the resolutions. Only the archetype-weight-differentiation question remains genuinely open; do not silently resolve it during roadmap/requirements generation.
5. **One v2 open item (mid-period task reassignment point attribution) has unclear status in v3** — neither resolved nor restated as open. Flag for Gabriel before committing to a specific behavior in implementation.
6. The rename WARNING (Parte 0) is unchanged in substance from the prior report and must still be resolved by the user (or explicitly deferred) before `PROJECT.md`'s name field is touched. File count affected has grown to ~117.

---
*Synthesized by gsd-doc-synthesizer — merge run (re-synthesis, v3 supersedes v2 entirely).*
