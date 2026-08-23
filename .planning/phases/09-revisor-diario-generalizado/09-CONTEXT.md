# Phase 9: Revisor Diário Generalizado - Context

**Gathered:** 2026-08-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Um agente GitHub Actions instalável nos repos cadastrados no DocuData que roda diariamente, analisa o diff acumulado das últimas 24h via Gemini, e envia achados estruturados de volta ao DocuData como registros `RevisaoDiaria`. Achados CRITICA/ALTA com confiança ALTA aparecem no Bloco B do Painel do gerente. O revisor opera estritamente em modo somente leitura — nunca altera código, arquivos ou estado do repositório.

Escopo desta fase: criação da tabela `revisoes_diarias` + schema de achados, GitHub Actions workflow + agente Python instalável, endpoint de ingestão no backend, expansão do endpoint `/painel` para incluir `achados_criticos` no bloco B, e exibição no PainelTab.tsx com toggle gerente/técnico.

</domain>

<decisions>
## Implementation Decisions

### Trigger do Revisor

- **D-01:** **Cron diário às 08:00 UTC (05:00 BRT)** — GitHub Actions `schedule: cron: '0 8 * * *'`. Um relatório por dia por projeto, independente de quantos commits houve no período.
- **D-02:** **Sem commits → para silenciosamente** — Se não há commits nas últimas 24h, o agente encerra sem criar registro `RevisaoDiaria`. Nenhum row vazio, nenhum noise no Bloco B.

### Janela de Análise

- **D-03:** **Diff acumulado das últimas 24h** — O agente coleta todos os commits das últimas 24h via `git log --since="24 hours ago"` e agrega o diff completo desse período. Mesma abordagem do commit tracker existente (Phase 4), mas agregada em vez de por commit.
- **D-04:** **Limite de 100k chars no diff** — Diff truncado em 100.000 chars antes de enviar ao Gemini. Cobre sprints intensas; o commit tracker atual usa 8k (um commit por vez), este limite é 12× maior para cobrir o período completo.

### Schema de RevisaoDiaria e Achados

- **D-05:** **Achados estruturados com severidade + confiança + arquivo:linha** — Cada achado tem:
  - `severidade`: `CRITICA | ALTA | MEDIA | BAIXA`
  - `confianca`: `ALTA | MEDIA | BAIXA`
  - `referencia`: `arquivo:linha` (string — ex: `"services/supabase_client.py:47"`)
  - `descricao_tecnica`: texto completo com contexto de código
  - `descricao_gerente`: versão macro sem arquivo:linha

  Tabela `revisoes_diarias` no Supabase:
  ```
  id            uuid PK
  project_id    uuid FK → projects
  data_revisao  date NOT NULL
  achados       jsonb  -- lista de achados estruturados acima
  relatorio_gerente  text  -- texto consolidado versão gerente
  relatorio_tecnico  text  -- texto consolidado versão técnica com arquivo:linha
  commits_analisados int   -- número de commits no período
  diff_chars_total   int   -- tamanho do diff antes de truncar
  created_at    timestamptz DEFAULT now()
  ```

- **D-06:** **Bloco B expandido via endpoint /painel existente** — `GET /projects/{id}/painel` passa a incluir `achados_criticos: list` no response de `bloco_b`. A lista contém achados com `severidade IN (CRITICA, ALTA)` E `confianca = ALTA` da `RevisaoDiaria` mais recente (último registro do projeto). Sem endpoint novo, sem mudança no contrato geral do response — apenas campo adicional em `bloco_b`.

### Entrega dos Relatórios

- **D-07:** **Apenas no DocuData — sem post no GitHub** — O agente Python envia os achados ao backend e encerra. Não cria issues, não posta comentários, não escreve no Job Summary. Relatórios acessados pelo Painel.
- **D-08:** **Dois campos no banco, toggle no frontend** — `relatorio_gerente` e `relatorio_tecnico` são dois campos separados no `RevisaoDiaria`. O PainelTab.tsx exibe o mais recente com um toggle (abas ou botão) para alternar entre "Gerente" e "Técnico". Padrão inicial: versão gerente.

### Instalação e Configuração

- **D-09:** **Mesmo padrão do commit tracker (Phase 4)** — Gerente copia `revisor.yml` (workflow) e `revisor_agent.py` (script) para o repo do projeto. Configura os mesmos dois secrets: `DOCUDATA_API_URL` e `DOCUDATA_PROJECT_ID`. Sem arquivo `.citi/revisao.yml` separado — configuração inline no workflow YML.

### Claude's Discretion

- Horário exato configurável no YML — padrão `0 8 * * *` mas o gerente pode ajustar sem código.
- Limite de achados por RevisaoDiaria (evitar prompt injection com listas enormes) — sugestão: cap em 20 achados, priorizando CRITICA > ALTA > MEDIA > BAIXA.
- Endpoint de ingestão do revisor: `POST /ingest/revisao` (análogo ao `POST /ingest/commit` da Phase 4).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Padrão de integração GitHub Actions (Phase 4)
- `docudata-backend/hooks/docudata.yml` — template do workflow de commit tracker; revisor segue o mesmo padrão de instalação
- `docudata-backend/hooks/docudata_agent.py` — agente Python de referência; revisor_agent.py é uma variação deste

### Endpoint de commit ingest (referência de padrão)
- `docudata-backend/routers/commit_ingest.py` — padrão de ingestão de dados do GitHub; endpoint revisor segue a mesma estrutura

### Bloco B e Painel (a expandir)
- `docudata-backend/routers/painel.py` — função `calcular_bloco_b` e endpoint `GET /projects/{id}/painel` que serão expandidos
- `docudata-frontend/app/components/PainelTab.tsx` — componente a expandir com achados e toggle gerente/técnico

### Roadmap e requirements
- `.planning/ROADMAP.md` §Phase 9 — success criteria e escopo oficial
- `.planning/phases/08-painel-do-gerente-kanban-de-sprint/08-CONTEXT.md` — decisões D-10 a D-15 sobre o Painel (não reabrir)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docudata-backend/hooks/docudata_agent.py` — script Python com padrão `git log`, `git show`, HTTP sem dependências externas (só stdlib). Copiar e adaptar para o revisor_agent.py.
- `docudata-backend/hooks/docudata.yml` — estrutura do workflow GitHub Actions; adaptar `on: schedule` no lugar do `on: push`.
- `docudata-backend/routers/commit_ingest.py` — roteador FastAPI com padrão de ingestão de dados externos; endpoint `POST /ingest/revisao` segue o mesmo padrão.

### Established Patterns
- **Agente best-effort:** o workflow usa `continue-on-error: true` em todos os steps — nunca bloqueia CI. O revisor diário segue a mesma convenção.
- **Sem dependências externas no agente:** `docudata_agent.py` usa apenas stdlib Python (`os`, `subprocess`, `json`, `urllib`). O `revisor_agent.py` deve seguir o mesmo padrão — sem `requests`, sem `langchain` no agente cliente.
- **Gemini fica no backend:** O agente Python só coleta dados e envia ao backend. O backend (FastAPI) faz a chamada Gemini. Não colocar GEMINI_API_KEY nos secrets do repo cliente.
- **Zero inline styles no frontend:** PainelTab.tsx usa `style={{...}}` objects, zero `className`. Manter ao expandir.

### Integration Points
- `GET /projects/{id}/painel` → adicionar `achados_criticos` em `bloco_b`
- `POST /ingest/revisao` → novo endpoint (análogo a `/ingest/commit`)
- `PainelTab.tsx` → nova sub-seção no Bloco B com lista de achados + toggle gerente/técnico
- Supabase: nova tabela `revisoes_diarias` (migration SQL)

</code_context>

<specifics>
## Specific Ideas

- Diff truncado em 100k chars (12× o limite atual do commit tracker de 8k)
- O agente usa `git log --since="24 hours ago" --no-merges` para listar commits do período, depois `git show` em cada um agregando os diffs
- Achados cap em 20 por dia (CRITICA > ALTA > MEDIA > BAIXA na priorização)
- Toggle padrão "Gerente" — versão técnica acessível por clique

</specifics>

<deferred>
## Deferred Ideas

- **Notificação por email/Slack** — enviar relatório por canal externo além do Painel. Fora do escopo desta fase.
- **`.citi/revisao.yml` como config file** — configuração por arquivo em vez de inline no workflow. Complexidade extra não necessária agora.
- **Histórico de revisões acessível pelo Painel** — lista de todas as RevisaoDiaria do projeto, paginada. Bloco B só mostra a mais recente nesta fase.
- **Filtro de severidade configurável** — gerente escolher threshold (CRITICA apenas vs CRITICA+ALTA). Hard-coded CRITICA+ALTA+confianca_ALTA nesta fase.

</deferred>

---

*Phase: 9-Revisor Diário Generalizado*
*Context gathered: 2026-08-22*
