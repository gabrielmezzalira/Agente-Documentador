## Feature Flow em Progresso

> **Sessão anterior encerrada com feature-flow ativo.**
> Use `/feature-flow` para retomar de onde parou.

- **Feature:** Phase 16: RBAC — Login Leve e Papéis de Acesso
- **Etapa atual:** Verificação final (Etapa 12) — concluída
- **Última sessão:** 2026-09-04T16:30:00Z

Para retomar: `/feature-flow` — a skill vai detectar o estado automaticamente.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260903-aeq | Fecha o gap real da Phase 13 (Kanban de Tasks — Métricas + Ganchos): endpoints performance-operacional (MET-01/06) e cycle-time/stats (MET-02), gate de DoD em patch_task (MET-08), extensão de MetricasTab.tsx/api.ts. MET-07 adiado, MET-04 não tocado. | 2026-09-03 | 040cb2c | [260903-aeq-implementar-o-escopo-real-da-phase-13-ka](./quick/260903-aeq-implementar-o-escopo-real-da-phase-13-ka/) |
| 260903-awe | Phase 14 (Confirmação de Transição + Reabertura + Bloqueio Manual): ConfirmTransicaoModal em drag-and-drop e no banner de sugestão da IA (resolve_task_sugestao agora passa por patch_task em vez de gravar coluna_kanban direto); tabela task_reaberturas + contador_reaberturas (motivo opcional); campos bloqueado_manual/bloqueado_em/bloqueado_por/bloqueado_resolvido_por/bloqueado_resolvido_em com gate 422. Migration em supabase_schema.sql ainda precisa ser aplicada manualmente no Supabase. | 2026-09-03 | 947074d | [260903-awe-implementar-phase-14-confirmacao-de-tran](./quick/260903-awe-implementar-phase-14-confirmacao-de-tran/) |
| 260903-bq4 | Phase 15 Parte 4 do SDD (Travamento Automático por Tempo, ALERT-01/02/03): relógio entrou_em_andamento_em setado/resetado em patch_task/create_task; job diário check_travamento_automatico no mesmo AsyncIOScheduler de main.py; POST /tasks/{id}/travado/override preservando histórico; badge "Travada" + ação de suprimir no kanban. Gap documentado (não implementado por instrução de escopo): replanejamento pós-lock do baseline do SprintCard (Parte 8). Migration pendente de aplicação manual no Supabase. | 2026-09-03/04 | d2bc21b | [260903-bq4-implementar-phase-15-parte-4-do-sdd-trav](./quick/260903-bq4-implementar-phase-15-parte-4-do-sdd-trav/) |
| 260904-rb1 | Phase 16 (RBAC — Login Leve e Papéis de Acesso, RBAC-01..05): tabela pessoa + login JWT em cookie httpOnly; auto-cadastro de operacional por casamento de email; gate global de autenticação em ~87 rotas (require_role/require_not_operacional/require_project_access); audit_log genérico + GET /performance protegido; frontend com /login, /cadastro, AuthGuard, apiFetch e abas filtradas por cargo. RBAC-03 aplicado só a dados futuros de Phase 18/19 (SPI interino da Phase 13 continua aberto pra Gerente). Gaps aceitos e documentados: require_project_access não cobre endpoints task_id-scoped nem os routers de Tecnologias/Documentos/Escopo/Config. Migration pendente de aplicação manual no Supabase + JWT_SECRET/FRONTEND_URL novos no Railway. | 2026-09-04 | 7b0cb5b | [260904-rb1-implementar-phase-16-rbac-login-leve](./quick/260904-rb1-implementar-phase-16-rbac-login-leve/) |

Last activity: 2026-09-04 - Completed quick task 260904-rb1: Phase 16 (RBAC — Login Leve e Papéis de Acesso)
