# Phase 11: Suíte de Verificação de Aceite - Context

**Gathered:** 2026-08-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Quando o gerente marca uma funcionalidade como `concluída`, o sistema dispara em paralelo uma suíte de gates de aceite (build, testes_unitarios, e2e, acessibilidade, performance) via GitHub Actions no repo do projeto. Os resultados chegam de volta ao DocuData via `POST /ingest/aceite`. O sistema registra cada execução em `ExecucaoAceite` com o resultado por gate e o `commit_sha` do HEAD no momento do disparo — sem poder bloquear nem reverter a transição de status. Funcionalidades concluídas com suíte falhando aparecem sinalizadas no Kanban e no Bloco B do Painel.

O gerente pode vincular manualmente testes E2E a uma funcionalidade dentro do DocuData. Quando nenhum teste E2E está vinculado ao `id_funcional`, o gate E2E registra `sem_cobertura`.

Escopo desta fase: tabela `execucoes_aceite` no Supabase + endpoint `POST /ingest/aceite` + trigger ao fazer PATCH status=concluida + script GitHub Actions (`aceite.yml` + `aceite_agent.py`) + badge visual no Kanban + sub-seção no Bloco B do Painel + % de cobertura de aceite por projeto.

</domain>

<decisions>
## Implementation Decisions

### Onde os gates rodam

- **D-01:** **GitHub Actions no repo do projeto** — Mesmo padrão do revisor diário (Phase 9) e do commit tracker (Phase 4). O gerente instala `aceite.yml` (workflow) e `aceite_agent.py` (script) no repo do projeto. Quando o DocuData detecta `status = concluida`, envia um `repository_dispatch` event ao repo do projeto via GitHub API. O workflow roda os gates e faz `POST /ingest/aceite` de volta ao DocuData com os resultados. — **Reversibility:** costly — mudar de GitHub Actions para outro CI exigiria reescrever o workflow e o protocolo de dispatch.

- **D-02:** **O status muda imediatamente — a suíte não bloqueia a transição** — O `PATCH /funcionalidades/{id}` com `status=concluida` salva no banco e retorna 200 imediatamente. O dispatch para o GitHub Actions acontece de forma assíncrona (background task no FastAPI, `asyncio.create_task`). Sem espera de resultado antes de responder ao frontend.

- **D-03:** **Dispatch via GitHub repository_dispatch** — O backend usa a GitHub API (`POST /repos/{owner}/{repo}/dispatches`) para disparar o workflow. Requer `GITHUB_TOKEN` no projeto (configurado pelo gerente). Se o repo não tiver token configurado, o dispatch falha silenciosamente e todos os gates ficam como `sem_cobertura`.

### Schema de ExecucaoAceite

- **D-04:** **5 gates fixos: build, testes_unitarios, e2e, acessibilidade, performance** — Resultado de cada gate: `passou | falhou | erro | sem_cobertura`. Tabela `execucoes_aceite`:
  ```
  id               uuid PK
  funcionalidade_id uuid FK → funcionalidades
  project_id       uuid FK → projects
  commit_sha       text NOT NULL
  gates            jsonb  -- list de {nome, resultado}
  disparado_em     timestamptz DEFAULT now()
  concluido_em     timestamptz  -- preenchido quando POST /ingest/aceite chega
  ```

- **D-05:** **POST /ingest/aceite recebe resultado de cada gate** — Payload do CI: `{ funcionalidade_id, commit_sha, gates: [{nome, resultado}] }`. O backend atualiza `execucoes_aceite` com os resultados e `concluido_em`.

### Vínculo id_funcional ↔ teste E2E

- **D-06:** **O gerente define manualmente no DocuData quais testes cobrem cada funcionalidade** — Campo `testes_e2e: list[str]` adicionado à tabela `funcionalidades` (lista de identificadores de teste, ex: nomes de arquivo ou tags). O CI recebe essa lista no dispatch payload e procura os testes correspondentes. Se a lista estiver vazia, gate E2E = `sem_cobertura`.

- **D-07:** **Por ora sem interface de edição de testes** — O campo `testes_e2e` é editável via `PATCH /funcionalidades/{id}`. Interface de gestão no frontend é deferred.

### Visualização no frontend

- **D-08:** **Badge no Kanban de sprint** — Funcionalidades no Kanban (Phase 8, coluna Concluído) ganham badge visual quando `execucao_aceite` existe com algum gate `falhou` ou `erro`. Badge: indicador vermelho/âmbar inline com o card. Zero className — style={{}} apenas.

- **D-09:** **Sub-seção no Bloco B do Painel** — Nova sub-seção "Cobertura de Aceite" no Bloco B. Lista funcionalidades concluídas com suíte falhando, sem alterar o peso no % de escopo concluído (Bloco A).

- **D-10:** **% de cobertura exibido no Bloco A ou Bloco D** — Campo `cobertura_aceite: float` adicionado ao response de `GET /projects/{id}/painel`. Calculado como: funcionalidades concluídas COM execução de aceite / total de funcionalidades concluídas. Exibido no Painel.

### Claude's Discretion

- **Trigger do dispatch:** `PATCH /funcionalidades/{id}` já detecta transição de status (Phase 7, `transicoes_status`). O dispatch para GitHub Actions é adicionado nesse mesmo handler, só quando o novo status for `concluida`.
- **Token GitHub:** `GITHUB_TOKEN` do repo do projeto é armazenado na tabela `projects` (novo campo `github_token: text`). O gerente configura uma vez na tela do projeto.
- **Repo do projeto:** Campo `github_repo: text` (ex: `owner/repo`) também adicionado a `projects`.
- **Tratamento de falha no dispatch:** Se o repo não estiver configurado (sem `github_token` ou `github_repo`), todos os gates são registrados como `sem_cobertura` imediatamente — sem tentar disparar.
- **aceite_agent.py:** Python stdlib apenas (mesma restrição do revisor). Roda cada gate via subprocess e reporta resultado.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Funcionalidades e TransicaoStatus (Phase 7)
- `docudata-backend/routers/funcionalidades.py` — handler `patch_funcionalidade` (adicionar dispatch do aceite); campo `testes_e2e` a adicionar
- `docudata-backend/models/schemas.py` — `FuncionalidadeResponse`, `FuncionalidadeUpdate` (adicionar `testes_e2e`)

### Padrão de integração GitHub Actions (Phases 4 e 9)
- `docudata-backend/hooks/docudata_agent.py` — agente Python stdlib de referência
- `docudata-backend/hooks/revisor_agent.py` — agente mais recente; `aceite_agent.py` segue o mesmo padrão
- `docudata-backend/hooks/revisor.yml` — template de workflow GitHub Actions

### Endpoint de ingest externo (referência de padrão)
- `docudata-backend/routers/revisao_ingest.py` — padrão de POST /ingest/* com Supabase insert; `/ingest/aceite` segue a mesma estrutura

### Painel e Bloco B (Phase 8 + 9)
- `docudata-backend/routers/painel.py` — `calcular_bloco_b` e endpoint `GET /projects/{id}/painel`; expandir com `cobertura_aceite` e achados de suíte falhando
- `docudata-frontend/app/components/PainelTab.tsx` — padrão zero className; expandir Bloco B

### Kanban (Phase 8)
- `docudata-frontend/app/components/KanbanTab.tsx` (ou equivalente em page.tsx) — adicionar badge visual nas funcionalidades concluídas
- `docudata-frontend/app/lib/api.ts` — interfaces TypeScript a expandir com `ExecucaoAceite`

### Roadmap e requirements
- `.planning/ROADMAP.md` §Phase 11 — 5 success criteria e escopo oficial
- `.planning/phases/07-matriz-de-escopo-transicaostatus-campos-novos-em-projeto/07-CONTEXT.md` — decisões sobre Funcionalidade (D-01 a D-08)
- `.planning/phases/08-painel-do-gerente-kanban-de-sprint/08-CONTEXT.md` — decisões sobre Painel e Kanban
- `.planning/phases/09-revisor-diario-generalizado/09-CONTEXT.md` — padrão do agente GitHub Actions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `patch_funcionalidade` em `funcionalidades.py` — já detecta transição de `status`/`status_cliente` e grava em `transicoes_status`. O dispatch do aceite é adicionado ao mesmo bloco de detecção.
- `docudata_agent.py` e `revisor_agent.py` — padrão de agente Python stdlib com subprocess + urllib. `aceite_agent.py` é uma variação para rodar gates e reportar.
- `calcular_bloco_b` em `painel.py` — já agrega dados por projeto; expandir para incluir funcionalidades com aceite falhando.

### Established Patterns
- **Zero className no frontend:** style={{...}} apenas — manter em todos os novos componentes.
- **Agente best-effort:** `continue-on-error: true` no workflow GitHub Actions.
- **Sem dependências externas no agente:** apenas Python stdlib.
- **Gemini fica no backend:** o agente só coleta e envia; não chama LLM.
- **Router FastAPI com tag e prefix:** registrar `aceite_ingest.router` em `main.py`.

### Integration Points
- `PATCH /funcionalidades/{id}` → adicionar dispatch assíncrono quando `status=concluida`
- `POST /ingest/aceite` → novo endpoint que recebe resultado dos gates e atualiza `execucoes_aceite`
- `GET /projects/{id}/painel` → adicionar `cobertura_aceite` no response e funcionalidades com falha no Bloco B
- Supabase: nova tabela `execucoes_aceite` + campos `github_token`, `github_repo`, `testes_e2e` em tabelas existentes
- `main.py` → registrar `aceite_ingest.router`

</code_context>

<specifics>
## Specific Ideas

- O dispatch acontece via `asyncio.create_task` no handler do PATCH — não bloqueia o response 200.
- Se `github_token` ou `github_repo` não estiverem configurados no projeto, todos os gates registram `sem_cobertura` imediatamente (sem tentar chamar a GitHub API).
- Badge no Kanban: indicador visual (ex: círculo vermelho ou ikon ⚠) no card da funcionalidade quando existe `ExecucaoAceite` com gate `falhou` ou `erro`.
- O % de cobertura é exibido no Painel, não bloqueia nem altera o % de escopo concluído do Bloco A.

</specifics>

<deferred>
## Deferred Ideas

- **Interface de gestão de testes E2E no frontend** — tela/modal para o gerente linkar testes a funcionalidades. Campo `testes_e2e` editável via PATCH mas sem UI dedicada nesta fase.
- **Histórico de execuções de aceite por funcionalidade** — lista paginada de todas as ExecucaoAceite. Nesta fase apenas a mais recente é relevante para o Bloco B.
- **Suporte a outros CIs além do GitHub Actions** — GitLab CI, Bitbucket Pipelines. Fora do escopo desta fase.
- **Re-disparo manual da suíte** — botão para re-rodar os gates sem mudar de status. Fora do escopo.
- **Notificações** — Slack/email quando suíte falha. Fora do escopo.

</deferred>

---

*Phase: 11-Suíte de Verificação de Aceite*
*Context gathered: 2026-08-23*
