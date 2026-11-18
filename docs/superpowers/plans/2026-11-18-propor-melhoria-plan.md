# Propor melhoria (PTA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** em projetos PTA, o candidato propõe uma melhoria (título, valor para o cliente, esforço) e o PM decide: aprova, recusa com motivo ou deixa para depois. A proposta aprovada vira task extra com a marca "inovação" e rende bônus no score da sprint no momento da aprovação.

**Architecture:**
- Tabela nova `propostas_melhoria` e router novo `routers/propostas.py`, no mesmo molde de `routers/solicitacoes.py` ("Quero mais uma task").
- Aprovar cria a task, que nasce extra, com `inovacao=true` e nível manual igual ao esforço (`classificador_ciclo.resultado_manual` + `gravar_classificacao`, status `manual`, sem IA).
- O fechamento da sprint (`services/pontuacao.py`) soma o esforço das propostas aprovadas naquela sprint em `pontuacao_operacional_sprint.bonus_pontos_inovacao`.
- `services/performance.py` converte esses pontos em bônus junto com o da task extra, sob o mesmo teto.

**Tech Stack:** FastAPI, Supabase, Next.js (estilos inline, `app/components/ds`).

**Spec:** decisões do usuário em 2026-11-18, todas valendo exatamente como escritas:
- só em projetos PTA (`projects.subarea == 'pta'`);
- o bônus entra na aprovação;
- o design abaixo foi aprovado.

## Global Constraints

- **Só PTA.** Toda rota de proposta devolve 422 com detail "Propostas de melhoria só existem em projetos PTA." quando o projeto não é PTA. O frontend só mostra o botão e o painel em projeto PTA.
- **Quem propõe:** operacional vinculado ao projeto. A proposta guarda `operacional_id`, resolvido pelo e-mail da pessoa em `operacionais` daquele projeto, no mesmo padrão de `_resolver_operacional_id_da_pessoa` em `routers/tasks.py`. Se a pessoa não estiver na equipe: 403.
- **Campos da proposta:** `titulo` (obrigatório, 3 a 200 caracteres), `valor_cliente` (obrigatório, até 2000) e `esforco` (int em {1, 2, 3, 5}; reusar o validador de nível da régua de `models/schemas.py`).
- **Status:** `pendente | aprovada | recusada | adiada`.
  - Recusar exige `motivo` não vazio (até 1000 caracteres); sem ele, 422.
  - "Deixar para depois" = `adiada`. Uma proposta adiada continua decidível depois (aprovar ou recusar).
  - Decidir uma proposta já aprovada ou recusada: 409.
- **Quem decide:** gerente, líder ou owner com acesso ao projeto (`require_not_operacional` + `require_project_access` com o `project_id` da proposta).
- **Ao aprovar:**
  - Cria a task com `titulo`, `descricao = "Valor para o cliente: " + valor_cliente`, `pontos = esforco`, `extra = true`, `inovacao = true`, `coluna_kanban = 'planejado'` e `sprint_id` = sprint atual do projeto (`services.sprints.get_current_sprint_id`). Se não houver sprint, `sprint_id` fica nulo.
  - Em projeto de modo `PULL`, `operacional_id` fica nulo (vai para a fila). Fora de Pull, recebe o `operacional_id` de quem propôs.
  - Grava a classificação manual com `classificador_ciclo.gravar_classificacao(client, task_id, classificador_ciclo.resultado_manual(esforco), tipo="criacao", criado_por=<pessoa decisora>, texto=...)`.
  - Na proposta, grava `status='aprovada'`, `decidido_por`, `decidido_em`, `task_id` e `sprint_id` (a sprint em que o bônus conta: a atual, a mesma da task).
- **Pontuação:**
  - No fechamento (`calcular_e_travar_pontuacao` em `services/pontuacao.py`), `bonus_pontos_inovacao[operacional_id]` = soma de `esforco` das propostas `aprovada` com `sprint_id` = a sprint fechada. Esse valor é gravado na linha do operacional em `pontuacao_operacional_sprint.bonus_pontos_inovacao`, com um evento em `pontuacao_eventos`: tipo `bonus_inovacao`, pontos = esforço, descrição "Proposta de melhoria aprovada".
  - A pessoa precisa entrar no conjunto de operacionais com linha, como já acontece com `bonus_extra`.
  - Task com `inovacao = true` concluída **não** soma em `bonus_extra`; continua fora de Entrega, como toda extra.
  - Na reabertura da sprint (`routers/avaliacoes.py` reabrir), `bonus_inovacao` entra na lista de tipos que o fechamento recria e que a reabertura apaga.
  - Em `services/performance.py`, `_bonus_extra` passa a ser `min((Σ bonus_pontos_extra + Σ bonus_pontos_inovacao × 0.5) × BONUS_EXTRA_POR_PONTO, BONUS_EXTRA_TETO)`. Crie a constante `BONUS_INOVACAO_FATOR = 0.5`.
  - Como PTA já é isolado do ranking CITi pelo `escopo`, nada vaza para o ranking real.
- **Migração "Migration v14 (2026-11-18): propostas de melhoria (PTA)":** comentada no fim de `supabase_schema.sql`, depois da v13, com preflight e rollback no estilo dos blocos v10–v13. Ela:
  - cria a tabela `propostas_melhoria`: `id uuid pk default gen_random_uuid()`, `project_id uuid not null references projects on delete cascade`, `operacional_id uuid not null references operacionais on delete cascade`, `titulo text not null`, `valor_cliente text not null`, `esforco int not null check in (1,2,3,5)`, `status text not null default 'pendente' check in ('pendente','aprovada','recusada','adiada')`, `motivo text`, `decidido_por uuid references pessoa(id) on delete set null`, `decidido_em timestamptz`, `task_id uuid references tasks(id) on delete set null`, `sprint_id uuid references sprints(id) on delete set null`, `criado_em timestamptz not null default now()`, mais um índice `(project_id, status)`;
  - `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS inovacao boolean NOT NULL DEFAULT false`;
  - `ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS bonus_pontos_inovacao int NOT NULL DEFAULT 0`;
  - recria o CHECK de `pontuacao_eventos.tipo`, se existir, com o tipo novo `bonus_inovacao`. Verifique o CHECK atual no schema antes.
- **Deploy antes da v14:** o fechamento de sprint NÃO pode quebrar.
  - Ao ler `propostas_melhoria`, use try/except com log e trate falha como "nenhuma proposta".
  - Só inclua `bonus_pontos_inovacao` no payload do snapshot quando ele for maior que zero, para que um projeto sem propostas grave como hoje.
  - Ler `task.get("inovacao")` é seguro.
  - As rotas novas podem dar erro antes da v14; isso é aceitável.
- Commits em português no estilo do repo (`feat(propostas): ...`), terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Comandos: `cd docudata-backend && .venv/bin/python -m pytest -q tests/<arquivo>` (última suíte: 1347 passed); frontend `cd docudata-frontend && npm test` (77) e `npx tsc --noEmit`.

---

### Task M1: Backend das propostas de melhoria

**Files:**
- Create: `docudata-backend/routers/propostas.py` (registrar em `main.py` com as mesmas dependências de autenticação do router de solicitações).
- Modify: `docudata-backend/models/schemas.py`: `PropostaMelhoriaCreate`, `PropostaMelhoriaDecisao` e `PropostaMelhoriaResponse`.
- Modify: `docudata-backend/services/pontuacao.py`, `docudata-backend/services/performance.py`, `docudata-backend/routers/avaliacoes.py` (tipos apagados na reabertura) e `docudata-backend/supabase_schema.sql`.
- Modify: `docudata-backend/models/schemas.py` `TaskResponse` ganha `inovacao: bool = False`.
- Test: `docudata-backend/tests/test_propostas_melhoria.py`, `tests/fake_supabase.py` (se faltar algo).

**Rotas:**
- `POST /projects/{project_id}/propostas`: o operacional cria a proposta. Devolve 201 com a proposta.
- `GET /projects/{project_id}/propostas`:
  - gerente, líder ou owner veem todas, em ordem: pendentes e adiadas primeiro, depois as demais por `criado_em` desc;
  - o operacional vê só as próprias.
- `POST /propostas/{id}/decisao` com `{ "acao": "aprovar" | "recusar" | "adiar", "motivo"?: str }`: devolve a proposta atualizada. Na aprovação, inclui `task_id`.

**Testes (TDD, escrever antes):**
1. Operacional de projeto PTA cria a proposta (201). Em projeto `dados`: 422 com o detail exato. Esforço 4: 422. Pessoa fora da equipe: 403.
2. Gerente cria proposta: 403. Só o operacional propõe.
3. GET: o gerente vê todas e o operacional vê só as próprias.
4. Aprovar em projeto de Atribuição:
   - a task nasce com `extra=true`, `inovacao=true`, `pontos=esforco`, `operacional_id` = quem propôs e `sprint_id` = sprint atual;
   - grava a classificação `status='manual'`;
   - a proposta fica `aprovada` com `task_id`, `sprint_id` e `decidido_por`.
5. Aprovar em projeto Pull: a task nasce com `operacional_id` nulo.
6. Recusar sem motivo: 422. Com motivo: grava o motivo. Decidir de novo uma proposta recusada ou aprovada: 409. Proposta adiada pode ser aprovada depois.
7. Operacional decidindo: 403.
8. Fechamento da sprint:
   - duas propostas aprovadas na sprint, de esforço 3 e 2, para o mesmo operacional, dão `bonus_pontos_inovacao=5` e eventos `bonus_inovacao`;
   - task `inovacao` concluída não gera `bonus_extra`;
   - falha ao ler `propostas_melhoria` não quebra o fechamento.
9. `_bonus_extra`:
   - `bonus_pontos_extra=0` e `bonus_pontos_inovacao=4` resultam em `4 × 0.5 × BONUS_EXTRA_POR_PONTO`;
   - o teto vale para a soma.
10. Reabrir a sprint apaga também `bonus_inovacao`.
11. Bloco v14 do schema só tem comentários. Siga o teste existente dos blocos v11–v13.

- [ ] Step 1: testes que falham; rodar e ver falhar.
- [ ] Step 2: implementar.
- [ ] Step 3: rodar os testes novos e a suíte completa.
- [ ] Step 4: commit `feat(propostas): candidato do PTA propõe melhoria, PM decide e a aprovada vira task de inovação com bônus`.

### Task M2: Frontend das propostas

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`:
  - tipos `PropostaMelhoria` e `StatusProposta`;
  - funções `criarProposta`, `listarPropostas` e `decidirProposta`;
  - o tipo da task kanban ganha `inovacao?: boolean`.
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx`, ou um componente novo `app/components/PropostasMelhoria.tsx` usado por ele (preferível, para não inchar o Kanban). Ele só aparece quando o projeto é PTA; descubra como o Kanban recebe o projeto ou a subárea, e passe a subárea como prop se preciso.
- Test: `docudata-frontend/tests/propostas.test.mjs`, no padrão dos testes existentes.

**Comportamento:**
- **Operacional em projeto PTA:** um botão "Propor melhoria" sempre visível no topo do Kanban (secundário, no mesmo estilo do "Quero mais uma task"). Ele abre um modal com:
  - "Título";
  - "Valor para o cliente" (textarea);
  - "Esforço" (select 1/2/3/5, com o rótulo de cada nível tirado de `app/lib/regua.ts`, se existir);
  - os botões "Enviar proposta" e "Cancelar".
- **Lista "Minhas propostas"** (compacta), com chip de status:
  - "Pendente" e "Adiada": tom neutro ou âmbar;
  - "Aprovada": verde;
  - "Recusada": vermelho, com o motivo.
- **Gerente/líder/owner em projeto PTA:** painel "Propostas de melhoria", no mesmo estilo do painel de pedidos de nova task.
  - Lista pendentes e adiadas, cada uma com título, quem propôs, valor para o cliente, esforço e os botões "Aprovar", "Recusar" e "Deixar para depois".
  - "Recusar" abre um campo de motivo obrigatório antes de confirmar.
  - Depois de aprovar, recarregar as tasks do Kanban (a task nova aparece).
- **Card:** task com `inovacao` mostra o `Chip` "inovação" (tom verde ou o de destaque já usado; sem cor nova).
- **Acessibilidade:** labels, foco no modal, erros do backend mostrados ao usuário e contraste AA com os tokens existentes.

- [ ] Step 1: teste que falha (contrato de `api.ts` e textos-chave).
- [ ] Step 2: implementar.
- [ ] Step 3: `npm test`, `npx tsc --noEmit` e `npm run build` verdes.
- [ ] Step 4: commit `feat(propostas): botão Propor melhoria e painel de decisão do PM no PTA`.
