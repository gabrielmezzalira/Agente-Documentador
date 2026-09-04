# Phase 16 — RBAC: Login Leve e Papéis de Acesso

**Status:** Aprovado para planejamento (brainstorming concluído em 2026-09-04)
**Fase no ROADMAP:** `.planning/ROADMAP.md`, Phase 16, requisitos RBAC-01..05
**Depende de:** Phase 14 (fluxo de tasks que o RBAC protege), Phase 13 (`operacionais` table)
**Afeta:** Phase 17 (Avaliação do Gerente), Phase 18 (Motor de Score), Phase 19 (RBAC-03 real + `/performance` real)

## Contexto e objetivo

Hoje o DocuData é um espaço totalmente aberto — "sem auth v1" foi decisão consciente do MVP original (`CLAUDE.md`). Esta phase substitui isso por um login leve de verdade: email/senha resolve um cargo (`lider`, `gerente`, `operacional`), e esse cargo passa a determinar o que cada pessoa vê e pode fazer, com enforcement real no backend (não só ocultação no frontend).

**Fora de escopo desta phase** (documentado explicitamente, não é esquecimento):
- Recuperação de senha ("esqueci minha senha") — reset manual via SQL pelo Líder por enquanto
- Convite de Gerente/Líder pela UI — continua seed manual/SQL
- Refresh token / renovação de sessão — expira e pede login de novo
- Throughput-por-operacional e agregação cross-project nas métricas — fica pra Phase 19
- Qualquer restrição em `metricas.py`/`MetricasTab.tsx` para Gerente — Gerente continua vendo tudo, sem mudança
- Dados reais de `/performance` (ranking, breakdown por dimensão) — fica pra Phase 19, esta phase só cria o endpoint protegido vazio

## Decisões-chave (do brainstorming)

| Decisão | Escolha | Alternativa descartada |
|---|---|---|
| Mecanismo de sessão | JWT em cookie httpOnly+Secure+SameSite=None, sem refresh token | Bearer token em localStorage; sessão opaca em tabela própria |
| Bootstrap do primeiro Líder | Seed manual via SQL/script, sem endpoint de setup exposto | Endpoint `/auth/bootstrap` protegido por env var |
| `pessoa` × `operacionais` | Casamento por `email` em runtime, sem FK nova | FK `operacionais.pessoa_id` nullable |
| Auto-cadastro de Operacional | Lista global (todos os projetos) de `operacionais` sem conta; clicar "sou eu" cria `pessoa` com esse email — vale para TODAS as linhas de `operacionais` com esse email, em qualquer projeto | Claim por linha específica (só destrava aquele projeto) |
| Cadastro sem achar a si mesmo na lista | Cria só `pessoa` (`cargo=operacional`), sem nenhuma linha em `operacionais` — fica sem projeto até ser adicionado depois | Formulário de cadastro já pede projeto (expõe lista de projetos sem login) |
| Escopo do audit log (RBAC-05) | Constrói o mecanismo genérico agora (tabela + helper); só o stub `/performance` chama nesta phase | Adiar tudo para Phase 17/18 |
| Escopo de `/performance` (RBAC-04) | Cria stub protegido (`{"status":"ok"}`) atrás do `require_role("lider")` dedicado agora; Phase 19 substitui o corpo | Só a dependency isolada, sem rota nenhuma |
| Escopo de "score" (RBAC-03) | Aplica só aos dados NOVOS de Phase 18 (Motor de Score)/Phase 19 (Ranking) — `metricas.py` (SPI/cycle-time/throughput/CFD/performance-operacional) fica igual pra Gerente, sem `require_role` novo | Restringir também o SPI interino existente |
| Acesso de Operacional | ZERO acesso a métricas/painel/escopo/config — só vê abas Sprint, Tasks, Tecnologias, Documentos | Ver só a própria linha nas métricas (rejeitado — quer bloqueio total) |
| Mecanismo de enforcement | Gate global (toda rota exige login por padrão, via dependency no app inteiro) + allowlist de rotas públicas + camadas `require_role`/`require_not_operacional`/`require_project_access` por cima | Anotar `Depends(get_current_pessoa)` manualmente em cada um dos 20 routers |

## Modelo de dados

```sql
CREATE TABLE pessoa (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email        text NOT NULL UNIQUE,
    nome         text NOT NULL,
    senha_hash   text NOT NULL,
    cargo        text NOT NULL CHECK (cargo IN ('lider','gerente','operacional')),
    created_at   timestamptz DEFAULT now()
);

CREATE TABLE audit_log (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pessoa_id     uuid REFERENCES pessoa(id),
    pessoa_email  text NOT NULL,
    rota          text NOT NULL,
    acao          text NOT NULL,
    created_at    timestamptz DEFAULT now()
);
```

- `pessoa.email` casa em runtime com `operacionais.email` (tabela existente da Phase 13, `docudata-backend/supabase_schema.sql`) — sem FK nova, sem migration em `operacionais`.
- Sem tabela de sessão — o JWT é auto-contido (`sub=pessoa.id`, `cargo`, `exp`); login não grava nada além de emitir o cookie.
- Nenhuma rota de cadastro cria `cargo=gerente` ou `cargo=lider` — essas duas continuam exclusivamente por seed manual (Líder).

## Fluxo de autenticação — endpoints novos

Novo router `docudata-backend/routers/auth.py`:

| Rota | Método | Auth | Descrição |
|---|---|---|---|
| `/auth/login` | POST | pública | `{email, senha}` → valida `senha_hash` (bcrypt/`passlib`), seta cookie JWT httpOnly, retorna `{nome, cargo}` |
| `/auth/logout` | POST | requer sessão | limpa o cookie |
| `/auth/me` | GET | requer sessão | retorna `{nome, email, cargo}` da sessão atual |
| `/auth/operacionais-sem-conta` | GET | pública | lista `{operacional_id, nome, project_id, project_name}` de `operacionais` sem `pessoa` correspondente (email sem match) |
| `/auth/signup/claim` | POST | pública | `{operacional_id, email, senha}` → confirma/atualiza email daquela linha, cria `pessoa` (`cargo=operacional`), loga automaticamente |
| `/auth/signup/novo` | POST | pública | `{nome, email, senha}` → cria só `pessoa` (`cargo=operacional`), sem `operacionais`, loga automaticamente |

## Enforcement — gate global + camadas por papel

**Dependency base — `get_current_pessoa`** (em `docudata-backend/services/auth.py` ou similar): lê o cookie, decodifica o JWT, retorna `{id, email, cargo}` ou `401`. Aplicada como dependency default de todo o app (via `dependencies=[Depends(get_current_pessoa)]` no `FastAPI(...)`), com allowlist explícita das rotas públicas listadas acima (montadas num router/inclusão separada, sem essa dependency).

**Camadas adicionais:**
- `require_role("lider")` — `403` se `cargo != "lider"`. Usada em `/performance`.
- `require_not_operacional` — `403` se `cargo == "operacional"`. Aplicada em `routers/metricas.py`, `routers/painel.py`, rotas de config/baseline de `routers/sprints.py`, CRUD de `routers/operacionais.py`, e o bloco "config" de projeto.
- `require_project_access(project_id)` — libera direto para `lider`/`gerente`; para `operacional`, verifica se existe linha em `operacionais` com `project_id` + `email` batendo, senão `403`. Aplicada nas rotas que o Operacional pode acessar mas são escopadas por projeto (`tasks`, `sprints` leitura, `tecnologias`, `documentos`).

A maioria dos ~87 endpoints existentes só herda o gate base (login válido) e continua funcionando igual para Gerente/Líder — as camadas extras entram só nos routers listados acima.

## `/performance` (stub)

Novo router `docudata-backend/routers/performance.py`, um único endpoint:

```
GET /performance
  → require_role("lider")
  → registrar_auditoria(pessoa, "/performance", "acesso")
  → retorna {"status": "ok", "message": "Ranking ainda não implementado — Phase 19"}
```

Prova o mecanismo de 403 + auditoria ponta a ponta sem inventar dado que a Phase 19 ainda não define.

## Frontend (Next.js)

**Telas novas:**
- `/login` — email + senha, `POST /auth/login` com `credentials: "include"`. 401 → mensagem inline. Sucesso → redireciona pra `/`.
- `/cadastro` — duas opções: "já sou operacional em algum projeto" (busca em `GET /auth/operacionais-sem-conta`, clica → `POST /auth/signup/claim`) ou "sou novo" (formulário → `POST /auth/signup/novo`).

**Proteção de rota:** layout/wrapper chama `GET /auth/me` no mount; sem sessão (401) redireciona pra `/login`. Contexto React guarda `{nome, email, cargo}` (não localStorage — cookie é a fonte de verdade).

**Abas por papel** (`app/projects/[id]/page.tsx`): `cargo === "operacional"` só vê `sprints`, `tasks`, `tecnologias`, `documentos` — as abas `escopo`, `painel`, `metricas`, `config` somem da UI. Isso é só UX; a fonte real de verdade é o backend.

**`lib/api.ts`:** toda função de fetch passa a mandar `credentials: "include"` (mudança mecânica em ~60+ funções, nenhuma manda hoje).

## Correção de infraestrutura necessária

`docudata-backend/main.py` hoje tem `allow_origins=["*"]` no CORS — incompatível com cookie credenciado cross-site. Precisa virar uma origem explícita (`FRONTEND_URL` via env var) com `allow_credentials=True`.

## Testes

Mesmo padrão pytest + `TestClient` já usado no projeto:
- `test_auth_login.py` — login válido seta cookie; senha errada → 401; email inexistente → 401
- `test_auth_signup.py` — claim com email batendo cria pessoa + loga; claim sem bater → 403/422; signup novo cria pessoa sem `operacionais`; email duplicado → 409/422
- `test_rbac_gate.py` — rota protegida sem cookie → 401; operacional em rota `require_not_operacional` → 403; gerente na mesma rota → 200; `require_project_access` com operacional de outro projeto → 403
- `test_performance_stub.py` — não-líder → 403; líder → 200 + linha gravada em `audit_log`

## Success criteria (do ROADMAP.md, mapeados)

1. ✅ Tabela `pessoa` + login por email/senha resolve cargo da sessão
2. ✅ Gerente/Líder acesso irrestrito a projetos; Operacional só aos projetos onde tem linha em `operacionais` com email batendo
3. ⚠️ Parcial por decisão explícita: nenhum payload retorna score/peso/fórmula/ranking pra Gerente/Operacional — vale para dados de Phase 18/19; métricas interinas da Phase 13 continuam visíveis pra Gerente (decisão registrada acima)
4. ✅ `/performance` retorna 403 pra não-Líder, middleware dedicado (`require_role`, não reaproveita `require_project_access`)
5. ✅ Mecanismo de audit log pronto e usado por `/performance`; Phase 17/18 reusam o mesmo helper quando existirem
