# Vínculo gerente ↔ projeto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerente só acessa projetos em que está vinculado (tabela `projeto_gerentes`); quem cria um projeto é vinculado; toda rota de dado de projeto confere acesso; listas cruzadas filtram por projetos visíveis.

**Architecture:** Uma regra central em `services/acesso.py` (projetos visíveis, checagem, resolvedores de project_id a partir de outros ids). `require_project_access` delega para ela. Cada router aplica a checagem (dependência quando o id vem no path/query, inline nos demais casos). Onda 1 = backend (Tasks 1–6), Onda 2 = UI (Task 7).

**Tech Stack:** FastAPI + supabase-py v2 (testes com `tests/fake_supabase.FakeClient` ou MagicMock), Next.js 15/React 19 com estilos inline, `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-19-vinculo-gerente-projeto-design.md`

## Global Constraints

- Owner e Líder passam sempre. Gerente: só projetos em `projeto_gerentes`. Operacional: só projetos com linha em `operacionais` com `email` igual ao da sessão.
- Sem acesso → `HTTPException(403, "Você não tem acesso a este projeto")`. Objeto inexistente → 404 (detalhe do router atual). Discovery mantém seu 404 que esconde existência.
- Tabela `projeto_gerentes` ausente (migração v16 não aplicada) → gerente é tratado como hoje (vê tudo) + `logging.warning` uma vez por processo. Só esse erro é engolido (mensagem com `projeto_gerentes` e `PGRST205` ou `42P01` ou `does not exist`); qualquer outro erro sobe.
- Testes existentes continuam verdes sem reescrever: `tests/conftest.py` ganha fixture autouse que deixa o gerente livre (`_ids_vinculados_gerente` → `None`); testes da regra pedem a fixture `vinculos_gerente`.
- Copy em português, no estilo dos routers atuais. Comentários só onde o porquê não é óbvio.
- Backend: `cd docudata-backend && .venv/bin/python -m pytest -q` verde. Frontend: `cd docudata-frontend && npx tsc --noEmit && npm test` verde.
- Migrações SQL só como bloco comentado no fim de `docudata-backend/supabase_schema.sql` (o usuário roda à mão).
- Nunca usar opus em subagentes (memória do usuário).

---

### Task 1: Serviço de acesso, migração v16 e `require_project_access`

**Files:**
- Create: `docudata-backend/services/acesso.py`
- Modify: `docudata-backend/services/auth.py` (`require_project_access`)
- Modify: `docudata-backend/supabase_schema.sql` (bloco v16 comentado no fim)
- Modify: `docudata-backend/tests/conftest.py`
- Test: `docudata-backend/tests/test_acesso.py`

**Interfaces (Produces):**
```python
# services/acesso.py
SEM_ACESSO = "Você não tem acesso a este projeto"
def _ids_vinculados_gerente(client, pessoa_id: str) -> set[str] | None   # None = tabela ausente
def projetos_visiveis(client, pessoa: dict) -> set[str] | None             # None = todos
def tem_acesso(client, pessoa: dict, project_id: str) -> bool
def exigir_acesso(client, pessoa: dict, project_id: str) -> None           # 403 SEM_ACESSO
def project_id_de(client, entidade: str, objeto_id: str) -> str           # 404 se não existe
def exigir_acesso_por(client, pessoa: dict, entidade: str, objeto_id: str) -> str
def vincular_gerente(client, project_id: str, pessoa_id: str, criado_por: str | None) -> None  # idempotente, tolera tabela ausente
```
`entidade` aceita: `"task"`→`tasks`, `"sprint"`→`sprints`, `"funcionalidade"`→`funcionalidades`, `"sprint_funcionalidade"`→`sprint_funcionalidades`, `"doc"`→`generated_docs`, `"ingestion"`→`ingestions`, `"proposta"`→`propostas_melhoria`, `"solicitacao"`→`solicitacoes_task`, `"sugestao"`→`task_sugestoes`, `"operacional"`→`operacionais` (todas com coluna `project_id`; confirme os nomes das tabelas no router correspondente antes de mapear), `"avaliacao"`→`avaliacoes_gerente` → `sprint_id` → `sprints.project_id`. Para `sprint_funcionalidade` sem `project_id`, resolva via `sprint_id`.

- [ ] Escrever `tests/test_acesso.py` com FakeClient cobrindo: owner/líder → `projetos_visiveis` None; gerente vinculado só vê os seus; gerente sem vínculo → set vazio e `exigir_acesso` 403; operacional por e-mail; tabela ausente (client cuja query em `projeto_gerentes` levanta `Exception("relation \"projeto_gerentes\" does not exist 42P01")`) → None; outro erro sobe; `project_id_de` para task, sprint, avaliacao (via sprint) e 404 inexistente; `vincular_gerente` não duplica.
- [ ] Implementar `services/acesso.py` até passar.
- [ ] `require_project_access(project_id, pessoa=Depends(get_current_pessoa))` passa a chamar `exigir_acesso(get_client(), pessoa, project_id)` e devolver `pessoa`. Mesma assinatura.
- [ ] `tests/conftest.py`: fixture autouse `acesso_gerente_livre(monkeypatch)` que faz `monkeypatch.setattr("services.acesso._ids_vinculados_gerente", lambda client, pid: None)`; fixture `vinculos_gerente(monkeypatch)` que devolve um dict `{pessoa_id: set(project_ids)}` mutável e repatcha a função para ler dele. `test_acesso.py` testa a função real (desfaz o patch com `monkeypatch.undo()` ou importa a implementação original guardada).
- [ ] Bloco v16 comentado no schema com o SQL do spec (tabela + índice em `pessoa_id` + backfill).
- [ ] Suite completa verde. Commit `feat(acesso): regra central de acesso por projeto e tabela projeto_gerentes (v16)`.

### Task 2: Projetos, vínculos e busca

**Files:** `routers/projects.py`, `routers/search.py`, `models/schemas.py` (se precisar de modelos), test `tests/test_vinculo_gerente_projects.py`.

**Consumes:** `services/acesso` (Task 1).
**Produces (HTTP):** `GET /projects/{id}/gerentes` → `[{pessoa_id, nome, email, criado_em}]`; `GET /projects/{id}/gerentes/candidatos` → `[{pessoa_id, nome, email, cargo}]`; `POST /projects/{id}/gerentes` body `{pessoa_id}` → 201 lista atualizada; `DELETE /projects/{id}/gerentes/{pessoa_id}` → 204, 409 `"O projeto precisa de pelo menos um gerente."` se for o último.

- [ ] `GET /projects`: filtra por `projetos_visiveis` para gerente (operacional segue com o filtro atual de `ativo=True`).
- [ ] `POST /projects`: depende de `get_current_pessoa` e chama `vincular_gerente(client, novo_id, pessoa["id"], pessoa["id"])` (operacional já é bloqueado? confira; se não, bloqueie com 403 — operacional não cria projeto).
- [ ] Toda rota `/{project_id}...` deste arquivo confere acesso (dependência `require_project_access` ou inline). Mantém as exigências de cargo atuais.
- [ ] Rotas de vínculo: gerenciar = owner/líder ou gerente com `tem_acesso`; candidatos = `pessoa` com cargo em (`gerente`,`lider`,`owner`) menos os vinculados; vincular só pessoa desses cargos (422 caso contrário).
- [ ] `GET /search`: filtra resultados por `projetos_visiveis`.
- [ ] Testes: gerente vinculado/não vinculado/líder/operacional para GET/PATCH representativos; lista filtrada; criar vincula; vincular/desvincular/último 409/candidatos; busca filtrada.
- [ ] Suite verde. Commit.

### Task 3: Tasks, funcionalidades, sprints, sprint-funcionalidades

**Files:** `routers/tasks.py`, `routers/funcionalidades.py`, `routers/sprints.py`, `routers/sprint_funcionalidades.py`; tests `tests/test_acesso_rotas_tasks.py`.

- [ ] Todas as rotas listadas no spec para esses arquivos conferem acesso: id no path/query → `require_project_access` (ou inline); body → `exigir_acesso(client, pessoa, data.project_id)`; por objeto → `exigir_acesso_por(client, pessoa, "task"|"sprint"|"funcionalidade"|"sprint_funcionalidade"|"sugestao", id)`. Rotas que já carregam a linha podem usar `exigir_acesso(client, pessoa, linha["project_id"])` para não buscar duas vezes.
- [ ] `PATCH /tasks/reordenar/batch`: cada task precisa estar em projeto visível (403 na primeira que não estiver, sem escrever nada).
- [ ] Preserve as regras atuais do operacional (`_checar_operacional_pode_mexer`, puxar/devolver).
- [ ] Testes: para cada arquivo, ao menos uma leitura e uma escrita com gerente de fora → 403 e sem escrita; gerente vinculado → passa.
- [ ] Suite verde. Commit.

### Task 4: Documentos e IA (generate, export, ingest, ingestions, enrich, sprint_docs, composer, boletins)

**Files:** os 8 routers; tests `tests/test_acesso_rotas_docs.py`.

- [ ] Conferir acesso em todas as rotas desses arquivos (Form `projeto_id` → inline antes de qualquer chamada ao Gemini ou upload; doc id → `"doc"`; ingestion id → `"ingestion"`).
- [ ] Testes por arquivo: gerente de fora 403 antes de chamar o modelo (monkeypatch o grafo/LLM para falhar se chamado); vinculado passa.
- [ ] Suite verde. Commit.

### Task 5: Equipe, pontos, propostas, solicitações, discovery, painel, métricas, GitHub

**Files:** `routers/operacionais.py`, `routers/pontuacao.py`, `routers/propostas.py`, `routers/solicitacoes.py`, `routers/discovery.py`, `routers/painel.py`, `routers/metricas.py`, `routers/github_integration.py` (só rotas `/projects/{project_id}/...`); tests `tests/test_acesso_rotas_equipe.py`.

- [ ] Conferir acesso em todas as rotas de projeto desses arquivos (`operacional_id` → `"operacional"`; `solicitacao_id` → `"solicitacao"`; `proposta_id` → já faz inline). Discovery: confirme que `requisito`/`reuniao` passam por `_acesso_ou_404` (mantém 404).
- [ ] Testes: gerente de fora 403 em painel, métricas, extrato de pontos, lista de operacionais, solicitações, repositórios; vinculado passa.
- [ ] Suite verde. Commit.

### Task 6: Avaliações e configurações

**Files:** `routers/avaliacoes.py`, `routers/settings.py`; tests `tests/test_acesso_rotas_avaliacoes.py`.

- [ ] `GET /avaliacoes/historico`: sem filtro → só avaliações cujas sprints são de projetos visíveis (None = sem filtro); `project_id`/`sprint_id` de fora → 403.
- [ ] Demais rotas por `sprint_id` (`"sprint"`) ou `avaliacao_id` (`"avaliacao"`) ou body (sprint do body) conferem acesso.
- [ ] `routers/settings.py`: rotas passam a exigir `require_role("lider")`.
- [ ] Testes: histórico filtrado para gerente com dois projetos (um vinculado); 403 com filtro de fora; confirmar/pendências de sprint de fora 403; gerente em `/settings/gemini` 403, líder passa.
- [ ] Suite verde. Commit.

### Task 7 (Onda 2): UI — Gerentes do projeto e 403

**Files:** `docudata-frontend/app/lib/api.ts`, `docudata-frontend/app/[subarea]/projects/[id]/page.tsx` (seção nova em Configurações, perto de "Operacionais"), tratamento de 403 no carregamento do projeto; test `docudata-frontend/tests/gerentes-projeto.test.mjs` se houver lógica pura (ex.: pode remover = mais de um vinculado).

- [ ] `api.ts`: `listGerentesProjeto(projectId)`, `listCandidatosGerente(projectId)`, `vincularGerente(projectId, pessoaId)`, `desvincularGerente(projectId, pessoaId)` lendo `detail` nos erros.
- [ ] Seção "Gerentes do projeto": lista nome/e-mail, select de candidatos + "Vincular", "Remover" (oculto quando só há um vinculado; confirma antes). Mesmo visual da seção Operacionais.
- [ ] Página do projeto: se o GET do projeto der 403, mostrar estado vazio "Você não tem acesso a este projeto" com link de volta, em vez de erro genérico.
- [ ] `npx tsc --noEmit && npm test` verdes. Commit.
