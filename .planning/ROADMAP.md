# Roadmap: DocuData

## Overview

DocuData is built in three phases aligned to the 3-day MVP deadline. Phase 1 wires the backend skeleton and proves the core pipeline with TXT files — a single upload produces a Supabase row. Phase 2 completes all file types, the generation pipeline, and deploys the backend to Railway. Phase 3 delivers the full Next.js frontend and makes the system demo-ready on Vercel.

## Phases

- [ ] **Phase 1: Backend Foundation + Extraction Proof** - Supabase, schemas, file parsing, extraction graph for TXT — one upload lands a row in the DB
- [ ] **Phase 2: Full Extraction Pipeline + Generation + Deploy** - All file types (DOCX, PDF, images), generation graph for all doc types, project CRUD, backend on Railway
- [ ] **Phase 3: Frontend + End-to-End Demo** - All three Next.js screens, markdown rendering, clipboard copy, Vercel deploy

## Phase Details

### Phase 1: Backend Foundation + Extraction Proof

**Goal:** The backend can receive a TXT file upload for a project/sprint and produce a structured 6-field JSON row in Supabase — proving the extraction pipeline works end to end.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** PROJ-01, PROJ-02, PROJ-03, INGS-01, INGS-02, EXTR-01, EXTR-02
**Success Criteria** (what must be TRUE):

  1. A TXT file uploaded to `POST /ingest` with a sprint number and project ID produces a row in the `ingestions` table with all 6 fields populated
  2. `POST /projects` creates a project and returns a UUID; `GET /projects` lists it
  3. `GET /projects/{id}` returns the project by ID
  4. A malformed upload (wrong content type) returns a clear error response, not a 500
  5. The extraction graph retries JSON parsing up to 2 times before marking the ingestion as failed

**Plans:** 3 plans
Plans:
**Wave 1**

- [ ] 01-01-PLAN.md — Backend foundation + project CRUD vertical slice (config, schemas, Supabase client, /projects, main.py)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-02-PLAN.md — Extraction graph + POST /ingest Walking Skeleton core (TXT -> Gemini -> ingestions row)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-03-PLAN.md — Code-based eval gates (AI-SPEC dims 1/5/6: schema validity, retry edge, write integrity)

### Phase 2: Full Extraction Pipeline + Generation + Deploy

**Goal:** All supported file types are processed correctly by the extraction graph, all four document types can be generated from accumulated ingestions, and the backend is live on Railway.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** INGS-03, EXTR-03, EXTR-04, GERA-01, GERA-02
**Success Criteria** (what must be TRUE):

  1. Uploading a DOCX, a text-layer PDF, a scanned PDF (image), a PNG, and a JPEG each produce a valid 6-field Supabase row
  2. `GET /ingestions/{project_id}` returns all ingestions; `GET /ingestions/{project_id}/{sprint}` filters correctly
  3. `POST /generate` with `sprint_status` returns a markdown document with the correct sprint's content
  4. `POST /generate` with `completo` returns a markdown document spanning all sprints of the project
  5. Backend is accessible at the Railway URL and cold-starts within 60 seconds

**Plans**: TBD
**UI hint**: no

### Phase 3: Frontend + End-to-End Demo

**Goal:** The complete Next.js frontend is deployed on Vercel; a manager can create a project, upload files, view ingestion history, generate all document types, read the rendered markdown, and copy it — entirely through the UI.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** GERA-03, GERA-04
**Success Criteria** (what must be TRUE):

  1. Manager can create a project via the `/projects/new` form and be redirected to the project dashboard
  2. Manager can upload a file with a sprint number from the dashboard and see a success or error message
  3. Manager can see the ingestion history grouped by sprint, including file name, date, and extracted summary
  4. Manager can click a generation button, enter a sprint number when required, and see the document rendered as formatted markdown on screen
  5. Manager can click the copy button and paste the raw markdown into any external tool

**Plans**: TBD
**UI hint**: yes

### Phase 4: Template v2 + GitHub Integration

**Goal:** Os templates de Planning, Review e Retrospectiva são preenchidos corretamente com todos os campos dos novos templates CITi; novos campos estruturados (Squad, Período, Horas, Dependências, Percepção do cliente, Sinal de satisfação) são coletados nos modais e armazenados; integração com repositório GitHub via commit hook permite ingestão automática de mudanças por sprint sem depender do gerente.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** TMPL-01, TMPL-02, TMPL-03, FORM-01, FORM-02, GH-01, GH-02
**Success Criteria** (what must be TRUE):

  1. Export de Planning preenche `{{BACKLOG}}`, `{{RISCOS}}`, `{{SQUAD}}`, `{{PERIODO}}`, `{{HORAS_REAIS}}`, `{{HORAS_ESTIMADAS}}`, `{{DEPENDENCIAS_CLIENTE}}`, `{{CARRY_OVER}}` no template Google Docs
  2. Export de Review preenche `{{PLANEJADO_ENTREGUE}}`, `{{PERCEPCAO_CLIENTE}}`, `{{SINAL_SATISFACAO}}`, `{{PEDIDOS_FORA_ESCOPO}}`, `{{ITENS_PROXIMA_SPRINT}}` no template
  3. Export de Retrospectiva preenche `{{O_QUE_FUNCIONOU}}`, `{{O_QUE_NAO_FUNCIONOU}}`, `{{CAUSA_RAIZ_IMPACTO}}`, `{{ACOES_MELHORIA}}`, `{{PEDIDO_FORA_ESCOPO_STATUS}}`
  4. Modal de Planning coleta: Squad, Período (início/fim), Horas disponíveis, Horas estimadas, Dependências do cliente
  5. Modal de Review coleta: Percepção do cliente (frase), Sinal de satisfação (dropdown 3 opções: 🟢 Verde / 🟡 Amarelo / 🔴 Vermelho), Pedidos fora do escopo
  6. Script de git hook envia payload estruturado ao `POST /ingest/commit` após commit com seção `[docudata]`
  7. `POST /ingest/commit` salva ingestion com `tipo_documentacao=commit` e `extracted_content` com mudança, decisão, tecnologias, impacto no backlog

**Plans:** 4 plans
Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Backend: novos campos estruturados (campos_planning, campos_review, endpoint /retrospectiva, CHECK constraint)
- [x] 04-02-PLAN.md — Frontend: modais atualizados (SprintDocModal, RetroModal, api.ts, carry-over pre-fill)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-03-PLAN.md — Export Google Docs com todos os placeholders CITi v2 preenchidos (busca campos do Supabase)
- [x] 04-04-PLAN.md — GitHub integration: GET /current-sprint + POST /ingest/commit + GitHub Actions workflow + Python agent (detecção automática de sprint, override [sprint:N], commit status)

### Phase 5: Content-Type Validation on Ingestion

**Goal:** Every file-based ingestion endpoint (upload livre, planning, daily, ata, review, retrospectiva — when a file attachment is present) validates whether the content corresponds to the expected document type and returns a diagnostic error identifying what the content looks like instead. Commit ingestion is excluded (structured JSON payload, no free-form file).
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):

  1. Uploading an ML lecture PDF when creating a planning returns a 422 with a message indicating the content is unrelated to project management (e.g., "Conteúdo parece ser material educacional, não um planejamento de sprint")
  2. Uploading a review-like document when creating a planning returns a 422 that identifies the mismatch (e.g., "Conteúdo parece ser uma Review, não um Planning")
  3. All 5 file-based ingestion endpoints (upload livre, planning, daily, ata, review/retrospectiva with attachment) have type validation — commit excluded (structured payload, no file)
  4. Upload livre blocks only clearly irrelevant content (nao_relacionado) with override available; any project document passes
  5. Validation runs via a Gemini call before extraction — rejected content is never saved to Supabase

**Plans:** 2 plans
Plans:
**Wave 1**

- [x] 05-01-PLAN.md — validar_tipo node in extraction_graph.py: new ExtractionState fields, classification prompt, conditional edge, _meta annotations in salvar

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-02-PLAN.md — Router wiring: ingest.py + sprint_docs.py accept force field, pass tipo_esperado + project context, surface structured 422 on validation failure

### Phase 7: Matriz de Escopo + TransicaoStatus + Campos Novos em Projeto

**Goal:** O gerente pode cadastrar funcionalidades com critérios de aceite em EARS, importar em massa do texto do contrato via IA, e o sistema registra automaticamente o tempo por fase (TransicaoStatus) desde o primeiro dia — garantindo histórico completo para todos os projetos novos.
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** M1 (§5), §4.1 (Funcionalidade), §4.2 (máquina de estados), §4.3 (TransicaoStatus), §4.6 (campos novos em Projeto)
**Success Criteria** (what must be TRUE):

  1. `POST /funcionalidades` cria funcionalidade com ao menos um critério de aceite — sem critério, retorna 422 com mensagem explicativa
  2. `POST /funcionalidades/importar` recebe texto do contrato, propõe quebra em funcionalidades com critérios EARS para revisão — não salva nada sem confirmação
  3. `POST /funcionalidades/importar/confirmar` cria as funcionalidades confirmadas e descarta as rejeitadas
  4. Toda transição de `status` ou `status_cliente` de uma funcionalidade grava um registro `TransicaoStatus` com autor, timestamp e duração da fase anterior calculada
  5. `PATCH /projects/{id}/contrato` aceita os campos novos: `data_inicio`, `data_fim_contratada`, `tolerancia_desvio_pontos`, `periodo_garantia_dias`
  6. Projetos sem funcionalidades cadastradas continuam funcionando exatamente como hoje — sem erro, sem bloqueio

**Plans:** 3/3 plans executed
Plans:
**Wave 1**

- [x] 07-01-PLAN.md — Tracer: Migration SQL + schemas (FuncionalidadeCreate/Response, ContratoUpdate, Import schemas) + GET/POST /funcionalidades CRUD + main.py wiring

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 07-02-PLAN.md — PATCH /funcionalidades/{id} state machine + TransicaoStatus recording; PATCH /projects/{id}/contrato contract fields

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 07-03-PLAN.md — graphs/import_graph.py (LangGraph, no salvar node) + POST /funcionalidades/importar + POST /funcionalidades/importar/confirmar

**UI hint:** yes

### Phase 8: Painel do Gerente + Kanban de Sprint

**Goal:** O gerente vê, na home do projeto, o painel com as 4 seções (Tempo × Escopo, Itens travados, Métricas de fluxo, Tempo por fase) e um kanban de sprint com as funcionalidades distribuídas por status.
**Mode:** mvp
**Depends on:** Phase 7
**Requirements:** M2 Blocos A, B, C, D (§5), M3 (§5)
**Success Criteria** (what must be TRUE):

  1. Bloco A exibe % prazo consumido, % escopo concluído e % aprovado pelo cliente quando `data_inicio` e `data_fim_contratada` estiverem preenchidos; exibe "sem dados" quando não estiverem
  2. Quando (% prazo − % escopo aprovado) exceder `tolerancia_desvio_pontos`, aparece alerta visual (desvio_detectado: bool no response do endpoint — sem persistência no banco, decisão D-05)
  3. Bloco B lista funcionalidades travadas (em_andamento > 7 dias sem mudança), aguardando cliente (enviado > 5 dias úteis) e que voltaram para em_ajuste
  4. Bloco C exibe throughput, WIP e cycle time (p50, p85) sempre agregados por squad
  5. Bloco D exibe tempo médio e p85 por fase de status e eficiência de fluxo do projeto; detalhe individual por funcionalidade disponível
  6. Kanban de sprint exibe funcionalidades em 3 colunas (Planejado / Em andamento / Concluído) sem persistir estado próprio — coluna Transbordou removida por decisão D-07; funcionalidades multi-sprint têm badge com sprint planejada

**Plans:** 2/2 plans executed
Plans:
**Wave 1**

- [x] 08-01-PLAN.md — Tracer: Backend GET /projects/{id}/painel (4 blocks calculated) + PainelTab.tsx stub + page.tsx tab wiring

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 08-02-PLAN.md — Expansion: Full polished PainelTab with Bloco A/B/C/D visual details, Bloco D accordion, kanban 3 columns with sprint dropdown

**UI hint:** yes

### Phase 9: Revisor Diário Generalizado

**Goal:** O revisor diário opera nos repositórios cadastrados no DocuData via workflow configurável por projeto; achados chegam ao Agente Documentador como registros RevisaoDiaria e alimentam o painel.
**Mode:** mvp
**Depends on:** Phase 8
**Requirements:** M7 (§5)
**Success Criteria** (what must be TRUE):

  1. Prompt de revisão vive versionado num repositório central; projetos aderem com workflow de 3 linhas + `.citi/revisao.yml` — somente repos vinculados a um projeto no DocuData enviam achados
  2. Revisor opera em modo somente leitura — não cria, edita, renomeia nem apaga arquivo; não escreve código nem roda comando que altere estado
  3. Quando não há mudança relevante na janela, o revisor emite uma frase e para — não inventa achado
  4. Toda afirmação técnica carrega referência `arquivo:linha`; sem referência, não entra no relatório
  5. Gera duas saídas: versão gerente (macro, sem arquivo:linha) e versão time técnico (com arquivo:linha em tudo)
  6. Ao concluir, envia achados ao Agente Documentador criando registro RevisaoDiaria; achados CRITICA/ALTA com confiança ALTA aparecem no Bloco B do painel

**Plans:** 2 plans
Plans:
**Wave 1**

- [ ] 09-01-PLAN.md — Backend tracer: migration SQL revisoes_diarias + POST /ingest/revisao + calcular_bloco_b expandido com achados_criticos

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 09-02-PLAN.md — Agente cliente: revisor_agent.py + revisor.yml + PainelTab.tsx com achados + toggle gerente/técnico

**UI hint:** no

### Phase 10: Composer de Planning

**Goal:** O gerente compõe o planning da sprint em 4 passos guiados (seleção, recorte, alocação, composição), com estado salvo entre sessões, e o sistema preenche automaticamente o template de Planning com os campos derivados.
**Mode:** mvp
**Depends on:** Phase 7
**Requirements:** M4 (§5)
**Success Criteria** (what must be TRUE):

  1. Gerente pode sair e voltar ao composer sem perder o progresso — estado salvo após cada passo
  2. Funcionalidades transbordadas da sprint anterior aparecem no topo marcadas como tal
  3. O sistema exibe throughput das últimas 3 sprints e indica se a seleção está acima dele — como informação, nunca como bloqueio
  4. Recorte é campo obrigatório por funcionalidade; o gerente pode marcar quais critérios de aceite entram nesta sprint
  5. Template de Planning preenchido automaticamente com itens, recortes, responsáveis, transbordos e throughput de referência
  6. Rascunho nunca vira Planning oficial sem confirmação humana explícita

**Plans:** 3/3 plans complete
Plans:
**Wave 1**

- [x] 10-01-PLAN.md — Backend tracer: migration SQL planning_rascunhos + GET/PATCH /composer/rascunho + POST /composer/confirmar + main.py wiring

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 10-02-PLAN.md — POST /composer/gerar (Gemini) + PlanningTab.tsx wizard 4 passos + api.ts funções + page.tsx tab wiring

**Wave 3** *(gap closure — blocked on Wave 2 completion)*

- [x] 10-03-PLAN.md — Fix CR-01: upsert ignore_duplicates=True + SELECT explícito em get_rascunho (fecha SC-1 e P1-1)

**UI hint:** yes

### Phase 11: Suíte de Verificação de Aceite

**Goal:** Quando o gerente marcar uma funcionalidade como concluída, o sistema dispara em paralelo a suíte de aceite (build, testes, e2e, acessibilidade, performance) e registra o resultado em ExecucaoAceite — sem poder de alterar o status.
**Mode:** mvp
**Depends on:** Phase 7
**Requirements:** M5 (§5), §4.4 (ExecucaoAceite)
**Success Criteria** (what must be TRUE):

  1. Ao marcar `status = concluida`, o status muda imediatamente e a suíte dispara em paralelo — nenhum resultado de gate reverte ou atrasa a transição
  2. Resultado de cada gate (passou / falhou / erro / sem_cobertura) fica registrado em ExecucaoAceite com commit_sha do HEAD no momento do disparo
  3. Funcionalidade concluída com suíte falhando ou sem cobertura aparece sinalizada no Bloco B do painel sem alterar seu peso no % de escopo concluído
  4. O sistema exibe, por projeto, o % de funcionalidades concluídas com cobertura de aceite
  5. Quando não existir teste E2E vinculado ao id_funcional, registra `resultado = sem_cobertura` e sinaliza

**Plans:** 2/2 plans executed
Plans:
**Wave 1**

- [x] 11-01-PLAN.md — Backend tracer: migration SQL + schemas + POST /ingest/aceite + BackgroundTasks dispatch em patch_funcionalidade + GET /execucoes_aceite + main.py wiring

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 11-02-PLAN.md — GitHub Actions agent (aceite_agent.py + aceite.yml) + painel.py cobertura_aceite + PainelTab badge Kanban + Bloco B sub-seção + api.ts types

**UI hint:** no

### Phase 12: Boletim de Aceite, Encerramento e Resumo Semanal

**Goal:** O gerente gera boletins de aceite para envio ao cliente, registra o retorno (aprovado / ajuste pedido com categorização bug vs mudança de escopo), e quando 100% das funcionalidades estiverem aprovadas pode gerar o Termo de Encerramento; o resumo semanal de anomalias é gerado automaticamente.
**Mode:** mvp
**Depends on:** Phase 7, Phase 8
**Requirements:** M6 (§5), M8 (§5), §4.5 (RevisaoDiaria)
**Success Criteria** (what must be TRUE):

  1. Gerente seleciona funcionalidades em `concluida` e gera boletim com título, critérios em linguagem de negócio, link de deploy preview e espaço para evidência visual
  2. Ao marcar boletim como enviado, funcionalidades movem para `status_cliente = enviado` com data registrada
  3. Ao registrar retorno do cliente como "ajuste pedido", o sistema exige classificação: bug (dentro do escopo) ou solicitação de mudança (escopo novo, lista separada)
  4. Quando 100% das funcionalidades estiverem `aprovado`, o sistema habilita geração do Termo de Encerramento com todas as funcionalidades, critérios, datas de aprovação e período de garantia
  5. Ao final de cada semana, o sistema gera por projeto um resumo de exceções (travadas, aguardando cliente, concluídas com suíte falhando, achados críticos, decisões pendentes, leitura tempo × escopo)
  6. Quando não houver anomalia, o resumo declara explicitamente que não há

**Plans:** 1/3 plans executed
Plans:
**Wave 1**

- [x] 12-01-PLAN.md — Tracer: Migration SQL boletins_aceite + schemas (BoletimCreate/Response) + POST /boletins (Gemini) + GET /boletins/{project_id} + main.py wiring

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 12-02-PLAN.md — Expansion: PATCH /boletins/{id} (status transitions + retorno_tipo + batch status_cliente + TransicaoStatus) + POST /boletins/resumo_semanal (deterministic, no Gemini)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 12-03-PLAN.md — Frontend: api.ts types/functions + AceiteTab.tsx (duas seções, zero className) + page.tsx aba Aceite wiring

**UI hint:** yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Foundation + Extraction Proof | 0/3 | Not started | - |
| 2. Full Extraction Pipeline + Generation + Deploy | 0/TBD | Not started | - |
| 3. Frontend + End-to-End Demo | 0/TBD | Not started | - |
| 4. Template v2 + GitHub Integration | 4/4 | Complete | 2026-07-28 |
| 5. Content-Type Validation on Ingestion | 2/2 | Complete | 2026-08-13 |
| ~~6. Token Usage Panel~~ | — | Removed | — |
| 7. Matriz de Escopo + TransicaoStatus + Campos Novos em Projeto | 3/3 | Complete | 2026-08-22 |
| 8. Painel do Gerente + Kanban de Sprint | 2/2 | Complete | 2026-08-22 |
| 9. Revisor Diário Generalizado | 0/TBD | Not started | - |
| 10. Composer de Planning | 3/3 | Complete    | 2026-08-23 |
| 11. Suíte de Verificação de Aceite | 2/2 | In Progress|  |
| 12. Boletim de Aceite, Encerramento e Resumo Semanal | 1/3 | In Progress|  |
