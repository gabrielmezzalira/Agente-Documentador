# Phase 5: Content-Type Validation on Ingestion - Context

**Gathered:** 2026-08-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Adicionar uma camada de validação semântica que roda **antes** de qualquer ingestão ser salva no Supabase. A validação verifica se o conteúdo do arquivo corresponde ao tipo de documento esperado pelo endpoint, usando contexto do projeto (nome, cliente, descrição) para avaliar relevância. Conteúdo incompatível retorna erro diagnóstico com override opcional.

**Em escopo:**
- Validação de arquivo em: `POST /ingest` (upload livre), `POST /sprint-docs/planning` (quando há anexo), `POST /sprint-docs/daily` (quando há anexo), `POST /sprint-docs/ata`, `POST /sprint-docs/review` (quando há anexo), `POST /sprint-docs/retrospectiva` (quando há anexo), `POST /ingest/commit`
- Mensagem de erro diagnóstica que identifica o tipo detectado
- Flag `force=true` no payload para override do bloqueio
- Classificação usando 7 tipos DocuData + categoria genérica para conteúdo externo

**Fora de escopo:**
- Validação de campos de formulário (planning, daily, review, retro sem anexo — tipo já definido pelo endpoint)
- Alterações no frontend (só o backend nesta fase — frontend consome o erro 422 existente)
- Validação de commits (commit_ingest tem contexto estruturado — não há arquivo aberto)

</domain>

<decisions>
## Implementation Decisions

### Onde a validação vive

- **D-01:** A validação é implementada como **nó `validar_tipo` novo no `extraction_graph.py`** — primeiro nó do grafo, antes de `detectar_tipo` e `preprocessar_arquivo`. Se o nó retornar `invalido=True` (e `force=False`), o grafo encerra sem chamar `extrair_conteudo`. — **Reversibility:** reversible

- **D-02:** Para endpoints de `sprint_docs` **sem anexo** (formulários puros), a validação não roda — o tipo é implícito pelo endpoint. Para endpoints com anexo opcional, a validação só roda quando há arquivo. O campo `force` deve ser adicionado ao estado do grafo e passado pelos routers. — **Reversibility:** reversible

### Categorias de diagnóstico

- **D-03:** O Gemini classifica o conteúdo em **8 categorias**: `planning`, `daily`, `review`, `retrospectiva`, `ata_reuniao`, `commit`, `upload_livre` (documentos de projeto genéricos) e `nao_relacionado` (para material claramente externo: aulas, documentos pessoais, conteúdo aleatório). — **Reversibility:** costly — mudança de categorias afeta prompts, mensagens de erro e lógica de bloqueio em todos os endpoints.

- **D-04:** Mensagem de erro é **direta e acionável**, em português, com dois padrões:
  - Tipo identificado como outro tipo DocuData: `"Esse arquivo parece ser uma Review, não um Planning. Para ingerir como Review, use o botão Review da sprint."`
  - Tipo identificado como não relacionado: `"Conteúdo parece ser material educacional — o sistema aceita documentos de projeto (atas, plannings, reviews, etc.)."`
  — **Reversibility:** reversible

### Override (bloqueio suave)

- **D-05:** O bloqueio é **soft** — retorna HTTP 422 com payload estruturado contendo `tipo_detectado`, `tipo_esperado`, `mensagem`, e `pode_forçar: true`. O frontend exibe a mensagem com botão "Ingerir mesmo assim", que reenvia com `force=true` no payload (Form field ou JSON field). Com `force=true`, o nó de validação registra o override mas não bloqueia. — **Reversibility:** costly — altera contrato da API (novo campo no payload e no response de erro).

### Custo da validação

- **D-06:** A validação faz uma **chamada Gemini separada e leve** antes da extração — prompt curto de classificação, sem structured output, só retorna a categoria e uma frase explicativa. Em ingestões bem-sucedidas o custo total é 2 chamadas Gemini. Ingestões bloqueadas custam apenas a chamada de validação (a de extração não roda). — **Reversibility:** reversible

### Contexto do projeto na validação

- **D-07:** O nó `validar_tipo` recebe **nome + cliente + descrição** do projeto (já disponíveis na tabela `projects`, buscados pelos routers antes de invocar o grafo). O prompt de validação inclui esse contexto para que o Gemini avalie relevância ao projeto, não apenas ao tipo de documento. — **Reversibility:** reversible

### Comportamento do upload livre

- **D-08:** Upload livre (`POST /ingest`) **bloqueia conteúdo claramente irrelevante** (categoria `nao_relacionado`) com override disponível. Documentos de projeto de qualquer tipo (mesmo que não sejam upload livre) passam sem bloqueio — apenas são classificados e o `tipo_detectado` é anotado no `extracted_content`. — **Reversibility:** reversible

### Claude's Discretion

- Threshold de confiança: se o Gemini retornar classificação ambígua (ex: conteúdo que poderia ser planning ou daily), o comportamento padrão é **não bloquear** — bloqueia só quando há alta confiança de mismatch. Implementar com instrução explícita no prompt: "Em caso de dúvida, não bloqueie."
- Formato do campo `tipo_detectado` no `extracted_content` de ingestões com override: string com a categoria detectada (ex: `"nao_relacionado"`, `"review"`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pontos de ingestão (onde a validação entra)
- `docudata-backend/routers/ingest.py` — `POST /ingest` (upload livre), principal ponto de entrada
- `docudata-backend/routers/sprint_docs.py` — 5 endpoints de sprint_docs com anexo opcional
- `docudata-backend/routers/commit_ingest.py` — `POST /ingest/commit` (commit do GitHub Action)

### Grafo de extração (onde o nó novo será adicionado)
- `docudata-backend/graphs/extraction_graph.py` — estado do grafo, nós existentes, padrão de retry e edges

### Schema e modelo de dados
- `docudata-backend/models/schemas.py` — `ConteudoEstruturado` e schemas de request/response

### Design doc (contexto do projeto)
- `CLAUDE.md` §2 (Arquitetura), §4 (Fluxo de Ingestão), §6 (API FastAPI) — referência de arquitetura

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_COMMIT_SYSTEM_PROMPT` em `commit_ingest.py`: padrão de prompt de sistema para Gemini — seguir o mesmo estilo para o prompt de validação
- `ChatGoogleGenerativeAI` + `ainvoke` já usado em todos os routers — reutilizar o mesmo padrão de instanciação com `api_key` do projeto
- `ensure_sprint_row` e `_project_or_404` em `sprint_docs.py` — helpers de validação de projeto que já buscam `gemini_api_key`

### Established Patterns
- Estado do `extraction_graph`: `TypedDict` com campos opcionais; nó retorna dict parcial. O nó `validar_tipo` deve seguir o mesmo padrão e adicionar `valido_tipo: bool`, `tipo_detectado: str`, `mensagem_validacao: str` ao estado.
- Routers passam `gemini_api_key` para o grafo via estado — `validar_tipo` usa a mesma chave
- HTTP 422 com `detail` string já é o padrão de erro nos routers (`raise HTTPException(status_code=422, detail=...)`) — para o erro de validação, `detail` será um dict estruturado com `tipo_detectado`, `tipo_esperado`, `mensagem`, `pode_forcar`

### Integration Points
- Os routers precisam receber o campo `force` (Form field para multipart, JSON field para JSON body) e passá-lo ao estado do grafo como `force: bool`
- O estado do grafo precisa de: `tipo_esperado: str`, `force: bool`, `projeto_nome: str`, `cliente: str`, `projeto_descricao: str`
- Edge condicional após `validar_tipo`: `(not valido_tipo and not force)` → END com erro; `(valido_tipo or force)` → `detectar_tipo`

</code_context>

<specifics>
## Specific Ideas

- Mensagem de erro deve ser em português, direta ao ponto, e quando o tipo detectado é outro tipo DocuData, deve indicar onde ir: "use o botão Review da sprint"
- O campo `tipo_detectado` deve sempre ser anotado no `extracted_content` — mesmo quando há override ou quando é upload livre (para rastreabilidade)
- No prompt de validação, incluir instrução explícita: "Em caso de dúvida ou conteúdo ambíguo, retorne `nao_bloquear: true`" — evita falsos positivos

</specifics>

<deferred>
## Deferred Ideas

- Alterações no frontend para exibir o botão "Ingerir mesmo assim" e consumir o novo formato de erro 422 — próxima fase de frontend
- Validação de campos de formulário (sem anexo) — escopo reduzido conscientemente: formulários têm tipo definido pelo endpoint
- Log de overrides para auditoria (quantas vezes gerentes forçaram ingestão de conteúdo bloqueado) — feature de analytics futura
- Validação no `commit_ingest.py` — **excluído conscientemente**: commits chegam como payload JSON estruturado (hash, diff, mensagem), sem arquivo livre; o tipo é implícito pela rota (`/ingest/commit`). Validação semântica de diff de código não se aplica ao mesmo modelo das 8 categorias.

</deferred>

---

*Phase: 5-content-type-validation-on-ingestion*
*Context gathered: 2026-08-13*
