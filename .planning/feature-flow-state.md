# Feature Flow State
feature: "Alinhamento à proposta (Cultura Data Driven / pull / piso / pontuação padronizada). Rodada A: régua única 1/2/3/5 + classificador (modo sombra), aprovação de funcionalidade, fim dos 100 pontos do projeto (escopo calculado, previsto = foto da planning). Rodada B (depois): SPI só da sprint, piso por pessoa, relógio do cliente que pausa de verdade, bônus por rapidez."
modo: "FULL"
tier: "COMPLEXA"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles, design system em app/components/ds)"
etapa: 2
etapa_nome: "Execução do back-end (Onda 1) — A1, Tasks 1-9 do plano"
gates_reusados: ["knowledge-graph"]
started_at: "2026-10-22T13:00:00Z"
last_saved: "2026-10-22T15:00:00Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — graphify update (código) em docudata-backend e docudata-frontend/app, sem docs
- [x] Etapa 1 — Brainstorm A1 (spec docs/superpowers/specs/2026-10-22-regua-aprovacao-previsto-design.md)
- [x] Etapa 2 — Plano A1 (docs/superpowers/plans/2026-10-22-regua-aprovacao-previsto.md; Onda 1 = Tasks 1-9, Onda 2 = Tasks 10-15)
- [ ] Etapa 3 — Onda 1 back-end ← PRÓXIMA (perguntar ao usuário: subagent-driven com sonnet ou inline)

## Contexto relevante
- Worktree ../Documentador-proposta, branch feat/regua-aprovacao-escopo, base fix/painel-ajustes-pequenos (2e4e250, sobre origin/main 48d0c87).
- Decisões já tomadas: memória project_spi_piso_proposta_2026-10-22.
- Estado anterior arquivado em .planning/feature-flow-state-2026-09-25-historico-avaliacoes.md.
- Rodada A dividida: A1 (régua, aprovação, fim do orçamento/valor/comparação de modos, previsto) e A2 (agente classificador híbrido LangGraph, spec própria).
- Decisões A1: aprovação de funcionalidade pelo gerente; escopo = aprovadas ÷ total (peso igual); previsto = foto do início + surgiu na sprint (sem extras); legado convertido só nas abertas; tirar valor_projeto da tela; comparação de modos removida.
