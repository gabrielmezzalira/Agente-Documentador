---
phase: 06-token-usage-panel
plan: "01"
subsystem: backend-api + frontend-dashboard
status: complete
tags:
  - usage-endpoint
  - token-tracking
  - monthly-cost
  - tracer-slice
dependencies:
  requires:
    - "05: ingestions com cost_usd/input_tokens/output_tokens já gravados"
    - "04: generated_docs com cost_usd/input_tokens/output_tokens já gravados"
  provides:
    - "GET /projects/{id}/usage?month=YYYY-MM com ProjectUsageResponse"
    - "Interface ProjectUsage tipada no frontend"
    - "Aba 'Custos' no dashboard mostrando total do mês atual"
  affects:
    - docudata-backend/routers/projects.py
    - docudata-backend/models/schemas.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/projects/[id]/page.tsx
tech-stack:
  added:
    - "ZoneInfo('America/Sao_Paulo') para cálculo de mês correto no backend"
    - "Intl.DateTimeFormat com timeZone America/Sao_Paulo no frontend"
  patterns:
    - "Agregação pura de colunas pré-existentes — sem recalculo de tarifa"
    - "Filtro por created_at >= start_iso AND < end_iso (UTC ISO 8601)"
    - "Monkeypatch em routers.projects.get_client para isolamento dos testes"
key-files:
  created:
    - docudata-backend/tests/test_project_usage.py
  modified:
    - docudata-backend/routers/projects.py
    - docudata-backend/models/schemas.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/projects/[id]/page.tsx
decisions:
  - "Monkeypatch em routers.projects.get_client (não em services.supabase_client.get_client) para o mock funcionar no módulo já importado"
  - "currentMonth computado com Intl.DateTimeFormat.formatToParts para extrair year/month sem depender do locale do sistema"
  - "Estado usage inicia null e carrega lazy no useEffect via activeTab === 'custos'"
metrics:
  duration_minutes: 30
  completed_date: "2026-08-13"
  tasks_completed: 1
  tasks_total: 1
  commits: 1
estimate:
  tokens: 60000
actuals:
  tokens: 28000
  tasks: 1
  commits: 1
---

# Phase 06 Plan 01: Token Usage Panel — Tracer Slice Summary

**One-liner:** Endpoint GET /projects/{id}/usage que agrega cost_usd/tokens mensais de ingestions + generated_docs via filtro UTC, com aba "Custos" no dashboard consumindo o mês atual em America/Sao_Paulo.

## O que foi construído

### Backend

**`GET /projects/{project_id}/usage`** em `docudata-backend/routers/projects.py`:
- Aceita query param `month=YYYY-MM` (opcional; default = mês atual em `America/Sao_Paulo`)
- Valida formato com regex `^\d{4}-(0[1-9]|1[0-2])$` — retorna 422 com `detail` explicativo se inválido
- Verifica existência do projeto — retorna 404 se não encontrado
- Calcula `start_iso` / `end_iso` em UTC a partir do início e fim do mês em `America/Sao_Paulo`
- Soma `cost_usd`, `input_tokens`, `output_tokens` de `ingestions` + `generated_docs` no intervalo — **nenhum recalculo de tarifa**
- Retorna `ProjectUsageResponse` com `project_id`, `month`, `total_usd` (round 6 casas), `input_tokens`, `output_tokens`

**`ProjectUsageResponse`** em `docudata-backend/models/schemas.py`:
- Adicionado logo após `ProjectCostResponse` para agrupar família de modelos de custo

### Testes

**`docudata-backend/tests/test_project_usage.py`** — 3 casos pytest, todos passando:
1. `test_usage_sem_month_retorna_mes_atual` — sem `month` → `response.month == mes_atual_sao_paulo`
2. `test_usage_agrega_ingestions_e_generated_docs` — 2 ingestions + 1 generated_doc → `total_usd=0.008, input_tokens=600, output_tokens=250`
3. `test_usage_month_invalido_retorna_422` — `month=2026-13` → 422 com mensagem sobre formato inválido

**Técnica de mock:** `monkeypatch.setattr(routers.projects, "get_client", ...)` — patcha no módulo do router (não no módulo do serviço) para interceptar a referência já importada.

### Frontend

**`docudata-frontend/app/lib/api.ts`**:
- Interface `ProjectUsage` com `{ project_id, month, total_usd, input_tokens, output_tokens }`
- Função `getProjectUsage(projectId, month?)` chamando `GET /projects/{id}/usage?month=...`

**`docudata-frontend/app/projects/[id]/page.tsx`**:
- `TabId` estendido com `"custos"`
- Tab `{ id: "custos", label: "Custos" }` registrado entre "documentos" e "config"
- Estado `usage: ProjectUsage | null` e `currentMonth: string` (calculado via `Intl.DateTimeFormat.formatToParts` com `timeZone: "America/Sao_Paulo"`)
- `useEffect` que dispara `getProjectUsage(id, currentMonth)` quando `activeTab === "custos"`
- Section "Custos" exibindo `total_usd` formatado e `input_tokens in · output_tokens out tokens`

## Verificações realizadas

| Verificação | Resultado |
|-------------|-----------|
| `pytest tests/test_project_usage.py -x -q` | 3 passed |
| `grep _COST_PER_INPUT_TOKEN routers/projects.py` \| wc -l | 0 (sem recalculo) |
| `npx tsc --noEmit` no frontend | 0 erros |

## Deviações do plano

Nenhuma — plano executado exatamente como escrito.

### Decisão de implementação notável

O monkeypatch nos testes precisou ser aplicado em `routers.projects.get_client` (não em `services.supabase_client.get_client`) porque o Python já havia importado a referência `get_client` no namespace do módulo `routers.projects` no momento da importação. Patchear o módulo de origem após a importação não afetaria a referência já vinculada. Este padrão é o mesmo utilizado em qualquer teste unitário que usa `from module import func`.

## O que fica pendente para o Plan 02

- **Breakdown por tipo:** separar `ingestions` vs `generated_docs` no payload do endpoint
- **Lista cronológica:** endpoint ou campo com lista de linhas individuais (id, data, cost_usd, tipo) para exibir tabela detalhada
- **Seletor de mês:** UI no frontend para o gerente navegar entre meses anteriores
- **Histórico acumulado:** gráfico ou tabela de custos por mês ao longo do projeto

## Self-Check

- [x] `docudata-backend/tests/test_project_usage.py` — arquivo existe e tem 3 testes
- [x] `docudata-backend/models/schemas.py` — `ProjectUsageResponse` adicionado
- [x] `docudata-backend/routers/projects.py` — handler `get_project_usage` adicionado
- [x] `docudata-frontend/app/lib/api.ts` — `ProjectUsage` + `getProjectUsage` adicionados
- [x] `docudata-frontend/app/projects/[id]/page.tsx` — aba "Custos" registrada e section renderizada
- [x] Commit `26b0521` existe no histórico

## Self-Check: PASSED
