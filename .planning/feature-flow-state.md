# Feature Flow State
feature: "Phase 19: Peso por Arquétipo + Área de Performance e Ranking"
modo: "FULL"
tier: "COMPLEXA"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js (React)"
etapa: 2
etapa_nome: "Execução do back-end (Onda 1)"
gates_reusados: ["knowledge-graph (docudata-backend/graphify-out atualizado na Etapa 0 — estava desatualizado em relação aos arquivos novos da Phase 18, como routers/pontuacao.py; reextração estrutural sem LLM, 851 nodes/2069 edges)"]
started_at: "2026-09-05T20:15:00Z"
last_saved: "2026-09-06T00:33:00Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — Onboarding de repositório: grafo estrutural do backend reextraído; grafo do frontend já estava atual, reaproveitado sem regenerar.
- [x] Etapa 1 — Requisitos via `/brainstorm` (caminho Architectural): spec aprovada e commitada em `docs/superpowers/specs/2026-09-06-peso-arquetipo-performance-design.md`.
- [x] Etapa 2 — Plano de implementação via `/write-plan`: `docs/superpowers/plans/2026-09-06-peso-arquetipo-performance.md`, 9 tasks (Onda 1: Tasks 1-7 back-end; Onda 2: Tasks 8-9 UI).

## Pausado — retomar em sessão nova
Usuário escolheu subagent-driven-development pra execução, mas a sessão atingiu ~69% de contexto antes de despachar a Task 1 (nenhum subagente foi despachado ainda — nada a recuperar). Pra retomar: numa sessão nova, invocar `superpowers:subagent-driven-development` apontando pro plano `docs/superpowers/plans/2026-09-06-peso-arquetipo-performance.md` (ou `/feature-flow-lean` pra Phase 19, que detecta este state file e vai direto pra Etapa 3 execução). O workspace da SDD já existe em `.superpowers/sdd/2026-09-06-peso-arquetipo-performance/` mas está vazio (sem ledger ainda) — a skill vai iniciar do zero na Task 1 normalmente.

## Contexto relevante
- Modo FULL, tier COMPLEXA (sem design-system/MASTER.md nem DESIGN.md no repo; tela de ranking sem equivalente visual existente).
- Depends on: Phase 16 (RBAC) e Phase 18 (Motor de Score) — ambas concluídas.
- Requirements: PERF-01..06.
- Escopo fechado no brainstorm ficou maior que o ROADMAP original — duas peças extras:
  1. Correção retroativa em `services/pontuacao.py` (Phase 18): `gerente_media` passa a usar as 7 respostas, não 6 (pergunta 6 entra duas vezes por design — na média geral e isolada em Evolução). Sem migração de dado (nenhuma linha real ainda existe).
  2. Pipeline novo de qualidade de commit via IA (tabela `commit_qualidade`, extensão de `POST /ingest/commit`, sem gatilho novo) — alimenta a dimensão Qualidade só pra `arquetipo=padrao`.
- 5 dimensões e pesos fechados: Gerente 35% · Entrega 20% · Qualidade 20% · Autonomia 15% · Evolução 10%. Normalização por escala fixa (não percentil). Detalhes completos e fórmulas exatas na spec.
- Descopado nesta sessão: botão de anúncio de top performer (só ranking). Arquétipos reduzidos a 2 valores: `padrao` \| `consultoria_discovery` (não os 3 que o ROADMAP original sugeria).
- `GET /performance` já existe como stub (Phase 16) com `require_role("lider")` + `registrar_auditoria` — Phase 19 implementa o corpo real, preservando a auditoria.
- Próximo passo: invocar `/write-plan` (superpowers:writing-plans) usando a spec acima — Onda 1 back-end (migração + correção Phase 18 + pipeline de commit + cálculo de ranking + endpoint), Onda 2 UI (`/performance`).
