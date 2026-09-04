---
phase: 16-rbac-login-leve-e-papeis-de-acesso
plan: 01
subsystem: auth
tags: [fastapi, jwt, bcrypt, cookie, rbac, nextjs, supabase]

requires:
  - phase: 14-confirmacao-de-transicao-reabertura-bloqueio-manual
    provides: "Fluxo de tasks/kanban que o RBAC protege"
  - phase: 13-kanban-de-tasks-m-tricas-ganchos
    provides: "Tabela operacionais (project_id, nome, email) — base do casamento pessoa×operacionais"
provides:
  - "Tabela pessoa (email/nome/senha_hash/cargo) + login JWT em cookie httpOnly, sem refresh token"
  - "Auto-cadastro de operacional: claim de operacionais existente (casamento por email) ou pessoa nova sem projeto"
  - "Gate global de autenticação no backend inteiro (services/auth.get_current_pessoa) + camadas require_role/require_not_operacional/require_project_access"
  - "audit_log genérico (services/audit.registrar_auditoria) — pronto para Phase 17/18"
  - "GET /performance protegido (require_role('lider')), stub sem dado real"
  - "Frontend: /login, /cadastro, AuthGuard (redirect + contexto de auth), apiFetch com credentials:'include', abas filtradas por cargo"
affects: [17-avaliacao-do-gerente, 18-motor-de-score, 19-peso-por-arquetipo-e-ranking]

actuals:
  tokens: 62000
  tasks: 5
  commits: 5

tech-stack:
  added: ["PyJWT>=2.8,<3", "bcrypt>=4.1,<5"]
  patterns:
    - "Gate global via FastAPI dependencies=[Depends(...)] no app.include_router(), não por endpoint — cobre ~87 rotas sem tocar cada uma individualmente"
    - "Camadas de RBAC compostas por Depends aninhado (require_not_operacional/require_role dependem de get_current_pessoa) — FastAPI cacheia a resolução por request, sem custo duplicado"
    - "pessoa × operacionais casados por email em runtime, sem FK — evita migration em operacionais e mantém auto-cadastro simples"
    - "apiFetch() como wrapper único de credentials:'include' + rename mecânico de fetch( -> apiFetch( via sed, em vez de tocar 66 call sites manualmente"

key-files:
  created:
    - docudata-backend/services/auth.py
    - docudata-backend/services/audit.py
    - docudata-backend/routers/auth.py
    - docudata-backend/routers/performance.py
    - docudata-backend/tests/test_auth_login.py
    - docudata-backend/tests/test_auth_signup.py
    - docudata-backend/tests/test_rbac_gate.py
    - docudata-backend/tests/test_performance_stub.py
    - docudata-frontend/app/components/AuthGuard.tsx
    - docudata-frontend/app/login/page.tsx
    - docudata-frontend/app/cadastro/page.tsx
  modified:
    - docudata-backend/supabase_schema.sql
    - docudata-backend/models/schemas.py
    - docudata-backend/requirements.txt
    - docudata-backend/main.py
    - docudata-backend/routers/sprints.py
    - docudata-backend/routers/tasks.py
    - docudata-backend/tests/test_bloqueio_manual.py
    - docudata-backend/tests/test_metricas_novos_endpoints.py
    - docudata-backend/tests/test_project_usage.py
    - docudata-backend/tests/test_task_confirmacao_sugestao.py
    - docudata-backend/tests/test_task_reabertura.py
    - docudata-backend/tests/test_tasks_dod_gate.py
    - docudata-backend/tests/test_travamento_job_override.py
    - docudata-backend/tests/test_travamento_relogio.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/layout.tsx
    - docudata-frontend/app/projects/[id]/page.tsx

key-decisions:
  - "RBAC-03 (score/peso/fórmula/ranking restrito) aplicado só aos dados futuros de Phase 18/19 — metricas.py/MetricasTab.tsx (Phase 13, SPI interino) não muda pra Gerente, só ganha require_not_operacional (que Gerente sempre passa). Decidido no brainstorming após o usuário apontar contradição na primeira resposta."
  - "require_project_access só cobre GET /tasks e os 2 endpoints de sprint por projeto (project_id direto no path/query) — endpoints task_id-scoped, funcionalidades.router (Escopo) e projects.router (config) ficam só com o gate básico de login, documentado como gap aceito em vez de silenciosamente ignorado."
  - "Auto-cadastro usa lista global de operacionais sem conta (todos os projetos) — claim em uma linha vale pra todas as linhas com o mesmo email, via casamento em runtime, sem FK nova em operacionais."
  - "gsd-execute-phase não serve pra plano em .planning/quick/ (exige .planning/phases/XX-nome/ com phase-plan-index) — as 5 tasks foram executadas diretamente nesta sessão, mesmo padrão usado nas Phases 13/14/15."
  - "8 arquivos de teste pré-existentes precisaram de cookie de sessão autenticado (cargo=gerente) no próprio _patch_and_client — não estava no PLAN.md original, necessário pra manter 'zero regressão' real depois do gate global entrar em vigor (Task 3)."

patterns-established:
  - "Todo novo router deve decidir explicitamente sua camada de auth ao ser registrado em main.py: get_current_pessoa (login básico), require_not_operacional (bloqueia cargo=operacional) ou require_role(cargo) (só um cargo específico) — nunca sem dependency nenhuma, exceto auth.router (única rota pública)."
  - "Testes que batem em rotas atrás do gate precisam setar cookie via tc.cookies.set('docudata_session', criar_jwt(...)) no próprio _patch_and_client — convenção nova a partir desta phase."

requirements-completed: [RBAC-01, RBAC-02, RBAC-03, RBAC-04, RBAC-05]

coverage:
  - id: D1
    description: "Tabela pessoa + POST /auth/login resolve cargo da sessão via cookie JWT httpOnly (sem refresh token)"
    requirement: "RBAC-01"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_auth_login.py (3 testes: login válido, senha errada, email inexistente)"
        status: pass
      - kind: unit
        ref: "docudata-backend/tests/test_auth_signup.py (5 testes: claim válido, claim email não bate, claim duplicado, signup novo, signup novo duplicado)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Gerente/Líder acessam qualquer projeto sem restrição; Operacional só passa em require_project_access quando existe operacionais.email == pessoa.email no project_id da rota (GET /tasks, POST/GET /projects/{id}/sprints)"
    requirement: "RBAC-02"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_rbac_gate.py (6 testes: 401 sem cookie, 403 operacional em rota bloqueada, 200 gerente, 403/200 require_project_access por vínculo, bypass gerente)"
        status: pass
    human_judgment: false
  - id: D3
    description: "metricas.py/painel.py/operacionais.py e os 3 endpoints administrativos de sprints.py (baseline/health/delete) recusam cargo=operacional com 403, sem mudar comportamento pra Gerente/Líder"
    requirement: "RBAC-02, RBAC-03"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_rbac_gate.py::test_operacional_bloqueado_em_rota_require_not_operacional, test_gerente_acessa_rota_require_not_operacional"
        status: pass
      - kind: unit
        ref: "Suíte completa de Phase 13/14/15 (96 testes) continua passando após a Task 3 — confirma que Gerente/Líder não perderam nenhum acesso"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET /performance retorna 403 pra não-Líder via require_role('lider') dedicado (não reaproveita require_not_operacional); grava audit_log a cada acesso de Líder"
    requirement: "RBAC-04, RBAC-05"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_performance_stub.py (3 testes: 401 sem cookie, 403 gerente, 200 líder + audit_log gravado)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Frontend: /login e /cadastro funcionam ponta a ponta contra os endpoints de auth; abas escopo/painel/metricas/config somem da UI pra cargo=operacional; toda chamada de api.ts manda credentials:'include'"
    verification:
      - kind: other
        ref: "npx tsc --noEmit (0 erros) + npm run build (Compiled successfully, /login e /cadastro geradas como rotas estáticas)"
        status: pass
    human_judgment: true
    rationale: "Compilação e build confirmam que o código está correto e a UI renderiza sem quebrar, mas o fluxo real de login/cadastro num navegador contra o Supabase de produção não foi testado manualmente nesta sessão — requer aplicar a migration e ter pelo menos um pessoa/operacional real no banco."

duration: 105min
completed: 2026-09-04
status: complete
---

# Quick Task 260904-rb1: Phase 16 — RBAC Login Leve e Papéis de Acesso

**Login JWT em cookie httpOnly (sem auth v1 removido), gate global de autenticação em ~87 rotas do backend, auto-cadastro de operacional por casamento de email, e telas de login/cadastro no frontend — fecha RBAC-01..05 sem acoplar com o Motor de Score (Phase 18) ou Ranking (Phase 19), que ainda não existem.**

## Performance

- **Duration:** ~105 min (brainstorming + spec + plano + execução das 5 tasks, nesta sessão)
- **Completed:** 2026-09-04
- **Tasks:** 5 (1-4 Onda 1 backend, 5 Onda 2 frontend)
- **Files modified:** 28 (11 criados, 17 modificados)

## Accomplishments

- Tabela `pessoa` (email/nome/senha_hash/cargo) e `audit_log`; login por email/senha (`POST /auth/login`) emite JWT auto-contido em cookie httpOnly+Secure+SameSite=None, sem refresh token (RBAC-01)
- Auto-cadastro de Operacional: `GET /auth/operacionais-sem-conta` lista globalmente (todos os projetos) linhas de `operacionais` sem `pessoa` correspondente; `POST /auth/signup/claim` cria a conta casando por email (vale pra todas as linhas com esse email, em qualquer projeto); `POST /auth/signup/novo` cria conta sem projeto vinculado. Nenhuma rota de cadastro aceita `cargo` != `operacional`
- Gate global de enforcement: todo router do backend (exceto `auth.router`) exige `Depends(get_current_pessoa)` no mínimo, aplicado via `app.include_router(..., dependencies=[...])` em vez de tocar cada endpoint individualmente; `metricas.py`/`painel.py`/`operacionais.py` e os 3 endpoints administrativos de `sprints.py` ganham `require_not_operacional`; `GET /tasks` e os 2 endpoints de sprint por projeto ganham `require_project_access` (casamento `operacionais.email` == `pessoa.email` + `project_id`) (RBAC-02, RBAC-03)
- CORS corrigido: `allow_origins=["*"]` (incompatível com cookie credenciado cross-site) virou `FRONTEND_URL` explícita
- `services/audit.registrar_auditoria` genérico + `GET /performance` (stub, `require_role("lider")` dedicado, grava auditoria a cada acesso) (RBAC-04, RBAC-05)
- Frontend: `/login`, `/cadastro` (claim + novo), `AuthGuard` (redirect pra `/login` em 401, contexto `useAuth()`), `apiFetch()` com `credentials:"include"` substituindo as 66 chamadas `fetch(` existentes em `api.ts`, abas `escopo`/`painel`/`metricas`/`config` filtradas da UI pra `cargo=operacional`
- 20 testes novos (8 de login/signup, 6 de gate RBAC, 3 de `/performance`, mais os 8 arquivos de teste pré-existentes corrigidos para autenticar); 96 testes passando no total, zero regressão real

## Task Commits

1. **Task 1: Migração pessoa/audit_log + schemas** - `fa74abd` (feat)
2. **Task 2: services/auth.py + router auth.py** - `29f8c92` (feat)
3. **Task 3: Gate global de enforcement + CORS + camadas por papel** - `88b13d8` (feat)
4. **Task 4: audit_log + GET /performance protegido** - `2276ca7` (feat)
5. **Task 5: Frontend — login, cadastro, guarda de rota, abas por papel** - `7b0cb5b` (feat)

## Files Created/Modified

- `docudata-backend/supabase_schema.sql` - bloco `-- Phase 16`: tabelas `pessoa`, `audit_log`
- `docudata-backend/models/schemas.py` - `LoginRequest/Response`, `MeResponse`, `OperacionalSemContaResponse`, `SignupClaimRequest`, `SignupNovoRequest`
- `docudata-backend/requirements.txt` - `PyJWT`, `bcrypt`
- `docudata-backend/services/auth.py` - hash/verify senha, criar/decodificar JWT, `get_current_pessoa`, `require_role`, `require_not_operacional`, `require_project_access`
- `docudata-backend/services/audit.py` - `registrar_auditoria`
- `docudata-backend/routers/auth.py` - login, logout, me, operacionais_sem_conta, signup_claim, signup_novo
- `docudata-backend/routers/performance.py` - stub protegido
- `docudata-backend/main.py` - CORS com `FRONTEND_URL`, `auth.router` público, todos os outros routers com `dependencies=[...]`
- `docudata-backend/routers/sprints.py` - `require_not_operacional` (baseline/health/delete), `require_project_access` (create/list por projeto)
- `docudata-backend/routers/tasks.py` - `require_project_access` em `list_tasks`
- 8 arquivos de teste pré-existentes - cookie autenticado (`cargo=gerente`) no `_patch_and_client` de cada um
- `docudata-frontend/app/lib/api.ts` - `apiFetch`, `MeResponse`/`LoginResponse`/`OperacionalSemConta`, 6 funções de auth, 66 call sites renomeados
- `docudata-frontend/app/components/AuthGuard.tsx` - novo, redirect + contexto de auth
- `docudata-frontend/app/login/page.tsx`, `app/cadastro/page.tsx` - novos
- `docudata-frontend/app/layout.tsx` - envolve `{children}` com `AuthGuard`
- `docudata-frontend/app/projects/[id]/page.tsx` - abas filtradas por `cargo`

## Decisions Made

- RBAC-03 aplicado só a dados futuros de Phase 18/19 — SPI interino da Phase 13 continua 100% visível pra Gerente (decisão revisada durante o brainstorming após o usuário apontar uma contradição na minha primeira proposta)
- `require_project_access` cobre só as rotas com `project_id` direto no path/query — endpoints `task_id`-scoped, `funcionalidades.router` e `projects.router` ficam com gap aceito e documentado (ver `<objective>` do PLAN.md), não implementados silenciosamente
- `gsd-execute-phase` não se aplica a planos em `.planning/quick/` (exige `.planning/phases/`) — as 5 tasks foram executadas diretamente nesta sessão, sem subagentes, mesmo padrão das Phases 13/14/15
- Onda 2 (frontend) foi confirmada como necessária pelo usuário antes de avançar pra Phase 17 — sem ela, o app ficaria inutilizável (backend já exige sessão, frontend não sabia logar)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 8 arquivos de teste pré-existentes quebrados pelo gate global (Task 3)**
- **Found during:** Task 3, ao rodar a suíte completa após o gate global entrar em vigor
- **Issue:** `test_bloqueio_manual.py`, `test_metricas_novos_endpoints.py`, `test_project_usage.py`, `test_task_confirmacao_sugestao.py`, `test_task_reabertura.py`, `test_tasks_dod_gate.py`, `test_travamento_job_override.py`, `test_travamento_relogio.py` — 43 testes passaram a retornar 401 porque nenhum mandava cookie de sessão (não existia autenticação antes desta phase)
- **Fix:** Adicionado `monkeypatch.setenv("JWT_SECRET", ...)` + `tc.cookies.set("docudata_session", criar_jwt(..., cargo="gerente"))` no `_patch_and_client` de cada um dos 8 arquivos
- **Files modified:** os 8 arquivos listados acima
- **Verification:** `pytest -q` completo — 96 passed, só os 4 pré-existentes (não relacionados) continuam falhando
- **Committed in:** `88b13d8` (Task 3 commit, mesmo commit — a correção era parte inseparável de fechar a task sem regressão real)

---

**Total deviations:** 1 auto-fixed (1 bug de regressão em teste, categoria "necessário pra correção")
**Impact on plan:** Não estava no PLAN.md original (o plano previa só criar `test_rbac_gate.py`), mas era estritamente necessário — sem isso a Task 3 teria "zero regressão" só nominal, não real. Nenhum scope creep: só toque nos `_patch_and_client`, nenhuma mudança de lógica de teste.

## Issues Encountered

- 4 falhas pré-existentes em `test_schemas_and_client.py` (asserções desatualizadas, documentadas desde a Phase 13 SUMMARY.md) — confirmadas novamente como não relacionadas a esta phase, não tocadas

## User Setup Required

**Ação manual necessária no Supabase:** o bloco `-- Phase 16` de `supabase_schema.sql` (tabelas `pessoa`, `audit_log`) precisa ser aplicado manualmente no SQL Editor do Supabase, mesma convenção de todas as phases anteriores.

**Variáveis de ambiente novas no Railway:**
- `JWT_SECRET` — chave de assinatura do JWT (gerar uma string aleatória longa, nunca reusar entre ambientes)
- `FRONTEND_URL` — URL do frontend no Vercel (usada pelo CORS; sem isso o cookie de sessão não vai funcionar cross-site)

**Seed do primeiro Líder:** decisão explícita do brainstorming — sem endpoint de bootstrap. Inserir manualmente a primeira linha em `pessoa` via SQL Editor, com senha já hasheada (`bcrypt.hashpw(senha.encode(), bcrypt.gensalt())` num Python REPL local, ou qualquer gerador de hash bcrypt).

## Next Phase Readiness

- Phase 17 (Avaliação do Gerente) e Phase 18 (Motor de Score) podem reusar `services/audit.registrar_auditoria` diretamente quando criarem rotas de leitura de avaliação/score — nenhum código novo de auditoria será necessário, só chamar a função já existente
- Phase 19 (Ranking) substitui o corpo de `GET /performance` pelos dados reais — a proteção (`require_role("lider")`) e a auditoria já estão prontas, não precisam ser tocadas
- Gaps aceitos e documentados no PLAN.md (`<objective>`) ficam como dívida conhecida: `require_project_access` não cobre endpoints `task_id`-scoped nem os routers de Tecnologias/Documentos/Escopo/Config — se algum desses viraper um vetor de abuso real (não apenas teórico), vale abrir uma quick task dedicada
- Spot-check manual em produção (não automatizado nesta sessão): aplicar a migration, criar o Líder via SQL, logar, confirmar abas por papel, testar auto-cadastro de um operacional real — ver seção "User Setup Required" acima

## Test Results

**Backend:**
```
docudata-backend/tests/test_auth_login.py: 3 passed
docudata-backend/tests/test_auth_signup.py: 5 passed
docudata-backend/tests/test_rbac_gate.py: 6 passed
docudata-backend/tests/test_performance_stub.py: 3 passed
Suíte completa: 96 passed, 4 failed (pré-existentes, não relacionados — test_schemas_and_client.py)
```

**Frontend:**
```
npx tsc --noEmit: 0 errors
npm run build: Compiled successfully — /login e /cadastro geradas como rotas estáticas
```

---
*Phase: 16-rbac-login-leve-e-papeis-de-acesso*
*Completed: 2026-09-04*

## Self-Check: PASSED

Todos os arquivos criados/modificados verificados em disco; os cinco commits de task (`fa74abd`, `29f8c92`, `88b13d8`, `2276ca7`, `7b0cb5b`) verificados presentes em `git log`; suíte de testes completa (96 testes) e `tsc --noEmit`/`npm run build` executados nesta sessão com sucesso.
