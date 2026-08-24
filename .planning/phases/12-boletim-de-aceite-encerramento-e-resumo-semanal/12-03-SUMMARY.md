---
phase: 12-boletim-de-aceite-encerramento-e-resumo-semanal
plan: "03"
subsystem: frontend
status: complete
tags:
  - aceite-tab
  - boletins
  - react
  - zero-className
  - typescript
dependency_graph:
  requires:
    - "12-01 (POST /boletins + GET /boletins/{project_id})"
    - "12-02 (PATCH /boletins/{id} + POST /boletins/resumo_semanal)"
  provides:
    - "AceiteTab.tsx — componente React com fluxo completo de boletins e resumo semanal"
    - "api.ts — BoletimResponse type + listBoletins + createBoletim + patchBoletim + gerarResumoSemanal"
    - "page.tsx — aba Aceite wired ao dashboard do projeto"
  affects:
    - "docudata-frontend/app/components/AceiteTab.tsx"
    - "docudata-frontend/app/lib/api.ts"
    - "docudata-frontend/app/projects/[id]/page.tsx"
tech_stack:
  added: []
  patterns:
    - "Zero className — todos os estilos via React.CSSProperties constantes (D-14)"
    - "ReactMarkdown para preview do boletim e resultado do resumo semanal"
    - "Props-based + internal fetch: AceiteTab recebe funcionalidades como prop e busca boletins internamente"
    - "Fluxo multi-step: seleção → createBoletim → preview → patchBoletim(enviado)"
key_files:
  created:
    - "docudata-frontend/app/components/AceiteTab.tsx"
  modified:
    - "docudata-frontend/app/lib/api.ts"
    - "docudata-frontend/app/projects/[id]/page.tsx"
decisions:
  - "AceiteTab busca listBoletins e listFuncionalidades internamente — reduz acoplamento com page.tsx (PlanningTab analog)"
  - "funcionalidades também passadas como props de page.tsx para evitar flash de conteúdo vazio na primeira renderização"
  - "page.tsx bootstrap expandido para incluir listFuncionalidades — funcionalidades disponíveis em todas as abas sem chamada extra"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-08-24"
  tasks_completed: 2
  tasks_total: 2
  commits: 2
estimate:
  tokens: 70000
actuals:
  tokens: 15000
  tasks: 2
  commits: 2
---

# Phase 12 Plan 03: Frontend AceiteTab + api.ts Wiring Summary

Frontend completo para boletins de aceite: api.ts com BoletimResponse type e 4 funções de fetch, AceiteTab.tsx com duas seções (Boletins + Resumo Semanal) em zero className, wired em page.tsx com nova aba Aceite.

## What Was Built

### Task 1 — api.ts (commit `3d1325d`)

- `FuncionalidadeResponse.status_cliente`: adicionado `"ajuste_pedido"` ao union type (RESEARCH Pitfall 1 / D-05)
- `BoletimResponse` interface exportada com todos os campos: `id`, `project_id`, `sprint_numero`, `funcionalidade_ids`, `status` (rascunho|enviado|aprovado|ajuste), `retorno_tipo`, `conteudo`, `criado_em`, `enviado_em`, `retorno_em`
- `listBoletins(projectId)`: GET `/boletins/{projectId}`
- `createBoletim(body)`: POST `/boletins`
- `patchBoletim(id, body)`: PATCH `/boletins/{id}`
- `gerarResumoSemanal(projectId)`: POST `/boletins/resumo_semanal`

### Task 2 — AceiteTab.tsx + page.tsx wiring (commit `d40b99d`)

**AceiteTab.tsx** (novo):
- Diretiva `"use client"`, imports React/useState/useEffect, ReactMarkdown, funções de api.ts
- `AceiteTabProps`: `{ projectId: string; funcionalidades: FuncionalidadeResponse[] }`
- 15 constantes CSSProperties fora do componente (zero className): `cardStyle`, `btnPrimary`, `btnSecondary`, `btnDanger`, `btnDisabled`, `badgeSuccess`, `badgeRascunho`, `badgeEnviado`, `badgeAprovado`, `badgeAjuste`, `badgeMudancaEscopo`, `markdownWrapStyle`, `checkboxRowStyle`, `errorTextStyle`, `selectStyle`, `dividerStyle`
- State: `boletins`, `funcs`, `loading`, `error`, `novoBoletimAberto`, `selectedFuncIds`, `boletimPreview`, `gerando`, `retornandoBoletimId`, `retornoTipo`, `resumoSemanal`, `gerandoResumo`
- Computed: `todasAprovadas = funcs.length > 0 && funcs.every(f => f.status_cliente === "aprovado")`
- **Badge encerramento** (D-04/D-13): `<div style={badgeSuccess}>Projeto encerrado — todas as funcionalidades aprovadas</div>` exibido quando `todasAprovadas === true`
- **Seção 1 Boletins**:
  - Lista de boletins existentes com status badge (cinza/azul/verde/vermelho) e badge "Mudança de Escopo Solicitada" em orange para `retorno_tipo === "mudanca_escopo"`
  - Fluxo rascunho → enviado: botão "Marcar como Enviado" chama `patchBoletim(id, {status: "enviado"})`
  - Fluxo enviado → aprovado: botão "Aprovado pelo Cliente" chama `patchBoletim(id, {status: "aprovado"})`, refresha funcionalidades também
  - Fluxo enviado → ajuste: botão "Ajuste Pedido" abre inline form com select de retorno_tipo + "Confirmar Ajuste" chama `patchBoletim(id, {status: "ajuste", retorno_tipo})`
  - Fluxo Novo Boletim: checkboxes de funcsConcluidas → "Gerar Boletim" → `createBoletim` → preview ReactMarkdown → "Marcar como Enviado" / "Descartar Rascunho"
- **Seção 2 Resumo Semanal**:
  - Botão "Gerar Resumo desta Semana" → `gerarResumoSemanal(projectId)` → exibe `result.content` via ReactMarkdown

**page.tsx** (4 edits):
- Import: `listFuncionalidades` e `FuncionalidadeResponse` adicionados ao bloco de imports de api.ts
- Import: `AceiteTab` adicionado após `PlanningTab`
- `TabId` union: `| "aceite"` adicionado
- `funcionalidades: FuncionalidadeResponse[]` state adicionado
- Bootstrap useEffect: `listFuncionalidades(id)` incluído no `Promise.all`, result setado em `setFuncionalidades`
- Tabs array: `{ id: "aceite", label: "Aceite" }` adicionado após planning
- Render condicional: `{activeTab === "aceite" && <AceiteTab projectId={id} funcionalidades={funcionalidades} />}` adicionado

## Verifications Passed

| Check | Result |
|-------|--------|
| npx tsc --noEmit | PASS — zero erros TypeScript |
| className count em AceiteTab.tsx | 0 |
| grep AceiteTab em page.tsx | 2 (import + uso) |
| grep ReactMarkdown em AceiteTab.tsx | 3 |
| grep todasAprovadas em AceiteTab.tsx | 2 |
| grep gerarResumoSemanal em AceiteTab.tsx | 2 |
| grep retorno_tipo em AceiteTab.tsx | 2 |
| grep ajuste_pedido em api.ts | 1 |
| grep BoletimResponse em api.ts | 4 |
| grep listBoletins\|createBoletim\|patchBoletim\|gerarResumoSemanal em api.ts | 4 |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Note on funcionalidades fetch:** AceiteTab recebe `funcionalidades` como props de page.tsx (conforme plano) E também chama `listFuncionalidades` internamente no useEffect para garantir dados frescos após mutations (patchBoletim atualiza status_cliente nas funcionalidades, então o refresh interno é necessário para refletir `todasAprovadas` corretamente sem recarregar a página). O estado inicial vem das props; o estado pós-mutação vem do refresh interno. Esse é um padrão mais robusto que apenas props estáticas.

## Security — Threat Mitigations Applied

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-12-09 | Aceito | Validação server-side é canônica; client-side é best-effort UX. Backend rejeita sequência inválida com 422 |
| T-12-10 | Mitigado | react-markdown ^9.x renderiza safe por default — sem dangerouslySetInnerHTML; mesmo padrão de PlanningTab.tsx |
| T-12-11 | Mitigado | AceiteTab recebe funcionalidades já filtradas por projectId via props de page.tsx; filtragem adicional por status="concluida" no client |

## Known Stubs

None — todos os componentes estão wired a dados reais via fetch functions em api.ts.

## Threat Flags

None — nenhuma nova surface de segurança introduzida além das já mapeadas no threat_model do plano.

## Commits

| Hash | Message |
|------|---------|
| 3d1325d | feat(12-03): api.ts — BoletimResponse type + FuncionalidadeResponse update + fetch functions |
| d40b99d | feat(12-03): AceiteTab.tsx (novo) + page.tsx wiring — zero className, duas seções, fluxo preview→confirmar, badge 100% aprovado |

## Self-Check: PASSED

- [x] `docudata-frontend/app/components/AceiteTab.tsx` exists
- [x] `docudata-frontend/app/lib/api.ts` updated with BoletimResponse + 4 functions + ajuste_pedido
- [x] `docudata-frontend/app/projects/[id]/page.tsx` updated with AceiteTab wiring
- [x] Commit 3d1325d exists (Task 1)
- [x] Commit d40b99d exists (Task 2)
- [x] TypeScript compila sem erros
- [x] Zero className em AceiteTab.tsx
