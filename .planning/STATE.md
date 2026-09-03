## Feature Flow em Progresso

> **Sessão anterior encerrada com feature-flow ativo.**
> Use `/feature-flow` para retomar de onde parou.

- **Feature:** Agente Documentador v2 — Matriz de Escopo + TransicaoStatus + Campos Novos em Projeto (Phase 7)
- **Etapa atual:** Plano de implementação (gsd-plan-phase)
- **Última sessão:** 2026-09-03T23:02:14Z

Para retomar: `/feature-flow` — a skill vai detectar o estado automaticamente.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260903-aeq | Fecha o gap real da Phase 13 (Kanban de Tasks — Métricas + Ganchos): endpoints performance-operacional (MET-01/06) e cycle-time/stats (MET-02), gate de DoD em patch_task (MET-08), extensão de MetricasTab.tsx/api.ts. MET-07 adiado, MET-04 não tocado. | 2026-09-03 | 040cb2c | [260903-aeq-implementar-o-escopo-real-da-phase-13-ka](./quick/260903-aeq-implementar-o-escopo-real-da-phase-13-ka/) |
| 260903-awe | Phase 14 (Confirmação de Transição + Reabertura + Bloqueio Manual): ConfirmTransicaoModal em drag-and-drop e no banner de sugestão da IA (resolve_task_sugestao agora passa por patch_task em vez de gravar coluna_kanban direto); tabela task_reaberturas + contador_reaberturas (motivo opcional); campos bloqueado_manual/bloqueado_em/bloqueado_por/bloqueado_resolvido_por/bloqueado_resolvido_em com gate 422. Migration em supabase_schema.sql ainda precisa ser aplicada manualmente no Supabase. | 2026-09-03 | 947074d | [260903-awe-implementar-phase-14-confirmacao-de-tran](./quick/260903-awe-implementar-phase-14-confirmacao-de-tran/) |
| 260903-bq4 | Phase 15 Parte 4 do SDD (Travamento Automático por Tempo, ALERT-01/02/03): relógio entrou_em_andamento_em setado/resetado em patch_task/create_task; job diário check_travamento_automatico no mesmo AsyncIOScheduler de main.py; POST /tasks/{id}/travado/override preservando histórico; badge "Travada" + ação de suprimir no kanban. Gap documentado (não implementado por instrução de escopo): replanejamento pós-lock do baseline do SprintCard (Parte 8). Migration pendente de aplicação manual no Supabase. | 2026-09-03 | d2bc21b | [260903-bq4-implementar-phase-15-parte-4-do-sdd-trav](./quick/260903-bq4-implementar-phase-15-parte-4-do-sdd-trav/) |

Last activity: 2026-09-03 - Completed quick task 260903-bq4: Phase 15 (Travamento Automático por Tempo — ALERT-01/02/03)
