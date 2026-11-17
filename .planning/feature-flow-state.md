# Feature Flow State
feature: "Subárea PTA + frente da task por IA (software/mobile/dados/ia) + (processo seletivo do CITi) + nível da task escolhido pelo gerente (com selo, também em projetos reais) + auditoria de bugs (pull vs normal, desempenho, análise de projetos)"
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles, ds.ts)"
etapa: 12
etapa_nome: "concluído — deploy via PR"
gates_reusados: ["knowledge-graph (sem grafo; exploração direta por grep)"]
started_at: "2026-11-17T00:00:00Z"
last_saved: "2026-11-17T00:00:00Z"
status: "concluido"

## Concluído
- [x] Etapa 0 — worktree ../Documentador-pta (feat/pta a partir de origin/main 8d53c3e); auditoria disparada em subagente
- [x] Etapa 1 — Spec docs/superpowers/specs/2026-11-17-pta-nivel-gerente-design.md
- [x] Etapa 2 — Planos: plans/2026-11-17-pta-nivel-gerente-plan.md (13 tasks) e plans/2026-11-17-correcoes-auditoria-plan.md (13 tasks)
- [x] Etapa 3 — Onda 1: auditoria Tasks 1-10 (9bae2ce..8eedc6e) + PTA Tasks 1-7 (5ca5db4..1345f6d), tudo revisado; migrações v10/v11/v12 comentadas no schema
- [x] Etapas 4-11 — UI (reuso do ds existente, sem protótipo/motion): PTA 8-9, kanban (auditoria 11, PTA 10-12, frente F2); auditoria UI/a11y nas reviews
- [x] Etapa 12 — review final da branch + onda de correções (override/reordenar RBAC, corrida frente, órfã v12, corrida /performance). Verificação: pytest 1347/0, npm test 77/0, tsc ok, next build ok. Pendente: migrações v10-v13 no Supabase; checagem visual em produção; backfill_frente.

## Contexto relevante
- Subárea hoje: projects.subarea CHECK ('dados','dev','produto'); front só mostra Dados/Dev (app/page.tsx, shell/navItems.ts).
- Nível: classificador decide (ciclo.classificar_para_criacao); gerente só dá opiniao_nivel; líder resolve revisão (/revisao-nivel).
