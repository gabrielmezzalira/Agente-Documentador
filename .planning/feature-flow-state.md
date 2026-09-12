# Feature Flow State
feature: "Auto-preencher a tabela 'planejado vs. entregue' da Review de sprint a partir de dados já existentes (tasks/kanban); campos obrigatórios em Planning e Review (com confirmação explícita de 'nenhum' em listas de evento)"
modo: "FULL"
tier: "BOUNDED (classificado via superpowers:brainstorming — sem spec/plan doc, implementado direto após aprovação em chat)"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js (React)"
etapa: 12
etapa_nome: "Concluído"
gates_reusados: ["knowledge-graph (graphify-out/ em docudata-backend e docudata-frontend, reextraído em 2026-09-12, mesma sessão anterior — reaproveitado sem regenerar)"]
started_at: "2026-09-12T00:00:00Z"
last_saved: "2026-09-12T18:19:07Z"
status: "concluido"

## Concluído
- [x] Etapa 1 — Requisitos via `/brainstorm`: caminho Bounded. Decisões fechadas em chat (sem spec file): granularidade por task (não funcionalidade); "entregue" = task `concluida`; motivo_nao/causa_raiz_num ficam em branco; recalcula do zero a cada abertura do formulário; pedido adicional do usuário no meio do brainstorm — bloquear geração de Planning/Review com campos vazios. Decisão final: removida a verificação de conteúdo do Gemini (sentinela "[Insumo insuficiente]"); virou validação de formulário — todo campo obrigatório, listas de evento exigem item ou confirmação explícita de "nenhum".
- [x] Etapa 2 — Implementação via TDD (sem plan doc, path Bounded):
  - `services/sprints.py`: nova função `compute_planejado_vs_entregue(client, project_id, numero)` — 1 linha por task da sprint, `entregue` = "S"/"N" conforme `coluna_kanban == "concluida"` (convenção "S"/"N" já usada no frontend, não "sim"/"não").
  - `routers/sprint_docs.py`: novo `GET /sprint-docs/review/planejado-entregue?projeto_id=&sprint_numero=` (prefill); `submit_planning` e `submit_review` com campos antes opcionais agora `Form(...)` obrigatórios; novo helper `_require_lista_ou_confirmado` + flags `sem_riscos`/`sem_dependencias`/`sem_carry_over` (planning) e `sem_pedidos_fora_escopo`/`sem_itens_proxima_sprint` (review); `itens_planejados_entregues` da Review exige ≥1 item (sem flag de exceção — Review pressupõe que algo foi planejado).
  - Testes novos: `test_review_planejado_entregue.py`, `test_sprint_docs_planejado_entregue_endpoint.py`, `test_sprint_docs_planning_required_fields.py`, `test_sprint_docs_review_required_fields.py` — todos via TDD (RED confirmado antes de cada implementação). Suíte completa: 256 passed, 4 failed (mesmas falhas pré-existentes de `test_schemas_and_client.py`, documentadas em memória, sem relação).
  - Frontend: `app/lib/api.ts` (nova `getPlanejadoVsEntregue`, tipos de `submitPlanning`/`submitReview` atualizados com campos obrigatórios + flags `sem*`); `SprintDocModal.tsx` (fetch automático do planejado-vs-entregue ao abrir Review — recalcula do zero sempre; checkboxes "nenhum X identificado" nas listas de evento; validação client-side espelhando o backend; novos campos Squad e Contexto Livre no Planning, que não existiam nesse modal); `PlanningModal.tsx` (Composer) recebeu o mesmo tratamento — também usa `submitPlanning`, precisou dos mesmos campos/flags novos (Squad não existia ali também).
  - `npm run build` limpo (type-check só, sem checagem visual em produção — mesmo padrão já registrado em memória para este projeto).
- **Pendência pós-deploy:** nenhuma migração de schema nova — este trabalho não mexeu no banco, só em lógica de API e formulários.

## Concluído
- [x] Etapa 0 — Onboarding de repositório: knowledge graph já existe e está atual (reextraído nesta mesma sessão de trabalho, ciclo anterior). Reaproveitado sem regenerar.

## Contexto relevante
- Escopo confirmado pelo usuário: back-end (lógica de cruzamento de dados) + UI (exibir já pré-preenchido no formulário/modal de Review existente, sem gerar design novo — reusar componentes já existentes).
- Investigação já feita nesta conversa (não repetir):
  - `routers/sprint_docs.py`, função `submit_review` (~linha 488-588): campo `itens_planejados_entregues` é `Form("[]")` — hoje só chega por digitação manual no formulário do frontend, ou por extração de IA de um anexo (`_extract_anexo_to_content`, tipo_esperado="review"). Nunca é calculado a partir de dados estruturados já existentes no sistema.
  - `app/components/SprintDocModal.tsx` linha ~296: só popula `itens_planejados_entregues` quando vem de `result` (extração de anexo), nunca a partir de tasks/kanban reais.
  - `app/lib/api.ts` linha ~599 (monta o FormData do submit) e ~742 (tipo `itens_planejados_entregues?: {item, entregue, motivo_nao, causa_raiz_num}[]`).
  - Dados que já existem no sistema pra cruzar: `sprint_funcionalidades` (vínculo funcionalidade↔sprint) e `tasks` (pontos, coluna/status `planejado`/`em_andamento`/`concluida`, vínculo a sprint e funcionalidade) — ambos já respondem "o que foi planejado pra essa sprint" e "o que terminou concluída".
  - Boletim de aceite (`routers/boletins.py`) existe no backend mas não tem nenhuma chamada no frontend (`grep` vazio em `api.ts` e em `app/`) — não faz parte deste trabalho, é só contexto de outra conversa.
- Pendente: rodar `/brainstorm` pra fechar exatamente a regra de "planejado" (todas as tasks da sprint? só as vinculadas a funcionalidade via sprint_funcionalidades? o que conta como "entregue" — task concluída, ou funcionalidade com todas as tasks concluídas?) e o que fazer com `motivo_nao`/`causa_raiz_num` (campos que dependem de julgamento humano, não dá pra derivar automaticamente) — decidir se ficam vazios pra edição manual ou se há alguma inferência possível.
