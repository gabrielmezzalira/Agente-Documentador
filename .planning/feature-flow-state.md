# Feature Flow State
feature: "Subárea PTA (processo seletivo do CITi) + nível da task escolhido pelo gerente (com selo, também em projetos reais) + auditoria de bugs (pull vs normal, desempenho, análise de projetos)"
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles, ds.ts)"
etapa: 2
etapa_nome: "Execução do back-end (Onda 1)"
gates_reusados: ["knowledge-graph (sem grafo; exploração direta por grep)"]
started_at: "2026-11-17T00:00:00Z"
last_saved: "2026-11-17T00:00:00Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — worktree ../Documentador-pta (feat/pta a partir de origin/main 8d53c3e); auditoria disparada em subagente
- [x] Etapa 1 — Spec docs/superpowers/specs/2026-11-17-pta-nivel-gerente-design.md
- [x] Etapa 2 — Planos: plans/2026-11-17-pta-nivel-gerente-plan.md (13 tasks) e plans/2026-11-17-correcoes-auditoria-plan.md (13 tasks)
- [ ] Etapa 3 — Onda 1 ← PRÓXIMA

## Contexto relevante
- Subárea hoje: projects.subarea CHECK ('dados','dev','produto'); front só mostra Dados/Dev (app/page.tsx, shell/navItems.ts).
- Nível: classificador decide (ciclo.classificar_para_criacao); gerente só dá opiniao_nivel; líder resolve revisão (/revisao-nivel).
