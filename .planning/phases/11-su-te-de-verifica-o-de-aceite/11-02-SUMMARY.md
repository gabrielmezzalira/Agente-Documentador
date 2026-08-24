---
phase: 11-su-te-de-verifica-o-de-aceite
plan: 02
subsystem: api
tags: [fastapi, github-actions, nextjs, painel, aceite, kanban]
requires:
  - phase: 11-su-te-de-verifica-o-de-aceite
    plan: 01
    provides: POST /ingest/aceite endpoint + execucoes_aceite table
provides:
  - aceite_agent.py (GitHub Actions agent, stdlib only)
  - aceite.yml (repository_dispatch workflow)
  - cobertura_aceite metric in GET /projects/{id}/painel
  - Bloco B sub-seção Cobertura de Aceite
  - badge ⚠ aceite no KanbanCard (zero className)
affects: []
actuals:
  tokens: 72000
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [zero className inline style para novos elementos UI]
key-files:
  created: [docudata-backend/hooks/aceite_agent.py, docudata-backend/hooks/aceite.yml]
  modified: [docudata-backend/routers/painel.py, docudata-frontend/app/lib/api.ts, docudata-frontend/app/components/PainelTab.tsx]
key-decisions:
  - "aceite_agent.py stdlib only — sem dependencias externas no repo do projeto"
  - "continue-on-error: true em aceite.yml — aceite nunca quebra CI do projeto"
  - "cobertura_aceite no response root de GET /painel — separado de bloco_a.pct_escopo_concluido"
  - "getExecucoesAceite em paralelo no Promise.all — nao bloqueia carregamento do painel"
requirements-completed:
  - "M5 (§5)"
  - "§4.4 (ExecucaoAceite)"
coverage:
  - id: D1
    description: "aceite_agent.py parseia + usa apenas stdlib"
    verification:
      - kind: other
        ref: "python3 ast.parse + grep stdlib"
        status: pass
    human_judgment: false
  - id: D2
    description: "aceite.yml tem repository_dispatch + continue-on-error: true x2"
    verification:
      - kind: other
        ref: "grep repository_dispatch + continue-on-error"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /painel retorna cobertura_aceite no response root"
    human_judgment: true
    rationale: "Requer Supabase com dados de aceite para testar end-to-end"
  - id: D4
    description: "Badge ⚠ aceite no Kanban com zero className"
    human_judgment: true
    rationale: "Requer browser + funcionalidades concluidas com gates falhando para verificar visualmente"
  - id: D5
    description: "TypeScript compila sem erros nos arquivos modificados"
    verification:
      - kind: other
        ref: "npx tsc --noEmit"
        status: pass
    human_judgment: false
duration: 32min
completed: 2026-08-24
status: complete
---

# Phase 11 Plan 02: Expansion — Agente GitHub Actions + Painel Aceite Summary

**Agente GitHub Actions (aceite_agent.py + aceite.yml) via repository_dispatch + expansão do Painel com cobertura_aceite no backend e badge Kanban + sub-seção Bloco B no frontend.**

## Performance

- Duration: ~32min
- Tasks completed: 3/3
- Commits: 3
- Files created: 2 (aceite_agent.py, aceite.yml)
- Files modified: 3 (painel.py, api.ts, PainelTab.tsx)

## Accomplishments

### Task 1 — aceite_agent.py + aceite.yml (commit 98ded8c)

**aceite_agent.py** — Script Python stdlib only:
- Imports: `os, subprocess, json, urllib.request, urllib.error` — zero dependências externas
- Guard: `SystemExit(0)` se `DOCUDATA_API_URL` ou `FUNCIONALIDADE_ID` ausentes
- `run_cmd(cmd)` — subprocess com `timeout=120`, retorna `(returncode, stdout+stderr)`
- `gate_resultado(cmd)` — mapeia para `passou | falhou | erro | sem_cobertura`
- `commit_sha` via `git rev-parse HEAD` do repo do projeto (não GITHUB_SHA — per RESEARCH Pitfall 3)
- Heurística de runtime: `has_package_json` / `has_requirements`
- 5 gates fixos (per D-04): `build`, `testes_unitarios`, `e2e`, `acessibilidade`, `performance`
- Gate `e2e`: `sem_cobertura` se `testes_e2e` vazio; else `gate_resultado(["python", "-m", "pytest"] + testes_e2e)`
- Gates `acessibilidade` e `performance`: `sem_cobertura` (MVP)
- Reporte via `urllib.request.urlopen` com `timeout=30`, best-effort (exceções logadas, não levantadas)

**aceite.yml** — Workflow GitHub Actions:
- `on.repository_dispatch.types: [docudata-aceite]`
- `continue-on-error: true` no job e no step
- `permissions.contents: read`
- Env vars injetadas via `github.event.client_payload.*`
- Comentário no topo documentando que deve estar no default branch (per RESEARCH Pitfall 2)

### Task 2 — painel.py (commit 132043b)

**calcular_bloco_b** — Novo parâmetro `execucoes_aceite: list[dict] | None = None`:
- Constrói `aceite_por_func` dict por `funcionalidade_id`
- Para cada funcionalidade `concluida`: verifica `concluido_em` + qualquer gate com `falhou|erro`
- Retorna `funcionalidades_com_aceite_falhando` no dict de saída

**_calcular_cobertura_aceite** — Helper privado:
- Conta funcionalidades concluídas com `concluido_em` preenchido
- Retorna `float | None` (None se sem concluídas)

**get_painel** — Expansão:
- Busca `execucoes_aceite` ordenado por `disparado_em DESC`
- Deduplica por `funcionalidade_id` (mantém mais recente via set)
- Passa lista deduplicada para `calcular_bloco_b`
- Campo `cobertura_aceite` no response root — não altera `pct_escopo_concluido` de `bloco_a`

### Task 3 — api.ts + PainelTab.tsx (commit e8618c4)

**api.ts:**
- `ExecucaoAceite` interface exportada
- `BlocoB.funcionalidades_com_aceite_falhando?: Array<{id, titulo}>` adicionado
- `PainelData.cobertura_aceite?: number | null` adicionado
- `getExecucoesAceite(projectId)` — fetch com fallback silencioso `[]`

**PainelTab.tsx:**
- Import de `getExecucoesAceite` e `ExecucaoAceite`
- State `execucoesAceite: ExecucaoAceite[]`
- `Promise.all` expandido para 3 chamadas paralelas
- `aceiteMap = new Map(execucoesAceite.map(ea => [ea.funcionalidade_id, ea]))` antes do JSX
- `KanbanCard`: prop `execucaoAceite: ExecucaoAceite | null` + badge `⚠ aceite` com `style={{}}` (zero className)
- Coluna Concluído: `execucaoAceite={aceiteMap.get(f.id) ?? null}` — outras colunas `null`
- `BlocoBCard`: sub-seção "Cobertura de Aceite" com lista de funcionalidades com falha (zero className)
- Cobertura de aceite exibida acima do grid 4-blocos quando `data.cobertura_aceite != null`

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (auto) | 98ded8c | feat(11-02): aceite_agent.py stdlib only + aceite.yml repository_dispatch |
| 2 (auto) | 132043b | feat(11-02): painel.py cobertura_aceite + funcionalidades_com_aceite_falhando |
| 3 (auto) | e8618c4 | feat(11-02): badge aceite Kanban + Bloco B Cobertura de Aceite + ExecucaoAceite api.ts |

## Files Created/Modified

| File | Action | Changes |
|------|--------|---------|
| `docudata-backend/hooks/aceite_agent.py` | Created | Agente Python stdlib, 5 gates, best-effort |
| `docudata-backend/hooks/aceite.yml` | Created | Workflow GitHub Actions, repository_dispatch, continue-on-error |
| `docudata-backend/routers/painel.py` | Modified | calcular_bloco_b + _calcular_cobertura_aceite + get_painel busca execucoes_aceite |
| `docudata-frontend/app/lib/api.ts` | Modified | ExecucaoAceite interface + getExecucoesAceite + BlocoB + PainelData |
| `docudata-frontend/app/components/PainelTab.tsx` | Modified | KanbanCard badge + BlocoBCard sub-seção + Promise.all paralelo |

## Decisions Made

1. **aceite_agent.py stdlib only** — Zero dependências externas no repo do projeto. Mesmo padrão de revisor_agent.py.

2. **continue-on-error: true em dois níveis** — Job e step — garante que qualquer falha interna nunca bloqueia o CI do projeto.

3. **cobertura_aceite no response root** — Campo separado de `bloco_a.pct_escopo_concluido` conforme D-10. As duas métricas medem coisas distintas: escopo concluído mede entrega, cobertura de aceite mede qualidade das entregas.

4. **getExecucoesAceite em Promise.all** — Chamada paralela às outras duas (getPainel + listFuncionalidades). Falha silenciosa (`[]`) para não bloquear o painel.

5. **aceiteMap antes do JSX** — Construído uma vez com `new Map(...)` antes da renderização para lookup O(1) por funcionalidade_id no Kanban.

## Deviations from Plan

### None

O plano foi executado exatamente como escrito. Nenhuma adaptação foi necessária.

## Known Stubs

Nenhum stub identificado. Gates `acessibilidade` e `performance` retornam `sem_cobertura` por design do MVP (documentado no código e no plano).

## Threat Surface Scan

Nenhuma nova superfície de rede ou endpoint foi adicionada nesta fase. Os endpoints `POST /ingest/aceite` e `GET /execucoes_aceite/{project_id}` foram criados na fase 11-01. T-11-05 (spoofing via POST sem autenticação) está documentado como aceito conscientemente no threat_model do plano.

## Self-Check: PASSED

- [x] aceite_agent.py criado em `docudata-backend/hooks/aceite_agent.py`
- [x] aceite_agent.py: `python3 -c "import ast; ast.parse(...)"` — PASS
- [x] aceite_agent.py: stdlib only (sem requests, httpx, aiohttp, asyncio) — PASS
- [x] aceite.yml: `on.repository_dispatch.types: [docudata-aceite]` — PASS
- [x] aceite.yml: `continue-on-error: true` no job e no step — PASS
- [x] 5 gates: build, testes_unitarios, e2e, acessibilidade, performance — PASS
- [x] commit_sha via `git rev-parse HEAD` (list literal) — PASS
- [x] testes_e2e vazio → gate e2e = sem_cobertura — PASS
- [x] painel.py: `python3 ast.parse` — PASS
- [x] painel.py: calcular_bloco_b aceita execucoes_aceite — PASS
- [x] painel.py: _calcular_cobertura_aceite criado — PASS
- [x] painel.py: get_painel busca e deduplica execucoes_aceite — PASS
- [x] painel.py: cobertura_aceite no response root — PASS
- [x] painel.py: pct_escopo_concluido não alterado — PASS
- [x] api.ts: ExecucaoAceite interface exportada — PASS
- [x] api.ts: getExecucoesAceite() exportada com fallback silencioso — PASS
- [x] api.ts: BlocoB.funcionalidades_com_aceite_falhando adicionado — PASS
- [x] api.ts: PainelData.cobertura_aceite adicionado — PASS
- [x] PainelTab.tsx: KanbanCard com execucaoAceite prop e badge zero className — PASS
- [x] PainelTab.tsx: BlocoBCard sub-seção Cobertura de Aceite zero className — PASS
- [x] npx tsc --noEmit — PASS (zero erros)
- [x] 3 commits individuais com formato correto (11-02)
