---
phase: 04-template-v2-github-integration
plan: "04-02"
subsystem: frontend
tags: [frontend, modais, planning, review, retrospectiva, carry-over]
dependency_graph:
  requires: []
  provides: [FORM-01, FORM-02]
  affects:
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/components/SprintDocModal.tsx
    - docudata-frontend/app/components/RetroModal.tsx
    - docudata-frontend/app/projects/[id]/page.tsx
tech_stack:
  added: []
  patterns:
    - "FormData with optional field appending pattern"
    - "initialCarryOver prop + useEffect prefill for cross-sprint data flow"
key_files:
  modified:
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/components/SprintDocModal.tsx
    - docudata-frontend/app/components/RetroModal.tsx
    - docudata-frontend/app/projects/[id]/page.tsx
decisions:
  - "initialCarryOver prop on SprintDocModal over callback: simpler, avoids prop drilling function"
  - "setCarryOver in useEffect open branch: ensures prefill re-triggers on each modal open"
  - "pedidoForaEscopoStatus as 2nd param of onSubmit in RetroModal: keeps signature minimal and typed"
metrics:
  duration: "3m"
  completed_date: "2026-07-28"
  tasks_completed: 4
  tasks_total: 4
---

# Phase 04 Plan 02: Frontend — Modais Atualizados Summary

**One-liner:** Modais de Planning, Review e Retro atualizados com 9 novos campos do template CITi v2, carry-over pré-preenchido da sprint anterior, e submitRetrospectiva dedicado em api.ts.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Update api.ts — submitPlanning/Review new fields + submitRetrospectiva + listIngestionsBySprint | 5f1f8f8 | api.ts |
| 2 | SprintDocModal planning section — 7 new fields with state/JSX/reset | 21eef02 | SprintDocModal.tsx |
| 3 | SprintDocModal review section — 3 new fields + sinalSatisfacao dropdown; RetroModal pedidoForaEscopoStatus | d680b63 | SprintDocModal.tsx, RetroModal.tsx |
| 4 | page.tsx — submitRetrospectiva, carryOverPrefill state, fetchCarryOver, initialCarryOver prop | 0adf4ff | page.tsx, SprintDocModal.tsx |

## What Was Built

### api.ts
- `submitPlanning` extended with: `squad`, `periodoInicio`, `periodoFim`, `horasDisponiveis`, `horasEstimadas`, `dependenciasCliente`, `carryOver` — all optional, appended to FormData only when defined
- `submitReview` extended with: `percepcaoCliente`, `sinalSatisfacao`, `pedidosForaEscopo` — all optional
- New `submitRetrospectiva` function calling `_postSprintDoc("retrospectiva", form)` with `observacoes`, `pedidoForaEscopoStatus`, `anexo`
- New `listIngestionsBySprint(projetoId, sprint)` helper for carry-over fetch

### SprintDocModal.tsx
- Planning: Squad (input), Período (2 date inputs inline), Horas disponíveis/estimadas (2 number inputs inline), Dependências do cliente (textarea), Carry-over (textarea, pré-preenchida)
- Review: Percepção do cliente (textarea), Sinal de satisfação (select 🟢/🟡/🔴), Pedidos fora do escopo (textarea)
- `initialCarryOver?: string` prop — pre-fills carry-over via useEffect when modal opens

### RetroModal.tsx
- `pedidoForaEscopoStatus` state + textarea
- `onSubmit` signature updated to 3 params: `(observacoes, pedidoForaEscopoStatus, file)`

### page.tsx
- Imports `submitRetrospectiva` and `listIngestionsBySprint`
- `carryOverPrefill` state
- `fetchCarryOver(sprintNumero)` — fetches review ingestion from sprint N-1, extracts `proximos_passos` or `campos_review.itens_proxima_sprint`
- `handleRetroSubmit` rewritten to call `submitRetrospectiva` (was `generateDoc`)
- `onOpenSprintDoc` calls `fetchCarryOver(n)` when `tipo === "planning"`
- SprintDocModal receives `initialCarryOver={carryOverPrefill}`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no hardcoded placeholder values. The carry-over field defaults to empty string gracefully when no prior review exists (fetchCarryOver catches errors and sets `""`).

## Threat Flags

None — no new network endpoints or auth paths introduced. All changes are frontend-only, adding fields to existing FormData calls.

## Self-Check: PASSED

- [x] SprintDocModal.tsx modified and committed (21eef02, d680b63, 0adf4ff)
- [x] RetroModal.tsx modified and committed (d680b63)
- [x] api.ts modified and committed (5f1f8f8)
- [x] page.tsx modified and committed (0adf4ff)
- [x] All 4 commits exist in git log
- [x] No STATE.md or ROADMAP.md modifications
