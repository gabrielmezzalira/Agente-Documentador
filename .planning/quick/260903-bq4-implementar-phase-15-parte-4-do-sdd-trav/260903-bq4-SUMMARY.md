---
phase: 15-travamento-automatico-por-tempo-trava-do-baseline-do-sprintcard
plan: 01
subsystem: api
tags: [fastapi, apscheduler, supabase, react, kanban, task-travamento]

requires:
  - phase: 14-confirmacao-de-transicao-reabertura-bloqueio-manual
    provides: patch_task com gates DoR/DoD/WIP + confirmação de transição, TasksKanbanTab, padrão visual de bloqueado_manual
provides:
  - "entrou_em_andamento_em setado/resetado em patch_task e create_task, ancorando o relógio em toda entrada/saída de em_andamento (inclusive reabertura)"
  - "check_travamento_automatico: job diário no mesmo AsyncIOScheduler de main.py, marca travado_automatico=true quando dias_desde(entrou_em_andamento_em) >= pontos × 2 e travado_override não é true"
  - "POST /tasks/{id}/travado/override: supressão do alerta pelo gerente sem apagar travado_automatico (histórico preservado)"
  - "Badge ⏱ Travada no TaskCard + caixa de alerta com botão Suprimir no TaskModal, condicionados a travado_automatico && !travado_override"
affects: [18-motor-de-score, 16-rbac-papeis]

actuals:
  tokens: 6500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Job de scheduler sem parâmetros que chama get_client() internamente (mesmo padrão de notification_checker.py), registrado no AsyncIOScheduler já existente em main.py em vez de criar um segundo scheduler"
    - "Campo de supressão (travado_override) separado do campo de sinalização (travado_automatico) — o endpoint de override nunca escreve no segundo, preservando o histórico de que o sistema detectou o travamento"

key-files:
  created:
    - docudata-backend/services/travamento_checker.py
    - docudata-backend/tests/test_travamento_relogio.py
    - docudata-backend/tests/test_travamento_job_override.py
  modified:
    - docudata-backend/supabase_schema.sql
    - docudata-backend/models/schemas.py
    - docudata-backend/routers/tasks.py
    - docudata-backend/main.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/components/TasksKanbanTab.tsx

key-decisions:
  - "travado_automatico e travado_override são campos server-computed, ausentes de TaskCreate/TaskUpdate — só patch_task/create_task (transição de coluna) e o endpoint dedicado de override escrevem neles, nunca o cliente diretamente"
  - "O endpoint de override nunca toca travado_automatico — só grava travado_override/_por/_em — para que o job diário e o histórico de sinalização do sistema permaneçam intactos mesmo depois do gerente suprimir a exibição"
  - "sprints.py (trava do baseline do SprintCard, Parte 8) não foi tocado por instrução explícita do plano; o gap de 'revisão posterior gera registro separado de replanejamento' permanece documentado, não implementado"
  - "Nenhuma checagem de RBAC foi adicionada — travado_override_por é texto livre sem autenticação, mesma postura já aceita para bloqueado_resolvido_por na Phase 14"

patterns-established:
  - "Restrição de acoplamento com score futuro documentada via comentário inline no próprio arquivo do job (travamento_checker.py), não só em texto de plano — para sobreviver a quem só lê o código quando a Phase 18 existir"

requirements-completed: [ALERT-01, ALERT-02, ALERT-03]

coverage:
  - id: D1
    description: "entrou_em_andamento_em é setado em toda transição confirmada para em_andamento (qualquer origem, inclusive reabertura concluida->em_andamento) e no POST /tasks que já cria em em_andamento; reseta ao sair de em_andamento"
    requirement: "ALERT-01"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_travamento_relogio.py (8 testes: entrada de planejado, entrada por reabertura, saída para concluida, saída para planejado, PATCH sem tocar coluna_kanban, transição planejado->concluida direto, POST com em_andamento, POST com planejado default)"
        status: pass
    human_judgment: false
  - id: D2
    description: "travado_automatico e travado_override/_por/_em resetam ao sair de em_andamento ou ao reentrar"
    requirement: "ALERT-02"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_travamento_relogio.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "check_travamento_automatico, registrado no AsyncIOScheduler de main.py (interval hours=24), marca travado_automatico=true quando dias_decorridos >= pontos*2 e travado_override não é true; idempotente; ignora tasks sem entrou_em_andamento_em"
    requirement: "ALERT-01"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_travamento_job_override.py (6 testes de job: cruza limiar, não cruza, override=true ignora, já marcado é idempotente, entrou_em_andamento_em nulo é pulado, select filtra só em_andamento)"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /tasks/{id}/travado/override grava a supressão (travado_override/_por/_em) sem apagar travado_automatico; 409 se a task não está em em_andamento; 404 se não existe"
    requirement: "ALERT-03"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_travamento_job_override.py (3 testes de endpoint: caminho feliz, 409 fora de em_andamento, 404)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Badge ⏱ Travada no TaskCard e caixa de alerta com botão Suprimir no TaskModal, visíveis só quando travado_automatico=true e travado_override=false; suprimir chama overrideTravamentoTask e some o badge imediatamente"
    verification:
      - kind: other
        ref: "npx tsc --noEmit (zero erros novos em TasksKanbanTab.tsx/api.ts) + leitura de código (condição !task.travado_override espelhada em TaskCard e TaskModal)"
        status: pass
    human_judgment: true
    rationale: "Comportamento de UI (badge aparece/some, modal mostra caixa de alerta, clique chama a API e fecha o modal) não tem teste de componente React neste projeto — só tsc/build confirmam compilação. Spot-check manual num dev server real não foi executado nesta sessão."

duration: 15min
completed: 2026-09-03
status: complete
---

# Quick Task 260903-bq4: Phase 15 — Travamento Automático por Tempo (Parte 4 do SDD)

**Relógio entrou_em_andamento_em ancorado em patch_task/create_task, job diário check_travamento_automatico no mesmo scheduler de main.py, endpoint de override que preserva histórico, e badge "Travada" no kanban de tasks — fecha ALERT-01/02/03 sem tocar em código de score.**

## Performance

- **Duration:** ~15min nesta sessão (Tasks 1 e 2 já haviam sido implementadas e commitadas em sessão anterior; esta sessão verificou, completou e commitou a Task 3, que já estava escrita no working tree, e escreveu este SUMMARY)
- **Completed:** 2026-09-03
- **Tasks:** 3
- **Files modified:** 9 (3 novos arquivos: 1 service + 2 testes; 6 modificados)

## Accomplishments

- `patch_task`/`create_task` gravam `entrou_em_andamento_em` e resetam `travado_automatico`/`travado_override`/`_por`/`_em` em toda entrada em `em_andamento` (qualquer origem, inclusive reabertura `concluida -> em_andamento`); resetam tudo ao sair de `em_andamento`; nenhum PATCH que não toca `coluna_kanban` ou que transiciona fora de `em_andamento` escreve nesses 5 campos (ALERT-01, ALERT-02)
- `services/travamento_checker.py` — `check_travamento_automatico()` roda diariamente no mesmo `AsyncIOScheduler` já usado por `check_and_send_notifications` em `main.py` (job `task_travamento_check`, `hours=24`), varre tasks em `em_andamento`, marca `travado_automatico=true` quando `dias_decorridos >= pontos × 2`, é idempotente e nunca marca tasks com `travado_override=true` (ALERT-01)
- `POST /tasks/{id}/travado/override` grava a supressão do gerente (`travado_override`, `travado_override_por`, `travado_override_em`) sem tocar `travado_automatico` — o histórico de que o sistema sinalizou o travamento é preservado mesmo depois de suprimido; 409 se a task não está em `em_andamento`, 404 se não existe (ALERT-03)
- Badge "⏱ Travada" no `TaskCard` + caixa de alerta com input de autor e botão "Suprimir alerta" no `TaskModal`, ambos condicionados a `travado_automatico && !travado_override`, seguindo o mesmo padrão visual já usado para `bloqueado_manual` na Phase 14 (ALERT-03)
- Comentário inline em `travamento_checker.py` documentando por escrito que o job nunca escreve em nenhum campo de score, para quando a Phase 18 (Motor de Score) existir
- 14 testes novos (8 em `test_travamento_relogio.py`, 9 em `test_travamento_job_override.py` — job + endpoint), todos passando junto com toda a suíte pré-existente de `tasks.py` (36 testes no total entre os arquivos relevantes de Phase 13/14/15)

## Task Commits

1. **Task 1: Relógio entrou_em_andamento_em** - `b848e68` (feat)
2. **Task 2: Job diário de travamento + endpoint de override** - `f79288a` (feat)
3. **Task 3: Badge "Travada" + ação de suprimir no kanban** - `d2bc21b` (feat)

## Files Created/Modified

- `docudata-backend/supabase_schema.sql` - bloco `-- Phase 15`: `entrou_em_andamento_em`, `travado_automatico`, `travado_override`, `travado_override_por`, `travado_override_em` em `tasks`
- `docudata-backend/models/schemas.py` - `TaskResponse` com os 5 campos novos (server-computed, ausentes de `TaskCreate`/`TaskUpdate`)
- `docudata-backend/routers/tasks.py` - `create_task` ancora o relógio ao criar já em `em_andamento`; `patch_task` seta/reseta os 5 campos na detecção de entrada/saída de `em_andamento` (reusando a mesma captura de `coluna_kanban` original já usada pela lógica de reabertura da Phase 14); novo `POST /{task_id}/travado/override`
- `docudata-backend/services/travamento_checker.py` - novo, `check_travamento_automatico()`
- `docudata-backend/main.py` - job registrado no `_scheduler` existente (`hours=24`, `id="task_travamento_check"`); `POST /tasks/travamento/check` para trigger manual
- `docudata-backend/tests/test_travamento_relogio.py` - novo, 8 testes
- `docudata-backend/tests/test_travamento_job_override.py` - novo, 9 testes (job + endpoint)
- `docudata-frontend/app/lib/api.ts` - `TaskKanbanResponse` com os 5 campos novos; `overrideTravamentoTask`
- `docudata-frontend/app/components/TasksKanbanTab.tsx` - badge no `TaskCard`; caixa de alerta + `handleOverrideTravamento` no `TaskModal`

## Decisions Made

- `travado_automatico`/`travado_override`/`_por`/`_em` nunca aparecem em `TaskCreate`/`TaskUpdate` — só o backend (transição de coluna gated e o endpoint dedicado) escreve neles, fechando a ameaça T-15-03 do threat model do plano
- O endpoint de override nunca escreve `travado_automatico` — só suprime a exibição (`!travado_override` na condição do badge), preservando o histórico de sinalização do sistema para auditoria futura
- `sprints.py` (trava do baseline, Parte 8 do SDD) não foi tocado — o gap de "revisão posterior gera registro separado de replanejamento" permanece documentado no `<objective>` do plano, não implementado, por instrução explícita de escopo
- Nenhuma checagem de RBAC foi adicionada; `travado_override_por` é texto livre sem autenticação, mesma postura já aceita para `bloqueado_resolvido_por` na Phase 14 (T-15-02, `accept`)

## Deviations from Plan

None — plano executado exatamente como escrito. Tasks 1 e 2 já estavam implementadas e commitadas quando esta sessão começou; Task 3 já estava escrita no working tree (não commitada) e foi verificada linha a linha contra o `<action>` do plano antes do commit, sem necessidade de ajuste.

## Issues Encountered

None.

## User Setup Required

None — nenhuma configuração de serviço externo necessária. A migration em `docudata-backend/supabase_schema.sql` (bloco `-- Phase 15`) precisa ser aplicada manualmente no Supabase, mesma convenção das phases anteriores.

## Next Phase Readiness

- ALERT-01/02/03 fechados. RBAC (Phase 16) e Motor de Score (Phase 17-18) continuam fora de escopo; `travado_automatico` está pronto para nunca ser lido por nenhuma dimensão de score quando a Phase 18 existir — comentário inline já documenta a restrição.
- Gap conhecido e documentado (não bloqueante para esta phase): a trava do baseline do SprintCard (`sprints.py`, Parte 8) não tem mecanismo de replanejamento pós-lock — revisão posterior de um baseline lockado é hoje permanentemente impossível. Fica para uma phase futura que trate a Parte 8 do SDD explicitamente.
- Spot-check manual recomendado antes de considerar a phase 100% fechada em produção: `POST /tasks/travamento/check` disparado manualmente numa task com `pontos=1` e `entrou_em_andamento_em` de 3 dias atrás (inserida via SQL) deve resultar em `travado_automatico=true`; o badge deve aparecer no kanban real; "Suprimir alerta" deve fazer o badge sumir sem apagar `travado_automatico` no banco.

## Test Results

**Backend:**
```
docudata-backend/tests/test_travamento_relogio.py: 8 passed
docudata-backend/tests/test_travamento_job_override.py: 9 passed
tests/test_tasks_dod_gate.py tests/test_task_reabertura.py tests/test_bloqueio_manual.py tests/test_task_confirmacao_sugestao.py: 19 passed
Total (suíte relevante de tasks.py): 36 passed
```

**Frontend:**
```
npx tsc --noEmit: 0 errors
```

---
*Phase: 15-travamento-automatico-por-tempo-trava-do-baseline-do-sprintcard*
*Completed: 2026-09-03*

## Self-Check: PASSED

Todos os arquivos criados/modificados verificados em disco; os três commits de task (`b848e68`, `f79288a`, `d2bc21b`) verificados presentes em `git log`; suíte de testes relevante (36 testes) e `npx tsc --noEmit` executados nesta sessão com sucesso.
