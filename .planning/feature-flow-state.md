# Feature Flow State
feature: "Backlog UAT Phase 19 — 6 bugs/polish (contraste gráficos, duplicata operacional case-sensitive, ícones info faltando, aba Sprints poluída, cascade delete operacional + bug de listagem, delete de task não limpa pontuação)"
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js (React)"
etapa: 12
etapa_nome: "Verificação final (parcial — UI adiada pelo usuário)"
gates_reusados: ["knowledge-graph (docudata-backend e docudata-frontend reextraídos nesta etapa — ambos estavam desatualizados em relação aos commits da Phase 19; backend agora 907 nodes/2227 edges, frontend 578 nodes/1092 edges, reextração estrutural sem LLM)", "design-system/DESIGN.md (tier PADRÃO, mas sem MASTER.md/DESIGN.md no repo — Etapas 4-6 do feature-flow-lean puladas como na Phase 19, UI seguiu o padrão visual existente em estilos inline)"]
started_at: "2026-09-06T00:00:00Z"
last_saved: "2026-09-06T00:00:00Z"
status: "concluido"

## Concluído
- [x] Etapa 0 — Onboarding de repositório: grafos estrutural do backend e frontend reextraídos (ambos estavam desatualizados em relação aos 17 commits da Phase 19).
- [x] Etapa 1 — Requisitos via `/brainstorm` (caminho Bounded, sem spec file — 6 itens são mudanças pontuais a fluxos já existentes). Design aprovado pelo usuário em chat (sem doc separado, path Bounded). Decisões de produto fechadas:
  - Item 2 (duplicata case-insensitive): só bloquear DAQUI PRA FRENTE — sem merge automático das duplicatas já existentes em produção. Implicação técnica: vira checagem em app-level (lower() no create_operacional), não índice único de banco, porque `CREATE UNIQUE INDEX` falharia com duplicatas existentes.
  - Item 5 (cascade delete operacional): ao forçar exclusão com tasks vinculadas, desvincula tasks (`operacional_id = NULL`) e apaga pontuação/ranking via `ON DELETE CASCADE` já existente no schema. Tasks continuam existindo, só ficam sem operacional.
  - Item 6 (delete de task pós-trava): bloquear com 409 se a task pertence a sprint com `avaliacao_completa_em` preenchido (pontuação já travada). `task_transicoes`/`task_reaberturas` já cascateiam via FK existente — não era o gap real.
- [x] Etapa 2 — Plano de implementação via `/write-plan`: `docs/superpowers/plans/2026-09-06-backlog-uat-phase19.md`, 8 tasks (Onda 1: Tasks 1-4 back-end; Onda 2: Tasks 5-8 UI). Execução escolhida: inline (executing-plans), direto na main.
- [x] Etapa 3 — Onda 1 (back-end) executada e verificada: Tasks 1-4 completas, cada uma com testes TDD (falha→implementa→passa), commits atômicos (`cbca20a`, `e4a6a1c`, `991d803`, `d47573c`). Suíte completa rodada ao final: 171 passed, 4 failed — as 4 falhas são pré-existentes em `test_schemas_and_client.py` (schema legado do MVP, confirmado via `git stash` que já falhavam antes desta sessão), sem relação com o backlog. Sem regressão.
- [x] Onda 2 (UI) executada: Tasks 5-8 completas — contraste WCAG (MetricasTab.tsx), InfoTooltip faltando (PainelTab.tsx), redesign da aba Sprints (SprintCard.tsx), mensagem de confirmação de exclusão (page.tsx). Verificadas via `npm run build` (type-check limpo). Checagem visual em navegador NÃO foi feita nesta sessão — Claude in Chrome e playwright MCP ambos falharam ao conectar; usuário optou explicitamente por testar manualmente depois ("eu testo dps") em vez de reconectar a extensão.
- [x] `finishing-a-development-branch`: suíte completa rodada de novo (171 passed, 4 failed — mesmas 4 falhas pré-existentes não relacionadas, confirmadas via git stash antes desta sessão). Trabalho direto na main (sem branch separada, por escolha do usuário). Push feito pra `origin/main` (9 commits: 4 back-end + 4 front-end + 1 do plano) — dispara deploy automático via Railway + Vercel.

## Status: CONCLUÍDO (verificação visual pendente do usuário)
Onda 1 e Onda 2 implementadas, testadas (backend) e pushadas pra produção. Falta apenas a confirmação visual das 4 mudanças de UI em produção, que o usuário disse que vai fazer depois por conta própria — não é um bloqueio, é uma decisão explícita de adiar o UAT ao vivo desta vez.

## Próximo passo
Nenhum pendente nesta feature. Se o usuário voltar com algum ajuste visual depois de testar em produção, é continuação natural desta mesma feature (não precisa nova sessão de feature-flow-lean do zero).

## Contexto relevante
- Origem: memória `project_uat_backlog_phase19` — 6 itens descobertos no UAT ao vivo de produção da Phase 19 (2026-09-06), todos independentes entre si e menores que a reforma de pontuação (`project_pontuacao_redesign_pendente`, adiada de propósito).
- Modo FULL porque os itens tocam back-end (migração de índice único, cascade delete, cleanup de pontuação) e UI (contraste, ícones, layout da aba Sprints).
- Tier PADRÃO: não são TRIVIAL puro (envolvem lógica de cascade delete e migração de índice único), mas também não são COMPLEXA (sem área nova do produto, dentro do design existente).
- Sem `design-system/MASTER.md` nem `DESIGN.md` no repo — gates de reuso (Etapas 4-6) provavelmente serão pulados de novo, como na Phase 19.
- Itens do backlog:
  1. Contraste baixo em gráficos de Métricas (SPI, Throughput, SPI por operacional) — barras/legendas cinza-claras quase invisíveis, provável violação WCAG AA.
  2. Duplicata de operacional por maiúscula/minúscula — `idx_operacionais_project_nome` é `UNIQUE(project_id, nome)` case-sensitive; precisa `lower(nome)` no índice único + normalização no insert.
  3. Ícones "i" faltando no card "Métricas de Fluxo" (WIP agora / Throughput), presentes nos cards vizinhos.
  4. Aba Sprints poluída visualmente — muitos chips/badges do mesmo estilo competindo por atenção.
  5. Sem exclusão em cascata de operacional (Configurações do projeto) + bug de listagem: card "Operacionais" em Configurações mostra "Nenhum operacional cadastrado" enquanto aba Métricas mostra operacionais reais — `routers/operacionais.py:42` (`list_operacionais`) filtra por `ativo=True`, precisa investigar qual query cada aba usa.
  6. Delete de task não limpa pontuação já gerada — `routers/tasks.py:490-496` (`delete_task`) é `DELETE` puro sem cleanup de `pontuacao_operacional_sprint`/`task_transicoes`/`task_reaberturas`; relacionado a `calcular_e_travar_pontuacao` (`routers/avaliacoes.py:162-165`) que trava snapshot.
- Próximo passo: invocar `/brainstorm` (superpowers) cobrindo os 6 itens — provavelmente vale separar em sub-tópicos dado que são independentes entre si, mas percorrer o mesmo brainstorm/write-plan pra manter uma única onda 1 (back-end) e onda 2 (UI) coesas.
