---
phase: 10-composer-de-planning
plan: 02
subsystem: api, ui
tags: [fastapi, nextjs, gemini, langgraph, react, planning-wizard]

requires:
  - phase: 10-01
    provides: planning_rascunhos table, GET/PATCH/POST confirmar endpoints, calcular_throughput_ref

provides:
  - POST /composer/gerar endpoint (Gemini call, returns markdown without persisting)
  - PlanningTab.tsx wizard (4 steps, zero className, inline styles)
  - api.ts composer functions (getRascunho, patchRascunho, gerarPlanning, confirmarPlanning)
  - TabId extended with "planning" literal
  - "Planning" tab wired in dashboard page.tsx

affects: []

key-files:
  created:
    - docudata-frontend/app/components/PlanningTab.tsx
  modified:
    - docudata-backend/routers/composer.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/projects/[id]/page.tsx

key-decisions:
  - "POST /gerar: returns {markdown} without calling .insert() anywhere — separation between preview (D-06) and persist (D-07)"
  - "zero className in PlanningTab.tsx: all styles as React.CSSProperties constants declared outside the component, following PainelTab.tsx byte-by-byte pattern (D-09)"
  - "Step 4 auto-calls gerarPlanning on mount via useEffect([wizardStep]) — no intermediate button click required (D-06)"
  - "insert-before-confirmar order preserved from Plan 01: POST /confirmar inserts generated_docs BEFORE deleting rascunho (D-07)"
  - "_PLANNING_SYSTEM_PROMPT: Portuguese prompt with 5 sections, ends with 'retorne APENAS o markdown sem texto antes ou depois'"
  - "Out-of-bounds index filter: [i for i in indices if i < len(criterios)] — Pitfall 5 from RESEARCH.md"
  - "passo2Valido: selecionadas.every(id => (recortes[id]??[]).length > 0) — Próximo in step 2 disabled={!passo2Valido} (D-04)"
  - "Transbordos sorted to top of step 1 with borderLeft 3px solid #c2410c and badge 'Transbordado' (background #ffedd5, color #c2410c)"

requirements-completed:
  - "M4 (§5)"

tech-stack:
  added: []
  patterns:
    - "POST /gerar pattern: fetch rascunho → fetch proj+api_key → fetch funcs → build context → ainvoke Gemini → return {markdown} (no persist)"
    - "useEffect([wizardStep]) auto-trigger gerarPlanning when entering step 4"
    - "patchRascunho called on every step advance/retreat — non-blocking (catches silently, continues navigation)"
    - "Zero-className wizard with all styles as named CSSProperties constants outside component"

estimate:
  tokens: 90000
  raw_tokens: 90000
  tasks: 2
  confidence: low

actuals:
  tokens: 18500
  tasks: 2
  commits: 2

duration: 22min
completed: 2026-08-23
status: complete
---

# Phase 10 Plan 02: Gemini endpoint + PlanningTab wizard

**One-liner:** POST /composer/gerar invoca Gemini (gemini-3.5-flash-lite) com contexto estruturado do rascunho e retorna markdown sem persistir; PlanningTab.tsx implementa wizard de 4 passos com zero className, tela de boas-vindas com throughput, transbordos no topo, recorte obrigatório de critérios, e preview confirmado via react-markdown.

## What Was Built

### Task 1: POST /composer/gerar (docudata-backend/routers/composer.py)

**Additions to composer.py:**

1. **`GerarBody`** — Pydantic body model com `project_id: str` e `sprint_numero: int`.

2. **`_PLANNING_SYSTEM_PROMPT`** — Constante de módulo em português. Define o assistente como especializado em documentação de projetos de dados do CITi, lista 5 seções obrigatórias (Objetivo da Sprint, Funcionalidades Selecionadas, Responsabilidades, Transbordos, Throughput de Referência), e encerra com "Retorne APENAS o markdown, sem texto antes ou depois, sem blocos de código, sem backticks."

3. **`_montar_contexto_gerar(rascunho, funcs_map, projeto, throughput_ref, transbordos)`** — Função auxiliar que monta o bloco de texto enviado ao Gemini como HumanMessage. Inclui filtragem out-of-bounds: `indices = [i for i in indices if i < len(criterios)]` (Pitfall 5 do RESEARCH.md).

4. **`POST /composer/gerar`** — Endpoint async que:
   - Busca rascunho (404 se não existe)
   - Busca projeto + `gemini_api_key` (422 se ausente/vazia — padrão idêntico a `commit_ingest.py`)
   - Busca todas as funcionalidades do projeto
   - Calcula `throughput_ref` e transbordos para enriquecer o contexto
   - Invoca `ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_tokens=2048)` via `ainvoke`
   - try/except → HTTPException 502
   - Retorna `{"markdown": result.content}` — **sem chamar `.insert()` em nenhuma tabela** (D-06)

### Task 2: Frontend (api.ts + PlanningTab.tsx + page.tsx)

**api.ts — interfaces adicionadas:**
- `DadosJson` — estrutura do `dados_json` do rascunho
- `RascunhoData` — shape completo do rascunho
- `TransbordoItem` — funcionalidade transbordada da sprint anterior
- `GetRascunhoResponse` — response do GET /rascunho com throughput_ref e transbordos
- `GerarResponse` — `{markdown: string}`
- `ConfirmarResponse` — `{doc_id, content, created_at}`

**api.ts — funções adicionadas:**
- `getRascunho(projectId, sprintNumero)` — GET /composer/rascunho/{id}/{sprint}
- `patchRascunho(projectId, sprintNumero, payload)` — PATCH com step_atual + dados_json
- `gerarPlanning(projectId, sprintNumero)` — POST /composer/gerar
- `confirmarPlanning(projectId, sprintNumero, markdown)` — POST /composer/confirmar

**PlanningTab.tsx — wizard completo:**
- **Zero className** — todos os estilos como constantes `React.CSSProperties` declaradas fora do componente
- **Tela de boas-vindas** (sem rascunho): exibe informação de throughput (disponível ao iniciar) + botão "Iniciar Planning da Sprint N" (D-10)
- **Barra horizontal de 4 steps**: labels "1. Seleção", "2. Recorte", "3. Alocação", "4. Composição" com cor verde (#dcfce7/#4ade80) para step ativo, cinza para anteriores
- **Step 1 — Seleção**: funcionalidades ordenadas com transbordos no topo (`borderLeft: "3px solid #c2410c"`) e badge inline "Transbordado" (background `#ffedd5`, color `#c2410c`)
- **Step 2 — Recorte**: checkboxes por índice de `criterios_aceite`; aviso vermelho por funcionalidade sem seleção; `passo2Valido = selecionadas.every(id => (recortes[id]??[]).length > 0)`; botão Próximo `disabled={!passo2Valido}` (D-04)
- **Step 3 — Alocação**: input de texto opcional por funcionalidade selecionada
- **Step 4 — Composição**: `useEffect([wizardStep])` dispara `gerarPlanning` ao entrar no step automaticamente (D-06); spinner "Gerando planning com IA…"; preview via `<ReactMarkdown>`; botão "Confirmar Planning" chama `confirmarPlanning` → tela de sucesso + reset (D-07/D-02)
- `patchRascunho` chamado ao avançar/retroceder (não-bloqueante)

**page.tsx — 3 edições cirúrgicas:**
- Import de `PlanningTab` adicionado
- `TabId` estendido com `| "planning"`
- Array de tabs recebe `{id: "planning", label: "Planning"}`
- Renderização condicional `{activeTab === "planning" && <PlanningTab projectId={id} sprints={sprints} />}`

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| /gerar rota registrada | `python -c "from routers import composer; assert any('/gerar' in r for r in [r.path for r in composer.router.routes])"` | PASS |
| main.py importa sem erro | `python -c "import main; print('OK')"` | PASS |
| OpenAPI paths composer | `TestClient.get('/openapi.json').json()['paths']` | `/composer/rascunho/…`, `/composer/confirmar`, `/composer/gerar` — PASS |
| TypeScript sem erros | `npx tsc --noEmit` | PASS (sem output) |
| Zero className | `grep -v "^//" PlanningTab.tsx \| grep -c "className"` | 0 — PASS |
| planning em page.tsx | `grep -c "planning" page.tsx` | 7 — PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-10-05 | `react-markdown` ^9.x renderiza safe por default — sem `dangerouslySetInnerHTML`; confirmado no componente |
| T-10-06 | `gemini_api_key` buscada no backend por `project_id`, nunca incluída no response de `/gerar` |
| T-10-07 | `gerandoMarkdown` state previne chamadas duplicadas ao Gemini enquanto em progresso; "Tentar novamente" só aparece em estado de erro |
| T-10-08 | Aceito — MVP sem isolamento de usuário; markdown é conteúdo de trabalho, não credencial |

## Self-Check: PASSED

- [x] `docudata-backend/routers/composer.py` — FOUND (POST /gerar adicionado)
- [x] `docudata-frontend/app/components/PlanningTab.tsx` — FOUND (criado)
- [x] `docudata-frontend/app/lib/api.ts` — FOUND (funções composer adicionadas)
- [x] `docudata-frontend/app/projects/[id]/page.tsx` — FOUND (TabId + tab + renderização)
- [x] Commit `1f17bed` (Task 1) — FOUND
- [x] Commit `0f89560` (Task 2) — FOUND
