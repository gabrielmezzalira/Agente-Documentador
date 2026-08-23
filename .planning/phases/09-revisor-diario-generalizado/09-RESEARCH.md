# Phase 9: Revisor Diário Generalizado — Research

**Researched:** 2026-08-22
**Domain:** GitHub Actions cron + Python stdlib agent + FastAPI ingestão + Supabase migration + Next.js frontend toggle
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Cron diário às 08:00 UTC — `schedule: cron: '0 8 * * *'`
- **D-02:** Sem commits nas 24h → para silenciosamente, sem criar registro
- **D-03:** Diff acumulado das últimas 24h via `git log --since="24 hours ago"`
- **D-04:** Limite 100k chars no diff antes de enviar ao Gemini
- **D-05:** Achados com `severidade` (CRITICA/ALTA/MEDIA/BAIXA), `confianca` (ALTA/MEDIA/BAIXA), `referencia` (arquivo:linha), `descricao_tecnica`, `descricao_gerente`
- **D-06:** Expandir `GET /projects/{id}/painel` com `achados_criticos` em `bloco_b` — sem endpoint novo
- **D-07:** Apenas no DocuData — sem post no GitHub, sem issues, sem comentários
- **D-08:** Dois campos: `relatorio_gerente` + `relatorio_tecnico`; toggle no frontend; padrão exibe gerente
- **D-09:** Mesmo padrão de instalação do commit tracker (Phase 4) — dois secrets, sem arquivo de config separado

### Claude's Discretion

- Horário exato configurável no YML (padrão `0 8 * * *`, gerente pode ajustar)
- Cap em 20 achados por RevisaoDiaria, prioridade: CRITICA > ALTA > MEDIA > BAIXA
- Endpoint de ingestão: `POST /ingest/revisao`

### Deferred Ideas (OUT OF SCOPE)

- Notificação por email/Slack
- `.citi/revisao.yml` como config file
- Histórico paginado de revisões no Painel
- Filtro de severidade configurável pelo gerente
</user_constraints>

---

## Summary

Esta fase adiciona um agente diário de revisão de código que roda via GitHub Actions cron, agrega o diff das últimas 24h, envia ao backend DocuData, e o backend processa via Gemini retornando achados estruturados com severidade/confiança/referência. O padrão de instalação replica exatamente o commit tracker da Phase 4: dois arquivos copiados para o repo cliente + dois GitHub Secrets.

O backend recebe os dados brutos (diff + metadados), chama Gemini com prompt de revisão de código, e persiste na tabela `revisoes_diarias`. O endpoint de painel existente é expandido para incluir `achados_criticos` como sub-campo de `bloco_b` — sem quebrar o contrato atual. O frontend `PainelTab.tsx` ganha uma nova sub-seção dentro de `BlocoBCard` com lista de achados e toggle gerente/técnico.

**Três regras invioláveis do agente cliente:** (1) usa apenas stdlib Python, (2) não tem GEMINI_API_KEY nos secrets do repo cliente — Gemini fica no backend, (3) encerra silenciosamente se não há commits.

**Primary recommendation:** Seguir o padrão commit_ingest.py para o novo router; seguir docudata_agent.py para o agente cliente. A única complexidade nova é o prompt de revisão de código e o schema `Achado` com dois campos de descrição.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Coletar diff das 24h | GitHub Actions agent (cliente) | — | Acesso ao repositório Git; stdlib apenas |
| Chamar Gemini para revisão | Backend FastAPI | — | Mantém API key no backend; padrão estabelecido |
| Persistir RevisaoDiaria | Backend FastAPI → Supabase | — | Supabase é a fonte de verdade; padrão commit_ingest |
| Filtrar achados críticos para bloco_b | Backend FastAPI (painel.py) | — | Cálculo de painel é responsabilidade do backend |
| Exibir achados + toggle gerente/técnico | Frontend Next.js (PainelTab.tsx) | — | UI pura, sem lógica de negócio |

---

## Standard Stack

### Core — Backend

| Library | Version atual no projeto | Purpose |
|---------|------------------------|---------|
| `fastapi` | já instalado | Framework do novo router |
| `langchain-google-genai` | já instalado | `ChatGoogleGenerativeAI` para revisão |
| `supabase` | já instalado | Inserção em `revisoes_diarias` |
| `pydantic` | já instalado | Schema `RevisaoDiaria` e `Achado` |

Nenhuma dependência nova no backend. [VERIFIED: docudata-backend/routers/commit_ingest.py:13-15]

### Core — Agente cliente (hooks/)

Apenas Python stdlib — mesma restrição do `docudata_agent.py`. [VERIFIED: docudata-backend/hooks/docudata_agent.py:11]

```python
import os, subprocess, json
import urllib.request, urllib.error
```

Nenhum `pip install` necessário no workflow do cliente.

### Core — Frontend

| Biblioteca | Já disponível | Purpose |
|------------|--------------|---------|
| React `useState` | sim | Toggle gerente/técnico |
| `api.ts` `getPainel` | sim | Busca dados do painel (incluindo achados) |

---

## Existing Code Patterns (VERIFIED — leia antes de implementar)

### Padrão 1: Agente cliente stdlib — docudata_agent.py

Funções reutilizáveis integralmente: [VERIFIED: docudata-backend/hooks/docudata_agent.py:17-33]

```python
def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True).stdout.strip()

def http_json(url, method="GET", data=None, token=None):
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return {}, e.code
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        print(f"[docudata] Aviso: requisição indisponível ({e}) — continuando")
        return {}, 0
```

Guard de variáveis de ambiente (copiar integralmente): [VERIFIED: docudata-backend/hooks/docudata_agent.py:35-37]

```python
if not API_URL or not PROJECT_ID:
    print("[docudata] Aviso: DOCUDATA_API_URL ou DOCUDATA_PROJECT_ID não configurado — continuando")
    raise SystemExit(0)
```

### Padrão 2: GitHub Actions workflow — docudata.yml

Estrutura de job com `continue-on-error: true` e `permissions: {}`: [VERIFIED: docudata-backend/hooks/docudata.yml:23-40]

```yaml
jobs:
  track:
    runs-on: ubuntu-latest
    continue-on-error: true
    permissions: {}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - name: Registrar commit no DocuData
        continue-on-error: true
        env:
          DOCUDATA_API_URL:    ${{ secrets.DOCUDATA_API_URL }}
          DOCUDATA_PROJECT_ID: ${{ secrets.DOCUDATA_PROJECT_ID }}
        run: python scripts/docudata_agent.py
```

Para o revisor, `fetch-depth: 0` é necessário (precisa de todo o histórico para `--since`). O trigger muda de `on: push` para `on: schedule`.

### Padrão 3: Router FastAPI de ingestão — commit_ingest.py

Estrutura do router a replicar para `revisao_ingest.py`: [VERIFIED: docudata-backend/routers/commit_ingest.py:100-115]

```python
router = APIRouter(tags=["revisao-ingest"])

class RevisaoPayload(BaseModel):
    project_id: str
    # ... campos do payload

@router.post("/ingest/revisao", status_code=201)
async def ingest_revisao(payload: RevisaoPayload):
    client = get_client()
    # 1. Verifica projeto existe + pega api_key
    project_resp = client.table("projects").select("gemini_api_key").eq("id", payload.project_id).execute()
    if not project_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    api_key = project_resp.data[0].get("gemini_api_key") or ""
    if not api_key:
        raise HTTPException(status_code=422, detail="...")
    # 2. Chama Gemini
    # 3. Salva em revisoes_diarias
    # 4. Retorna 201
```

Pattern de chamada ao Gemini com structured output: [VERIFIED: docudata-backend/routers/commit_ingest.py:129-146]

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    max_tokens=2048,
    google_api_key=api_key,
)
structured_llm = llm.with_structured_output(ConteudoEstruturado, method="json_schema", include_raw=True)
messages = [
    SystemMessage(content=_SYSTEM_PROMPT),
    HumanMessage(content=user_content),
]
raw_result = await structured_llm.ainvoke(messages)
parsed = raw_result["parsed"]
```

### Padrão 4: Expansão de bloco_b — painel.py

Assinatura atual de `calcular_bloco_b`: [VERIFIED: docudata-backend/routers/painel.py:69-125]

```python
def calcular_bloco_b(funcs: list[dict], transicoes: list[dict]) -> dict:
    # ... lógica atual ...
    return {
        "travadas": travadas,
        "aguardando_cliente": aguardando_cliente,
        "em_ajuste": em_ajuste,
    }
```

Para adicionar `achados_criticos`, a função precisa receber um terceiro parâmetro com a RevisaoDiaria mais recente e adicionar o campo ao dict retornado. O endpoint `get_painel` em [VERIFIED: docudata-backend/routers/painel.py:274-308] precisa buscar a revisão mais recente antes de chamar `calcular_bloco_b`.

### Padrão 5: BlocoBCard — PainelTab.tsx

Interface atual de `BlocoB` no frontend: [VERIFIED: docudata-frontend/app/lib/api.ts:676-680]

```typescript
export interface BlocoB {
  travadas: Array<{ id: string; titulo: string; dias: number }>;
  aguardando_cliente: Array<{ id: string; titulo: string; dias_uteis: number }>;
  em_ajuste: Array<{ id: string; titulo: string }>;
}
```

O componente `BlocoBCard` usa `style={{...}}` objects sem nenhum `className`. [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:133-235]

O separador `sep` entre sub-seções: [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:134-136]

```tsx
const sep = (
  <hr style={{ border: "none", borderTop: "1px solid #f0f0f4", margin: "10px 0" }} />
);
```

Sub-seção com título: [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:181-188]

```tsx
<p style={subSectionTitleStyle}>
  Aguardando cliente{" "}
  <span style={{ ...chipBaseStyle, background: "#fef9c3", color: "#a16207", fontSize: 11 }}>
    {bloco.aguardando_cliente.length}
  </span>
</p>
```

`subSectionTitleStyle` definido em [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:58-64]:

```typescript
const subSectionTitleStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  color: "#374151",
  marginBottom: 8,
  marginTop: 12,
};
```

### Padrão 6: Schema SQL existente

Padrão de tabela com FK + CASCADE + jsonb do supabase_schema.sql: [VERIFIED: docudata-backend/supabase_schema.sql:1-93]

```sql
CREATE TABLE example (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid        REFERENCES projects(id) ON DELETE CASCADE,
    -- campos...
    created_at  timestamptz DEFAULT now()
);
```

O padrão de migration incremental do projeto usa `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` como comentário no mesmo arquivo, não arquivos de migration separados. [VERIFIED: docudata-backend/supabase_schema.sql:30-48]

### Padrão 7: Registro do router em main.py

[VERIFIED: docudata-backend/main.py:6-29]

```python
from routers import ..., commit_ingest, ...
# ...
app.include_router(commit_ingest.router)
```

O novo `revisao_ingest` deve seguir exatamente o mesmo padrão: import no topo + `app.include_router(revisao_ingest.router)`.

---

## Architecture Patterns

### System Architecture Diagram

```
[Repo cliente — GitHub Actions cron 08:00 UTC]
    |
    | git log --since="24 hours ago" --no-merges
    | git show <hash> (agregado, truncado em 100k chars)
    |
    | POST /ingest/revisao  { project_id, diff_agregado, commits_analisados, diff_chars_total }
    v
[DocuData Backend — FastAPI]
    |
    | Verifica projeto + busca gemini_api_key
    | Chama Gemini com prompt de revisão de código
    | Parse JSON → lista de Achado (cap 20)
    | Compila relatorio_gerente + relatorio_tecnico
    |
    | INSERT revisoes_diarias
    v
[Supabase — revisoes_diarias]
    ^
    |  SELECT última revisão WHERE project_id = ?
    |
[GET /projects/{id}/painel]
    |
    | calcular_bloco_b(..., achados_da_revisao_mais_recente)
    | filtra: severidade IN (CRITICA, ALTA) AND confianca = ALTA
    |
    v
[PainelTab.tsx — BlocoBCard]
    |
    | lista achados_criticos
    | toggle [Gerente] [Técnico] → alterna relatorio_gerente / relatorio_tecnico
```

### Recommended Project Structure (novos arquivos)

```
docudata-backend/
├── hooks/
│   ├── docudata.yml          # EXISTENTE — commit tracker
│   ├── docudata_agent.py     # EXISTENTE — commit tracker agent
│   ├── revisor.yml           # NOVO — cron workflow
│   └── revisor_agent.py      # NOVO — daily review agent
├── routers/
│   ├── revisao_ingest.py     # NOVO — POST /ingest/revisao
│   └── painel.py             # MODIFICAR — calcular_bloco_b + get_painel
├── models/
│   └── schemas.py            # MODIFICAR — Achado + RevisaoDiaria schemas
└── main.py                   # MODIFICAR — include_router(revisao_ingest.router)

docudata-frontend/app/
├── components/
│   └── PainelTab.tsx         # MODIFICAR — BlocoBCard + toggle + tipos
└── lib/
    └── api.ts                # MODIFICAR — BlocoB interface + AchadoCritico
```

---

## Technical Approach por Domínio

### 1. Supabase Migration — tabela `revisoes_diarias`

O projeto não usa arquivos de migration separados. O padrão estabelecido é: CREATE TABLE no `supabase_schema.sql` com comentário de ALTER para bases existentes. [VERIFIED: docudata-backend/supabase_schema.sql:30-48]

**Migration SQL a adicionar ao final de `supabase_schema.sql`:**

```sql
-- Phase 9: Revisor Diário
CREATE TABLE revisoes_diarias (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    data_revisao        date        NOT NULL,
    achados             jsonb       NOT NULL DEFAULT '[]',
    relatorio_gerente   text        NOT NULL DEFAULT '',
    relatorio_tecnico   text        NOT NULL DEFAULT '',
    commits_analisados  int         NOT NULL DEFAULT 0,
    diff_chars_total    int         NOT NULL DEFAULT 0,
    created_at          timestamptz DEFAULT now()
);

-- Índice para lookup rápido da revisão mais recente por projeto
CREATE INDEX IF NOT EXISTS idx_revisoes_diarias_project_created
    ON revisoes_diarias (project_id, created_at DESC);

-- Se tabela já existe:
-- ALTER TABLE revisoes_diarias ADD COLUMN IF NOT EXISTS commits_analisados int NOT NULL DEFAULT 0;
-- ALTER TABLE revisoes_diarias ADD COLUMN IF NOT EXISTS diff_chars_total int NOT NULL DEFAULT 0;
```

**Schema JSON de um `Achado` (campo `achados` é uma lista destes):**

```json
{
  "severidade": "CRITICA",
  "confianca": "ALTA",
  "referencia": "services/supabase_client.py:47",
  "descricao_tecnica": "Senha hardcoded encontrada na linha 47...",
  "descricao_gerente": "Credencial exposta no código fonte do serviço de banco de dados"
}
```

### 2. FastAPI Router — `revisao_ingest.py`

**Payload do agente cliente → backend:**

```python
class RevisaoPayload(BaseModel):
    project_id: str
    data_revisao: str          # ISO date "YYYY-MM-DD"
    diff_agregado: str         # diff completo truncado em 100k chars
    commits_analisados: int    # número de commits no período
    diff_chars_total: int      # tamanho antes de truncar
    lista_commits: list[str]   # mensagens dos commits (para contexto no prompt)
```

**Schema Pydantic para structured output do Gemini:**

```python
class Achado(BaseModel):
    severidade: str   # CRITICA | ALTA | MEDIA | BAIXA
    confianca: str    # ALTA | MEDIA | BAIXA
    referencia: str   # "arquivo:linha" — ex: "routers/painel.py:47"
    descricao_tecnica: str
    descricao_gerente: str

class RevisaoEstruturada(BaseModel):
    achados: list[Achado]
    relatorio_gerente: str
    relatorio_tecnico: str
```

**Cap de 20 achados:** após o parse, ordenar por prioridade e fatiar:

```python
PRIORIDADE = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2, "BAIXA": 3}
achados_sorted = sorted(parsed.achados, key=lambda a: PRIORIDADE.get(a.severidade, 4))
achados_capped = achados_sorted[:20]
```

### 3. Gemini Prompt para Revisão de Código

O prompt deve ser em português (padrão do projeto) e pedir JSON estritamente. Seguindo o estilo do `_COMMIT_SYSTEM_PROMPT` em [VERIFIED: docudata-backend/routers/commit_ingest.py:84-97]:

```python
_REVISAO_SYSTEM_PROMPT = (
    "Voce e um revisor tecnico senior de projetos de dados do CITi. "
    "A partir do diff acumulado das ultimas 24h fornecido, identifique achados relevantes: "
    "bugs potenciais, vulnerabilidades de seguranca, divida tecnica acumulada, "
    "remocao de testes ou validacoes, credenciais expostas, logica incorreta. "
    "Regras obrigatorias: "
    "(1) Toda afirmacao tecnica DEVE ter referencia no formato arquivo:linha. "
    "Sem referencia confirmada no diff, nao inclua o achado. "
    "(2) Se nao ha mudanca relevante ou o diff esta vazio, retorne achados=[] e relatorios indicando ausencia de problemas. "
    "(3) Nao invente achados. Apenas o que e explicitamente visivel no diff. "
    "(4) severidade: CRITICA (seguranca/dado perdido), ALTA (bug funcional), MEDIA (qualidade), BAIXA (estilo). "
    "(5) confianca: ALTA (certeza do achado), MEDIA (provavelmente), BAIXA (suspeita). "
    "descricao_gerente deve ser em linguagem de negocio, sem arquivo:linha, max 2 frases. "
    "descricao_tecnica deve ser precisa, com arquivo:linha, contexto do codigo. "
    "relatorio_gerente: texto consolidado para o gerente, sem referencias tecnicas. "
    "relatorio_tecnico: texto consolidado com todos os arquivo:linha. "
    "Retorne APENAS JSON valido, sem markdown, sem backticks, sem texto antes ou depois."
)
```

### 4. GitHub Actions Cron — `revisor.yml`

**Sintaxe correta para cron diário 08:00 UTC:** [ASSUMED — padrão GitHub Actions]

```yaml
on:
  schedule:
    - cron: '0 8 * * *'
```

**Gotcha:** GitHub Actions scheduled workflows que não têm atividade no repositório padrão por 60 dias são automaticamente desabilitados. Para repos de clientes ativos isso não é problema — haverá commits regulares. [ASSUMED]

**`fetch-depth: 0` é necessário** para que `git log --since="24 hours ago"` funcione corretamente — `fetch-depth: 2` (usado no commit tracker) só baixa os 2 últimos commits. [ASSUMED — comportamento do checkout action]

```yaml
name: DocuData Revisor Diário

on:
  schedule:
    - cron: '0 8 * * *'

jobs:
  revisar:
    runs-on: ubuntu-latest
    continue-on-error: true
    permissions:
      contents: read   # apenas leitura — somente leitura é o contrato
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0     # histórico completo para --since
      - name: Executar revisão diária
        continue-on-error: true
        env:
          DOCUDATA_API_URL:    ${{ secrets.DOCUDATA_API_URL }}
          DOCUDATA_PROJECT_ID: ${{ secrets.DOCUDATA_PROJECT_ID }}
        run: python scripts/revisor_agent.py
```

**Por que `permissions: contents: read` em vez de `permissions: {}`?** O commit tracker usa `permissions: {}` porque só faz HTTP. O revisor usa `git log` dentro do runner, o que não exige permissão especial além do checkout padrão — `{}` também funciona. Usar `contents: read` explícito é mais legível e seguro. [ASSUMED]

### 5. Git commands para diff acumulado — `revisor_agent.py`

**Lógica central do agente:**

```python
# 1. Listar commits das últimas 24h (sem merges)
commits_raw = git("log", "--since=24 hours ago", "--no-merges", "--pretty=%H|%s")

if not commits_raw.strip():
    print("[revisor] Nenhum commit nas últimas 24h — encerrando")
    raise SystemExit(0)

linhas = [l for l in commits_raw.strip().splitlines() if l.strip()]
commits = [l.split("|", 1) for l in linhas]
# commits = [["abc1234...", "mensagem"], ...]

commits_analisados = len(commits)
lista_msgs = [msg for _, msg in commits]

# 2. Agregar diffs de todos os commits
LIMITE = 100_000
diffs = []
total_chars = 0

for hash_, _ in commits:
    diff = git("show", hash_, "--unified=3", "--no-color")
    total_chars += len(diff)
    diffs.append(diff)

diff_agregado = "\n".join(diffs)
diff_chars_total = total_chars

# 3. Truncar se necessário
if len(diff_agregado) > LIMITE:
    diff_agregado = diff_agregado[:LIMITE] + "\n[DIFF TRUNCADO EM 100k CHARS]"

# 4. Data de hoje para data_revisao
from datetime import date
data_revisao = date.today().isoformat()

# 5. Enviar ao backend
payload = {
    "project_id": PROJECT_ID,
    "data_revisao": data_revisao,
    "diff_agregado": diff_agregado,
    "commits_analisados": commits_analisados,
    "diff_chars_total": diff_chars_total,
    "lista_commits": lista_msgs,
}
_, status = http_json(f"{API_URL}/ingest/revisao", method="POST", data=payload)
```

**Diferença crítica vs docudata_agent.py:** o commit tracker usa `git("show", "HEAD", "--unified=3")[:8000]` para um único commit. O revisor itera sobre todos os commits do período e concatena. [VERIFIED: docudata-backend/hooks/docudata_agent.py:58]

### 6. Expansão de `bloco_b` — painel.py + api.ts + PainelTab.tsx

**Backend — painel.py:**

Adicionar busca da revisão mais recente no `get_painel` antes de chamar `calcular_bloco_b`:

```python
# Nova query antes de calcular_bloco_b:
revisao_resp = (
    client.table("revisoes_diarias")
    .select("achados, relatorio_gerente, relatorio_tecnico, data_revisao")
    .eq("project_id", project_id)
    .order("created_at", desc=True)
    .limit(1)
    .execute()
)
revisao_recente = revisao_resp.data[0] if revisao_resp.data else None

# Modificar assinatura de calcular_bloco_b:
bloco_b = calcular_bloco_b(func_list, trans_list, revisao_recente)
```

Dentro de `calcular_bloco_b`, adicionar ao return:

```python
# Extrair achados críticos da revisão mais recente
achados_criticos = []
relatorio_gerente = None
relatorio_tecnico = None
data_revisao = None

if revisao_recente:
    achados_raw = revisao_recente.get("achados") or []
    achados_criticos = [
        a for a in achados_raw
        if a.get("severidade") in ("CRITICA", "ALTA")
        and a.get("confianca") == "ALTA"
    ]
    relatorio_gerente = revisao_recente.get("relatorio_gerente")
    relatorio_tecnico = revisao_recente.get("relatorio_tecnico")
    data_revisao = revisao_recente.get("data_revisao")

return {
    "travadas": travadas,
    "aguardando_cliente": aguardando_cliente,
    "em_ajuste": em_ajuste,
    "achados_criticos": achados_criticos,        # novo
    "relatorio_gerente": relatorio_gerente,      # novo
    "relatorio_tecnico": relatorio_tecnico,      # novo
    "data_revisao": data_revisao,               # novo
}
```

**Frontend — api.ts:**

Adicionar interface `AchadoCritico` e expandir `BlocoB`:

```typescript
export interface AchadoCritico {
  severidade: "CRITICA" | "ALTA";
  confianca: "ALTA";
  referencia: string;
  descricao_tecnica: string;
  descricao_gerente: string;
}

export interface BlocoB {
  travadas: Array<{ id: string; titulo: string; dias: number }>;
  aguardando_cliente: Array<{ id: string; titulo: string; dias_uteis: number }>;
  em_ajuste: Array<{ id: string; titulo: string }>;
  // Novos campos — opcionais pois projetos sem revisor não os terão
  achados_criticos?: AchadoCritico[];
  relatorio_gerente?: string | null;
  relatorio_tecnico?: string | null;
  data_revisao?: string | null;
}
```

**Frontend — PainelTab.tsx, `BlocoBCard`:**

Adicionar state de toggle e nova sub-seção após "Em ajuste":

```tsx
function BlocoBCard({ bloco }: { bloco: PainelData["bloco_b"] }) {
  const [visoesRelatorio, setVisaoRelatorio] = useState<"gerente" | "tecnico">("gerente");
  // ... sep existente ...

  return (
    <div style={cardStyle}>
      {/* ... seções existentes (travadas, aguardando_cliente, em_ajuste) ... */}

      {/* Nova sub-seção: Achados do Revisor */}
      {bloco.achados_criticos !== undefined && (
        <>
          {sep}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <p style={{ ...subSectionTitleStyle, marginTop: 12 }}>
              Achados do Revisor{" "}
              <span style={{ ...chipBaseStyle, background: "#fee2e2", color: "#dc2626", fontSize: 11 }}>
                {bloco.achados_criticos.length}
              </span>
            </p>
            {/* Toggle gerente/técnico */}
            <div style={{ display: "flex", gap: 4 }}>
              {(["gerente", "tecnico"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setVisaoRelatorio(v)}
                  style={{
                    background: visaoRelatorio === v ? "#111116" : "#f1f5f9",
                    color: visaoRelatorio === v ? "#ffffff" : "#374151",
                    border: "none",
                    borderRadius: 6,
                    padding: "3px 10px",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {v === "gerente" ? "Gerente" : "Técnico"}
                </button>
              ))}
            </div>
          </div>
          {bloco.data_revisao && (
            <p style={{ fontSize: 11, color: "#9696a0", margin: "0 0 8px" }}>
              Revisão de {bloco.data_revisao}
            </p>
          )}
          {bloco.achados_criticos.length === 0 ? (
            <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>
              Nenhum achado crítico/alta com alta confiança
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {bloco.achados_criticos.map((a, i) => (
                <div key={i} style={{ borderLeft: "3px solid #dc2626", paddingLeft: 8 }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 2 }}>
                    <span style={{ ...chipBaseStyle, background: a.severidade === "CRITICA" ? "#fee2e2" : "#ffedd5", color: a.severidade === "CRITICA" ? "#dc2626" : "#c2410c", fontSize: 10 }}>
                      {a.severidade}
                    </span>
                    <span style={{ fontSize: 11, color: "#9696a0", fontFamily: "monospace" }}>
                      {visaoRelatorio === "tecnico" ? a.referencia : ""}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: "#374151", margin: 0, lineHeight: 1.4 }}>
                    {visaoRelatorio === "gerente" ? a.descricao_gerente : a.descricao_tecnica}
                  </p>
                </div>
              ))}
            </div>
          )}
          {/* Relatório consolidado */}
          {(bloco.relatorio_gerente || bloco.relatorio_tecnico) && (
            <div style={{ marginTop: 10, background: "#f7f7fa", borderRadius: 8, padding: "10px 12px" }}>
              <p style={{ fontSize: 12, color: "#374151", margin: 0, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                {visaoRelatorio === "gerente" ? bloco.relatorio_gerente : bloco.relatorio_tecnico}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

**Importante:** `useState` para o toggle deve ser declarado dentro do componente `BlocoBCard`, não no componente pai. Importar `useState` no topo do arquivo caso não esteja já (está: [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:3]).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON estruturado do Gemini | Parser manual com regex | `structured_llm.with_structured_output(Schema, method="json_schema")` | Já funciona no commit_ingest.py; retry built-in |
| Ordenação de achados por prioridade | Sort customizado complexo | Dict lookup + `sorted()` com key | Trivial com `PRIORIDADE = {"CRITICA": 0, ...}` |
| HTTP no agente cliente | `requests` | `urllib.request` (stdlib) | Sem dependências externas no agente |
| Busca da revisão mais recente | Loop Python sobre todas as revisões | `.order("created_at", desc=True).limit(1)` no Supabase | Uma query, sem código extra |

---

## Common Pitfalls

### Pitfall 1: `fetch-depth: 2` no cron workflow

**What goes wrong:** `git log --since="24 hours ago"` retorna vazio mesmo com commits recentes porque o checkout só baixou os 2 últimos commits.

**Why it happens:** O commit tracker usa `fetch-depth: 2` (só precisa do HEAD e do anterior para o diff). O revisor precisa do histórico das últimas 24h, que pode ser profundo.

**How to avoid:** `fetch-depth: 0` no `actions/checkout@v4` do `revisor.yml`.

**Warning signs:** `commits_analisados = 0` mesmo em projetos ativos.

### Pitfall 2: `permissions: {}` bloqueia checkout

**What goes wrong:** Com `permissions: {}` o checkout pode falhar em alguns contextos de repositório privado.

**How to avoid:** Usar `permissions: contents: read` no job do revisor. Best-effort: mesmo que falhe, `continue-on-error: true` garante que o CI não quebra.

### Pitfall 3: `calcular_bloco_b` recebe `revisao_recente = None`

**What goes wrong:** Projetos sem nenhuma revisão ainda causam KeyError ou AttributeError se o código não trata `None`.

**How to avoid:** Guard `if revisao_recente:` antes de acessar campos. Retornar `"achados_criticos": []` quando `None`.

### Pitfall 4: `BlocoBCard` não tem `useState` — é um function component puro

**What goes wrong:** Toggle gerente/técnico precisa de `useState` local. O componente atual não tem estado próprio — adicionar `useState` requer `"use client"` na página, que já está presente. [VERIFIED: docudata-frontend/app/components/PainelTab.tsx:1]

**How to avoid:** Adicionar `useState` import já existe na linha 4 do arquivo. Apenas declarar `const [visaoRelatorio, setVisaoRelatorio] = useState<"gerente" | "tecnico">("gerente")` dentro de `BlocoBCard`.

### Pitfall 5: Diff de 100k chars excede `max_tokens` do Gemini

**What goes wrong:** O limite é de chars no diff (input), mas o Gemini pode atingir `max_tokens=2048` no output antes de completar a lista de achados.

**How to avoid:** Para revisão de código com lista de achados, usar `max_tokens=4096`. O commit_ingest usa 2048 que é suficiente para um commit, mas 100k de diff pode gerar mais achados.

### Pitfall 6: `git log --since="24 hours ago"` em timezone UTC vs local

**What goes wrong:** O runner do GitHub Actions usa UTC. Repos com commits às 23:59 BRT (02:59 UTC do dia seguinte) podem ser incluídos ou excluídos dependendo do momento de execução.

**How to avoid:** Aceitável pelo design — a janela é "24h atrás a partir do momento da execução" que é 08:00 UTC. Documentar no YML como limitação conhecida e não problema.

### Pitfall 7: `structured_output` falha se diff está vazio

**What goes wrong:** Se `diff_agregado` está vazio (só havia commits de merge que foram filtrados por `--no-merges`), o modelo pode retornar resposta malformada.

**How to avoid:** No agente cliente, verificar se `commits_raw` está vazio **após** o filtro de merges e encerrar com `SystemExit(0)` antes de enviar ao backend. No backend, adicionar try/except em volta do `ainvoke`.

---

## Files to Create vs Modify

### Novos arquivos

| Arquivo | Responsabilidade |
|---------|-----------------|
| `docudata-backend/hooks/revisor.yml` | GitHub Actions cron workflow |
| `docudata-backend/hooks/revisor_agent.py` | Agente Python stdlib — coleta diff e envia ao backend |
| `docudata-backend/routers/revisao_ingest.py` | `POST /ingest/revisao` — recebe payload, chama Gemini, salva |

### Arquivos a modificar

| Arquivo | O que muda |
|---------|-----------|
| `docudata-backend/supabase_schema.sql` | Adicionar `CREATE TABLE revisoes_diarias` + índice |
| `docudata-backend/models/schemas.py` | Adicionar `Achado` + `RevisaoEstruturada` Pydantic models |
| `docudata-backend/routers/painel.py` | `calcular_bloco_b` recebe `revisao_recente`; `get_painel` busca revisão mais recente |
| `docudata-backend/main.py` | `from routers import ..., revisao_ingest` + `app.include_router(revisao_ingest.router)` |
| `docudata-frontend/app/lib/api.ts` | Adicionar `AchadoCritico` interface; expandir `BlocoB` com campos opcionais |
| `docudata-frontend/app/components/PainelTab.tsx` | `BlocoBCard` com nova sub-seção + toggle |

---

## Migration SQL (pronto para executar no Supabase SQL Editor)

```sql
-- Phase 9: Revisor Diário — Migration
-- Execute no Supabase SQL Editor

CREATE TABLE IF NOT EXISTS revisoes_diarias (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    data_revisao        date        NOT NULL,
    achados             jsonb       NOT NULL DEFAULT '[]',
    relatorio_gerente   text        NOT NULL DEFAULT '',
    relatorio_tecnico   text        NOT NULL DEFAULT '',
    commits_analisados  int         NOT NULL DEFAULT 0,
    diff_chars_total    int         NOT NULL DEFAULT 0,
    created_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_revisoes_diarias_project_created
    ON revisoes_diarias (project_id, created_at DESC);
```

---

## Package Legitimacy Audit

Nenhum pacote novo é instalado nesta fase. O backend reutiliza `langchain-google-genai`, `supabase`, `fastapi`, `pydantic` já presentes. O agente cliente usa apenas Python stdlib. [VERIFIED: docudata-backend/routers/commit_ingest.py:13-15, docudata-backend/hooks/docudata_agent.py:11]

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fetch-depth: 0` necessário para `git log --since` funcionar corretamente | GitHub Actions cron | Baixo — testável localmente antes de fazer push |
| A2 | GitHub Actions desabilita scheduled workflows após 60 dias sem atividade | Pitfall 6 | Baixo — projetos ativos sempre têm commits |
| A3 | `permissions: contents: read` funciona para repos privados no revisor | revisor.yml | Baixo — `continue-on-error: true` mitiga |
| A4 | `max_tokens=4096` suficiente para lista de até 20 achados | Pitfall 5 | Médio — se insuficiente, achados são truncados no JSON; structured_output levanta exceção |

---

## Open Questions

1. **Modelo Gemini a usar no revisor**
   - O que sabemos: commit_ingest.py usa `gemini-3.5-flash-lite`. A memory do projeto diz que chaves novas só funcionam com `gemini-3.5-flash+`. [VERIFIED: memory/MEMORY.md — "chaves novas só funcionam com gemini-3.5-flash+ (modelos 2.x bloqueados com 404)"]
   - O que está incerto: se `gemini-3.5-flash-lite` é adequado para revisar 100k chars de diff, ou se precisa do modelo mais capaz.
   - Recomendação: usar `gemini-3.5-flash-lite` (padrão do projeto) com `max_tokens=4096`. Se qualidade for insuficiente, o planner pode escalar para `gemini-3.5-flash`.

2. **Duplicate guard por data**
   - O que sabemos: cron roda uma vez por dia, mas pode ser re-triggered manualmente.
   - O que está incerto: se deve ter constraint `UNIQUE (project_id, data_revisao)` na tabela para evitar duplicatas.
   - Recomendação: não adicionar UNIQUE constraint nesta fase — simplicidade primeiro; se o cron rodar duas vezes, haverá dois registros; o `get_painel` busca o mais recente por `created_at`.

---

## Sources

### Primary (HIGH confidence — lido diretamente nesta sessão)

- `docudata-backend/hooks/docudata_agent.py` — padrão completo do agente cliente
- `docudata-backend/hooks/docudata.yml` — estrutura do GitHub Actions workflow
- `docudata-backend/routers/commit_ingest.py` — padrão do router FastAPI de ingestão
- `docudata-backend/routers/painel.py` — `calcular_bloco_b` e `get_painel` a expandir
- `docudata-backend/models/schemas.py` — schemas Pydantic existentes
- `docudata-backend/main.py` — padrão de registro de routers
- `docudata-backend/supabase_schema.sql` — padrão de migration SQL do projeto
- `docudata-frontend/app/components/PainelTab.tsx` — componente BlocoBCard a expandir
- `docudata-frontend/app/lib/api.ts:676-717` — tipos BlocoB e PainelData
- `.planning/phases/09-revisor-diario-generalizado/09-CONTEXT.md` — decisões bloqueadas D-01 a D-09

### Tertiary (LOW confidence — [ASSUMED])

- GitHub Actions cron `fetch-depth: 0` requirement
- GitHub Actions 60-day inactivity disablement
- `permissions: contents: read` vs `permissions: {}`

---

## Metadata

**Confidence breakdown:**
- Migration SQL: HIGH — padrão direto do supabase_schema.sql existente
- Router FastAPI: HIGH — réplica direta do commit_ingest.py
- Agente cliente Python: HIGH — réplica direta do docudata_agent.py
- GitHub Actions cron: MEDIUM — padrão conhecida, alguns detalhes [ASSUMED]
- Frontend expansão: HIGH — código exato do PainelTab.tsx lido

**Research date:** 2026-08-22
**Valid until:** 2026-09-22

---

## RESEARCH COMPLETE
