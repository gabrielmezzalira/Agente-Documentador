# Feature Flow State
feature: "Phase 16: RBAC — Login Leve e Papéis de Acesso"
modo: "FULL"
tier: "COMPLEXA"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js"
etapa: 12
etapa_nome: "Concluído"
gates_reusados: ["prototype (tier complexa, mas telas simples de formulário sem padrão visual novo — pulado por decisão direta, não gate automático)"]
started_at: "2026-09-04T00:00:00Z"
last_saved: "2026-09-04T16:30:00Z"
status: "concluido"

## Concluído
- [x] Etapa 0 — Onboarding de repositório: grafo estrutural (AST, sem LLM) gerado em docudata-backend/graphify-out (658 nós, 1563 edges) e docudata-frontend/graphify-out (531 nós, 918 edges) via `graphify update <pasta> --no-cluster`.
- [x] Etapa 1 — Requisitos via /brainstorm: spec aprovada e commitada em `docs/superpowers/specs/2026-09-04-rbac-login-leve-papeis-acesso-design.md` (commit 8045127)
- [x] Etapa 2 — Plano de implementação via /write-plan: `.planning/quick/260904-rb1-implementar-phase-16-rbac-login-leve/260904-rb1-PLAN.md` (5 tasks)
- [x] Etapa 3 — Execução do back-end (Onda 1), executada diretamente (gsd-execute-phase não serve pra .planning/quick/): Task 1 (fa74abd), Task 2 (29f8c92), Task 3 (88b13d8 — corrigiu 8 testes pré-existentes sem cookie), Task 4 (2276ca7). Confirmado com o usuário antes de avançar.
- [x] Etapas 4-11 — puladas por decisão direta: telas de login/cadastro são formulários simples, sem padrão visual novo, seguindo o mesmo estilo inline já usado em todo o resto do app (sem design system pra reaproveitar ou criar).
- [x] Etapa 12 — Verificação final: Task 5 (7b0cb5b, frontend/Onda 2). 96 testes de backend passando (4 pré-existentes não relacionados), `tsc --noEmit` e `npm run build` limpos. SUMMARY.md escrito em `.planning/quick/260904-rb1-implementar-phase-16-rbac-login-leve/260904-rb1-SUMMARY.md`.

## Contexto relevante — resumo final
- **RBAC-01..05 fechados.** Login JWT em cookie httpOnly (sem refresh); auto-cadastro de operacional por casamento de email com `operacionais`; gate global de autenticação; audit_log genérico; GET /performance protegido.
- **Gates reaproveitados nesta rodada:** grafo estrutural de código (Etapa 0, ganho real — evitou reexploração via grep na hora de planejar); pipeline de design pulado por decisão direta (Etapas 4-11), já que não havia nada de design system pra reaproveitar nem criar.
- **Ação manual pendente no Supabase:** aplicar migration `-- Phase 16` (tabelas pessoa, audit_log); variáveis novas no Railway: JWT_SECRET, FRONTEND_URL; seed manual do primeiro Líder via SQL.
- **Gaps aceitos e documentados** (não são esquecimento): require_project_access não cobre endpoints task_id-scoped nem routers de Tecnologias/Documentos/Escopo/Config — ver `<objective>` do PLAN.md.
- Lição registrada nesta sessão: /graphify completo (código + toda .planning/) sem GEMINI_API_KEY bate rate limit de sessão rápido — corrigido instalando a versão nova da feature-flow-lean (Etapa 0 só mapeia código por padrão).
