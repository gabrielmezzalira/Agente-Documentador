# DocuData
## Software Design Document
**Agente de Documentação Automática de Projetos de Dados**

Versão 1.0 · Maio 2026  
Gabriel Mezzalira · CITi — Subárea de Dados

---

## 1. Visão Geral

### 1.1 Problema

Gerentes de projetos de dados dentro do CITi não documentam sistematicamente o que acontece ao longo das sprints. O conhecimento — decisões técnicas, contexto de cliente, dificuldades, escolhas de arquitetura — fica retido na memória das pessoas e se perde ao final de cada projeto ou gestão.

A raiz do problema não é apenas falta de disciplina: é ausência de padrão mínimo e alto custo percebido para documentar. Gerentes que tentam documentar usam formatos diferentes; quem documenta bem (como identificado em entrevista interna) já terceiriza informalmente para o Claude, sem estrutura replicável.

### 1.2 Solução

O DocuData é um sistema web que permite ao gerente alimentar o projeto com arquivos produzidos naturalmente no dia a dia — documentos de task para analistas, prints de kanban, atas de reunião, PDFs. Um agente LangGraph processa cada arquivo, extrai conhecimento estruturado e o acumula em banco de dados por projeto e sprint. A qualquer momento, o gerente pode gerar documentos sob demanda: status da sprint, retrospectiva, log de decisões ou documento completo do projeto.

### 1.3 Objetivos

- Eliminar o esforço manual de documentação sem eliminar o registro de conhecimento
- Padronizar a documentação entre todos os gerentes da subárea
- Preservar contexto de negócio e decisões técnicas que não aparecem no código
- Institucionalizar o uso de IA nos projetos — não depender de quem paga a ferramenta do próprio bolso

### 1.4 Escopo do MVP

Este documento cobre a versão 1.0 do sistema, com foco no MVP funcional para demonstração. Features de múltiplos usuários simultâneos, autenticação e controle de acesso por projeto não fazem parte do escopo inicial.

---

## 2. Arquitetura e Stack

### 2.1 Componentes

| Camada | Tecnologia | Responsabilidade | Deploy |
|---|---|---|---|
| Frontend | Next.js (React) | Interface do usuário — três telas principais | Vercel |
| Backend | FastAPI (Python) | API REST — orquestra os grafos LangGraph | Railway |
| Agente IA | LangChain + LangGraph | Extração e geração de documentos | Dentro do FastAPI |
| Modelo | Gemini 1.5 Flash | Processamento de texto e visão (imagens/PDFs) | API externa |
| Banco de dados | Supabase (PostgreSQL) | Persistência de projetos, ingestões e documentos | Supabase Cloud |

### 2.2 Fluxo de dados — visão macro

O sistema opera em dois fluxos distintos e independentes:

1. O gerente faz upload de um arquivo associado a uma sprint. O backend detecta o tipo, pré-processa, extrai conhecimento estruturado via Gemini e salva no Supabase. **(Fluxo de Ingestão)**
2. O gerente seleciona um tipo de documento e, se necessário, uma sprint. O backend busca todas as ingestões relevantes, compila o contexto e gera o documento em markdown via Gemini. **(Fluxo de Geração)**

### 2.3 Por que LangGraph?

LangGraph gerencia cada fluxo como um grafo de estados com nós encadeados. Os benefícios concretos para este sistema:

- **Estado explícito:** em cada etapa é possível inspecionar exatamente o que foi processado
- **Retry granular:** se o nó de parse do JSON falhar, reexecuta só esse nó — não o fluxo inteiro
- **Extensível:** adicionar um novo tipo de documento ou nova lógica de validação é adicionar um nó/edge, sem refatorar toda a chain

---

## 3. Modelo de Dados

Três tabelas no Supabase:

### 3.1 `projects`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Gerado automaticamente via `gen_random_uuid()` |
| `name` | text NOT NULL | Nome do projeto |
| `client` | text NOT NULL | Nome do cliente |
| `description` | text | Descrição opcional do escopo |
| `created_at` | timestamptz | Data de criação — default `now()` |

### 3.2 `ingestions`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Gerado automaticamente |
| `project_id` | uuid (FK) | Referência a `projects` — cascade delete |
| `sprint_number` | int NOT NULL | Número da sprint informado pelo gerente no upload |
| `file_name` | text | Nome original do arquivo |
| `file_type` | text | Tipo detectado: `texto` \| `imagem` \| `pdf` |
| `extracted_content` | jsonb | JSON estruturado com os campos extraídos pelo Gemini |
| `created_at` | timestamptz | Data da ingestão |

### 3.3 `generated_docs`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | uuid (PK) | Gerado automaticamente |
| `project_id` | uuid (FK) | Referência a `projects` — cascade delete |
| `doc_type` | text NOT NULL | `sprint_status` \| `sprint_retro` \| `decisoes` \| `completo` |
| `sprint_number` | int | Preenchido quando `doc_type` é `sprint_status` ou `sprint_retro` |
| `content` | text NOT NULL | Documento em markdown gerado pelo Gemini |
| `created_at` | timestamptz | Data de geração |

### 3.4 Estrutura do JSON extraído (`extracted_content`)

```json
{
  "resumo": "string — descrição do que foi trabalhado",
  "tarefas": ["lista de tarefas identificadas no arquivo"],
  "decisoes": ["decisões técnicas tomadas nesta sprint"],
  "problemas": ["problemas e bloqueios identificados"],
  "contexto_cliente": "string — informações sobre o cliente ou requisitos",
  "proximos_passos": ["lista de próximos passos identificados"]
}
```

---

## 4. Fluxo de Ingestão (Grafo de Extração)

**Arquivo:** `graphs/extraction_graph.py`

### 4.1 Estado do grafo

| Campo | Tipo | Descrição |
|---|---|---|
| `arquivo_bytes` | bytes | Conteúdo bruto do arquivo recebido via upload |
| `arquivo_nome` | str | Nome original do arquivo |
| `mime_type` | str | MIME type detectado pelo FastAPI |
| `sprint_numero` | int | Número da sprint informado pelo gerente |
| `projeto_id` | str | UUID do projeto |
| `tipo` | str | Tipo detectado: `texto` \| `imagem` \| `pdf` |
| `texto_preprocessado` | str | Conteúdo preparado para o modelo (texto ou base64) |
| `conteudo_estruturado` | dict | JSON final após parse pelo LangChain |
| `valido` | bool | `True` se o JSON passou na validação de campos obrigatórios |
| `tentativas` | int | Contador de retries no nó de estruturação |
| `erro` | str | Mensagem de erro se algum nó falhar |

### 4.2 Nós do grafo

#### `detectar_tipo`

Olha o `mime_type` do arquivo e escreve o campo `tipo` no estado:

- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` → `texto`
- `text/plain` → `texto`
- `application/pdf` → `pdf`
- `image/png`, `image/jpeg`, `image/jpg`, `image/webp` → `imagem`

#### `preprocessar_arquivo`

Prepara o conteúdo conforme o tipo:

- **DOCX:** usa `python-docx` para extrair texto puro como string
- **TXT:** decodifica os bytes como UTF-8
- **PDF:** tenta `pdfplumber` para extrair texto. Se o texto extraído tiver menos de 100 caracteres (PDF escaneado sem camada de texto), converte a primeira página para imagem com `pdf2image` e trata como imagem
- **PNG / JPEG / JPG / WEBP:** converte para base64 com Pillow e armazena em `texto_preprocessado` com o prefixo `base64_image:` para sinalizar ao próximo nó que deve usar visão multimodal

#### `extrair_conteudo`

Chama o Gemini via LangChain com `ChatGoogleGenerativeAI` usando o modelo `gemini-1.5-flash`:

- Se `texto_preprocessado` começa com `base64_image:`: monta mensagem multimodal com `image_url` inline. O Gemini processa tanto imagens quanto PDFs escaneados via visão
- Caso contrário: manda o texto puro como conteúdo da mensagem

O prompt pede retorno estritamente em JSON com os seis campos do schema definido na seção 3.4.

#### `estruturar_output`

Usa `JsonOutputParser` do LangChain para garantir que o resultado é um dict Python válido. Se o parse falhar (o modelo retornou texto livre ou markdown em vez de JSON puro), incrementa `tentativas` e retorna ao nó `extrair_conteudo` com o prompt reforçado: *"Retorne APENAS JSON, sem texto antes ou depois, sem markdown, sem backticks."* Máximo de 2 retries.

#### `salvar`

Insere na tabela `ingestions` via `supabase-py`. O campo `extracted_content` recebe o dict diretamente — o cliente Supabase serializa para `jsonb` automaticamente.

### 4.3 Edges do grafo

```
detectar_tipo
  → preprocessar_arquivo
  → extrair_conteudo
  → estruturar_output
    → (inválido, tentativas < 2) → extrair_conteudo [retry]
    → (válido) → salvar → END
```

---

## 5. Fluxo de Geração (Grafo de Geração)

**Arquivo:** `graphs/generation_graph.py`

### 5.1 Estado do grafo

| Campo | Tipo | Descrição |
|---|---|---|
| `projeto_id` | str | UUID do projeto |
| `projeto_nome` | str | Nome do projeto — usado nos prompts |
| `cliente` | str | Nome do cliente — usado nos prompts |
| `tipo_doc` | str | `sprint_status` \| `sprint_retro` \| `decisoes` \| `completo` |
| `sprint_numero` | int \| None | Número da sprint — `None` para tipos que cobrem o projeto inteiro |
| `ingestions` | list | Lista de registros buscados do Supabase |
| `contexto` | str | Texto compilado de todas as ingestões relevantes |
| `documento` | str | Markdown final gerado pelo Gemini |

### 5.2 Nós do grafo

#### `buscar_ingestions`

Consulta a tabela `ingestions` no Supabase:

- `sprint_status` e `sprint_retro`: filtra por `projeto_id` + `sprint_number`
- `decisoes` e `completo`: busca todos os registros do `projeto_id`, ordena por `sprint_number ASC`

#### `compilar_contexto`

Transforma a lista de ingestões em bloco de texto estruturado que o modelo vai consumir como contexto. Cada ingestão vira:

```
--- Sprint {n} | {file_name} ---
Resumo: {resumo}
Tarefas: {tarefas separadas por virgula}
Decisoes: {decisoes separadas por virgula}
Problemas: {problemas separados por virgula}
Contexto do cliente: {contexto_cliente}
Proximos passos: {proximos_passos separados por virgula}
```

Quanto mais o gerente alimentou ao longo do projeto, mais rico fica esse contexto e mais preciso o documento gerado.

#### `selecionar_prompt`

Usa `ChatPromptTemplate.from_template()` do LangChain com um template diferente por `tipo_doc`:

| `tipo_doc` | Seções do documento gerado |
|---|---|
| `sprint_status` | O que foi concluído nesta sprint / O que está pendente / Bloqueios identificados |
| `sprint_retro` | O que foi feito / O que funcionou / O que não funcionou / Aprendizados e decisões tomadas |
| `decisoes` | Log cronológico: Sprint · Decisão tomada · Motivo (para todo o projeto) |
| `completo` | Visão geral · Timeline de sprints · Decisões arquiteturais · Desafios · Estado atual |

#### `gerar_documento`

Executa a chain: `prompt | ChatGoogleGenerativeAI(model=gemini-1.5-flash) | StrOutputParser()`. O output é markdown estruturado com headings e listas.

#### `salvar_documento`

Insere o markdown na tabela `generated_docs` e retorna o conteúdo para o router FastAPI, que responde ao frontend.

### 5.3 Edges do grafo

```
buscar_ingestions → compilar_contexto → selecionar_prompt → gerar_documento → salvar_documento → END
```

---

## 6. API FastAPI

| Método | Rota | Body / Params | Descrição |
|---|---|---|---|
| POST | `/projects` | JSON: `name`, `client`, `description` | Cria novo projeto |
| GET | `/projects` | — | Lista todos os projetos |
| GET | `/projects/{id}` | Path: `id` | Busca projeto por ID |
| POST | `/ingest` | multipart: `arquivo`, `sprint_numero`, `projeto_id` | Inicia grafo de extração |
| GET | `/ingestions/{projeto_id}` | Path: `projeto_id` | Lista ingestões do projeto |
| GET | `/ingestions/{projeto_id}/{sprint}` | Path: `projeto_id`, `sprint` | Ingestões de uma sprint específica |
| POST | `/generate` | JSON: `projeto_id`, `tipo_doc`, `sprint_numero?` | Inicia grafo de geração |
| GET | `/docs/{projeto_id}` | Path: `projeto_id` | Lista documentos gerados |

CORS configurado no `main.py` para aceitar qualquer origem durante desenvolvimento (`allow_origins=["*"]`).

---

## 7. Frontend — Três Telas

### 7.1 `/` — Lista de projetos (`page.tsx`)

- Exibe cards com nome e cliente de cada projeto
- Botão para criar novo projeto
- Clique no card navega para o dashboard do projeto

### 7.2 `/projects/new` — Criar projeto (`page.tsx`)

- Formulário com campos: Nome do projeto, Cliente, Descrição (opcional)
- Submit chama `POST /projects` e redireciona para o dashboard do projeto criado

### 7.3 `/projects/[id]` — Dashboard do projeto (`page.tsx`)

**Seção de Ingestão:**
- Input numérico para número da sprint
- Upload de arquivo — aceita: `.docx`, `.pdf`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.webp`
- Ao submeter: chama `POST /ingest` via `multipart/form-data` e exibe status de sucesso ou erro

**Seção de Histórico:**
- Lista de ingestões agrupadas por sprint
- Exibe: nome do arquivo, data, e o campo `resumo` do JSON extraído

**Seção de Geração:**
- Quatro botões: Status da Sprint, Retrospectiva, Log de Decisões, Documento Completo
- Botões de Status e Retrospectiva abrem um input para número da sprint antes de gerar
- Chama `POST /generate` e exibe o documento em markdown renderizado via `react-markdown`
- Botão de copiar o markdown gerado

---

## 8. Estrutura de Pastas

### 8.1 Backend

```
docudata-backend/
├── main.py              # FastAPI app — registra routers e configura CORS
├── requirements.txt
├── Procfile             # web: uvicorn main:app --host 0.0.0.0 --port $PORT
├── .env.example
├── routers/
│   ├── projects.py      # CRUD de projetos
│   ├── ingest.py        # recebe upload e dispara extraction_graph
│   └── generate.py      # recebe tipo_doc e dispara generation_graph
├── graphs/
│   ├── extraction_graph.py   # LangGraph — fluxo de ingestão
│   └── generation_graph.py   # LangGraph — fluxo de geração
├── services/
│   ├── supabase_client.py    # inicialização do cliente Supabase
│   └── file_parser.py        # parsing de DOCX, PDF, TXT, imagens
└── models/
    └── schemas.py       # Pydantic models para request e response
```

### 8.2 Frontend

```
docudata-frontend/
└── app/
    ├── page.tsx                  # lista de projetos
    ├── projects/
    │   ├── new/page.tsx          # formulário de criação
    │   └── [id]/page.tsx         # dashboard do projeto
    └── lib/
        └── api.ts                # funções fetch para todos os endpoints
```

---

## 9. Dependências e Variáveis de Ambiente

### 9.1 `requirements.txt` (backend)

| Pacote | Uso |
|---|---|
| `fastapi` | Framework web Python para a API REST |
| `uvicorn` | Servidor ASGI para rodar o FastAPI |
| `python-multipart` | Suporte a upload de arquivos no FastAPI |
| `supabase` | Cliente Python para Supabase (`supabase-py`) |
| `langchain` | Abstração sobre modelos de linguagem — prompts, parsers, chains |
| `langgraph` | Orquestração de fluxos com grafo de estados |
| `langchain-google-genai` | Integração LangChain com Gemini |
| `python-docx` | Extração de texto de arquivos DOCX |
| `pdfplumber` | Extração de texto de PDFs com camada de texto |
| `pdf2image` | Conversão de PDFs escaneados para imagem |
| `Pillow` | Manipulação de imagens e conversão para base64 |
| `python-dotenv` | Carregamento de variáveis do `.env` |
| `pydantic` | Validação de schemas de request e response |

### 9.2 Variáveis de ambiente (`.env`)

| Variável | Onde obter |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio — aistudio.google.com |
| `SUPABASE_URL` | Painel do projeto Supabase — Settings > API |
| `SUPABASE_SERVICE_KEY` | Painel do projeto Supabase — Settings > API (service_role key) |

---

## 10. Deploy

### 10.1 Backend — Railway

1. Sobe o repositório `docudata-backend` no GitHub
2. Cria novo projeto no Railway e conecta o repositório
3. Railway detecta o `requirements.txt` automaticamente
4. Adiciona as três variáveis de ambiente no painel do Railway
5. Railway gera uma URL pública — ex: `docudata-backend.up.railway.app`

### 10.2 Frontend — Vercel

1. Sobe o repositório `docudata-frontend` no GitHub
2. Cria novo projeto no Vercel e conecta o repositório
3. Vercel detecta Next.js automaticamente
4. Adiciona variável de ambiente:
   ```
   NEXT_PUBLIC_API_URL=https://docudata-backend.up.railway.app
   ```
5. Deploy automático a cada push na branch `main`

---

## 11. Ordem de Implementação

Sequência recomendada para implementar o MVP em uma semana:

| Etapa | Arquivo(s) | Estimativa |
|---|---|---|
| 1 | `schemas.py` — Pydantic models de request e response | 1–2h |
| 2 | `supabase_client.py` — inicialização e helpers de query | 1h |
| 3 | `file_parser.py` — parsing de DOCX, PDF, TXT, PNG, JPEG, WEBP | 2–3h |
| 4 | `extraction_graph.py` — grafo completo com todos os nós e edges | 3–4h |
| 5 | `generation_graph.py` — grafo completo com os quatro tipos de documento | 3–4h |
| 6 | `routers/` — `projects.py`, `ingest.py`, `generate.py` | 2–3h |
| 7 | `main.py` — registrar routers, configurar CORS | 30min |
| 8 | `lib/api.ts` — funções fetch para todos os endpoints | 1–2h |
| 9 | `page.tsx`, `projects/new`, `projects/[id]` — as três telas | 4–6h |
| 10 | Testes end-to-end + ajustes de prompt + deploy | 3–4h |

---

## 12. Decisões de Design

| Decisão | Alternativa considerada | Motivo da escolha |
|---|---|---|
| Gemini 2.5 Flash como modelo | Claude ou GPT-4 | Aceita imagens e PDFs nativamente, custo menor, API key gratuita disponível |
| Sprint como metadado obrigatório no upload | Inferir sprint pelo timestamp | Permite ao gerente atribuir uploads retroativos à sprint correta sem ambiguidade |
| LangGraph para orquestração | Chains simples do LangChain | Retry granular por nó e estado explícito — facilita debugging e extensão futura |
| JSON com 6 campos fixos como schema de extração | Texto livre no banco | Permite filtrar, agregar e referenciar campos específicos na compilação de contexto |
| Markdown como formato de output de geração | DOCX ou PDF direto | Renderizável no frontend, copiável, e portável — o gerente pode colar em qualquer ferramenta |
| FastAPI separado do frontend | Next.js com API routes | Permite escalar backend independentemente e usar Python com suas bibliotecas de dados |

<!-- GSD:project-start source:PROJECT.md -->
## Project

**DocuData**

DocuData é um sistema web que permite a gerentes de projetos de dados do CITi alimentar seus projetos com arquivos do dia a dia (documentos de task, prints de kanban, atas de reunião, PDFs) e receber documentação estruturada gerada automaticamente. Um agente LangGraph processa cada arquivo, extrai conhecimento estruturado e o acumula por projeto e sprint; o gerente pode então gerar documentos sob demanda — status de sprint, retrospectiva, log de decisões ou documento completo do projeto.

**Core Value:** O fluxo de ingestão + geração precisa funcionar de ponta a ponta — subir um arquivo, extrair conteúdo estruturado e gerar um documento útil.

### Constraints

- **Stack:** Next.js (frontend) + FastAPI Python (backend) + LangGraph/LangChain + Gemini 1.5 Flash + Supabase PostgreSQL — stack definida no design doc
- **Modelo de IA:** Gemini 1.5 Flash — aceita imagens e PDFs nativamente, API key gratuita, custo menor
- **Deploy:** Railway (backend) + Vercel (frontend) — conforme design doc
- **Prazo:** ~3 dias para MVP funcional
- **Sem auth v1:** Espaço compartilhado sem isolamento por usuário — decisão consciente para simplificar o MVP
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Key Findings
- LangGraph `StateGraph` API is stable since 0.1.x. Correct pattern: `TypedDict` state + node functions returning partial dicts + `add_conditional_edges` for retry. `compile()` once at module level, `invoke()` per request.
- `langchain-google-genai` `ChatGoogleGenerativeAI` supports multimodal via `HumanMessage` with `image_url` content type using `data:{mime};base64,{str}` inline URLs.
- `supabase-py` v2 sync API handles `dict` → `jsonb` serialization automatically. Use `service_role` key on backend.
- FastAPI requires `python-multipart` installed explicitly; without it, `UploadFile` routes fail with 422.
- `pdf2image` requires `poppler-utils` system package on Railway — **not installed by default**. Add `nixpacks.toml`.
- LangChain, FastAPI, and supabase-py have all made breaking API changes in the last 2 years.
## Recommended Stack (prescriptive)
### Backend
### Frontend
## LangGraph StateGraph Pattern
# Define state
# Compile once at module level (NOT inside a request handler)
# ... add nodes ...
## Gemini Multimodal Pattern
# Image / scanned PDF path
# Text path
## Railway Deployment
## Critical "What NOT To Do"
## Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| LangGraph StateGraph API | HIGH | Stable API, well-documented |
| langchain-google-genai multimodal | MEDIUM | Verify exact HumanMessage dict structure against current PyPI |
| supabase-py v2 sync API | HIGH | Stable, canonical API |
| FastAPI file upload | HIGH | Unchanged since FastAPI 0.95+ |
| Library versions | MEDIUM | Accurate Aug 2025; verify before pinning |
| Railway + poppler | MEDIUM | nixpacks.toml approach documented; verify current Railway defaults |
## Roadmap Implications
- **Phase 1:** `schemas.py` + `supabase_client.py` + `file_parser.py` can be built in parallel — no LangGraph dependency.
- **Phase 2:** `extraction_graph.py` is highest risk — depends on pdf2image + poppler on Railway, Gemini multimodal, JSON retry. Build and test locally before Railway deploy.
- **Phase 3:** `generation_graph.py` simpler — no multimodal, no retry. Depends on Phase 1 being stable.
- **Phase 4:** Routers + frontend — mechanical wiring after Phase 3.
## Open Questions
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
