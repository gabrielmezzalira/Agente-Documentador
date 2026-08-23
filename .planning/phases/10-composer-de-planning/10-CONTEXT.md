# Phase 10: Composer de Planning - Context

**Gathered:** 2026-08-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Um wizard guiado em 4 passos — Seleção, Recorte, Alocação, Composição — que permite ao gerente compor o planning de uma sprint com estado persistido entre sessões. Funcionalidades transbordadas da sprint anterior aparecem destacadas. O sistema exibe throughput das últimas 3 sprints como referência (informativo, não bloqueante). O Gemini gera o texto do planning a partir dos dados estruturados do rascunho; o gerente vê o preview e confirma antes de oficializar. O rascunho nunca se torna planning oficial sem clique explícito de confirmação.

Escopo desta fase: tabela `planning_rascunhos` + endpoints do composer (`/composer/*`) + nova aba "Planning" no dashboard do projeto com wizard de 4 passos em steps horizontais.

</domain>

<decisions>
## Implementation Decisions

### Onde o rascunho é salvo

- **D-01:** **Nova tabela `planning_rascunhos` no Supabase** — campos: id uuid PK, project_id uuid FK→projects, sprint_numero int NOT NULL, step_atual int NOT NULL DEFAULT 1, dados_json jsonb NOT NULL DEFAULT '{}', created_at timestamptz, updated_at timestamptz. Um rascunho por (project_id, sprint_numero) — UNIQUE constraint. Rascunho sobrevive a troca de browser/máquina; qualquer sessão do mesmo projeto retoma de onde parou.

- **D-02:** **Rascunho descartado ao confirmar o planning oficial** — após `POST /composer/confirmar` ser bem-sucedido, o registro em `planning_rascunhos` é deletado. Sem TTL nem botão manual de descarte nesta fase.

### O que é o recorte

- **D-03:** **Recorte representado como lista de índices** — `dados_json` do rascunho armazena `recortes: { [funcionalidade_id]: number[] }` onde cada array contém os índices dos `criterios_aceite` que entram nesta sprint. Ex: `{"abc-123": [0, 2]}` significa que os critérios de índice 0 e 2 da funcionalidade `abc-123` entram no planning. Não altera a tabela `funcionalidades`.

- **D-04:** **Recorte obrigatório — bloqueia avançar sem critérios selecionados** — o botão "Próximo" do passo 2 (Recorte) fica desabilitado enquanto alguma funcionalidade selecionada não tiver nenhum índice marcado. Mensagem de aviso inline por funcionalidade problemática.

### Como o planning oficial é gerado

- **D-05:** **Gemini gera o texto do planning** — o backend monta um prompt estruturado com as funcionalidades selecionadas, seus recortes de critérios, responsáveis, throughput de referência, e lista de transbordos. O Gemini (`gemini-3.5-flash-lite`) elabora o documento de planning em markdown.

- **D-06:** **Preview do markdown + botão 'Confirmar Planning'** — o passo 4 (Composição) exibe o markdown gerado pelo Gemini via react-markdown. O gerente lê e clica "Confirmar Planning" para oficializar. Cancelar ou fechar volta para o passo 3 sem perder o rascunho.

- **D-07:** **Novo endpoint `POST /composer/confirmar`** — recebe project_id, sprint_numero, e o markdown gerado. Salva em `generated_docs` com `doc_type = 'planning'` e `sprint_number` correto. Em seguida, deleta o registro em `planning_rascunhos`. Não cria ingestion — planning foi composto, não ingerido de arquivo.

### Onde o composer vive no frontend

- **D-08:** **Nova aba "Planning" no Tabs.tsx existente** — adicionada ao lado das abas existentes (Visão Geral, Sprints, Painel, etc.). O wizard vive dentro dessa aba.

- **D-09:** **Steps horizontais no topo + painel de conteúdo abaixo** — barra de progresso visual com os 4 passos ("1. Seleção → 2. Recorte → 3. Alocação → 4. Composição"), conteúdo do passo ativo abaixo, botões "Anterior"/"Próximo" no rodapé. Zero className — todos os estilos via `style={{...}}` objects.

- **D-10:** **Tela de boas-vindas quando não há rascunho ativo** — exibe throughput das últimas 3 sprints (via query a `calcular_bloco_c` ou endpoint próprio) e botão "Iniciar Planning da Sprint N". Ao clicar, cria o rascunho no backend e entra no passo 1.

### Claude's Discretion

- **Estrutura completa do `dados_json`:** `{ funcionalidades_selecionadas: string[], recortes: Record<string, number[]>, alocacoes: Record<string, string>, transbordos: string[] }`. `transbordos` é lista de funcionalidade_ids cuja `sprint_alvo` é a sprint anterior (sprint_numero - 1) e status ≠ concluida.
- **Throughput das últimas 3 sprints:** calculado no endpoint `GET /composer/rascunho/{project_id}/{sprint_numero}` retornando também `throughput_ref` = throughput médio das 3 sprints anteriores (via query a transicoes_status). Reutiliza a lógica de `calcular_bloco_c`.
- **Endpoints do composer:** `GET /composer/rascunho/{project_id}/{sprint_numero}` (cria se não existe), `PATCH /composer/rascunho/{project_id}/{sprint_numero}` (salva step e dados), `POST /composer/gerar` (chama Gemini, retorna markdown sem salvar), `POST /composer/confirmar` (salva em generated_docs, deleta rascunho).
- **Funcionalidades transbordadas:** detectadas no passo 1 via `sprint_alvo == sprint_numero - 1 AND status != 'concluida'`; aparecem no topo da lista com badge visual "Transbordado".

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Entidade Funcionalidade e TransicaoStatus (Phase 7)
- `docudata-backend/routers/funcionalidades.py` — CRUD de funcionalidades, campos sprint_alvo e responsavel
- `docudata-backend/models/schemas.py` — FuncionalidadeResponse com criterios_aceite, sprint_alvo, responsavel, status

### Throughput e Painel (Phase 8)
- `docudata-backend/routers/painel.py` — `calcular_bloco_c` calcula throughput por semana; lógica reutilizável para o throughput de referência

### Geração de Planning existente (referência de padrão)
- `docudata-backend/routers/sprint_docs.py` — padrão de endpoint que salva em generated_docs + ingestions; o /composer/confirmar salva apenas em generated_docs

### Frontend
- `docudata-frontend/app/components/Tabs.tsx` — componente de abas existente; aba "Planning" a ser adicionada
- `docudata-frontend/app/components/PainelTab.tsx` — padrão de zero className, inline style={{...}}, useState local

### Roadmap e requirements
- `.planning/ROADMAP.md` §Phase 10 — 6 success criteria e escopo oficial
- `.planning/phases/07-matriz-de-escopo-transicaostatus-campos-novos-em-projeto/07-CONTEXT.md` — decisões sobre Funcionalidade e TransicaoStatus

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `calcular_bloco_c` em `painel.py` — calcula throughput por semana via transicoes_status; lógica a ser extraída ou chamada para o throughput de referência do composer
- `FuncionalidadeResponse` em `schemas.py` — tem todos os campos necessários: criterios_aceite, sprint_alvo, responsavel, status, id_funcional
- `ChatGoogleGenerativeAI` com `gemini-3.5-flash-lite` — padrão estabelecido em commit_ingest.py e revisao_ingest.py para chamar Gemini no backend

### Established Patterns
- **Zero className no frontend:** PainelTab.tsx usa exclusivamente `style={{...}}` objects; PlanningTab.tsx (novo) deve seguir o mesmo padrão
- **Router FastAPI com tag e prefix:** todos os routers usam `APIRouter(prefix=..., tags=[...])` e são registrados em main.py
- **Agente best-effort:** padrão de try/except + HTTPException 502 para falhas do Gemini (commit_ingest.py:146)
- **Supabase sync:** `get_client()` de `services/supabase_client.py` — padrão em todos os routers

### Integration Points
- `Tabs.tsx` → nova aba "Planning" adicionada
- `GET /composer/rascunho/{project_id}/{sprint_numero}` → conecta frontend ao rascunho persistido
- `POST /composer/confirmar` → salva em `generated_docs`, deleta de `planning_rascunhos`
- Supabase: nova tabela `planning_rascunhos` (migration SQL em supabase_schema.sql)
- `main.py` → registrar `composer.router`

</code_context>

<specifics>
## Specific Ideas

- Funcionalidades transbordadas aparecem **no topo** da lista do passo 1 com badge "Transbordado" (distinto visualmente — ex: borderLeft laranja)
- Throughput exibido na tela de boas-vindas E no passo de Seleção como referência ("Throughput médio das últimas 3 sprints: X funcionalidades/semana")
- O passo de Alocação é responsável → funcionalidade (não exige que toda funcionalidade tenha responsável, mas permite definir)
- Preview no passo 4 usa `react-markdown` já presente no projeto

</specifics>

<deferred>
## Deferred Ideas

- **Histórico de plannings anteriores na aba Planning** — lista de plannings gerados para o projeto com possibilidade de ver. Bloco B do Painel já expõe docs; fora do escopo desta fase.
- **Edição inline do markdown no preview** — editor de texto no passo 4. Transforma o wizard em editor; fora do escopo.
- **Múltiplos rascunhos por sprint** — suporte a mais de um rascunho em andamento simultaneamente. Complexidade desnecessária nesta fase; UNIQUE (project_id, sprint_numero) é suficiente.
- **Notificação quando planning é confirmado** (Slack/email) — fora do escopo desta fase.

</deferred>

---

*Phase: 10-Composer de Planning*
*Context gathered: 2026-08-23*
