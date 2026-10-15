# DocuData — Documento de Contexto

> Documento de contexto técnico-funcional do sistema, escrito para ser lido por um
> agente de IA. Descreve o estado real do código em 12/09/2026 — não é o design doc
> original (que está desatualizado em relação ao que foi construído).
>
> Repositório: `Documentador/` · Backend `docudata-backend/` · Frontend `docudata-frontend/`

---

## 1. O que o sistema é

DocuData é um sistema web interno da subárea de Dados do CITi. O problema de origem
era documentação: gerentes de projeto não documentam, e o conhecimento se perde no
fim de cada gestão. A aposta do produto é inverter o fluxo — em vez de pedir que
alguém escreva documentação, o sistema lê o que o time já produz (kanban, atas,
prints, PDFs, commits) e monta os documentos sozinho.

Ao longo do desenvolvimento o escopo cresceu de "gerador de documentos" para três
produtos que compartilham a mesma fonte de dados:

1. **Documentação automática** — 9 tipos de documento gerados por IA a partir do que
   foi alimentado no sistema.
2. **Saúde do projeto** — prazo × escopo, SPI, throughput, cycle-time, CFD,
   eficiência de fluxo, gargalos por fase.
3. **Acompanhamento de contribuição individual** — um motor de score que consolida,
   a cada fechamento de sprint, cinco dimensões por pessoa e alimenta um ranking.

A premissa que amarra os três: **a única fonte é o trabalho registrado no sistema**.
Não existe um passo separado de "documentar" — quanto mais fiel o Kanban, melhor
tudo o que sai dele.

---

## 2. Stack e arquitetura

| Camada | Tecnologia | Observação |
|---|---|---|
| Frontend | Next.js (App Router) + React + TypeScript | Deploy Vercel |
| Backend | FastAPI (Python) | Deploy Railway |
| Agente IA | LangChain + LangGraph | Roda dentro do processo FastAPI |
| Modelo | **`gemini-3.5-flash-lite`** via `langchain-google-genai` | Único modelo usado (13 pontos de chamada) |
| Banco | Supabase (PostgreSQL), cliente `supabase-py` v2 | Chave `service_role` no backend |
| E-mail | Resend | Lembretes e notificações |
| Export | Google Docs API | Exportação de documento gerado |
| Scheduler | APScheduler dentro do lifespan do FastAPI | 2 jobs recorrentes |

### Estrutura de pastas (backend)

```
docudata-backend/
├── main.py                  # app FastAPI, CORS, scheduler, registro de 27 routers
├── supabase_schema.sql      # schema completo, idempotente — NUNCA roda sozinho
├── models/schemas.py        # todos os Pydantic models (~746 linhas)
├── routers/                 # 27 routers
├── graphs/                  # extraction_graph, generation_graph, import_graph
├── services/                # regras de negócio compartilhadas
├── hooks/                   # agentes instaláveis no repo do cliente (GitHub Actions)
├── docs/                    # 3 markdowns servidos pelo app via /metodologia
├── tests/                   # ~40 arquivos de teste (pytest)
└── evals/                   # testes do grafo de extração
```

### Detalhes de infraestrutura que importam

- **CORS restrito**: `allow_origins=[FRONTEND_URL]` com `allow_credentials=True` —
  necessário porque a sessão é cookie httpOnly. Não é mais `["*"]`.
- **Exception handler global** em `main.py`: sem ele, exceção não tratada escapa da
  `ExceptionMiddleware` antes do `CORSMiddleware` rodar, e o navegador reporta
  "bloqueado por CORS" escondendo o erro real.
- **Migrações são manuais.** `supabase_schema.sql` é idempotente e precisa ser colado
  no SQL Editor do Supabase à mão. Não há CI/CD de schema. Qualquer alteração de
  schema exige avisar quem for aplicar.

### Variáveis de ambiente

`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `JWT_SECRET` (obrigatórias — acesso direto a
`os.environ[...]`), `GEMINI_API_KEY`, `FRONTEND_URL`, `RESEND_API_KEY`, `RESEND_FROM`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`,
`GDOCS_TEMPLATE_ID`, `GDRIVE_FOLDER_ID`.

Frontend: `NEXT_PUBLIC_API_URL`.

---

## 3. Autenticação e RBAC

`services/auth.py`. JWT (HS256, 8h) em **cookie httpOnly** `docudata_session`. Sem
tabela de sessão e sem refresh token: expirou, loga de novo. Senha com bcrypt.

### Hierarquia de cargos

```python
_HIERARQUIA = ["operacional", "gerente", "lider", "owner"]
```

Um cargo alcança tudo o que os abaixo alcançam.

| Cargo | Alcance |
|---|---|
| **owner** | Tudo + único que promove/rebaixa cargos de outras pessoas |
| **lider** | Todos os projetos + área de Performance (ranking) + reabrir fechamento de sprint |
| **gerente** | Todos os projetos, sem ranking de performance |
| **operacional** | Só os projetos em que está cadastrado como `operacionais`, e só as abas Sprints, Tasks, Tecnologias e Documentos |

### Dependencies de gate

- `get_current_pessoa` — decodifica o JWT, devolve `{id, email, cargo}`.
- `require_role(cargo_minimo)` — compara pela hierarquia.
- `require_not_operacional` — bloqueia só o cargo mais baixo.
- `require_project_access(project_id)` — gerente+ passa direto; operacional precisa ter
  linha em `operacionais` com o mesmo e-mail naquele projeto.

### Cadastro

Duas rotas: `POST /auth/signup/claim` (a pessoa reivindica uma linha `operacionais`
já criada por um gerente, casando por e-mail) e `POST /auth/signup/novo`. Ambas
coletam `github_login` e `github_email` — o e-mail do GitHub é separado do e-mail de
login porque o que casa commit é o `git config user.email` local, nem sempre igual ao
e-mail do CITi.

---

## 4. Modelo de dados

Todas as tabelas em Supabase/PostgreSQL. FKs para `projects` em geral com
`ON DELETE CASCADE`.

### Núcleo

**`projects`** — `id`, `name`, `client`, `description`, `squad`, `gemini_api_key`
(chave própria por projeto; nunca exposta na API — `_sanitize()` remove antes de
responder), `is_delivered`, `data_inicio`, `data_fim_contratada`,
`tolerancia_desvio_pontos` (default 20), `periodo_garantia_dias`, `github_token`,
`github_repo`, `wip_config` (jsonb: `{por_pessoa, por_coluna_em_andamento}`),
`valor_por_ponto`, `valor_projeto`, `arquetipo` (`padrao` | `consultoria_discovery`).

**`ingestions`** — toda matéria-prima que entra no sistema. `project_id`,
`sprint_number`, `file_name`, `file_type`, `tipo_documentacao`
(`planning|daily|review|retrospectiva|commit|outro`), `extracted_content` (jsonb com o
JSON extraído pela IA).

**`generated_docs`** — `project_id`, `doc_type`, `sprint_number`, `content` (markdown).

**`sprints`** — `project_id`, `numero` (UNIQUE junto), `status_saude`
(`verde|amarelo|vermelho`), `plano_correcao`, `pontos_previstos`, `pontos_orcamento`,
`faturamento_previsto`, `baseline_locked_at`, `data_inicio`, `data_fim`,
`avaliacao_completa_em`, **`iniciada`** (boolean).

> `iniciada` separa *sprint planejada* de *sprint em execução*: uma sprint criada na
> aba Planejamento (para reservar orçamento de pontos com antecedência) não aparece na
> aba Sprints com Planning/Daily/Review até ser iniciada. Mesma linha, mesmo
> `sprint_id` — só esconde da aba de execução.

### Escopo

**`funcionalidades`** — entregas de alto nível para o cliente. `id_funcional`,
`titulo`, `descricao`, `criterios_aceite[]`, `prioridade` (MoSCoW: must/should/could/
won't), `status` (`nao_iniciada|em_andamento|concluida`), `status_cliente`
(`nao_enviado|...|aprovado`), `data_aprovacao_cliente`, `responsavel`, `sprint_alvo`,
`testes_e2e[]`.

**`transicoes_status`** — histórico de mudança de campo de funcionalidade, com
`duracao_fase_anterior_segundos` (é o que alimenta tempo-por-fase e eficiência de fluxo).

**`sprint_funcionalidades`** — liga funcionalidade ↔ sprint com `status` e `tasks` (jsonb).

### Execução

**`operacionais`** — uma linha **por pessoa por projeto**. `nome`, `email`, `papel`,
`ativo`, `github_login`, `github_email`. Identidade cross-projeto é reconciliada **por
e-mail** (ver `services/performance.py::listar_pessoas_ativas`).

**`tasks`** — o coração do sistema. `project_id`, `funcionalidade_id`, `sprint_id`
(CASCADE), `operacional_id`, `titulo`, `descricao`, `pontos` (>0), `coluna_kanban`
(`planejado|em_andamento|concluida`), `checklist` (jsonb), `ordem`,
`bloqueado`/`motivo_bloqueio`, `contador_reaberturas`, `bloqueado_manual`,
`bloqueado_em`, `bloqueado_por`, `bloqueado_resolvido_por` (`operacional|gerente`),
`bloqueado_resolvido_em`, `entrou_em_andamento_em`, `travado_automatico`,
`travado_override` (+ `_por`, `_em`), **`extra`** (task concedida além do planejado).

**`task_transicoes`** — histórico de movimentação, com snapshot de `operacional_id` no
momento da transição (permite saber quem estava com a task mesmo após reatribuição).

**`task_reaberturas`**, **`task_travamentos`**, **`task_sugestoes`**,
**`solicitacoes_task`** (pedido de task extra, com `sugestao` em texto livre).

### Score e performance

**`pessoa`** — conta de login. `email` UNIQUE, `nome`, `senha_hash`, `cargo`,
`github_login`, `github_email`.

**`avaliacoes_gerente`** — 7 respostas 0–5 por (operacional, sprint), com
`editavel_ate` e `reaproveitada_de`.

**`pontuacao_operacional_sprint`** — **linha travada** de dado bruto por (operacional,
sprint). É o registro imutável que alimenta o ranking. Campos: `gerente_media`,
`gerente_pergunta3`, `gerente_pergunta6`, `entrega_pontos_concluidos`,
`entrega_pontos_alocados`, `entrega_pontos_penalizados`, `bonus_pontos_extra`,
`qualidade_reaberturas`, `qualidade_tasks_concluidas`, `qualidade_commit_media`,
`autonomia_bloqueios_resolvidos_proprio`, `autonomia_bloqueios_totais`,
`finalizado_em`.

**`pesos_arquetipo`** — pesos das dimensões por arquétipo de projeto.

**`eventos_pontuacao_tardios`** — ledger para eventos de qualidade/autonomia que
acontecem numa task cuja sprint de origem já fechou. Redireciona para a sprint ativa em
vez de descartar.

**`commit_qualidade`** — nota 0–10 por commit, atribuída por IA.

**`baseline_evolucao`** — snapshot de nota inicial por ciclo.

### Outras

**`revisoes_diarias`** (revisor de código), **`execucoes_aceite`** (gates de CI),
**`boletins_aceite`**, **`planning_rascunhos`** (composer), **`audit_log`**,
**`sprint_notifications`** (dedup de e-mail).

### View

**`sprint_spi`** — `pontos_realizados` (soma de pontos de tasks concluídas) sobre
`pontos_previstos`, por sprint.

> ⚠️ As colunas `input_tokens`, `output_tokens`, `cost_usd` (em `ingestions` e
> `generated_docs`) e `budget_usd` (em `projects`) **ainda existem no schema mas não
> são mais lidas nem escritas por nenhum código**. O rastreamento de custo de IA foi
> removido do produto em 07/09/2026. Não readicionar.

---

## 5. Os dois grafos LangGraph

### 5.1 Grafo de Extração (`graphs/extraction_graph.py`)

Roda a cada arquivo que entra no sistema.

```
START → validar_tipo ─┬─ (bloqueado) → END
                      └→ detectar_tipo → preprocessar_arquivo → extrair_conteudo
                                                                     ↓ (retry ≤2)
                                                                 estruturar/roteador
                                                                     ↓ (válido)
                                                                   salvar → END
```

**`validar_tipo`** — classifica o documento em 8 categorias (`planning`, `daily`,
`review`, `retrospectiva`, `ata_reuniao`, `commit`, `upload_livre`, `nao_relacionado`)
usando nome/cliente/descrição do projeto como contexto, e compara com o tipo esperado
pela rota. O prompt instrui explicitamente a devolver `nao_bloquear: true` em caso de
dúvida — **nunca bloquear sem alta confiança**. `force=true` pula a validação.

**`preprocessar_arquivo`** (`services/file_parser.py`):
- DOCX → `python-docx`, texto puro
- TXT → decode UTF-8
- PDF → `pdfplumber`; se o texto extraído for vazio, converte a 1ª página para imagem
  com `pdf2image` a **100 DPI** e trata como imagem
- Imagens → Pillow, redimensiona para máx. **1024px** no lado maior, normaliza para
  PNG, base64

> As duas constantes de tamanho (100 DPI, 1024px) são deliberadas: cada 256px extra
> custa ~258 tokens de visão sem ganho de extração.

**`extrair_conteudo`** — chama o Gemini com `with_structured_output(ConteudoEstruturado,
method="json_schema")`. Retry com prompt endurecido ("APENAS JSON, sem markdown, sem
backticks"), máximo de 2 tentativas.

**Schema de extração (`ConteudoEstruturado`)** — o contrato que atravessa todo o sistema:

```python
resumo: str
tarefas: list[str]
decisoes: list[str]
problemas: list[str]
contexto_cliente: str
proximos_passos: list[str]
tecnologias: list[str]
tecnologias_removidas: list[str]   # só remoção explícita em commit
```

### 5.2 Grafo de Geração (`graphs/generation_graph.py`)

```
START → buscar_ingestions → compilar_contexto → gerar_documento → salvar_documento → END
```

**Escopo de busca por tipo de documento:**

| Escopo | Tipos | Query |
|---|---|---|
| ingestion-only | `ata_reuniao`, `planning`, `daily` | `WHERE id = <ingestion_id>` (âncora criada imediatamente antes) |
| sprint-scoped | `repasse_semanal`, `retrospectiva`, `review` | `WHERE project_id = X AND sprint_number = N` |
| project-wide | `log_decisoes`, `onboarding`, `documentacao_final` | `WHERE project_id = X ORDER BY sprint_number ASC` |

**Guardas anti-alucinação (`_validar_contexto_suficiente`)** — o grafo se recusa a gerar:
- qualquer tipo sem nenhuma ingestão no escopo;
- `log_decisoes` se nenhuma ingestão tem o campo `decisoes` preenchido;
- `documentacao_final` com dados de menos de 2 sprints.

**`compilar_contexto`** — serializa cada ingestão em bloco de texto marcado com sprint,
arquivo e tipo, e para tipos sprint-scoped **injeta também o kanban de tasks real da
sprint** (`_bloco_kanban_tasks`). Campos estruturados preenchidos pelo gerente
(`campos_planning`, `campos_daily`, `campos_review`, `campos_retrospectiva`) entram
rotulados como "preenchidos pelo gerente".

---

## 6. Os 9 tipos de documento

Metadados canônicos em `docudata-frontend/app/lib/doc_types.ts` (`o_que`, `pra_que`,
`quando`, `fontes` — consumidos pelo `DocTypeCard` na UI).

| Tipo | Escopo | O que é |
|---|---|---|
| `repasse_semanal` | sprint | Status executivo da sprint: concluído / em andamento / bloqueado |
| `retrospectiva` | sprint | O que foi feito, o que funcionou, o que não funcionou, aprendizados |
| `review` | híbrido | Planejado vs. entregue, com o delta explicitado |
| `planning` | híbrido | Backlog, objetivos, responsabilidades, riscos da sprint |
| `daily` | híbrido | Feito / fazendo / impedimentos |
| `ata_reuniao` | ingestão | Ata formal: pauta, decisões, outcomes, outputs |
| `log_decisoes` | projeto | Log cronológico de todas as decisões técnicas e de escopo |
| `onboarding` | projeto | Guia de ramp-up: contexto, stack, decisões, estado atual |
| `documentacao_final` | projeto | Entregável de fechamento no template do CITi |

"Híbrido" = criado por modal estruturado (formulário + anexo opcional), que cria a
ingestão e dispara a geração na mesma chamada.

Além disso: **doc manual** (`POST /docs/manual`) para colar texto pronto sem custo de
IA, e **doc manual via PDF** (`/docs/manual/upload`).

Todo documento gerado pode ser copiado como markdown, **exportado para o Google Docs**
(`POST /docs/{id}/export-gdocs`) ou **movido de sprint sem regerar**
(`PATCH /docs/{id}`).

---

## 7. Funcionalidades por tela

### 7.1 Telas globais

- `/login`, `/cadastro` — login e os dois fluxos de signup.
- `/` — lista de projetos (filtrada por acesso), criação de projeto.
- `/projects/new` — formulário de criação.
- `/performance` — ranking (só Líder+).
- `/pessoas` — gestão de cargos (só Owner efetivamente altera).
- `/metodologia` — os 3 documentos internos servidos pelo backend.

### 7.2 Abas do projeto (`/projects/[id]`)

Operacional só vê: **Sprints, Tasks, Tecnologias, Documentos**.

#### Painel
Quatro blocos calculados em `routers/painel.py`:
- **Bloco A — Tempo × Escopo**: `pct_prazo_consumido` (dias corridos sobre
  `data_inicio`→`data_fim_contratada`) vs. `pct_escopo_concluido` e
  `pct_aprovado_cliente`. O **desvio** é `pct_prazo − pct_aprovado`; acima de
  `tolerancia_desvio_pontos` dispara alerta.
- **Bloco B — Itens em atenção**: funcionalidades travadas, dependentes de cliente,
  de dependência externa ou de decisão pendente; WIP, throughput e cobertura de aceite.
- **Bloco C — Cycle-time de funcionalidades** e eficiência de fluxo (% do tempo em
  que a funcionalidade esteve de fato em andamento, não parada entre etapas).
- **Bloco D — Tempo por fase**: onde está o gargalo, a partir de
  `duracao_fase_anterior_segundos`.

#### Planejamento (Escopo)
- CRUD de **funcionalidades** com MoSCoW e critérios de aceite.
- **Importar do contrato**: sobe o PDF da proposta, a IA extrai as funcionalidades,
  o gerente revisa e confirma (`/funcionalidades/importar/arquivo` →
  `/funcionalidades/importar/confirmar`). Usa `graphs/import_graph.py`.
- **Orçamento de 100 pontos**: todo projeto vale 100 pontos fixos, distribuídos entre
  sprints. Regras: a soma não pode passar de 100, e uma sprint não pode receber menos
  do que as tasks dela já somam. Sprint sem orçamento não trava nada.
- **Valor do projeto**: informado em reais, cada ponto passa a valer 1/100 do valor e
  o faturamento previsto por sprint é derivado. Congela quando a primeira sprint
  recebe orçamento.
- Criação de sprints planejadas (`iniciada = false`).

#### Tasks (Kanban)
Três colunas: Planejado, Em andamento, Concluída.

- **Criação**: título e pontos obrigatórios; sprint, operacional, funcionalidade e
  checklist opcionais.
- **Checklist como DoD gate**: task com checklist só vai para Concluída com todos os
  itens marcados. O card mostra "3/5".
- **Sprint obrigatória para iniciar**: task só entra em Em andamento se tiver sprint.
- **Limites WIP** (`services/wip_check.py`): configuráveis por projeto
  (`por_coluna_em_andamento`) e por pessoa (`por_pessoa`). Só são checados na entrada
  em `em_andamento`.
- **Bloqueio manual**: o operacional marca "Bloqueada" e escreve o motivo; o card ganha
  borda vermelha. Ao destravar, registra-se `bloqueado_resolvido_por`
  (`operacional` ou `gerente`) — esse campo alimenta a dimensão Autonomia.
- **Travamento automático por tempo** (job diário, `services/travamento_checker.py`):
  task ativa (planejado **ou** em andamento) parada por
  `dias ≥ pontos × 1.5` ganha etiqueta amarela "Travada" e grava um evento em
  `task_travamentos`. O gerente pode dar **override** — travamento dispensado não
  penaliza ninguém.
- **Reabertura**: mover de Concluída de volta incrementa `contador_reaberturas` e grava
  em `task_reaberturas` — alimenta a dimensão Qualidade.
- **Pedido de task extra**: quando a pessoa fecha tudo que tinha, aparece o botão
  "Quero mais uma task", que abre `solicitacoes_task` com sugestão opcional em texto
  livre e avisa o gerente por e-mail. A task concedida é marcada `extra = true`: não
  consome orçamento de pontos da sprint e vira bônus no score, não Entrega.
- **Sugestões do review**: quando um review é ingerido, a IA detecta tasks mencionadas
  como concluídas e cria `task_sugestoes`; o gerente aceita ou ignora.
- **Redistribuir pontos** entre tasks da sprint (`POST /tasks/redistribuir-pontos`).

#### Sprints e Documentação
- **Criar sprint** (numeração automática, 1 semana), **iniciar sprint**
  (`PATCH /sprints/{id}/iniciar` → também **ancora o relógio de travamento** das tasks
  que já estavam nela e ainda não tinham relógio rodando).
- **Planning** — modal que já abre mostrando as tasks da sprint no Kanban (é dali que
  sai o backlog). Contexto em texto livre + campos estruturados (período, horas,
  riscos, dependências, carry-over). Há também o **Composer** (`routers/composer.py`),
  um fluxo multi-step com rascunho persistido em `planning_rascunhos` e cálculo de
  throughput de referência.
- **Daily** — cada upload vira histórico; sem mínimo obrigatório.
- **Review** — campos do gerente (percepção do cliente, sinal de satisfação, pedidos
  fora do escopo) + **tabela planejado vs. entregue montada automaticamente do kanban
  real** (`services/sprints.py::compute_planejado_vs_entregue`, 1 linha por task,
  `entregue = S` se concluída; `motivo_nao`/`causa_raiz` ficam em branco por serem
  julgamento humano).
- **Retrospectiva** — gerada a partir de planning + dailys + review.
- **Avaliação Semanal** — as 7 perguntas por pessoa que teve task na sprint; a
  confirmação **fecha e trava a pontuação da sprint**. Só o Líder reabre.
- **Pendências** — sprint sem planning ou review recebe badge "pend." na aba.

#### Métricas (`routers/metricas.py`)
- **SPI** por sprint: pontos concluídos / pontos previstos. ≥0,9 saudável; 0,7–0,9
  atenção; <0,7 crítico. Só aparece com orçamento definido.
- **Throughput** — tasks concluídas por sprint.
- **Cycle-time** — tempo em Em andamento, com percentis (`/cycle-time/stats`).
- **CFD** — foto do estado das tasks por sprint.
- **SPI por operacional (estimado)** — proxy **ao vivo** sobre as tasks atuais, para
  ver quem está sobrecarregado agora. Diferente do SPI travado que alimenta o ranking.
- **Entrega e evolução por pessoa** — dado consolidado dos fechamentos.

#### Tecnologias
Timeline construída por `services/tech_timeline.py` a partir do campo `tecnologias`
das ingestões. Regra importante: uma tecnologia só é marcada como **abandonada** se
aparecer explicitamente em `tecnologias_removidas` de alguma ingestão — ausência de
menção em sprints recentes **não** é abandono.

#### Documentos
Duas visões: **por sprint** (repasse + retrospectiva de cada uma) e **cross-sprint**
(ata, log de decisões, onboarding, documentação final, doc manual). Campo livre de
"observações adicionais" para orientar a IA.

#### Configurações
Datas de contrato, tolerância de desvio, período de garantia, limites WIP, arquétipo do
projeto, e-mail do gerente, chave Gemini própria do projeto, integração GitHub, marcar
projeto como entregue, excluir projeto.

---

## 8. Motor de Score

A parte mais densa em regra de negócio do sistema. Dois módulos:
`services/pontuacao.py` (fecha o dado bruto) e `services/performance.py` (calcula o
ranking).

### 8.1 Fechamento (`calcular_e_travar_pontuacao`)

Disparado quando o gerente **confirma a Avaliação Semanal** da sprint. É um cálculo
único a partir do estado final, **não um contador incremental** — por isso reatribuição
de task no meio da sprint não precisa de tratamento especial. **Idempotente**: se já
existe linha para a sprint, devolve as existentes sem recalcular.

Mecanismos-chave:

- **Cutoff**: usa o `finalizado_em` do último fechamento do projeto para não contar de
  novo reaberturas, travamentos e notas de commit já contabilizados.
- **"Quem completou"** (`_resolver_quem_completou`): lê `task_transicoes` filtrando
  `campo = coluna_kanban AND para = concluida`, pegando o snapshot de `operacional_id`
  da transição mais recente. Assim, quem recebe o crédito é quem estava com a task
  quando ela foi concluída, mesmo que tenha sido reatribuída depois.
- **Task extra** entra em `bonus_pontos_extra` e conta em `tasks_concluidas`, mas
  **não** entra em Entrega (nem no numerador nem no denominador) — pôr no denominador
  puniria quem pediu mais trabalho.
- **Travamento automático** desconta pontos da Entrega, mas **só de tasks que foram
  efetivamente concluídas**: se a task nunca foi concluída, seus pontos já não estão
  nos concluídos, e descontar de novo puniria as outras entregas da pessoa.
- **Eventos tardios** (`rotear_evento_pos_fechamento`): se uma reabertura ou bloqueio
  acontece numa task cuja sprint já fechou, o evento é redirecionado para a sprint
  ativa via `eventos_pontuacao_tardios`, em vez de descartado.

### 8.2 As 7 perguntas da avaliação do gerente

Cada uma de 0 a 5:

1. Entregou o que se comprometeu dentro do combinado nesta sprint?
2. A qualidade da entrega precisou de pouca ou nenhuma correção?
3. A pessoa destravou sozinha antes de te escalar?
4. A comunicação da entrega foi clara a ponto de você não precisar perguntar?
5. Ajudou, desbloqueou ou ensinou outro membro nesta sprint?
6. Evoluiu em relação a onde estava no começo do ciclo?
7. Trouxe algo além do que foi pedido?

**A pergunta 6 fica fora da média do gerente de propósito** — ela é a fonte exclusiva
da dimensão Evolução; contá-la também na média daria peso triplo a uma única pergunta.
A pergunta 3 é usada duas vezes: entra na média do gerente **e** alimenta Autonomia.

`gerente_media` = média das respostas 1, 2, 3, 4, 5, 7.

### 8.3 As 5 dimensões

Todas normalizadas para 0–100, com teto 100. Agregação em **duas camadas**: soma dentro
de cada projeto, depois **média simples entre projetos** (uma pessoa pode ter linhas de
`operacionais` em vários projetos, reconciliadas por e-mail).

| Dimensão | Fórmula |
|---|---|
| **Entrega** | `max(concluídos − penalizados, 0) / alocados × 100` |
| **Gerente** | `gerente_media × 20` |
| **Evolução** | `média(pergunta 6) × 20` |
| **Autonomia** | mistura `peso_pergunta3 × (média p3 × 20)` com `(1−peso) × (bloqueios resolvidos sozinho / totais × 100)` |
| **Qualidade** | mistura `peso_commit × (nota média de commit × 10)` com `(1−peso) × (max(1 − reaberturas/tasks concluídas, 0) × 100)` |

Decisões de design que estão codificadas ali e não são óbvias:

- **Autonomia**: o sinal de bloqueio só existe quando alguém marca bloqueio, o que na
  prática é raro. Sem a pergunta 3, Autonomia era sempre 100 e virava peso morto.
  Quando não há bloqueio nenhum, a pergunta 3 sustenta a dimensão sozinha.
- **Qualidade**: sem nenhuma task concluída e sem nota de commit, a dimensão fica
  **indisponível** (`None`), não 100 — dar 100 a quem não entregou nada premiava a
  ausência de entrega.
- **Dimensão indisponível não vira zero**: `_score_final` reponderar apenas os pesos
  das dimensões disponíveis (`soma_ponderada / peso_disponivel`).

### 8.4 Pesos por arquétipo

| Dimensão | `padrao` | `consultoria_discovery` |
|---|---|---|
| Gerente | 0,35 | **0,50** |
| Entrega | 0,20 | 0,20 |
| Qualidade | 0,20 | 0,10 |
| Autonomia | 0,15 | 0,12 |
| Evolução | 0,10 | 0,08 |

Auxiliares: `peso_commit_qualidade = 0.50` (mistura dentro de Qualidade),
`peso_pergunta3_autonomia = 0.50` (mistura dentro de Autonomia).

Consultoria/discovery não tem sinal de commit, então a leitura do gerente pesa mais.
O arquétipo usado numa janela é o **dominante** (mais linhas; empate desempatado pela
sprint mais recente).

### 8.5 Ranking

Três janelas por **contagem de sprints**, nunca por calendário:

```python
JANELAS = {"sprint": 1, "quinzenal": 2, "mensal": 4}
```

Só entram linhas com `entrega_pontos_alocados > 0`. Janela com menos linhas que o
esperado é marcada `janela_parcial = true`.

**Bônus de task extra**: 1 ponto de score por ponto entregue além do planejado, com
**teto de 5** — o teto é o que impede o ranking de virar "quem pediu mais task".
`score_final = min(base + bonus, 100)`.

### 8.6 Documentação da metodologia

Três markdowns em `docudata-backend/docs/`, servidos por `routers/metodologia.py` com
gate **por documento**:

| Slug | Arquivo | Acesso |
|---|---|---|
| `guia` | `guia-do-sistema.md` | todos |
| `acompanhamento` | `acompanhamento-publico.md` | todos |
| `performance` | `metodologia-performance.md` (1256 linhas: pesos, fórmulas, manual do gerente) | **Gerente+** |

A listagem também é filtrada — um operacional não vê sequer que o documento restrito
existe.

---

## 9. Integração com GitHub

Agentes instaláveis no repositório do cliente, em `docudata-backend/hooks/`. Todos são
**best-effort: nunca falham o processo do CI**.

### `docudata_agent.py` — ingestão de commits
Roda em GitHub Actions a cada push. Secrets: `DOCUDATA_API_URL`, `DOCUDATA_PROJECT_ID`.
Envia metadados + diff para `POST /ingest/commit`, que:

1. Resolve a sprint atual (última ingestão `planning` cujo `sprint_number` ainda existe;
   fallback: maior sprint).
2. Extrai `ConteudoEstruturado` do diff (inclui `tecnologias` e `tecnologias_removidas`).
3. **Avalia a qualidade técnica do commit de 0 a 10** (`AvaliacaoQualidadeCommit`) —
   olhando complexidade, documentação e aderência a boas práticas — e grava em
   `commit_qualidade`, alimentando a dimensão Qualidade do score.
4. Casa o commit com a pessoa por `github_login` / `github_email`.
5. Suporta tag `[task:<uuid>]` na mensagem do commit para vincular a uma task.

### `revisor_agent.py` — revisor diário
Envia o diff acumulado das últimas 24h para `POST /ingest/revisao`, que devolve achados
estruturados (`severidade`, `confianca`, `referencia` no formato `arquivo:linha`,
`descricao_tecnica`, `descricao_gerente`) gravados em `revisoes_diarias`, com relatório
em duas versões — uma para o gerente, outra técnica.

### `aceite_agent.py` — suíte de verificação de aceite
`POST /ingest/aceite` recebe o resultado dos 5 gates do CI e atualiza `execucoes_aceite`,
alimentando a cobertura de aceite no Painel.

---

## 10. Jobs automáticos

Dois jobs no APScheduler, iniciados no lifespan do FastAPI:

**`check_and_send_notifications`** (a cada 1h) — lembretes por e-mail via Resend:
- Planning: 24h após a criação da sprint, depois a cada 24h enquanto faltar
- Review: 5 dias após
- Retrospectiva: 7 dias após

Dedup por `sprint_notifications`: um e-mail por tipo, por sprint, por dia.

**`check_travamento_automatico`** (a cada 24h) — varre tasks em `planejado` ou
`em_andamento` e marca as que passaram de `pontos × 1.5` dias desde
`entrou_em_andamento_em`.

Outros e-mails transacionais: atribuição de task ao operacional, task concluída
(avisa o gerente), pedido de task extra (avisa o gerente).

---

## 11. Superfície de API

Base: `NEXT_PUBLIC_API_URL`. Autenticação por cookie em todas as rotas (exceto login e
signup). 27 routers.

| Grupo | Rotas principais |
|---|---|
| **auth** | `POST /auth/login`, `/logout`, `GET /auth/me`, `GET /auth/operacionais-sem-conta`, `POST /auth/signup/claim`, `/signup/novo` |
| **projects** | `POST/GET /projects`, `GET /projects/{id}`, `PATCH /{id}/api-key`, `/delivered`, `/gerente-email`, `/contrato`, `GET /{id}/technologies`, `DELETE /{id}` |
| **ingest** | `POST /ingest` (multipart), `POST /ingest/commit`, `/ingest/revisao`, `/ingest/aceite` |
| **ingestions** | `GET /ingestions/{proj}`, `/{proj}/{sprint}`, `PATCH`/`DELETE /ingestions/{id}` |
| **generate** | `POST /generate`, `GET /docs/{proj}`, `POST /docs/manual`, `/docs/manual/upload`, `PATCH`/`DELETE /docs/{id}`, `POST /docs/{id}/export-gdocs` |
| **sprint-docs** | `POST /sprint-docs/planning`, `/daily`, `/review`, `/retrospectiva`, `/ata`, `GET /sprint-docs/review/planejado-entregue` |
| **sprints** | `POST/GET /projects/{id}/sprints`, `PATCH /sprints/{id}/orcamento`, `/iniciar`, `/health`, `DELETE /sprints/{id}` |
| **tasks** | `POST/GET /tasks`, `PATCH`/`DELETE /tasks/{id}`, `POST /tasks/{id}/mover`, `/travado/override`, `PATCH /tasks/reordenar/batch`, `POST /tasks/redistribuir-pontos`, `GET/PATCH /tasks/sugestoes` |
| **funcionalidades** | CRUD + `POST /funcionalidades/importar`, `/importar/arquivo`, `/importar/confirmar`, `GET /{id}/transicoes` |
| **sprint-funcionalidades** | `POST`, `GET /sprint/{id}`, `PATCH /{id}`, `GET /recomendadas/{proj}` |
| **operacionais** | `POST`, `GET /projects/{id}`, `GET /disponiveis/{id}`, `PATCH /{id}`, `POST /{id}/remover-do-projeto`, `DELETE` |
| **avaliacoes** | `GET /avaliacoes/{sprint}/pendencias`, `POST /avaliacoes`, `POST`/`DELETE /avaliacoes/{sprint}/confirmar` |
| **pontuacao** | `GET` SPI do operacional, SPI+evolução do projeto, `POST` baseline |
| **performance** | `GET /performance` (ranking; Líder+) |
| **metricas** | `GET /metricas/{proj}/spi`, `/throughput`, `/cycle-time`, `/cycle-time/stats`, `/cfd`, `/performance-operacional` |
| **painel** | `GET /projects/{id}/painel` |
| **composer** | `GET`/`PATCH /composer/rascunho/{proj}/{sprint}`, `POST /composer/gerar`, `/confirmar` |
| **enrich** | `POST /enrich`, `/enrich/planning-correlacoes` |
| **boletins** | `POST`/`GET /boletins`, `POST /boletins/resumo_semanal`, `PATCH /boletins/{id}` |
| **solicitacoes** | `POST /solicitacoes-task`, `GET /projects/{id}`, `PATCH /{id}` |
| **pessoas** | `GET /pessoas`, `PATCH /pessoas/{id}` (cargo; Owner) |
| **metodologia** | `GET /metodologia`, `GET /metodologia/{slug}` |
| **search** | `GET /search?q=` (busca de stack entre projetos) |

---

## 12. Testes

~40 arquivos em `docudata-backend/tests/` (pytest), concentrados exatamente onde a
regra de negócio é densa: RBAC, fechamento de pontuação, eventos tardios, travamento,
reabertura, orçamento de sprint, DoD gate, task extra, arquétipo, SPI operacional,
planejado vs. entregue. Mais `docudata-backend/evals/` para o grafo de extração
(validade de schema, retry, escrita no Supabase).

---

## 13. Pontos de atenção conhecidos

- **Migrações são manuais** — `supabase_schema.sql` não roda sozinho.
- **Custo de IA foi removido** (07/09/2026): colunas `cost_usd`/`input_tokens`/
  `output_tokens`/`budget_usd` continuam no schema mas estão órfãs. A seção "Custos" do
  `guia-do-sistema.md` está desatualizada em relação a isso.
- **"Ver fontes" de documento é incompleto**: falta `ingestion_id` em `generated_docs`
  para linkar um documento à ingestão específica que o originou.
- **Chaves novas do Gemini só funcionam com `gemini-3.5-flash`+** — modelos 2.x
  respondem 404.
- **Identidade cross-projeto depende de e-mail**: `operacionais` sem e-mail preenchido
  vira uma pessoa distinta no ranking.
- **Sem multi-tenancy real**: gerente e líder enxergam todos os projetos.
- **Duas telas de Planning coexistem** — `SprintDocModal.tsx` (aba Sprints) e
  `PlanningModal.tsx` (Composer). Alteração no fluxo de planning precisa ser aplicada
  nas duas para não divergirem.
- **Boletim de aceite está implementado mas não é usado na prática** — o fluxo
  `boletins_aceite` existe end-to-end no backend e nunca entrou na rotina dos gerentes.
