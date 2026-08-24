# Phase 12: Boletim de Aceite, Encerramento e Resumo Semanal - Research

**Researched:** 2026-08-23
**Domain:** Boletim de aceite (Gemini generation + status lifecycle), resumo semanal determinístico, nova aba frontend
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Boletim por lote — um único boletim agrupa N funcionalidades selecionadas. Nova tabela `boletins_aceite`: `id uuid PK`, `project_id uuid FK→projects`, `sprint_numero int`, `funcionalidade_ids uuid[]`, `status text` (rascunho|enviado|aprovado|ajuste), `retorno_tipo text` (null|bug|mudanca_escopo), `conteudo text` (markdown gerado), `criado_em timestamptz`, `enviado_em timestamptz`, `retorno_em timestamptz`.
- **D-02:** Gemini gera o conteúdo do boletim — mesmo padrão do Composer (Phase 10): backend monta prompt com funcionalidades e seus `criterios_aceite`, Gemini (`gemini-1.5-flash`) elabora em linguagem de negócio, gerente vê preview (react-markdown) e confirma antes de marcar como `enviado`.
- **D-03:** Sem campo de evidência visual — removido do escopo.
- **D-04:** Sem geração de Termo de Encerramento — removido do escopo. O sistema apenas sinaliza quando 100% aprovado.
- **D-05:** `status_cliente` derivado do boletim — ao criar o boletim as funcionalidades recebem `status_cliente = rascunho` no boletim; ao marcar `enviado`, recebem `status_cliente = enviado`; ao registrar retorno `aprovado`, recebem `status_cliente = aprovado`; ao registrar `ajuste`, recebem `status_cliente = ajuste_pedido`.
- **D-06:** Classificação obrigatória ao registrar ajuste pedido — o sistema exige seleção de `retorno_tipo`: `bug` ou `mudanca_escopo`. Sem essa classificação, o retorno não pode ser salvo.
- **D-07:** On-demand — botão no dashboard — sem cron, sem GitHub Actions.
- **D-08:** Listagem estruturada pura — sem Gemini no resumo semanal. Backend busca dados diretamente do banco e formata em markdown estruturado.
- **D-09:** Período: semana atual (dom–sáb) — cobre segunda a domingo da semana em curso no momento do clique.
- **D-10:** Resumo salvo em `generated_docs` — `doc_type = 'resumo_semanal'`, sem `sprint_number`.
- **D-11:** Nova aba "Aceite" no Tabs.tsx — ao lado das abas existentes.
- **D-12:** Aba Aceite contém duas seções: (1) Boletins + (2) Resumo Semanal.
- **D-13:** Sem Termo de Encerramento — quando 100% aprovado, aba exibe badge "Projeto encerrado — todas as funcionalidades aprovadas".
- **D-14:** Zero className — apenas `style={{}}` — padrão de todas as fases anteriores (8, 9, 10, 11).

### Claude's Discretion

- Endpoint para boletim: `POST /boletins` (cria rascunho + chama Gemini), `PATCH /boletins/{id}` (atualiza status: enviado/aprovado/ajuste + retorno_tipo), `GET /boletins/{project_id}` (lista por projeto).
- Preview antes de confirmar: igual ao Composer — gerente vê o markdown gerado e confirma "Marcar como Enviado" para salvar e atualizar `status_cliente` nas funcionalidades.
- Endpoint para resumo semanal: `POST /generate/resumo_semanal` com `project_id` — reutiliza o router `/generate` existente ou cria endpoint dedicado no novo router `/boletins`.
- "Mudanças de escopo" como lista separada: a aba Aceite exibe uma seção "Mudanças de Escopo Solicitadas" listando funcionalidades com `retorno_tipo = mudanca_escopo`, sem integração com tabela de funcionalidades.

### Deferred Ideas (OUT OF SCOPE)

- Evidência visual no boletim (upload de imagem ou URL)
- Termo de Encerramento como documento gerado
- Notificação por e-mail ao cliente com o boletim
- Geração automática do resumo semanal via GitHub Actions/cron
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| M6 (§5) | Boletim de aceite — gerente seleciona funcionalidades `concluida`, gera boletim, registra retorno do cliente com classificação obrigatória bug/mudanca_escopo | Backend: nova tabela `boletins_aceite` + router `/boletins` + Gemini generation; Frontend: AceiteTab com fluxo novo boletim → preview → confirmar enviado → registrar retorno |
| M8 (§5) | Resumo semanal de anomalias — gerado on-demand, sem Gemini, cobre semana atual | Backend: endpoint `POST /boletins/resumo_semanal` que reutiliza queries de `painel.py` e salva em `generated_docs`; Frontend: seção no AceiteTab |
| §4.5 (RevisaoDiaria) | Achados críticos de revisão diária alimentam o resumo semanal | `painel.py`:`calcular_bloco_b` já extrai `achados_criticos` de `revisoes_diarias` — reutilizável diretamente |
</phase_requirements>

---

## Summary

Phase 12 entrega três capacidades distintas sobre a infraestrutura já estabilizada nas Phases 7–11: (1) geração de boletim de aceite por lote via Gemini com fluxo preview → confirmar, (2) gestão do ciclo de status do cliente nas funcionalidades derivado do boletim, e (3) resumo semanal de anomalias determinístico (sem IA).

A fase é de integração: não cria nenhum novo padrão de extração ou grafo LangGraph. O boletim replica o padrão do Composer (Phase 10) — `ChatGoogleGenerativeAI` direto, sem `StateGraph`. O resumo semanal replica as queries do Painel (Phase 8) — sem custo de tokens, determinístico, zero risco de hallucination.

O risco mais alto é a introdução do novo `status_cliente = 'ajuste_pedido'` nas funcionalidades. O valor `ajuste_pedido` não existe no enum atual da TypeScript (`"nao_enviado" | "enviado" | "aprovado" | "rejeitado"`), então tanto o frontend quanto qualquer lógica de painel que filtre por `status_cliente` precisam ser atualizados para não quebrar.

**Primary recommendation:** Implementar em três ondas sequenciais — (1) migration SQL + router `/boletins` + schemas, (2) lógica de geração Gemini + PATCH de status + derivação de `status_cliente`, (3) `AceiteTab.tsx` + wiring no `page.tsx`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Nova tabela `boletins_aceite` + migration SQL | Database / Storage | — | Persistência — estado do boletim não é derivável, precisa ser armazenado |
| Geração Gemini do boletim | API / Backend | — | Chave Gemini é server-side; nunca exposta no frontend |
| Derivação de `status_cliente` nas funcionalidades | API / Backend | — | Transação de duas tabelas (`boletins_aceite` + `funcionalidades`) — deve ser atômica no backend |
| Preview markdown do boletim | Frontend Server (SSR) | Browser | `react-markdown` já instalado; renderização é client-side no Next.js app router |
| Resumo semanal (cálculo determinístico) | API / Backend | — | Queries sobre `funcionalidades`, `transicoes_status`, `revisoes_diarias`, `execucoes_aceite` — mesmo padrão de `painel.py` |
| Aba Aceite (UI) | Browser / Client | — | Componente React com estado local — lista boletins, fluxo de criação, histórico de resumos |
| Classificação bug/mudanca_escopo | API / Backend | — | Validação obrigatória no PATCH — backend rejeita sem `retorno_tipo` quando `status = ajuste` |

---

## Standard Stack

### Core (todos já instalados — nenhuma dependência nova)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain-google-genai` | já instalado | `ChatGoogleGenerativeAI` para gerar conteúdo do boletim | Mesmo padrão do Composer (Phase 10) — padrão estabelecido no projeto |
| `supabase-py` | já instalado | Queries à nova tabela `boletins_aceite` e updates em `funcionalidades` | Único cliente de DB do projeto |
| `fastapi` | já instalado | Router `/boletins` com endpoints POST/PATCH/GET | Framework web do projeto |
| `react-markdown` | já instalado | Preview do conteúdo do boletim no frontend | Já usado em todos os fluxos de geração |

**Nenhum pacote novo a instalar.** Toda a stack desta fase já está presente.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ChatGoogleGenerativeAI` direto (padrão Composer) | `StateGraph` LangGraph completo | LangGraph acrescenta retry granular mas é overkill para a geração do boletim — sem multimodal, sem parsing JSON — o padrão do Composer é suficiente |
| Endpoint dedicado `/boletins/resumo_semanal` | Reutilizar `POST /generate` com `tipo_doc='resumo_semanal'` | O `/generate` invoca `generation_graph` e Gemini; o resumo semanal é determinístico (D-08) — reutilizar o router de geração adicionaria complexidade desnecessária. Endpoint dedicado em `/boletins` é mais claro. |

---

## Package Legitimacy Audit

> Não aplicável — nenhum pacote novo é instalado nesta fase.

---

## Architecture Patterns

### System Architecture Diagram

```
Gerente (browser)
  │
  ├─[Novo Boletim]──► POST /boletins
  │                     │  1. Busca funcionalidades em status=concluida
  │                     │  2. ChatGoogleGenerativeAI(gemini-1.5-flash)
  │                     │  3. Salva em boletins_aceite (status=rascunho)
  │                     │  4. Funcionalidades → status_cliente=rascunho (no boletim, não na tabela)
  │                   ◄─┘ retorna {id, conteudo (markdown preview)}
  │
  ├─[Confirmar Enviado]─► PATCH /boletins/{id} {status: enviado}
  │                         │  1. Update boletins_aceite.status = enviado, enviado_em = now()
  │                         │  2. PATCH funcionalidades (ids do boletim) → status_cliente = enviado
  │                         │     → registra TransicaoStatus para cada uma
  │                       ◄─┘
  │
  ├─[Registrar Retorno]─► PATCH /boletins/{id} {status: aprovado|ajuste, retorno_tipo?}
  │                         │  1. Valida retorno_tipo obrigatório se status=ajuste
  │                         │  2. Update boletins_aceite (status, retorno_tipo, retorno_em)
  │                         │  3. PATCH funcionalidades → status_cliente = aprovado|ajuste_pedido
  │                       ◄─┘
  │
  ├─[Gerar Resumo]──────► POST /boletins/resumo_semanal {project_id}
  │                         │  1. Calcula período dom–sáb da semana atual
  │                         │  2. Queries determinísticas (sem Gemini):
  │                         │     - funcionalidades travadas (status=em_andamento > 7d)
  │                         │     - aguardando cliente (status_cliente=enviado > 5 dias úteis)
  │                         │     - concluidas com suite falhando (execucoes_aceite)
  │                         │     - achados críticos (revisoes_diarias)
  │                         │     - decisões pendentes (funcionalidades em_andamento)
  │                         │     - leitura tempo × escopo (bloco_a)
  │                         │  3. Formata markdown estruturado
  │                         │  4. Salva em generated_docs (doc_type='resumo_semanal')
  │                       ◄─┘ retorna GenerateResponse
  │
  └─[AceiteTab]─────────► GET /boletins/{project_id}  (lista boletins)
                         ► GET /docs/{project_id}?doc_type=resumo_semanal  (histórico resumos)
```

### Recommended Project Structure

```
docudata-backend/
├── routers/
│   └── boletins.py           # NOVO — POST /boletins, PATCH /boletins/{id}, GET /boletins/{project_id}, POST /boletins/resumo_semanal
├── models/
│   └── schemas.py            # ATUALIZAR — BoletimCreate, BoletimResponse, BoletimPatch
└── main.py                   # ATUALIZAR — include_router(boletins.router)

docudata-frontend/
└── app/
    ├── projects/[id]/
    │   └── page.tsx           # ATUALIZAR — adicionar "aceite" ao TabId + render AceiteTab
    ├── components/
    │   └── AceiteTab.tsx      # NOVO — componente completo da aba Aceite
    └── lib/
        └── api.ts             # ATUALIZAR — funções createBoletim, patchBoletim, listBoletins, gerarResumoSemanal + tipos BoletimResponse, FuncionalidadeResponse (status_cliente union)
```

### Pattern 1: Geração de Boletim — Replicar Padrão do Composer

**What:** `POST /boletins` busca funcionalidades selecionadas + `criterios_aceite`, monta contexto, chama Gemini, salva como rascunho, retorna markdown sem persistir como documento final até o gerente confirmar.

**When to use:** Sempre que a geração Gemini requer confirmação humana antes de oficializar.

```python
# Source: docudata-backend/routers/composer.py:416-433 (padrão estabelecido)
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",      # D-02 especifica gemini-1.5-flash (não gemini-3.5-flash-lite)
    max_tokens=2048,
    google_api_key=api_key,        # sempre da tabela projects.gemini_api_key
)
result = await llm.ainvoke([
    SystemMessage(content=_BOLETIM_SYSTEM_PROMPT),
    HumanMessage(content=contexto_funcionalidades),
])
markdown: str = result.content
# Salvar em boletins_aceite com status='rascunho' — NÃO em generated_docs
# Retornar {id, conteudo: markdown} para o frontend exibir preview
```

**Diferença importante vs Composer:** O boletim é salvo em `boletins_aceite` (não em `planning_rascunhos`). O "confirmar" é um `PATCH /boletins/{id}` com `status=enviado`, não um endpoint separado.

### Pattern 2: Derivação de `status_cliente` via Boletim

**What:** PATCH `/boletins/{id}` é responsável por atualizar `status_cliente` em **todas** as funcionalidades do lote. O endpoint de funcionalidades (`PATCH /funcionalidades/{id}`) já registra `TransicaoStatus` — o router de boletins deve chamá-lo ou replicar a lógica.

**Decisão de implementação:** O router `boletins.py` chama diretamente o cliente Supabase para atualizar `status_cliente` em batch e insere os `TransicaoStatus` manualmente — mais eficiente que chamar N vezes `PATCH /funcionalidades/{id}` via HTTP.

```python
# Source: docudata-backend/routers/funcionalidades.py:280-307 (padrão de TransicaoStatus)
# Replicar lógica de registro de transição para cada funcionalidade do lote
agora = datetime.now(timezone.utc)
for func_id in boletim["funcionalidade_ids"]:
    func = client.table("funcionalidades").select("*").eq("id", func_id).execute().data[0]
    # Calcular duracao desde a última transição de status_cliente
    # Inserir em transicoes_status com campo="status_cliente", de=func["status_cliente"], para=novo_valor
    # Update em funcionalidades: status_cliente = novo_valor
```

### Pattern 3: Resumo Semanal Determinístico

**What:** `POST /boletins/resumo_semanal` reutiliza as funções de cálculo de `painel.py` para montar um markdown sem chamar Gemini.

```python
# Source: docudata-backend/routers/painel.py:69-163 (calcular_bloco_b)
# Reutilizar diretamente — calcular_bloco_b já retorna travadas, aguardando_cliente,
# em_ajuste, achados_criticos, funcionalidades_com_aceite_falhando

from routers.painel import calcular_bloco_a, calcular_bloco_b

# Período da semana atual
hoje = date.today()
weekday = hoje.weekday()  # 0=segunda, 6=domingo
inicio_semana = hoje - timedelta(days=(weekday + 1) % 7)  # domingo anterior
fim_semana = inicio_semana + timedelta(days=6)

# Formatar markdown estruturado
linhas = [f"# Resumo Semanal — {inicio_semana} a {fim_semana}\n"]
if not bloco_b["travadas"] and not bloco_b["aguardando_cliente"] ...:
    linhas.append("Nenhuma anomalia identificada nesta semana.")
else:
    # Seções: Travadas / Aguardando Cliente / Suíte Falhando / Achados Críticos / etc.

# Salvar em generated_docs (D-10)
client.table("generated_docs").insert({
    "project_id": project_id,
    "doc_type": "resumo_semanal",
    "sprint_number": None,
    "content": "\n".join(linhas),
    "input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0,
}).execute()
```

### Anti-Patterns to Avoid

- **Chamar `POST /funcionalidades/{id}` N vezes para atualizar status_cliente em batch:** Cria N transações independentes e N chamadas HTTP. O router `boletins.py` deve fazer o batch update diretamente via Supabase client.
- **Salvar o boletim em `generated_docs`:** O boletim tem seu próprio ciclo de vida (rascunho → enviado → aprovado/ajuste) e a nova tabela `boletins_aceite` é a fonte canônica. `generated_docs` é apenas para documentos finais de geração.
- **Salvar o resumo semanal em `boletins_aceite`:** O resumo semanal vai para `generated_docs` com `doc_type='resumo_semanal'` (D-10).
- **Usar `StateGraph` LangGraph para o boletim:** Overkill — o Composer (Phase 10) prova que `ChatGoogleGenerativeAI` direto é suficiente para geração simples sem retry de JSON.
- **Gerar resumo semanal com Gemini:** D-08 é explícito — listagem estruturada pura, zero custo de token. Qualquer chamada Gemini neste endpoint é um bug de design.
- **Permitir PATCH do status do boletim sem validar sequência:** `rascunho → enviado → aprovado|ajuste`. Não deve ser possível aprovar um boletim que não foi enviado.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cálculo de anomalias (travadas, aguardando, falhando) | Queries duplicadas | `calcular_bloco_b()` de `painel.py` [VERIFIED: docudata-backend/routers/painel.py:69-163] | Lógica já testada e em produção — reutilizar evita drift |
| Cálculo tempo × escopo (bloco A) | Reescrever | `calcular_bloco_a()` de `painel.py` [VERIFIED: docudata-backend/routers/painel.py:34-66] | Mesma lógica, mesma fonte de dados |
| Registro de TransicaoStatus | Inserção manual sem padrão | Replicar padrão de `funcionalidades.py:280-307` [VERIFIED: docudata-backend/routers/funcionalidades.py:280-307] | O padrão calcula `duracao_fase_anterior_segundos` — campo obrigatório para o Bloco D do Painel |
| Preview markdown | Parser custom | `react-markdown` (já instalado) | Já usado em todos os fluxos de geração existentes |
| Geração Gemini | Prompt direto sem padrão | Padrão do Composer (`ChatGoogleGenerativeAI` + `SystemMessage` + `HumanMessage`) [VERIFIED: docudata-backend/routers/composer.py:416-433] | Padrão consistente, já funcionando em produção |

**Key insight:** Esta fase é quase 100% integração — as primitivas existem. O trabalho é criar a tabela `boletins_aceite`, o router `boletins.py`, e o `AceiteTab.tsx`, compondo infraestrutura já provada.

---

## Common Pitfalls

### Pitfall 1: `status_cliente = 'ajuste_pedido'` não existe no tipo TypeScript atual

**What goes wrong:** O TypeScript em `api.ts:660` define `status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado"`. Se `boletins.py` persistir `ajuste_pedido` nas funcionalidades sem atualizar o tipo, o frontend vai exibir o valor bruto (sem label) ou TypeScript vai reclamar em build time.

**Why it happens:** O valor `ajuste_pedido` é introduzido pela primeira vez nesta fase (D-05). O enum no frontend foi definido na Phase 7 antes desta decisão existir.

**How to avoid:** Atualizar `api.ts:660` para incluir `"ajuste_pedido"` no union type de `status_cliente`. Verificar também se `PainelTab.tsx` ou `PlanningTab.tsx` tem lógica de filtro/label que precise ser atualizada.

**Warning signs:** TypeScript build error em `api.ts`; valores sem label no Kanban do Painel.

### Pitfall 2: Sequência de status do boletim sem validação

**What goes wrong:** Backend aceita `PATCH /boletins/{id} {status: aprovado}` em um boletim que ainda está em `rascunho` (nunca foi enviado ao cliente), corrompendo o histórico.

**Why it happens:** PATCH sem validação de transição válida.

**How to avoid:** O handler de PATCH deve verificar o status atual antes de aceitar a transição. Transições válidas: `rascunho → enviado`, `enviado → aprovado`, `enviado → ajuste`. Qualquer outra combinação retorna 422.

**Warning signs:** Boletins com `aprovado_em` mas sem `enviado_em`.

### Pitfall 3: `retorno_tipo` obrigatório não validado

**What goes wrong:** Backend aceita `PATCH /boletins/{id} {status: ajuste}` sem `retorno_tipo`, deixando funcionalidades com `status_cliente = ajuste_pedido` sem classificação bug/mudanca_escopo.

**Why it happens:** Validação esquecida no handler do PATCH.

**How to avoid:** Handler de PATCH deve checar: se `status == 'ajuste'` e `retorno_tipo` não está em `{'bug', 'mudanca_escopo'}`, retornar 422 com mensagem `"retorno_tipo é obrigatório quando status = ajuste (valores aceitos: bug, mudanca_escopo)"`.

**Warning signs:** Boletins com `status = ajuste` e `retorno_tipo = null`.

### Pitfall 4: Batch update de `status_cliente` sem registro de TransicaoStatus

**What goes wrong:** As funcionalidades do lote têm `status_cliente` atualizado, mas sem registro em `transicoes_status`. O Bloco B do Painel (`calcular_bloco_b`) usa `transicoes_status` para calcular `aguardando_cliente` (dias úteis desde `enviado`). Sem o registro, a lógica de detecção de "aguardando há mais de 5 dias úteis" fica cega.

**Why it happens:** Update direto em batch sem usar o fluxo de transição que `funcionalidades.py` implementa.

**How to avoid:** Para cada funcionalidade no lote, inserir um registro em `transicoes_status` com `campo='status_cliente'`, `de=valor_anterior`, `para=novo_valor`, `timestamp=now()`, `duracao_fase_anterior_segundos=calculado`. Verificar o padrão em `funcionalidades.py:280-307`.

**Warning signs:** Bloco B do Painel não lista funcionalidades como "aguardando cliente" mesmo após dias sem retorno.

### Pitfall 5: Período da semana semanal — definição de "início de semana"

**What goes wrong:** Python `date.today().weekday()` retorna 0=segunda (ISO). D-09 diz "dom–sáb". Se o cálculo assumir que a semana começa na segunda, o período fica errado.

**Why it happens:** Confusão entre `weekday()` (0=segunda) e a definição dom–sáb de D-09.

**How to avoid:** Para semana dom–sáb:
```python
hoje = date.today()
# weekday(): 0=seg, 6=dom — domingo é dia 6
# Dias desde o último domingo: (weekday + 1) % 7
dias_desde_domingo = (hoje.weekday() + 1) % 7
inicio_semana = hoje - timedelta(days=dias_desde_domingo)  # domingo
fim_semana = inicio_semana + timedelta(days=6)  # sábado
```

**Warning signs:** Resumo gerado numa segunda-feira inclui dados da semana anterior errada.

### Pitfall 6: `doc_type = 'resumo_semanal'` não registrado em `generate.py`

**What goes wrong:** Se o resumo semanal for roteado via `POST /generate` (em vez de endpoint dedicado em `/boletins`), o `_VALID_DOC_TYPES` em `generate.py:13-17` rejeita `'resumo_semanal'` com 422.

**Why it happens:** `_VALID_DOC_TYPES` é um conjunto fixo que não conhece este novo tipo.

**How to avoid:** Usar endpoint dedicado `POST /boletins/resumo_semanal` (preferencial, per Claude's Discretion). Se optar por reutilizar `generate.py`, adicionar `'resumo_semanal'` a `_VALID_DOC_TYPES` E ao `generation_graph.py`. O endpoint dedicado em `/boletins` é mais simples — não invoca o `generation_graph`.

**Warning signs:** 422 "Invalid tipo_doc" ao tentar gerar resumo semanal.

### Pitfall 7: `funcionalidade_ids` como `uuid[]` no Supabase — serialização do cliente Python

**What goes wrong:** Inserir `funcionalidade_ids` como lista Python em `supabase-py` pode falhar se o tipo da coluna for `uuid[]` e o driver não serializar automaticamente.

**Why it happens:** `supabase-py` v2 serializa `dict` para `jsonb` automaticamente, mas arrays de UUIDs (`uuid[]`) podem precisar de cast explícito ou tratamento como `text[]`.

**How to avoid:** Declarar `funcionalidade_ids text[]` na migration SQL (mais simples — UUIDs como strings) e passar a lista Python de strings diretamente. Verificar que os valores são strings, não objetos UUID.

**Warning signs:** `PostgrestAPIError: invalid input syntax for type uuid` ao inserir boletim.

---

## Code Examples

### Migration SQL — `boletins_aceite`

```sql
-- Source: padrão das migrations anteriores (supabase_schema.sql)
CREATE TABLE IF NOT EXISTS boletins_aceite (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_numero       int,
    funcionalidade_ids  text[]      NOT NULL DEFAULT '{}',
    status              text        NOT NULL DEFAULT 'rascunho'
                        CHECK (status IN ('rascunho', 'enviado', 'aprovado', 'ajuste')),
    retorno_tipo        text        CHECK (retorno_tipo IS NULL OR retorno_tipo IN ('bug', 'mudanca_escopo')),
    conteudo            text        NOT NULL DEFAULT '',
    criado_em           timestamptz NOT NULL DEFAULT now(),
    enviado_em          timestamptz,
    retorno_em          timestamptz
);

CREATE INDEX IF NOT EXISTS idx_boletins_aceite_project
    ON boletins_aceite (project_id, criado_em DESC);
```

### Pydantic Schemas para `boletins.py`

```python
# Source: padrão de schemas.py — baseado em ExecucaoAceitePayload e BoletimCreate
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BoletimCreate(BaseModel):
    project_id: str
    sprint_numero: Optional[int] = None
    funcionalidade_ids: list[str]  # UUIDs como strings

class BoletimPatch(BaseModel):
    status: str  # enviado | aprovado | ajuste
    retorno_tipo: Optional[str] = None  # obrigatório se status=ajuste

class BoletimResponse(BaseModel):
    id: str
    project_id: str
    sprint_numero: Optional[int]
    funcionalidade_ids: list[str]
    status: str
    retorno_tipo: Optional[str]
    conteudo: str
    criado_em: datetime
    enviado_em: Optional[datetime]
    retorno_em: Optional[datetime]
```

### Atualização de `api.ts` — tipo `FuncionalidadeResponse`

```typescript
// Source: docudata-frontend/app/lib/api.ts:660 (linha a atualizar)
// DE:
status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado";
// PARA:
status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado" | "ajuste_pedido";
```

### Wiring de `page.tsx` — nova aba Aceite

```typescript
// Source: docudata-frontend/app/projects/[id]/page.tsx:48 (TabId existente)
// DE:
type TabId = "sprints" | "painel" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config" | "planning";
// PARA:
type TabId = "sprints" | "painel" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config" | "planning" | "aceite";

// Source: docudata-frontend/app/projects/[id]/page.tsx:471-483 (Tabs existente)
// Adicionar ao array de tabs:
{ id: "aceite", label: "Aceite" },
```

### Prompt do sistema para o boletim

```python
# Source: padrão de composer.py:17-27 e geração do projeto
_BOLETIM_SYSTEM_PROMPT = """Você é um assistente especializado em comunicação com clientes de projetos de dados do CITi.
Sua tarefa é gerar um Boletim de Aceite em markdown, em português, de forma clara e acessível para um cliente não técnico.

O boletim deve conter:
1. **Título** — nome do projeto e identificação do lote de funcionalidades
2. **Funcionalidades para Aceite** — para cada funcionalidade: nome e critérios de aceite em linguagem de negócio (sem jargão técnico)
3. **Instruções para Aceite** — como o cliente deve registrar o retorno (aprovado ou ajuste pedido)

Reescreva os critérios de aceite em linguagem acessível ao cliente — sem termos técnicos como "endpoint", "payload", "UUID".
Retorne APENAS o markdown, sem texto antes ou depois, sem blocos de código, sem backticks."""
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `status_cliente` com valores `nao_enviado|enviado|aprovado|rejeitado` | Adiciona `ajuste_pedido` nesta fase | Phase 12 | Frontend e painel precisam reconhecer o novo valor |
| `generated_docs` para toda saída de geração | `boletins_aceite` para boletins (ciclo de vida próprio) + `generated_docs` para resumo semanal | Phase 12 | Dois destinos diferentes — clareza de responsabilidade |

---

## Existing Code — Integration Points (Read-Only Summary)

### Tabelas que este phase lê/modifica

| Tabela | Operação | Fonte | Notas |
|--------|----------|-------|-------|
| `funcionalidades` | UPDATE `status_cliente` em batch | `boletins.py` (novo) | Deve registrar `transicoes_status` para cada update |
| `transicoes_status` | INSERT (via batch) | `boletins.py` (novo) | Necessário para Bloco B do Painel |
| `boletins_aceite` | INSERT + UPDATE + SELECT | `boletins.py` (novo) | Nova tabela |
| `generated_docs` | INSERT (`doc_type='resumo_semanal'`) | `boletins.py` (novo) | Reutiliza tabela existente |
| `revisoes_diarias` | SELECT (achados recentes) | via `calcular_bloco_b` reutilizado | Fonte para seção "Achados Críticos" do resumo |
| `execucoes_aceite` | SELECT (gates com falha) | via `calcular_bloco_b` reutilizado | Fonte para "Concluídas com Suíte Falhando" |

### Valores existentes — verificados diretamente nos arquivos

| Campo | Valores atuais | Source |
|-------|---------------|--------|
| `funcionalidades.status` | `nao_iniciada`, `em_andamento`, `em_ajuste`, `concluida` | [VERIFIED: docudata-backend/routers/funcionalidades.py:263] — validação implícita via painel e state machine |
| `funcionalidades.status_cliente` | `nao_enviado`, `enviado`, `aprovado`, `rejeitado` | [VERIFIED: docudata-frontend/app/lib/api.ts:660] — `"nao_enviado" | "enviado" | "aprovado" | "rejeitado"` |
| `status_cliente` padrão DB | `'nao_enviado'` | [VERIFIED: .planning/phases/07-matriz-de-escopo-transicaostatus-campos-novos-em-projeto/07-01-PLAN.md:110] — `status_cliente text NOT NULL DEFAULT 'nao_enviado'` |
| `generated_docs.doc_type` válidos no router | `repasse_semanal`, `retrospectiva`, `log_decisoes`, `documentacao_final`, `ata_reuniao`, `onboarding`, `planning`, `daily`, `review` | [VERIFIED: docudata-backend/routers/generate.py:13-17] — `_VALID_DOC_TYPES = {"repasse_semanal", "retrospectiva", "log_decisoes", "documentacao_final", "ata_reuniao", "onboarding", "planning", "daily", "review"}` |
| Tabs existentes no dashboard | `sprints`, `painel`, `tecnologias`, `cross_sprint`, `documentos`, `custos`, `config`, `planning` | [VERIFIED: docudata-frontend/app/projects/[id]/page.tsx:48] — `type TabId = "sprints" \| "painel" \| "tecnologias" \| "cross_sprint" \| "documentos" \| "custos" \| "config" \| "planning"` |
| Modelo Gemini em uso no Composer | `gemini-3.5-flash-lite` | [VERIFIED: docudata-backend/routers/composer.py:417] — `model="gemini-3.5-flash-lite"` |
| `_PLANNING_SYSTEM_PROMPT` — estrutura de prompt | SystemMessage + HumanMessage via `llm.ainvoke` | [VERIFIED: docudata-backend/routers/composer.py:416-433] |
| Routers registrados em `main.py` | `projects`, `sprints`, `sprint_docs`, `ingest`, `generate`, `ingestions`, `search`, `export`, `commit_ingest`, `enrich`, `funcionalidades`, `painel`, `revisao_ingest`, `composer`, `aceite_ingest` | [VERIFIED: docudata-backend/main.py:6] |

**Nota sobre modelo Gemini:** D-02 especifica `gemini-1.5-flash`. O Composer usa `gemini-3.5-flash-lite`. A memory do projeto ([VERIFIED: MEMORY.md]) indica que chaves novas só funcionam com `gemini-3.5-flash+` (modelos 2.x bloqueados com 404). O planner deve usar `gemini-1.5-flash` conforme D-02, mas documentar este risco para que o executor verifique com a chave disponível. [ASSUMED: que gemini-1.5-flash é aceito pela chave do projeto — verificar antes de usar]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `gemini-1.5-flash` é acessível com a chave Gemini do projeto (D-02 especifica este modelo) | Standard Stack / Code Examples | Endpoint 404; executor deve testar com a chave real e fazer fallback para `gemini-3.5-flash-lite` se necessário |
| A2 | `funcionalidades.status_cliente` não tem CHECK constraint no banco (só validação application-level) | Architecture Patterns | Se houver CHECK constraint bloqueando `ajuste_pedido`, a migration precisa de `ALTER TABLE ... DROP CONSTRAINT ... ADD CONSTRAINT` |
| A3 | `AceiteTab.tsx` é um componente novo independente (não modifica componentes existentes) | Architecture Patterns | Se o painel ou outro componente tiver acoplamento com `status_cliente` que precise de update, há trabalho adicional |

---

## Open Questions

1. **Modelo Gemini — D-02 vs projeto**
   - What we know: D-02 especifica `gemini-1.5-flash`; Composer usa `gemini-3.5-flash-lite`; memory indica que modelos 2.x bloqueados com chaves novas
   - What's unclear: Qual exatamente é o modelo mínimo aceito pela chave do projeto
   - Recommendation: O planner deve usar `gemini-1.5-flash` conforme D-02 e adicionar nota para o executor testar antes de commitar

2. **Batch update de `status_cliente` — usar PATCH HTTP ou query direta**
   - What we know: Chamar N vezes `PATCH /funcionalidades/{id}` gera N HTTP round-trips; query direta em batch é mais eficiente mas duplica lógica de `transicoes_status`
   - What's unclear: Se a lógica de `transicoes_status` deve ser extraída para um service compartilhado ou duplicada
   - Recommendation: Implementar como função auxiliar em `boletins.py` que replica o padrão de `funcionalidades.py:280-307` — aceitar duplicação por ora e refatorar para service se necessário

---

## Environment Availability

> Esta fase é de código/configuração — apenas dependências já disponíveis no projeto são usadas. Nenhuma ferramenta externa nova.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langchain-google-genai` | Geração do boletim | ✓ | já instalado | — |
| `supabase-py` | Queries à nova tabela | ✓ | já instalado | — |
| `react-markdown` | Preview do boletim | ✓ | já instalado | — |
| Supabase (PostgreSQL) | Nova tabela `boletins_aceite` | ✓ | Cloud | — |

---

## Security Domain

> `security_enforcement` não está explicitamente configurado — tratado como habilitado.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | não — sem auth no MVP | — |
| V3 Session Management | não | — |
| V4 Access Control | não — espaço compartilhado sem isolamento (decisão consciente do MVP) | — |
| V5 Input Validation | sim | Pydantic schemas em `BoletimCreate`, `BoletimPatch`; validação de `retorno_tipo` obrigatório; validação de sequência de status |
| V6 Cryptography | não | — |

### Known Threat Patterns for Esta Fase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Transição inválida de status do boletim (ex: `rascunho → aprovado` sem `enviado`) | Tampering | Validação explícita da sequência de status no handler PATCH |
| `retorno_tipo` nulo em boletim com ajuste | Tampering | 422 obrigatório se `status=ajuste` e `retorno_tipo` não fornecido |
| IDs de funcionalidades no payload do boletim não pertencem ao projeto | Spoofing | Verificar que todos os `funcionalidade_ids` têm `project_id` igual ao do boletim |

---

## Sources

### Primary (HIGH confidence)

- `docudata-backend/routers/funcionalidades.py` — padrão de TransicaoStatus, state machine, dispatch_aceite_background
- `docudata-backend/routers/painel.py` — funções calcular_bloco_a, calcular_bloco_b (reutilizáveis para resumo semanal)
- `docudata-backend/routers/composer.py` — padrão Gemini direto (sem LangGraph), fluxo preview → confirmar
- `docudata-backend/routers/generate.py` — `_VALID_DOC_TYPES`, padrão de geração, destino em `generated_docs`
- `docudata-backend/models/schemas.py` — schemas existentes, `FuncionalidadeResponse`, `GenerateResponse`
- `docudata-backend/main.py` — lista de routers registrados
- `docudata-backend/supabase_schema.sql` — padrão de migrations incrementais
- `docudata-frontend/app/projects/[id]/page.tsx` — `TabId` union, Tabs.tsx wiring, estilo geral
- `docudata-frontend/app/lib/api.ts` — tipos TypeScript existentes, funções fetch
- `docudata-frontend/app/components/Tabs.tsx` — implementação do componente Tabs
- `.planning/phases/12-boletim-de-aceite-encerramento-e-resumo-semanal/12-CONTEXT.md` — decisões D-01 a D-14
- `.planning/phases/07-matriz-de-escopo-transicaostatus-campos-novos-em-projeto/07-01-PLAN.md` — schema da tabela `funcionalidades`

### Secondary (MEDIUM confidence)

- `.planning/ROADMAP.md` — contexto de dependências (Phase 7 e Phase 8)

---

## Metadata

**Confidence breakdown:**
- Tabela `boletins_aceite` + migration: HIGH — padrão idêntico às migrations anteriores
- Padrão Gemini (boletim): HIGH — Composer (Phase 10) é a referência direta, lida nesta sessão
- Resumo semanal determinístico: HIGH — `painel.py` está completo e verificado nesta sessão
- `status_cliente = ajuste_pedido` — impacto no frontend: HIGH — tipo TypeScript verificado nesta sessão
- Modelo Gemini correto (`gemini-1.5-flash` vs atual): LOW — D-02 especifica o modelo mas a compatibilidade com a chave do projeto é [ASSUMED]

**Research date:** 2026-08-23
**Valid until:** 2026-09-23 (stack estável — bibliotecas sem mudanças de API esperadas)
