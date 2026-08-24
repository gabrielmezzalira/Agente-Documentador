# Phase 12: Boletim de Aceite, Encerramento e Resumo Semanal - Context

**Gathered:** 2026-08-23
**Status:** Ready for planning

<domain>
## Phase Boundary

O gerente seleciona funcionalidades em status `concluida` e gera um boletim de aceite (por lote) para envio ao cliente. O boletim é redigido pelo Gemini com os critérios de aceite em linguagem de negócio. Ao marcar como enviado, as funcionalidades movem para `status_cliente = enviado`. O retorno do cliente é registrado como `aprovado` ou `ajuste pedido`; ajustes pedidos exigem classificação obrigatória: `bug` (dentro do escopo) ou `mudanca_escopo` (fora do escopo, lista separada). Quando 100% das funcionalidades estiverem `aprovado`, o sistema sinaliza o encerramento — sem geração de Termo de Encerramento (removido do escopo). Ao final de cada semana, o gerente pode gerar on-demand um resumo de anomalias por projeto (listagem estruturada, sem Gemini).

**Removido do escopo pelo usuário:**
- Campo de evidência visual no boletim
- Geração do Termo de Encerramento

</domain>

<decisions>
## Implementation Decisions

### Modelo do Boletim

- **D-01:** **Boletim por lote** — Um único boletim agrupa N funcionalidades concluídas selecionadas pelo gerente. Nova tabela `boletins_aceite`: `id uuid PK`, `project_id uuid FK→projects`, `sprint_numero int`, `funcionalidade_ids uuid[]`, `status text` (rascunho|enviado|aprovado|ajuste), `retorno_tipo text` (null|bug|mudanca_escopo), `conteudo text` (markdown gerado), `criado_em timestamptz`, `enviado_em timestamptz`, `retorno_em timestamptz`. — **Reversibility:** costly — adicionar histórico de revisões exigiria nova tabela de versões.

- **D-02:** **Gemini gera o conteúdo do boletim** — mesmo padrão do Composer (Phase 10): backend monta prompt com funcionalidades e seus `criterios_aceite`, Gemini (`gemini-1.5-flash`) elabora em linguagem de negócio, gerente vê preview (react-markdown) e confirma antes de marcar como `enviado`. O markdown gerado é salvo em `boletins_aceite.conteudo`.

- **D-03:** **Sem campo de evidência visual** — removido do escopo a pedido do usuário. [informational]

- **D-04:** **Sem geração de Termo de Encerramento** — removido do escopo a pedido do usuário. O sistema apenas sinaliza quando 100% aprovado (badge/mensagem na aba).

### Fluxo de Status do Cliente

- **D-05:** **`status_cliente` derivado do boletim** — ao criar o boletim, as funcionalidades incluídas recebem `status_cliente = rascunho` no boletim; ao marcar `enviado`, recebem `status_cliente = enviado` com `enviado_em` registrado; ao registrar retorno `aprovado`, recebem `status_cliente = aprovado`; ao registrar `ajuste`, recebem `status_cliente = ajuste_pedido`.

- **D-06:** **Classificação obrigatória ao registrar ajuste pedido** — o sistema exige seleção de `retorno_tipo`: `bug` (dentro do escopo, corrigido internamente) ou `mudanca_escopo` (fora do escopo, gera lista separada). Sem essa classificação, o retorno não pode ser salvo.

### Resumo Semanal de Anomalias

- **D-07:** **On-demand — botão no dashboard** — o gerente clica "Gerar Resumo desta Semana" na aba Aceite. Sem cron, sem GitHub Actions, sem infra extra. Mais simples para o MVP.

- **D-08:** **Listagem estruturada pura — sem Gemini** — o backend busca os dados diretamente do banco e formata em markdown estruturado: funcionalidades travadas, aguardando cliente, concluídas com suíte falhando, achados críticos (de revisão diária), decisões pendentes, leitura tempo × escopo. Quando não há anomalia, declara explicitamente. Deterministico, zero custo de token.

- **D-09:** **Período: semana atual (dom–sáb)** — cobre segunda a domingo da semana em curso no momento do clique. Não é janela deslizante.

- **D-10:** **Resumo salvo em `generated_docs`** — `doc_type = 'resumo_semanal'`, sem `sprint_number` (cobre o projeto inteiro na semana). Reutiliza a tabela existente.

### Frontend

- **D-11:** **Nova aba "Aceite" no Tabs.tsx** — ao lado das abas existentes (Visão Geral, Sprints, Painel, Planning, etc.). Mesmo padrão do Composer (Phase 10).

- **D-12:** **Aba Aceite contém duas seções:** (1) Boletins — lista de boletins existentes + botão "Novo Boletim" que abre seleção de funcionalidades concluídas e fluxo de geração; (2) Resumo Semanal — histórico de resumos + botão "Gerar Resumo desta Semana".

- **D-13:** **Termo de Encerramento substituído por sinalização simples** — quando 100% das funcionalidades tiverem `status_cliente = aprovado`, a aba Aceite exibe uma mensagem/badge de "Projeto encerrado — todas as funcionalidades aprovadas". Sem botão de geração de documento.

- **D-14:** **Zero className — apenas `style={{}}`** — padrão de todas as fases anteriores (8, 9, 10, 11).

### Claude's Discretion

- **Endpoint para boletim:** `POST /boletins` (cria rascunho + chama Gemini), `PATCH /boletins/{id}` (atualiza status: enviado/aprovado/ajuste + retorno_tipo), `GET /boletins/{project_id}` (lista por projeto).
- **Preview antes de confirmar:** igual ao Composer — o gerente vê o markdown gerado e confirma "Marcar como Enviado" para salvar o boletim e atualizar `status_cliente` nas funcionalidades.
- **Endpoint para resumo semanal:** `POST /generate/resumo_semanal` com `project_id` — reutiliza o router `/generate` existente ou cria endpoint dedicado no novo router `/boletins`.
- **"Mudanças de escopo" como lista separada:** a aba Aceite exibe uma seção "Mudanças de Escopo Solicitadas" listando funcionalidades com `retorno_tipo = mudanca_escopo`, sem integração com tabela de funcionalidades (só exibe).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Funcionalidades e Status (Phase 7)
- `docudata-backend/routers/funcionalidades.py` — `status_cliente` field; `PATCH /funcionalidades/{id}` handler que pode ser reutilizado para derivar status do boletim
- `docudata-backend/models/schemas.py` — `FuncionalidadeResponse`, campos `criterios_aceite` e `status_cliente`

### Geração de documentos (Padrão existente)
- `docudata-backend/routers/generate.py` — router de geração existente; `doc_type` enum; padrão de salvar em `generated_docs`
- `docudata-backend/routers/sprint_docs.py` — padrão de hybrid generation (campos estruturados + Gemini) — referência para o endpoint de boletim

### Composer Pattern (Phase 10 — referência para fluxo preview → confirmar)
- `.planning/phases/10-composer-de-planning/10-CONTEXT.md` — decisões D-05, D-06, D-07 descrevem o padrão preview + confirmação que o boletim replica

### Frontend — Tabs existente
- `docudata-frontend/app/projects/[id]/page.tsx` — onde a aba "Aceite" é adicionada (Tabs.tsx referenciado)
- `docudata-frontend/app/lib/api.ts` — funções fetch para todos os endpoints

### Painel — Anomalias (Phase 8/9)
- `docudata-backend/routers/painel.py` — fonte de dados para funcionalidades travadas, aguardando cliente, suítes falhando (reutilizado pelo resumo semanal)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docudata-backend/routers/generate.py` + tabela `generated_docs`: resumo semanal pode usar `doc_type = 'resumo_semanal'` sem criar nova tabela
- `docudata-backend/routers/painel.py` — queries para `funcionalidades` filtradas por status: reutilizável para montar os dados do resumo semanal
- `docudata-frontend/app/projects/[id]/page.tsx` Tabs.tsx: adicionar aba "Aceite" segue o padrão das abas existentes (Composer, Painel)
- `react-markdown` já instalado: exibição do conteúdo do boletim e do resumo semanal sem dependência adicional

### Established Patterns
- **Zero className:** todos os estilos via `style={{...}}` — obrigatório nesta fase
- **Preview → Confirmar:** fluxo do Composer (Phase 10) — Gemini gera, gerente confirma antes de oficializar
- **`generated_docs` para saída:** documentos gerados vão para essa tabela com `doc_type` específico
- **Python stdlib para agentes:** não se aplica aqui (sem GitHub Actions nesta fase)

### Integration Points
- `PATCH /funcionalidades/{id}` precisa atualizar `status_cliente` quando o boletim é marcado como enviado/aprovado/ajuste
- `GET /painel/{project_id}` pode servir como fonte dos dados de anomalias para o resumo semanal (ou query direta nas mesmas tabelas)
- Aba "Aceite" se integra ao Tabs.tsx existente no dashboard do projeto

</code_context>

<specifics>
## Specific Ideas

- O fluxo de "Novo Boletim" começa com um seletor de funcionalidades concluídas (checkboxes), igual ao passo 1 do Composer — padrão já conhecido
- A mensagem de "100% aprovado" é apenas um indicador visual na aba, sem geração de documento
- A listagem de "mudanças de escopo solicitadas" é uma seção passiva na aba Aceite — sem ação associada, apenas visibilidade

</specifics>

<deferred>
## Deferred Ideas

- Evidência visual no boletim (upload de imagem ou URL) — removido do escopo pelo usuário
- Termo de Encerramento como documento gerado — removido do escopo pelo usuário
- Notificação por e-mail ao cliente com o boletim — nova funcionalidade, fase própria
- Geração automática do resumo semanal via GitHub Actions/cron — possível extensão futura

</deferred>

---

*Phase: 12-boletim-de-aceite-encerramento-e-resumo-semanal*
*Context gathered: 2026-08-23*
