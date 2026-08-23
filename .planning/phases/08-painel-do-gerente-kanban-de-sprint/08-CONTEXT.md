# Phase 8: Painel do Gerente + Kanban de Sprint - Context

**Gathered:** 2026-08-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega duas capacidades visuais read-only na home do projeto:

1. **Painel de saúde** — 4 blocos de métricas (Bloco A: Tempo × Escopo, Bloco B: Itens travados, Bloco C: Métricas de fluxo, Bloco D: Tempo por fase). Dados já existem no banco: `funcionalidades`, `transicoes_status`, `projects` (com campos de contrato da Fase 7).
2. **Kanban de sprint** — funcionalidades distribuídas em 3 colunas por status, filtradas pela sprint selecionada. Sem persistir estado próprio.

Toda a lógica de cálculo fica no backend (endpoint dedicado). Frontend só renderiza o JSON retornado.

</domain>

<decisions>
## Implementation Decisions

### Localização e Layout

- **D-01:** **Nova aba "Painel"** — 7a aba no dashboard, inserida entre "Sprints" e "Tecnologias". Painel (4 blocos) + Kanban ficam juntos nessa aba. Sem alterar as 6 abas existentes.
- **D-02:** **Layout da aba:** grid 2×2 com os 4 blocos (A/B/C/D) no topo; kanban de sprint como seção full-width abaixo. Hierarquia: métricas primeiro, detalhe por funcionalidade depois.
- **D-03:** **Bloco A sem dados de contrato** (`data_inicio` ou `data_fim_contratada` nulos): card cinza com texto "Sem dados de contrato" + link para a aba Configurações. Grid permanece 2×2 — bloco não some.
- **D-04:** **Detalhe do Bloco D:** acordeom expansível inline. Clica em "ver detalhe" e uma lista expande abaixo do resumo agregado, listando cada funcionalidade com seus tempos por fase (ex: "Login — em_andamento: 15 dias | Dashboard — em_andamento: 4 dias").
- **D-05:** **Alerta de desvio (Bloco A):** só visual — campo `desvio_detectado: bool` no response do endpoint. Não persiste no banco. Sem tabela nova, sem migration para alerta.

### Kanban

- **D-06:** **Sprint selecionável via dropdown** — ao abrir a aba Painel, o kanban pré-seleciona a sprint mais recente (maior número). Gerente pode mudar via dropdown.
- **D-07:** **3 colunas** (em vez das 4 do SDD): `Planejado` (nao_iniciada) / `Em andamento` (em_andamento + em_ajuste) / `Concluído` (concluida). Coluna "Transbordou" removida — funcionalidades podem legitimamente span múltiplas sprints sem ser carry-over clássico. — **Reversibility:** costly — altera a estrutura de colunas que o SDD especificou; mudança requer acordo explícito.
- **D-08:** **Funcionalidades multi-sprint:** badge no card mostrando as sprints em que a funcionalidade aparece (ex: chip "Sprint 1 · Sprint 2"). Não requer campo novo — leitura do conjunto de `sprint_alvo` das funcionalidades que o gerente atribuiu.
- **D-09:** **Filtro do kanban:** funcionalidades com `sprint_alvo = sprint_selecionada`. Sem persistência de estado próprio — só leitura de dados existentes.

### Backend e Cálculos

- **D-10:** **Endpoint dedicado:** `GET /projects/{id}/painel` retorna JSON com os 4 blocos calculados. Cálculos de percentil (p50/p85), dias úteis e cycle time ficam em Python. Frontend recebe o JSON e só renderiza. — **Reversibility:** reversible
- **D-11:** **Bloco B — funcionalidades travadas:** usa `MAX(transicoes_status.timestamp)` por funcionalidade. Se `hoje − ultima_transicao > 7 dias` E `status = em_andamento` → travada. Dados já existem em `transicoes_status`.
- **D-12:** **Bloco B — aguardando cliente (5 dias úteis):** `status_cliente = enviado` E `tempo desde a transição para enviado > 5 dias úteis`. Aproximar dias úteis como `dias_corridos × 5/7` sem biblioteca de calendário de feriados (ver Claude's Discretion).

### Squad e Métricas de Fluxo

- **D-13:** **Sem agrupamento por squad no Bloco C** — cada projeto tem um único squad. Métricas de throughput/WIP/cycle time agregam o projeto inteiro. Sem campo `squad` nas funcionalidades.
- **D-14:** **Janela de tempo do Bloco C:** projeto inteiro desde a primeira funcionalidade (sem janela deslizante).
- **D-15:** **Cycle time:** de `em_andamento` até `concluida` — exclui o tempo de fila em `nao_iniciada`. Usa `transicoes_status` para calcular duração entre a transição para `em_andamento` e a transição para `concluida`.

### Claude's Discretion

- **Fórmula de eficiência de fluxo (Bloco D):** implementador define. Sugestão: `tempo_em_andamento / tempo_total_de_vida × 100%`. "Tempo total de vida" = criado_em até concluida (ou hoje se não concluída).
- **Cálculo de dias úteis (Bloco B):** aproximar como `dias_corridos × 5/7` — suficiente para detecção de "5 dias úteis sem resposta". Sem biblioteca de calendário.
- **Throughput (Bloco C):** funcionalidades concluídas por semana, calculado como média sobre as semanas com atividade desde o início do projeto.
- **p50/p85 de cycle time (Bloco C):** percentil da distribuição de cycle times de todas as funcionalidades concluídas. Se nenhuma concluída, retornar `null`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Entidade funcionalidades (Fase 7)
- `docudata-backend/routers/funcionalidades.py` — endpoints CRUD, PATCH de status com TransicaoStatus
- `docudata-backend/models/schemas.py` — FuncionalidadeResponse, TransicaoStatusResponse (campos disponíveis para cálculo)

### Dados de tempo por fase
- `docudata-backend/routers/funcionalidades.py` linha ~141 — `GET /funcionalidades/{id}/transicoes` (padrão de busca de transicoes_status)

### Dashboard frontend existente
- `docudata-frontend/app/projects/[id]/page.tsx` — estrutura de abas, tipo TabId, padrão de fetch de dados por tab, componentes disponíveis (Tabs, SprintCard, etc.)
- `docudata-frontend/app/lib/api.ts` — padrão de funções fetch tipadas

### Campos de contrato do projeto (Fase 7)
- `.planning/phases/07-matriz-de-escopo-transicaostatus-campos-novos-em-projeto/07-CONTEXT.md` §Campos novos em Projeto — `data_inicio`, `data_fim_contratada`, `tolerancia_desvio_pontos`

### Roadmap e requirements
- `.planning/ROADMAP.md` §Phase 8 — success criteria completos (fonte de verdade dos blocos)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docudata-frontend/app/components/Tabs.tsx` — componente de abas já em uso; adicionar tab "Painel" segue o padrão existente (adicionar `{ id: "painel", label: "Painel" }` ao array)
- `docudata-frontend/app/components/TechnologiesTab.tsx` — padrão de componente de aba isolado em arquivo próprio; Painel deve seguir o mesmo padrão (`PainelTab.tsx` como componente separado)
- `type TabId` em `page.tsx` — union type existente; adicionar `"painel"` ao union

### Established Patterns
- Abas isolam fetch de dados: cada aba busca seus dados próprios (ver aba "custos" que faz fetch ao ativar). Aba "Painel" deve fazer `GET /projects/{id}/painel` ao ativar, com `useEffect` dependente de `activeTab === "painel"`.
- Routers FastAPI seguem padrão em `routers/projects.py` / `routers/funcionalidades.py` — novo router `routers/painel.py` com `GET /projects/{id}/painel`
- `supabase_client.get_client()` para consultas ao banco — reutilizar em `routers/painel.py`

### Integration Points
- **Novo endpoint:** `GET /projects/{id}/painel` em `routers/painel.py` — registrar em `main.py` com `app.include_router(painel_router)`
- **Kanban:** lê funcionalidades do mesmo endpoint `/funcionalidades?project_id={id}` já existente — filtra no frontend pela sprint selecionada
- **Dropdown de sprint:** lista de sprints já buscada no dashboard (`listSprints` em `api.ts`) — reutilizar para o seletor do kanban

</code_context>

<specifics>
## Specific Ideas

- O gerente quer ver "o que está acontecendo agora" — a aba Painel deve ser a segunda aba mais visitada depois de Sprints. Mantê-la enxuta e sem scroll infinito.
- Bloco D accordion: cada linha no resumo é uma fase de status (nao_iniciada, em_andamento, em_ajuste, concluida) com tempo médio e p85. Ao expandir, lista funcionalidades individuais naquela fase.
- Bloco B deve ter 3 sub-seções visuais: "Travadas" (> 7 dias em_andamento), "Aguardando cliente" (> 5 dias úteis com status_cliente=enviado), "Em ajuste" (voltaram para em_ajuste — independe de tempo).
- Badge multi-sprint no kanban: chips pequenos, estilo dos chips de status já existentes na UI do projeto.

</specifics>

<deferred>
## Deferred Ideas

- Coluna "Transbordou" no kanban (SDD original tinha 4 colunas) — removida; funcionalidades span multi-sprint legitimamente. Se o gerente quiser visualização explícita de carry-over, é uma nova feature.
- Histórico de alertas de desvio — gravar cada detecção de desvio no banco para análise retrospectiva. Fora do escopo desta fase.
- Filtro de Bloco C por janela deslizante (últimas 4 semanas) — deferido; projeto inteiro é suficiente para v1.
- Agrupamento por squad dentro de um projeto — deferido; no modelo atual cada projeto é um squad. Se um projeto tiver múltiplos squads no futuro, requer campo `squad` nas funcionalidades + migration.
- Integração do kanban com drag-and-drop para mudar status — kanban é read-only nesta fase; drag-and-drop seria nova feature de edição.

</deferred>

---

*Phase: 8-painel-do-gerente-kanban-de-sprint*
*Context gathered: 2026-08-22*
