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

- [ ] 04-01-PLAN.md — Backend: novos campos estruturados (campos_planning, campos_review, endpoint /retrospectiva, CHECK constraint)
- [ ] 04-02-PLAN.md — Frontend: modais atualizados (SprintDocModal, RetroModal, api.ts, carry-over pre-fill)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 04-03-PLAN.md — Export Google Docs com todos os placeholders CITi v2 preenchidos (busca campos do Supabase)
- [ ] 04-04-PLAN.md — GitHub integration: POST /ingest/commit + script bash de git hook

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Foundation + Extraction Proof | 0/3 | Not started | - |
| 2. Full Extraction Pipeline + Generation + Deploy | 0/TBD | Not started | - |
| 3. Frontend + End-to-End Demo | 0/TBD | Not started | - |
| 4. Template v2 + GitHub Integration | 0/4 | Not started | - |
