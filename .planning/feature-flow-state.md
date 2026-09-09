# Feature Flow State
feature: "Reforma do modelo de pontuação — 100 pontos fixos por projeto, orçamento por sprint (Escopo), distribuídos em tasks (Kanban)"
modo: "FULL"
tier: "COMPLEXA"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js (React)"
etapa: 12
etapa_nome: "Verificação final / finishing-a-development-branch"
gates_reusados: ["knowledge-graph (docudata-backend e docudata-frontend reextraídos nesta etapa — backend 926 nodes/2272 edges, frontend 579 nodes/1093 edges, reextração estrutural sem LLM)"]
started_at: "2026-09-06T00:00:00Z"
last_saved: "2026-09-09T10:37:02Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — Onboarding de repositório: grafos estrutural do backend e frontend reextraídos.
- [x] Etapa 1 — Requisitos via `/brainstorm` (caminho Architectural, como esperado dado o escopo). Spec aprovada pelo usuário e commitada em `docs/superpowers/specs/2026-09-06-reforma-pontuacao-design.md` (commit `c3f0e08`). O design evoluiu bastante durante o brainstorm em relação à ideia original da memória — ver resumo abaixo.

## Contexto relevante — design final aprovado
- **Onde os pontos nascem:** NÃO na funcionalidade (ideia original da memória, descartada) — a "Etapa Específica" da planilha real do usuário é do tamanho de uma TASK (1-3 pontos, atribuível a 1 pessoa), não de uma funcionalidade (que é maior, com critérios de aceite). Pontos continuam nascendo em `tasks.pontos`, como já é hoje.
- **Como o total de 100 é garantido sem saber o escopo completo de antemão:** decompor em dois níveis. (1) Planejamento (aba Escopo, Phase 7): gerente define quantos dos 100 pontos cada SPRINT recebe (`sprints.pontos_orcamento`, novo campo) — soma de todas as sprints do projeto ≤ 100, validado aqui. (2) Execução (Kanban): pontos de tasks dentro de uma sprint ≤ orçamento já fixado daquela sprint — validação local e simples, não mais contra o total do projeto toda vez. Ideia do usuário, não minha — muito mais simples que minha proposta inicial de checar contra 100 a cada task criada.
- **Faturamento:** reaproveita `projects.valor_por_ponto`, campo dormente desde a Phase 12 (nunca lido em nenhum código). Novo campo `projects.valor_projeto` (valor do contrato, NÃO confundir com `budget_usd` que é teto de custo de IA). `valor_por_ponto = valor_projeto / 100`, calculado uma vez. Trava: `valor_projeto` só editável enquanto nenhuma sprint tiver `pontos_orcamento` definido ainda (edição fica em `PainelTab.tsx`, formulário de Contrato onde já vive `arquetipo`/datas/tolerância — Phase 19-08).
- **Sprint faturamento previsto:** `pontos_orcamento × valor_por_ponto`, calculado em memória — nunca mais uma coluna gravada manualmente.
- **Baseline manual antigo (Phase 12, que eu mesmo toquei no backlog anterior — Task 7 do ciclo passado):** removido. `PATCH /sprints/{id}/baseline` sai, `SprintBaselineUpdate`/`SprintBaselineResponse` saem dos schemas. Substituído por `PATCH /sprints/{id}/orcamento`. SprintCard.tsx perde o link de Baseline, ganha texto derivado read-only.
- **"Marcar como entregue":** aviso não-bloqueante (confirm() no frontend) se soma dos `pontos_orcamento` das sprints ≠ 100. Sem mudança no backend do endpoint `/projects/{id}/delivered`.
- **Exibição de saldo:** pool do projeto (soma de pontos_orcamento das sprints vs 100) na aba Escopo. Saldo de uso por sprint (pontos usados em tasks vs pontos_orcamento) no card da sprint, aba Sprints.
- **Fora de escopo (YAGNI), registrado na spec:** divisão automática de pontos entre sprints, rebalanceamento retroativo, `funcionalidades.sprint_alvo` virar FK real, migração/backfill de dados existentes (não há pontuação real em produção ainda).
- **Nota operacional:** `supabase_schema.sql` não roda sozinho — as duas `ALTER TABLE` (`sprints.pontos_orcamento`, `projects.valor_projeto`) precisam de aplicação manual em produção depois do deploy (ver memória `project_manual_migrations`).
- Arquivos-chave já identificados durante a exploração: `routers/sprints.py` (create_sprint, list_sprints ~64-142, update_baseline ~145-186 a remover), `routers/tasks.py` (create_task ~84, patch_task ~273-394), `routers/projects.py` (create_project, update_contrato ~344), `models/schemas.py` (ContratoUpdate ~308, SprintBaselineUpdate/Response ~495-508 a remover), `supabase_schema.sql` (sprints ~101-110, projects valor_por_ponto ~311, tasks ~258-275), `EscopoTab.tsx`, `PainelTab.tsx` (formulário de contrato ~109-125), `SprintCard.tsx`, `app/lib/api.ts` (updateSprintBaseline ~418 a remover).
- [x] Etapa 2 — Plano de implementação via `/write-plan`: `docs/superpowers/plans/2026-09-06-reforma-pontuacao.md`, 9 tasks. Execução escolhida: inline, direto na main (mesmo padrão do ciclo anterior).
- [x] Etapa 3 — Onda 1 (back-end) executada e verificada: Tasks 1-4 completas, TDD em todas, commits atômicos (`15db630`, `63f5c87`, `420f36b`, `87045ca`). Suíte completa: 187 passed, 4 failed (mesmas falhas pré-existentes de `test_schemas_and_client.py`, sem relação). Sem regressão.
- **Descoberta durante a execução (fora do plano original, corrigida na Task 1):** `services/spi_health.py` (status_saude verde/amarelo/vermelho, calculado após orçamento definido ou task concluída) e `routers/metricas.py` (`GET /metricas/{id}/spi`, gráfico "SPI — Schedule Performance Index" na aba Métricas) ambos liam `sprints.pontos_previstos` diretamente — ficariam permanentemente mortos pra qualquer sprint nova assim que o baseline manual saiu. Adaptados pra ler `pontos_orcamento` em vez disso; mesma fórmula, mesmo contrato de resposta (`GET /metricas/.../spi` continua devolvendo a chave `pontos_previstos` no JSON, só a coluna fonte no banco mudou — não quebra o `dataKey="pontos_previstos"` do gráfico em MetricasTab.tsx).
- [x] Onda 2 (UI) executada: Tasks 5-9 completas — api.ts (tipos/funções), SprintCard.tsx (baseline removido), SprintOrcamentoPlanner.tsx (novo) + EscopoTab.tsx (planejamento de orçamento por sprint), PainelTab.tsx (campo valor_projeto travável), page.tsx (aviso não-bloqueante em Marcar como entregue). `npm run build` limpo após cada task. Commits: `6850293`, `f3d098c`, `8bdc3ec`, `52ca1b0`, `a4f7e2d`.
- **Lembrete pós-deploy pendente:** aplicar manualmente em produção (Supabase) as duas migrações — `ALTER TABLE sprints ADD COLUMN IF NOT EXISTS pontos_orcamento int CHECK (pontos_orcamento IS NULL OR pontos_orcamento >= 0);` e `ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_projeto numeric(10,2);` — `supabase_schema.sql` não roda sozinho.
- Próximo passo: `finishing-a-development-branch` (rodar suíte, decidir sobre push).
