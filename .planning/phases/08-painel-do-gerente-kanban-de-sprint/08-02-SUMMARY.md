---
id: "08-02"
phase: "08-painel-do-gerente-kanban-de-sprint"
plan: "02"
status: complete
completed_at: "2026-08-22T00:00:00Z"
---

# Plan 08-02 Summary — Expansion: Full Visual Polish

## What Was Built

`PainelTab.tsx` fully implements all polished visual states per CONTEXT.md decisions:

**Bloco A (D-02, D-03, D-05):**
- `sem_dados: true` → grey placeholder "Sem dados de contrato" + "Ir para Configurações" button calling `onNavigateToConfig?.()` → page.tsx wires `setActiveTab("config")`
- `sem_dados: false` → three percentage bars (prazo consumido, escopo concluído, aprovado pelo cliente) + orange desvio badge when `desvio_detectado` is true

**Bloco B (D-11, D-12):**
- Three sub-sections: Travadas (>7 dias in em_andamento), Aguardando cliente (>5 d.u. enviado), Em ajuste
- Each shows funcionalidade titles with colored count/day badges or empty state text

**Bloco C (D-13, D-14, D-15):**
- WIP, throughput/semana, cycle time p50 and p85
- Null values displayed as "—" character; zero concluidas shows informational message

**Bloco D — accordion (D-04):**
- `expandedFase` state controls which phase row is expanded
- Clicking "▼ ver detalhe" expands per-funcionalidade time list; clicking "▲ fechar" collapses
- Empty fases_resumo shows muted placeholder text

**Kanban (D-06, D-07, D-08, D-09):**
- Sprint dropdown defaults to `Math.max(...sprints.map(s => s.numero))`
- 3 columns: Planejado (nao_iniciada), Em andamento (em_andamento + em_ajuste), Concluído (concluida)
- Each card shows titulo + prioridade chip (colored by level) + sprint badges grouped by `id_funcional` across all project funcionalidades (D-08 multi-sprint logic)
- Empty columns show "Nenhuma funcionalidade" placeholder

## Key Decisions

- Full polished layout was implemented directly in Wave 1 (08-01) rather than a minimal stub, so Wave 2 validates rather than rewrites. All 08-02 must-haves were already satisfied.
- No new files created — only `PainelTab.tsx` modified (as declared in plan frontmatter).
- Zero `className` attributes — all styling via inline `style={{...}}` objects.

## Artifacts Modified

- `docudata-frontend/app/components/PainelTab.tsx` (623 lines, full polished implementation)

## Self-Check: PASSED

- `npx tsc --noEmit` → no errors
- `grep -c "className=" PainelTab.tsx` → 0
- "Sem dados de contrato" present ✓
- "Desvio" badge present with `desvio_detectado` check ✓
- "Travadas" + "Aguardando cliente" + "Em ajuste" sub-sections ✓
- `expandedFase` state + "ver detalhe" toggle ✓
- "Planejado" + "Em andamento" + "Concluído" columns ✓
- `Math.max` sprint default ✓
- `sprint_alvo === String(sprintSelecionada)` filter ✓
- `id_funcional` grouping for D-08 multi-sprint badges ✓
- `nao_iniciada` filter for planejado column ✓
- 623 lines (> 150 required) ✓
