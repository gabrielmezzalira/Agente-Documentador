# Feature Flow State
feature: "Entrega não vira 0 quando não houve o que entregar — (1) bloqueio tipo 'cliente' (só gerente marca) isenta a task de Entrega no fechamento; (2) sprint PULL sem nada pra puxar → Entrega sem dado, não 0; (3) correção retroativa via SQL manual."
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles)"
etapa: 12
etapa_nome: "Verificação final — automatizada concluída; migração manual + checklist em navegador pendentes (usuário)"
gates_reusados: ["knowledge-graph", "design-system (padrão inline existente)", "design-doc", "libs", "prototype"]
started_at: "2026-09-23T23:30:00Z"
last_saved: "2026-09-24T02:07:44Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — graphify-out existente reaproveitado (não regenerado)
- [x] Etapa 1 — Brainstorm bounded, design aprovado pelo usuário
- [x] Etapa 2 — Plano em docs/superpowers/plans/2026-09-23-entrega-sem-dado-dependencia-cliente-plan.md (Onda 1 = Tasks 1-5, Onda 2 = Tasks 6-7), execução inline
- [x] Onda 1 — Tasks 1-5 (b1394f8, 5f7f765, 6032251, cb2a091, e6cab7c). Backend: 603 passando.
- [x] Onda 2 — Task 6 (69712fe): select "Tipo do bloqueio" no TaskModal, chip "Aguardando cliente", ajuda. tsc limpo + npm test 43/43.
- [x] Task 7 — verificação automatizada.

## Pendência real (não fingir que foi feito)
- NÃO pushado ainda.
- Usuário precisa rodar no Supabase ANTES do deploy: ALTER TABLE tasks ADD COLUMN bloqueio_tipo + UPDATE retroativo da PULL vazia (supabase_schema.sql, bloco "Dependência do cliente").
- Retroativo de task de cliente em sprint fechada: queries comentadas no schema (SELECT candidatos + WITH alvo ... UPDATE), uma task por vez.
- Checklist manual em navegador pendente.

## Contexto relevante
- Estado anterior (Entrega 4 Modos de Trabalho, aguardando checklist manual do usuário) arquivado em .planning/feature-flow-state-2026-09-21-modos-entrega4.md.
- Decisões do usuário: só gerente marca tipo cliente; tipo cliente DENTRO do bloqueio existente (bloqueado_manual); corrigir retroativo via SQL que ele roda; contador "sprints avaliadas" NÃO muda (conta sprints avaliadas pelo gerente = referencial de top performer).
- Código-chave: services/pontuacao.py:97-130 (loop de tasks no fechamento), :203-235 (nota relativa PULL, piso 1 faz 0/1=0), services/performance.py:163-176 (_entrega_atribuicao já devolve None com alocados=0), routers/tasks.py:851-960 (patch bloqueado_manual), :993 override_travamento (dispensa penalidade + reancora relógio), services/travamento_checker.py, TasksKanbanTab.tsx:449-500 (UI bloqueio), :986 auth.cargo.
