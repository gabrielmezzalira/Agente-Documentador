# Phase 19 — Peso por Arquétipo + Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calcular e expor um ranking de operacionais em 3 janelas (sprint/quinzenal/mensal), combinando 5 dimensões ponderadas (Gerente 35% · Entrega 20% · Qualidade 20% · Autonomia 15% · Evolução 10%) a partir do dado bruto já travado pela Phase 18, incluindo uma nova dimensão de qualidade de commit avaliada por IA.

**Architecture:** Duas correções pontuais em `services/pontuacao.py` (Phase 18) — `gerente_media` passa a usar as 7 respostas, e o fechamento passa a gravar `qualidade_commit_media`. Um pipeline novo, best-effort, estende `POST /ingest/commit` (Phase 4) com uma segunda chamada Gemini que pontua qualidade de commit, gravando em `commit_qualidade` — só pra `arquetipo=padrao`. Um serviço novo, `services/performance.py`, agrega a sequência pessoal do operacional (cross-projeto, casada por e-mail) em duas camadas por dimensão, replicando o método já usado por `calcular_spi_operacional`. `GET /performance` (já existe como stub, Phase 16) passa a devolver o ranking real.

**Tech Stack:** FastAPI (Python) + Supabase PostgreSQL (supabase-py v2, sync) + LangChain/Gemini (`gemini-3.5-flash-lite`, já em uso) + Next.js/React (frontend sem design system formal — segue o padrão visual de `PainelTab.tsx`/`MetricasTab.tsx`).

**Spec:** `docs/superpowers/specs/2026-09-06-peso-arquetipo-performance-design.md`

## Global Constraints

- Migrações em `docudata-backend/supabase_schema.sql` são idempotentes (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`) e aplicadas manualmente no Supabase — nunca rodam sozinhas (memória do projeto).
- `GET /performance` é restrito a `cargo=lider` via `require_role("lider")` — nunca `require_not_operacional`. Toda leitura registra `registrar_auditoria` (já presente no stub, Phase 16) — não pode se perder na implementação real.
- Os 5 pesos principais (`peso_gerente/entrega/qualidade/autonomia/evolucao`) são idênticos entre os 2 valores de `arquetipo` — decisão fechada e permanente (`.planning/intel/decisions.md` #3). Só `peso_commit_qualidade` (blend interno dentro de Qualidade) é ajustável.
- Sem botão de anúncio de top performer — só ranking (descopado no brainstorming).
- **Correção de design descoberta durante o planejamento** (não estava na spec): `docudata_agent.py` (script instalado nos repositórios cliente) envia hoje `author` como o **nome** do autor do commit (`git log --pretty=%an`), não o e-mail. A spec assumia que dava pra casar `author` direto contra `operacionais.email`. A Task 5 corrige isso adicionando `author_email` (`%ae`) ao agente e ao payload, best-effort — sem essa correção, a resolução de `operacional_id` na tabela `commit_qualidade` nunca bateria.
- Testes seguem o padrão do projeto: pytest + `unittest.mock.MagicMock` por `client.table(...)`, cada arquivo de teste com seu próprio helper de mock local — sem `conftest.py` compartilhado. Frontend não tem infraestrutura de teste automatizado (sem `test` script no `package.json`) — tasks de UI verificam via `npm run build` (typecheck), consistente com o padrão já usado nas fases anteriores.

---

### Task 1: Migração SQL

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (apenda ao final)

**Interfaces:**
- Produces: `projects.arquetipo`, tabela `pesos_arquetipo` (2 linhas seed), tabela `commit_qualidade`, coluna `pontuacao_operacional_sprint.qualidade_commit_media` — consumidos por todas as tasks seguintes.

- [ ] **Step 1: Apendar a migração ao final de `supabase_schema.sql`**

```sql

-- ═══════════════════════════════════════════════════════════════
-- Phase 19: Peso por Arquétipo + Área de Performance e Ranking
-- (PERF-01..06)
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE projects ADD COLUMN IF NOT EXISTS arquetipo text NOT NULL DEFAULT 'padrao'
    CHECK (arquetipo IN ('padrao', 'consultoria_discovery'));

CREATE TABLE IF NOT EXISTS pesos_arquetipo (
    arquetipo               text        PRIMARY KEY CHECK (arquetipo IN ('padrao', 'consultoria_discovery')),
    peso_gerente            numeric(3,2) NOT NULL DEFAULT 0.35,
    peso_entrega            numeric(3,2) NOT NULL DEFAULT 0.20,
    peso_qualidade          numeric(3,2) NOT NULL DEFAULT 0.20,
    peso_autonomia          numeric(3,2) NOT NULL DEFAULT 0.15,
    peso_evolucao           numeric(3,2) NOT NULL DEFAULT 0.10,
    peso_commit_qualidade   numeric(3,2) NOT NULL DEFAULT 0.50
);
INSERT INTO pesos_arquetipo (arquetipo) VALUES ('padrao'), ('consultoria_discovery')
    ON CONFLICT (arquetipo) DO NOTHING;

CREATE TABLE IF NOT EXISTS commit_qualidade (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_hash     text        NOT NULL,
    task_id         uuid        REFERENCES tasks(id) ON DELETE SET NULL,
    operacional_id  uuid        REFERENCES operacionais(id) ON DELETE SET NULL,
    projeto_id      uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    nota            int         NOT NULL CHECK (nota BETWEEN 0 AND 10),
    evidencia       text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_commit_qualidade_operacional ON commit_qualidade(operacional_id);
CREATE INDEX IF NOT EXISTS idx_commit_qualidade_projeto ON commit_qualidade(projeto_id);

ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS qualidade_commit_media numeric(4,2);
```

- [ ] **Step 2: Commit**

```bash
git add docudata-backend/supabase_schema.sql
git commit -m "feat(19-01): migração SQL — arquetipo, pesos_arquetipo, commit_qualidade, qualidade_commit_media"
```

Sem teste automatizado (migração SQL, aplicada manualmente no Supabase — mesmo padrão da Phase 18).

---

### Task 2: Correção retroativa — `gerente_media` usa as 7 respostas

**Files:**
- Modify: `docudata-backend/services/pontuacao.py:130`
- Test: `docudata-backend/tests/test_pontuacao_fechamento.py` (adiciona um teste)

**Interfaces:**
- Consumes: nada novo.
- Produces: nenhuma mudança de assinatura — só o valor calculado de `gerente_media` muda.

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `docudata-backend/tests/test_pontuacao_fechamento.py` (reaproveita `_mock_client`, `_SPRINT` já definidos no arquivo):

```python
def test_gerente_media_usa_as_sete_respostas(monkeypatch):
    aval = {
        "operacional_id": "op-1",
        "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_6": 0, "resposta_7": 5,
    }
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 1, "coluna_kanban": "em_andamento"}],
        avaliacoes=[aval],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    # Média das 7 respostas (inclui resposta_6=0), não das 6 que excluíam resposta_6.
    assert linha["gerente_media"] == round((5 + 5 + 5 + 5 + 5 + 0 + 5) / 7, 2)
    assert linha["gerente_pergunta6"] == 0
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_pontuacao_fechamento.py::test_gerente_media_usa_as_sete_respostas -v`
Expected: FAIL — `assert round((5+5+5+5+5+0+5)/6, 2) == round((5+5+5+5+5+0+5)/7, 2)` é falso (média de 6 vs. 7 valores diferem quando `resposta_6` não é 0... na verdade com esses valores a diferença é sutil; confirme lendo a asserção: o código atual usa `[resposta_1,2,3,4,5,7]` — 6 valores todos 5 → média 5.0; a asserção espera `(5+5+5+5+5+0+5)/7 ≈ 4.29`. `5.0 != 4.29` → falha como esperado.

- [ ] **Step 3: Implementar**

Em `docudata-backend/services/pontuacao.py:130`, trocar:

```python
            notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_7"]]
```

por:

```python
            notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_6"], aval["resposta_7"]]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS (todos os testes do arquivo, incluindo o novo)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "fix(19-02): gerente_media usa as 7 respostas (pergunta 6 entra duas vezes por design)"
```

---

### Task 3: `qualidade_commit_media` no fechamento

**Files:**
- Modify: `docudata-backend/services/pontuacao.py`
- Test: `docudata-backend/tests/test_pontuacao_fechamento.py` (adiciona testes)

**Interfaces:**
- Consumes: tabela `commit_qualidade` (Task 1).
- Produces: campo `qualidade_commit_media` no dict retornado por `calcular_e_travar_pontuacao` — consumido pela Task 6 (`services/performance.py`).

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao `_mock_client` de `tests/test_pontuacao_fechamento.py` um parâmetro novo `commit_qualidade=None` e um branch pra tabela `"commit_qualidade"`:

```python
def _mock_client(
    pontuacao_existente=None,
    sprint=None,
    tasks=None,
    task_transicoes=None,
    task_reaberturas=None,
    eventos_tardios=None,
    avaliacoes=None,
    commit_qualidade=None,
    insert_capture=None,
):
    pontuacao_existente = pontuacao_existente or []
    tasks = tasks or []
    task_transicoes = task_transicoes or []
    task_reaberturas = task_reaberturas or []
    eventos_tardios = eventos_tardios or []
    avaliacoes = avaliacoes or []
    commit_qualidade = commit_qualidade or []
    insert_capture = insert_capture if insert_capture is not None else []

    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        # ... (branches existentes de pontuacao_operacional_sprint, sprints, tasks,
        #      task_transicoes, task_reaberturas, eventos_pontuacao_tardios, avaliacoes_gerente
        #      permanecem exatamente como já estão no arquivo — só adicionar o branch abaixo)

        if name == "commit_qualidade":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.gt = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = commit_qualidade
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client
```

(Ao aplicar este `Step`, o engenheiro deve inserir o `if name == "commit_qualidade":` bloco dentro da função `table_side_effect` já existente, junto dos outros `elif`/`if` — não substituir a função inteira, só adicionar este branch e o parâmetro novo na assinatura.)

Adicionar ao final do arquivo:

```python
def test_qualidade_commit_media_calculada_no_fechamento(monkeypatch):
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        commit_qualidade=[
            {"operacional_id": "op-1", "nota": 8},
            {"operacional_id": "op-1", "nota": 6},
        ],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["qualidade_commit_media"] == round((8 + 6) / 2, 2)


def test_qualidade_commit_media_null_sem_commit_no_periodo(monkeypatch):
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        commit_qualidade=[],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["qualidade_commit_media"] is None
```

- [ ] **Step 2: Rodar e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_pontuacao_fechamento.py::test_qualidade_commit_media_calculada_no_fechamento tests/test_pontuacao_fechamento.py::test_qualidade_commit_media_null_sem_commit_no_periodo -v`
Expected: FAIL — `KeyError: 'qualidade_commit_media'` (campo ainda não existe no dict retornado)

- [ ] **Step 3: Implementar**

Em `docudata-backend/services/pontuacao.py`, adicionar a função auxiliar (junto de `_contar_reaberturas`):

```python
def _calcular_qualidade_commit(client, projeto_id: str, cutoff: str | None) -> dict[str, float]:
    query = (
        client.table("commit_qualidade")
        .select("operacional_id, nota")
        .eq("projeto_id", projeto_id)
    )
    if cutoff is not None:
        query = query.gt("criado_em", cutoff)
    rows = query.execute().data or []
    por_operacional: dict[str, list[int]] = {}
    for row in rows:
        op = row.get("operacional_id")
        if op:
            por_operacional.setdefault(op, []).append(row["nota"])
    return {op: round(sum(notas) / len(notas), 2) for op, notas in por_operacional.items()}
```

Em `calcular_e_travar_pontuacao`, logo depois da linha `reaberturas = _contar_reaberturas(client, [t["id"] for t in tasks], cutoff)`, adicionar:

```python
    qualidade_commit = _calcular_qualidade_commit(client, project_id, cutoff)
```

E no dict dentro do loop `for operacional_id in operacional_ids:`, adicionar o campo (junto dos outros, antes de `"arquetipo": None,`):

```python
            "qualidade_commit_media": qualidade_commit.get(operacional_id),
```

(Nota: `qualidade_commit` NÃO entra na união `operacional_ids` — só enriquece operacionais que já apareceram via outras dimensões nesta sprint. Um commit sem nenhuma task associada na sprint não cria uma linha nova sozinho.)

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS (todos os testes do arquivo)

- [ ] **Step 5: Rodar a suíte inteira**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS — mesmas 4 falhas pré-existentes de `test_schemas_and_client.py` (Phase 1 obsoleta), nenhuma nova.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "feat(19-03): qualidade_commit_media calculada no fechamento (mesmo cutoff das outras dimensões)"
```

---

### Task 4: `arquetipo` no contrato do projeto

**Files:**
- Modify: `docudata-backend/models/schemas.py` (`ContratoUpdate`, `ProjectResponse`)
- Test: `docudata-backend/tests/test_contrato_arquetipo.py`

**Interfaces:**
- Consumes: coluna `projects.arquetipo` (Task 1).
- Produces: `PATCH /projects/{id}/contrato` aceita `arquetipo`; `ProjectResponse.arquetipo` — consumido pela Task 6 (`_arquetipos_dos_projetos`) e pela Task 8 (frontend).

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para arquetipo no contrato do projeto (Phase 19, PERF-01)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(project_exists=True, updated_row=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "proj-1"}] if project_exists else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                inner = MagicMock()
                resp = MagicMock()
                base = {
                    "id": "proj-1", "name": "P", "client": "C", "created_at": "2026-01-01T00:00:00+00:00",
                    "has_api_key": False, "is_delivered": False,
                }
                resp.data = [dict(base, **(updated_row or {}), **payload)]
                inner.execute = MagicMock(return_value=resp)
                q.eq = MagicMock(return_value=inner)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "ger@citi.com", "gerente"))
    return tc


def test_atualiza_arquetipo_para_consultoria_discovery(monkeypatch):
    mock_sb = _mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"arquetipo": "consultoria_discovery"})

    assert resp.status_code == 200
    assert resp.json()["arquetipo"] == "consultoria_discovery"


def test_arquetipo_invalido_retorna_422(monkeypatch):
    mock_sb = _mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"arquetipo": "dev"})

    assert resp.status_code == 422
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_contrato_arquetipo.py -v`
Expected: FAIL — `test_atualiza_arquetipo...` falha com 422 (campo `arquetipo` desconhecido é ignorado pelo Pydantic hoje, então o payload fica vazio e a rota responde 422 "Nenhum campo fornecido"; ou, dependendo da versão do Pydantic, o campo extra é simplesmente descartado silenciosamente). `test_arquetipo_invalido...` falha porque não há validação (o valor `"dev"` passaria hoje).

- [ ] **Step 3: Implementar**

Em `docudata-backend/models/schemas.py`, adicionar `Literal` ao import do topo:

```python
from typing import Literal, Optional
```

Em `ContratoUpdate` (linha ~307), adicionar o campo:

```python
class ContratoUpdate(BaseModel):
    data_inicio: Optional[date] = None
    data_fim_contratada: Optional[date] = None
    tolerancia_desvio_pontos: Optional[int] = Field(default=None, ge=0)
    periodo_garantia_dias: Optional[int] = Field(default=None, ge=0)
    arquetipo: Optional[Literal["padrao", "consultoria_discovery"]] = None
```

Em `ProjectResponse` (linha ~42), adicionar:

```python
    arquetipo: str = "padrao"
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_contrato_arquetipo.py -v`
Expected: PASS (2 testes)

- [ ] **Step 5: Rodar a suíte inteira**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS — mesmas 4 falhas pré-existentes, nenhuma nova.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/tests/test_contrato_arquetipo.py
git commit -m "feat(19-04): arquetipo no contrato do projeto (PATCH /projects/{id}/contrato)"
```

---

### Task 5: Pipeline de qualidade de commit via IA

**Files:**
- Modify: `docudata-backend/hooks/docudata_agent.py` (adiciona `author_email`)
- Modify: `docudata-backend/routers/commit_ingest.py`
- Modify: `docudata-backend/models/schemas.py` (`CommitPayload`, novo `AvaliacaoQualidadeCommit`)
- Test: `docudata-backend/tests/test_commit_qualidade_pipeline.py`

**Interfaces:**
- Consumes: tabela `commit_qualidade` (Task 1), `projects.arquetipo` (Task 4).
- Produces: linhas em `commit_qualidade` — consumidas pela Task 3 (já implementada, lê a mesma tabela) e pela Task 6.

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para o pipeline de qualidade de commit via IA (Phase 19).

Estende POST /ingest/commit (Phase 4) — não cria gatilho novo. Só roda pra
arquetipo=padrao (consultoria/discovery não tem commit). Best-effort: falha
na avaliação de qualidade nunca derruba a ingestão de conhecimento já
existente.
"""
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from models.schemas import ConteudoEstruturado, AvaliacaoQualidadeCommit


def _mock_client(arquetipo="padrao", operacionais=None, commit_qualidade_insert=None):
    operacionais = operacionais if operacionais is not None else []
    commit_qualidade_insert = commit_qualidade_insert if commit_qualidade_insert is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"gemini_api_key": "fake-key", "arquetipo": arquetipo}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "sprint-1"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "ingestions":
            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="ingestion-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "commit_qualidade":
            def insert_side_effect(payload):
                commit_qualidade_insert.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="cq-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_PAYLOAD = {
    "project_id": "proj-1", "sprint_number": 1, "commit_hash": "abc1234",
    "commit_message": "fix: corrige bug [task:11111111-1111-1111-1111-111111111111]",
    "author": "Ana Silva", "author_email": "ana@citi.com", "date": "2026-01-01T00:00:00Z",
}


def _client(monkeypatch, mock_supabase):
    import routers.commit_ingest as commit_router
    monkeypatch.setattr(commit_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def _mock_gemini(monkeypatch, conteudo: ConteudoEstruturado, avaliacao: AvaliacaoQualidadeCommit):
    import routers.commit_ingest as commit_router

    class _FakeStructuredExtracao:
        async def ainvoke(self, messages):
            fake_msg = MagicMock()
            fake_msg.usage_metadata = {"input_tokens": 10, "output_tokens": 10}
            return {"parsed": conteudo, "raw": fake_msg}

    class _FakeStructuredQualidade:
        async def ainvoke(self, messages):
            return avaliacao

    class _FakeLLM:
        def with_structured_output(self, schema, **kwargs):
            if schema is ConteudoEstruturado:
                return _FakeStructuredExtracao()
            return _FakeStructuredQualidade()

    monkeypatch.setattr(commit_router, "ChatGoogleGenerativeAI", lambda **kwargs: _FakeLLM())


_CONTEUDO = ConteudoEstruturado(
    resumo="r", tarefas=[], decisoes=[], problemas=[], contexto_cliente="", proximos_passos=[], tecnologias=[],
)


def test_padrao_com_email_bate_grava_commit_qualidade(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(
        arquetipo="padrao",
        operacionais=[{"id": "op-1"}],
        commit_qualidade_insert=insert_capture,
    )
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=8, evidencia="Boa cobertura de testes"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert len(insert_capture) == 1
    assert insert_capture[0]["operacional_id"] == "op-1"
    assert insert_capture[0]["nota"] == 8
    assert insert_capture[0]["task_id"] == "11111111-1111-1111-1111-111111111111"
    assert insert_capture[0]["projeto_id"] == "proj-1"


def test_consultoria_discovery_nao_avalia_qualidade(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(arquetipo="consultoria_discovery", commit_qualidade_insert=insert_capture)
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=8, evidencia="x"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert insert_capture == []


def test_sem_email_correspondente_grava_operacional_id_none(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(arquetipo="padrao", operacionais=[], commit_qualidade_insert=insert_capture)
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=5, evidencia="x"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert insert_capture[0]["operacional_id"] is None


def test_falha_na_avaliacao_de_qualidade_nao_derruba_ingestao(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(arquetipo="padrao", operacionais=[{"id": "op-1"}], commit_qualidade_insert=insert_capture)

    import routers.commit_ingest as commit_router

    class _FakeStructuredExtracao:
        async def ainvoke(self, messages):
            fake_msg = MagicMock()
            fake_msg.usage_metadata = {"input_tokens": 10, "output_tokens": 10}
            return {"parsed": _CONTEUDO, "raw": fake_msg}

    class _FakeStructuredQualidadeQuebrado:
        async def ainvoke(self, messages):
            raise RuntimeError("Gemini indisponível")

    class _FakeLLM:
        def with_structured_output(self, schema, **kwargs):
            if schema is ConteudoEstruturado:
                return _FakeStructuredExtracao()
            return _FakeStructuredQualidadeQuebrado()

    monkeypatch.setattr(commit_router, "ChatGoogleGenerativeAI", lambda **kwargs: _FakeLLM())
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert insert_capture == []
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_commit_qualidade_pipeline.py -v`
Expected: FAIL — `ImportError: cannot import name 'AvaliacaoQualidadeCommit'`

- [ ] **Step 3: Implementar — `models/schemas.py`**

Adicionar ao final do arquivo:

```python
class AvaliacaoQualidadeCommit(BaseModel):
    nota: int = Field(ge=0, le=10, description="Nota de 0 a 10 avaliando a qualidade tecnica da entrega deste commit")
    evidencia: str = Field(description="Frase curta explicando o motivo da nota — nunca uma lista de pendencias a corrigir")
```

- [ ] **Step 4: Implementar — `hooks/docudata_agent.py`**

Adicionar, junto da coleta de `author` (linha ~54):

```python
author       = git("log", "-1", "--pretty=%an")
author_email = git("log", "-1", "--pretty=%ae")
```

No payload (linha ~61-70), adicionar o campo:

```python
payload = {
    "project_id":    PROJECT_ID,
    "sprint_number": sprint_number,
    "commit_hash":   commit_hash,
    "commit_message": commit_msg,
    "author":        author,
    "author_email":  author_email,
    "date":          date,
    "diff_stat":     diff_stat,
    "diff":          diff_full,
}
```

- [ ] **Step 5: Implementar — `routers/commit_ingest.py`**

Adicionar `import re` ao topo, `Literal` não é necessário aqui. Adicionar `AvaliacaoQualidadeCommit` ao import de `models.schemas`:

```python
import re
...
from models.schemas import ConteudoEstruturado, AvaliacaoQualidadeCommit
```

Adicionar `author_email` a `CommitPayload`:

```python
class CommitPayload(BaseModel):
    project_id: str
    sprint_number: int
    commit_hash: str
    commit_message: str
    author: str
    author_email: Optional[str] = None
    date: str
    branch: Optional[str] = None
    diff_stat: Optional[str] = None
    diff: Optional[str] = None
```

Adicionar o prompt novo (junto de `_COMMIT_SYSTEM_PROMPT`):

```python
_COMMIT_QUALIDADE_PROMPT = (
    "Voce avalia a qualidade tecnica de uma entrega de codigo a partir do commit e do diff "
    "fornecidos. Pontue de 0 a 10 olhando: complexidade da tarefa resolvida no contexto do "
    "commit, qualidade da documentacao e das mensagens de commit, e aderencia a boas praticas "
    "esperadas (nomes claros, tratamento de erro, testes quando cabivel). "
    "Nunca liste pendencia pra corrigir — devolva so a nota e uma frase curta explicando o "
    "porque, no mesmo espirito de um placar."
)

_TASK_TAG_RE = re.compile(r"\[task:([0-9a-fA-F-]{36})\]")
```

Trocar a query que busca o projeto (linha ~106) pra também buscar `arquetipo`:

```python
    project_resp = client.table("projects").select("gemini_api_key, arquetipo").eq("id", payload.project_id).execute()
```

Depois do bloco que salva a ingestion e loga (logo antes do `return` final de `ingest_commit`), adicionar:

```python
    arquetipo = project_resp.data[0].get("arquetipo") or "padrao"
    if arquetipo == "padrao":
        try:
            task_id = None
            match_task = _TASK_TAG_RE.search(payload.commit_message)
            if match_task:
                task_id = match_task.group(1)

            operacional_id = None
            if payload.author_email:
                op_resp = (
                    client.table("operacionais")
                    .select("id")
                    .eq("project_id", payload.project_id)
                    .eq("email", payload.author_email)
                    .execute()
                )
                if op_resp.data:
                    operacional_id = op_resp.data[0]["id"]

            qualidade_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_tokens=512, google_api_key=api_key)
            qualidade_structured = qualidade_llm.with_structured_output(AvaliacaoQualidadeCommit)
            avaliacao: AvaliacaoQualidadeCommit = await qualidade_structured.ainvoke([
                SystemMessage(content=_COMMIT_QUALIDADE_PROMPT),
                HumanMessage(content=user_content),
            ])
            client.table("commit_qualidade").insert({
                "commit_hash": payload.commit_hash,
                "task_id": task_id,
                "operacional_id": operacional_id,
                "projeto_id": payload.project_id,
                "nota": avaliacao.nota,
                "evidencia": avaliacao.evidencia,
            }).execute()
        except Exception as exc:
            print(f"[ingest_commit] Aviso: avaliacao de qualidade de commit falhou ({exc}) — continuando")

    return {
```

(O `return {...}` final já existente continua exatamente igual — só a inserção do bloco acima antes dele.)

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_commit_qualidade_pipeline.py -v`
Expected: PASS (4 testes)

- [ ] **Step 7: Rodar a suíte inteira**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS — mesmas 4 falhas pré-existentes, nenhuma nova.

- [ ] **Step 8: Commit**

```bash
git add docudata-backend/hooks/docudata_agent.py docudata-backend/routers/commit_ingest.py docudata-backend/models/schemas.py docudata-backend/tests/test_commit_qualidade_pipeline.py
git commit -m "feat(19-05): pipeline de qualidade de commit via IA, estendendo POST /ingest/commit"
```

---

### Task 6: `services/performance.py` — cálculo de ranking

**Files:**
- Create: `docudata-backend/services/performance.py`
- Test: `docudata-backend/tests/test_performance_ranking.py`

**Interfaces:**
- Consumes: `pontuacao_operacional_sprint` (com `qualidade_commit_media` da Task 3), `projects.arquetipo` (Task 4), `pesos_arquetipo` (Task 1).
- Produces: `listar_pessoas_ativas(client) -> list[dict]` e `calcular_ranking_pessoa(client, pessoa: dict, pesos_por_arquetipo: dict) -> dict` — consumidos pela Task 7 (`routers/performance.py`).

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para services/performance.py (Phase 19).

Cobre: identidade cross-projeto por e-mail, janelas por contagem (1/2/4),
agregação em duas camadas por dimensão com projetos assimétricos, arquétipo
da janela por contagem de linhas (empate por mais recente), janela parcial,
blend de Qualidade com e sem qualidade_commit_media, score final como soma
ponderada re-normalizada pelos pesos disponíveis.
"""
from unittest.mock import MagicMock

from services.performance import listar_pessoas_ativas, calcular_ranking_pessoa, JANELAS


_PESOS = {
    "padrao": {
        "arquetipo": "padrao", "peso_gerente": 0.35, "peso_entrega": 0.20,
        "peso_qualidade": 0.20, "peso_autonomia": 0.15, "peso_evolucao": 0.10,
        "peso_commit_qualidade": 0.50,
    },
    "consultoria_discovery": {
        "arquetipo": "consultoria_discovery", "peso_gerente": 0.35, "peso_entrega": 0.20,
        "peso_qualidade": 0.20, "peso_autonomia": 0.15, "peso_evolucao": 0.10,
        "peso_commit_qualidade": 0.50,
    },
}


def _mock_client(operacionais=None, pontuacao=None, projetos=None):
    operacionais = operacionais or []
    pontuacao = pontuacao or []
    projetos = projetos or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                q.gt = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = projetos
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _linha(sprint_fim, projeto_id="proj-1", **overrides):
    base = {
        "operacional_id": "op-1", "sprint_id": f"sprint-{sprint_fim}", "projeto_id": projeto_id,
        "sprint_fim": sprint_fim, "gerente_media": 5.0, "gerente_pergunta6": 5,
        "entrega_pontos_concluidos": 10, "entrega_pontos_alocados": 10,
        "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 2,
        "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
        "qualidade_commit_media": None,
    }
    base.update(overrides)
    return base


def test_listar_pessoas_ativas_agrupa_por_email():
    client = _mock_client(operacionais=[
        {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
        {"id": "op-2", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
        {"id": "op-3", "nome": "Bia", "email": None, "ativo": True},
    ])

    pessoas = listar_pessoas_ativas(client)

    ana = next(p for p in pessoas if p["email"] == "ana@citi.com")
    assert sorted(ana["operacional_ids"]) == ["op-1", "op-2"]
    bia = next(p for p in pessoas if p["nome"] == "Bia")
    assert bia["operacional_ids"] == ["op-3"]


def test_janela_sprint_usa_so_a_ultima_linha():
    linhas = [_linha("2026-09-05T00:00:00+00:00"), _linha("2026-09-04T00:00:00+00:00")]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert ranking["sprint"]["janela_parcial"] is False
    assert ranking["sprint"]["entrega"] == 100.0


def test_janela_parcial_quando_menos_linhas_que_o_tamanho():
    linhas = [_linha("2026-09-05T00:00:00+00:00")]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert ranking["quinzenal"]["janela_parcial"] is True
    assert ranking["mensal"]["janela_parcial"] is True


def test_agregacao_duas_camadas_com_dois_projetos_assimetricos():
    linhas = [
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
        _linha("2026-09-04T00:00:00+00:00", projeto_id="proj-2", entrega_pontos_concluidos=5, entrega_pontos_alocados=20),
    ]
    client = _mock_client(
        pontuacao=linhas,
        projetos=[{"id": "proj-1", "arquetipo": "padrao"}, {"id": "proj-2", "arquetipo": "padrao"}],
    )
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # proj-1: SPI=100, proj-2: SPI=25 -> média simples = 62.5 (não pooled-sum = 50.0)
    assert ranking["quinzenal"]["entrega"] == 62.5


def test_arquetipo_da_janela_por_contagem_com_empate_por_mais_recente():
    linhas = [
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-recente"),
        _linha("2026-09-04T00:00:00+00:00", projeto_id="proj-antigo"),
        _linha("2026-09-03T00:00:00+00:00", projeto_id="proj-antigo"),
        _linha("2026-09-02T00:00:00+00:00", projeto_id="proj-recente"),
    ]
    client = _mock_client(
        pontuacao=linhas,
        projetos=[
            {"id": "proj-recente", "arquetipo": "consultoria_discovery"},
            {"id": "proj-antigo", "arquetipo": "padrao"},
        ],
    )
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # 2 linhas cada -> empate -> desempate pela mais recente (proj-recente, 09-05)
    assert ranking["mensal"]["arquetipo_usado"] == "consultoria_discovery"


def test_qualidade_com_blend_de_commit():
    linhas = [_linha("2026-09-05T00:00:00+00:00", qualidade_reaberturas=0, qualidade_tasks_concluidas=2, qualidade_commit_media=10)]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # retrabalho = 100 (0 reaberturas), commit = 10*10=100 -> blend 0.5*100+0.5*100=100
    assert ranking["sprint"]["qualidade"] == 100.0


def test_qualidade_sem_commit_usa_so_retrabalho():
    linhas = [_linha("2026-09-05T00:00:00+00:00", qualidade_reaberturas=1, qualidade_tasks_concluidas=2, qualidade_commit_media=None)]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert ranking["sprint"]["qualidade"] == 50.0


def test_score_final_e_soma_ponderada():
    linhas = [_linha(
        "2026-09-05T00:00:00+00:00",
        gerente_media=5.0, gerente_pergunta6=5,
        entrega_pontos_concluidos=10, entrega_pontos_alocados=10,
        qualidade_reaberturas=0, qualidade_tasks_concluidas=2,
        autonomia_bloqueios_resolvidos_proprio=0, autonomia_bloqueios_totais=0,
    )]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # todas as dimensões = 100 -> score final = 100
    assert ranking["sprint"]["score_final"] == 100.0
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_performance_ranking.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.performance'`

- [ ] **Step 3: Implementar**

Criar `docudata-backend/services/performance.py`:

```python
"""Cálculo de ranking do Motor de Score (Phase 19).

Agrega a sequência pessoal de cada operacional em 3 janelas por contagem de
sprints (nunca calendário), com agregação em duas camadas por dimensão: por
projeto primeiro, depois média simples entre projetos — mesmo método de
services/pontuacao.py::calcular_spi_operacional. Uma pessoa pode ter mais de
uma linha `operacionais` (uma por projeto) — agrupadas aqui por e-mail.
"""

JANELAS = {"sprint": 1, "quinzenal": 2, "mensal": 4}


def listar_pessoas_ativas(client) -> list[dict]:
    """Agrupa operacionais ativos por e-mail — uma pessoa pode ter uma linha
    `operacionais` por projeto. Sem e-mail, cada linha vira sua própria pessoa
    (não dá pra casar identidade cross-projeto sem um identificador comum)."""
    rows = client.table("operacionais").select("id, nome, email, ativo").eq("ativo", True).execute().data or []
    por_chave: dict[str, dict] = {}
    for row in rows:
        chave = row.get("email") or row["id"]
        pessoa = por_chave.setdefault(chave, {"email": chave, "nome": row["nome"], "operacional_ids": []})
        pessoa["operacional_ids"].append(row["id"])
    return list(por_chave.values())


def _sequencia_pessoal(client, operacional_ids: list[str]) -> list[dict]:
    if not operacional_ids:
        return []
    return (
        client.table("pontuacao_operacional_sprint")
        .select("*")
        .in_("operacional_id", operacional_ids)
        .gt("entrega_pontos_alocados", 0)
        .order("sprint_fim", desc=True)
        .execute()
        .data or []
    )


def calcular_ranking_pessoa(client, pessoa: dict, pesos_por_arquetipo: dict[str, dict]) -> dict:
    """Calcula o score das 3 janelas pra uma pessoa. `pesos_por_arquetipo` é
    pré-carregado ({arquetipo: row de pesos_arquetipo}) — evita reconsultar
    a tabela pra cada pessoa do ranking."""
    sequencia = _sequencia_pessoal(client, pessoa["operacional_ids"])
    resultado: dict[str, dict | None] = {}
    for nome_janela, tamanho in JANELAS.items():
        linhas = sequencia[:tamanho]
        if not linhas:
            resultado[nome_janela] = None
            continue
        resultado[nome_janela] = _calcular_janela(client, linhas, tamanho, pesos_por_arquetipo)
    return resultado


def _calcular_janela(client, linhas: list[dict], tamanho_esperado: int, pesos_por_arquetipo: dict) -> dict:
    projeto_ids = list({l["projeto_id"] for l in linhas})
    arquetipos = _arquetipos_dos_projetos(client, projeto_ids)
    arquetipo_usado = _arquetipo_dominante(linhas, arquetipos)
    pesos = pesos_por_arquetipo.get(arquetipo_usado) or pesos_por_arquetipo["padrao"]

    por_projeto: dict[str, list[dict]] = {}
    for linha in linhas:
        por_projeto.setdefault(linha["projeto_id"], []).append(linha)

    sub_scores = {
        "entrega": _media_cross_projeto(por_projeto, _entrega_por_projeto),
        "gerente": _media_cross_projeto(por_projeto, _gerente_por_projeto),
        "evolucao": _media_cross_projeto(por_projeto, _evolucao_por_projeto),
        "autonomia": _media_cross_projeto(por_projeto, _autonomia_por_projeto),
        "qualidade": _media_cross_projeto(
            por_projeto,
            lambda ls: _qualidade_por_projeto(ls, float(pesos["peso_commit_qualidade"])),
        ),
    }

    return {
        **sub_scores,
        "score_final": _score_final(sub_scores, pesos),
        "janela_parcial": len(linhas) < tamanho_esperado,
        "arquetipo_usado": arquetipo_usado,
    }


def _media_cross_projeto(por_projeto: dict[str, list[dict]], calc_por_projeto) -> float | None:
    valores = [v for v in (calc_por_projeto(linhas) for linhas in por_projeto.values()) if v is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 2)


def _entrega_por_projeto(linhas: list[dict]) -> float | None:
    concluidos = sum(l["entrega_pontos_concluidos"] for l in linhas)
    alocados = sum(l["entrega_pontos_alocados"] for l in linhas)
    if alocados <= 0:
        return None
    return round(min(concluidos / alocados * 100, 100), 2)


def _gerente_por_projeto(linhas: list[dict]) -> float | None:
    valores = [l["gerente_media"] for l in linhas if l.get("gerente_media") is not None]
    if not valores:
        return None
    return round(min(sum(valores) / len(valores) * 20, 100), 2)


def _evolucao_por_projeto(linhas: list[dict]) -> float | None:
    valores = [l["gerente_pergunta6"] for l in linhas if l.get("gerente_pergunta6") is not None]
    if not valores:
        return None
    return round(min(sum(valores) / len(valores) * 20, 100), 2)


def _autonomia_por_projeto(linhas: list[dict]) -> float:
    resolvidos = sum(l["autonomia_bloqueios_resolvidos_proprio"] for l in linhas)
    totais = sum(l["autonomia_bloqueios_totais"] for l in linhas)
    if totais <= 0:
        return 100.0
    return round(resolvidos / totais * 100, 2)


def _qualidade_por_projeto(linhas: list[dict], peso_commit: float) -> float:
    reaberturas = sum(l["qualidade_reaberturas"] for l in linhas)
    tasks_concluidas = sum(l["qualidade_tasks_concluidas"] for l in linhas)
    retrabalho = 100.0 if tasks_concluidas <= 0 else round(max(1 - reaberturas / tasks_concluidas, 0) * 100, 2)

    notas_commit = [l["qualidade_commit_media"] for l in linhas if l.get("qualidade_commit_media") is not None]
    if not notas_commit:
        return retrabalho
    commit_score = min(sum(notas_commit) / len(notas_commit) * 10, 100)
    return round(peso_commit * commit_score + (1 - peso_commit) * retrabalho, 2)


def _arquetipos_dos_projetos(client, projeto_ids: list[str]) -> dict[str, str]:
    rows = client.table("projects").select("id, arquetipo").in_("id", projeto_ids).execute().data or []
    return {r["id"]: r.get("arquetipo") or "padrao" for r in rows}


def _arquetipo_dominante(linhas: list[dict], arquetipos: dict[str, str]) -> str:
    contagem: dict[str, int] = {}
    mais_recente: dict[str, str] = {}
    for linha in linhas:
        pid = linha["projeto_id"]
        contagem[pid] = contagem.get(pid, 0) + 1
        if pid not in mais_recente or linha["sprint_fim"] > mais_recente[pid]:
            mais_recente[pid] = linha["sprint_fim"]
    maior = max(contagem.values())
    empatados = [pid for pid, c in contagem.items() if c == maior]
    vencedor = max(empatados, key=lambda pid: mais_recente[pid])
    return arquetipos.get(vencedor, "padrao")


def _score_final(sub_scores: dict[str, float | None], pesos: dict) -> float | None:
    mapa_peso = {
        "entrega": float(pesos["peso_entrega"]),
        "gerente": float(pesos["peso_gerente"]),
        "qualidade": float(pesos["peso_qualidade"]),
        "autonomia": float(pesos["peso_autonomia"]),
        "evolucao": float(pesos["peso_evolucao"]),
    }
    disponiveis = {k: v for k, v in sub_scores.items() if v is not None}
    if not disponiveis:
        return None
    peso_disponivel = sum(mapa_peso[k] for k in disponiveis)
    if peso_disponivel <= 0:
        return None
    soma_ponderada = sum(mapa_peso[k] * v for k, v in disponiveis.items())
    return round(soma_ponderada / peso_disponivel, 2)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_performance_ranking.py -v`
Expected: PASS (8 testes)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/performance.py docudata-backend/tests/test_performance_ranking.py
git commit -m "feat(19-06): services/performance.py — cálculo de ranking em 3 janelas"
```

---

### Task 7: `GET /performance` real

**Files:**
- Modify: `docudata-backend/routers/performance.py`
- Modify: `docudata-backend/models/schemas.py` (novos `PerformanceOperacionalResponse`, `PerformanceResponse`)
- Test: `docudata-backend/tests/test_performance_endpoint.py`

**Interfaces:**
- Consumes: `listar_pessoas_ativas`, `calcular_ranking_pessoa` (Task 6).
- Produces: `GET /performance` retornando `PerformanceResponse` — consumido pela Task 9 (frontend).

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para GET /performance real (Phase 19, PERF-06).

RBAC: restrito a cargo=lider (já coberto por test_performance_stub.py pro
comportamento anterior — este arquivo cobre o corpo real da resposta).
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(pesos=None, operacionais=None, pontuacao=None, projetos=None):
    pesos = pesos if pesos is not None else [
        {"arquetipo": "padrao", "peso_gerente": 0.35, "peso_entrega": 0.20, "peso_qualidade": 0.20,
         "peso_autonomia": 0.15, "peso_evolucao": 0.10, "peso_commit_qualidade": 0.50},
        {"arquetipo": "consultoria_discovery", "peso_gerente": 0.35, "peso_entrega": 0.20, "peso_qualidade": 0.20,
         "peso_autonomia": 0.15, "peso_evolucao": 0.10, "peso_commit_qualidade": 0.50},
    ]
    operacionais = operacionais or []
    pontuacao = pontuacao or []
    projetos = projetos or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pesos_arquetipo":
            q = MagicMock()
            resp = MagicMock()
            resp.data = pesos
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_operacional_sprint":
            # Diferente do mock do Task 6 (onde só há um operacional nos dados
            # de teste, então "não filtrar" não vaza nada) — aqui há duas
            # pessoas (op-1 e op-2) na MESMA lista `pontuacao`, então o mock
            # PRECISA filtrar de verdade por `.in_(...)`, senão o ranking da
            # Ana vazaria as linhas da Bia (e vice-versa).
            def select_side_effect(cols):
                q = MagicMock()
                state = {"ids": None}

                def in_side_effect(field, values):
                    state["ids"] = set(values)
                    return q

                def execute_side_effect():
                    resp = MagicMock()
                    if state["ids"] is None:
                        resp.data = pontuacao
                    else:
                        resp.data = [p for p in pontuacao if p["operacional_id"] in state["ids"]]
                    return resp

                q.in_ = MagicMock(side_effect=in_side_effect)
                q.gt = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.execute = MagicMock(side_effect=execute_side_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = projetos
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _client_as(monkeypatch, mock_supabase, cargo):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.performance as performance_router
    monkeypatch.setattr(performance_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", cargo))
    return tc


_LINHA = {
    "operacional_id": "op-1", "sprint_id": "sprint-1", "projeto_id": "proj-1",
    "sprint_fim": "2026-09-05T00:00:00+00:00", "gerente_media": 5.0, "gerente_pergunta6": 5,
    "entrega_pontos_concluidos": 10, "entrega_pontos_alocados": 10,
    "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 2,
    "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
    "qualidade_commit_media": None,
}


def test_ranking_ordenado_por_score_desc(monkeypatch):
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
            {"id": "op-2", "nome": "Bia", "email": "bia@citi.com", "ativo": True},
        ],
        pontuacao=[
            dict(_LINHA, operacional_id="op-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
            dict(_LINHA, operacional_id="op-2", entrega_pontos_concluidos=2, entrega_pontos_alocados=10),
        ],
        projetos=[{"id": "proj-1", "arquetipo": "padrao"}],
    )
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/performance")

    assert resp.status_code == 200
    body = resp.json()
    assert [p["nome"] for p in body["sprint"]] == ["Ana", "Bia"]


def test_gerente_recebe_403(monkeypatch):
    client = _mock_client()
    tc = _client_as(monkeypatch, client, "gerente")

    resp = tc.get("/performance")

    assert resp.status_code == 403


def test_operacional_recebe_403(monkeypatch):
    client = _mock_client()
    tc = _client_as(monkeypatch, client, "operacional")

    resp = tc.get("/performance")

    assert resp.status_code == 403
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_performance_endpoint.py -v`
Expected: FAIL — resposta atual do stub não tem chave `"sprint"` (retorna `{"status": "ok", "message": "..."}`), `KeyError`/`AssertionError`.

- [ ] **Step 3: Implementar — `models/schemas.py`**

Adicionar ao final do arquivo:

```python
class PerformanceOperacionalResponse(BaseModel):
    email: str
    nome: str
    score_final: float
    entrega: Optional[float] = None
    gerente: Optional[float] = None
    qualidade: Optional[float] = None
    autonomia: Optional[float] = None
    evolucao: Optional[float] = None
    janela_parcial: bool
    arquetipo_usado: str


class PerformanceResponse(BaseModel):
    sprint: list[PerformanceOperacionalResponse] = []
    quinzenal: list[PerformanceOperacionalResponse] = []
    mensal: list[PerformanceOperacionalResponse] = []
```

- [ ] **Step 4: Implementar — `routers/performance.py`**

```python
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import PerformanceResponse
from services.audit import registrar_auditoria
from services.auth import get_current_pessoa, require_role
from services.performance import listar_pessoas_ativas, calcular_ranking_pessoa
from services.supabase_client import get_client

router = APIRouter(tags=["performance"])


@router.get("/performance", response_model=PerformanceResponse, dependencies=[Depends(require_role("lider"))])
async def performance(pessoa: dict = Depends(get_current_pessoa)):
    registrar_auditoria(pessoa, "/performance", "acesso")
    client = get_client()

    pesos_rows = client.table("pesos_arquetipo").select("*").execute().data or []
    pesos_por_arquetipo = {r["arquetipo"]: r for r in pesos_rows}
    if not pesos_por_arquetipo:
        raise HTTPException(status_code=500, detail="pesos_arquetipo não configurado")

    janelas: dict[str, list[dict]] = {"sprint": [], "quinzenal": [], "mensal": []}
    for pessoa_ranking in listar_pessoas_ativas(client):
        ranking = calcular_ranking_pessoa(client, pessoa_ranking, pesos_por_arquetipo)
        for nome_janela, dados in ranking.items():
            if dados is None or dados.get("score_final") is None:
                continue
            janelas[nome_janela].append({
                "email": pessoa_ranking["email"],
                "nome": pessoa_ranking["nome"],
                **dados,
            })

    for nome_janela in janelas:
        janelas[nome_janela].sort(key=lambda r: r["score_final"], reverse=True)

    return janelas
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_performance_endpoint.py -v`
Expected: PASS (3 testes)

- [ ] **Step 6: Rodar a suíte inteira**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS — mesmas 4 falhas pré-existentes, nenhuma nova. Confirmar também que `tests/test_performance_stub.py` (teste antigo do stub da Phase 16) ainda passa ou precisa de ajuste — se ele testava literalmente a mensagem `"Ranking ainda não implementado"`, esse teste específico precisa ser removido/atualizado nesta task (o comportamento antigo deixou de existir por design).

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/routers/performance.py docudata-backend/models/schemas.py docudata-backend/tests/test_performance_endpoint.py
git commit -m "feat(19-07): GET /performance real — ranking em 3 janelas"
```

---

### Task 8: Frontend — campo `arquetipo` no contrato do projeto

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`
- Modify: `docudata-frontend/app/components/PainelTab.tsx`

**Interfaces:**
- Consumes: `PATCH /projects/{id}/contrato` com `arquetipo` (Task 4).

- [ ] **Step 1: Implementar — `app/lib/api.ts`**

Adicionar `arquetipo` à interface `Project` (linha ~104, junto de `periodo_garantia_dias`):

```typescript
  periodo_garantia_dias?: number | null;
  arquetipo?: "padrao" | "consultoria_discovery";
```

Adicionar `arquetipo` aos parâmetros de `updateContrato` (linha ~298-306):

```typescript
export async function updateContrato(
  projectId: string,
  data: {
    data_inicio?: string | null;
    data_fim_contratada?: string | null;
    tolerancia_desvio_pontos?: number | null;
    periodo_garantia_dias?: number | null;
    arquetipo?: "padrao" | "consultoria_discovery";
  }
): Promise<Project> {
```

- [ ] **Step 2: Implementar — `app/components/PainelTab.tsx`**

Em `BlocoACard`, adicionar estado pro arquétipo (junto de `dataInicio`/`dataFim`/`tolerancia`, linha ~106):

```typescript
  const [arquetipo, setArquetipo] = useState<"padrao" | "consultoria_discovery">(project.arquetipo ?? "padrao");
```

Em `handleSave`, incluir no payload enviado:

```typescript
      const updated = await updateContrato(project.id, {
        data_inicio: dataInicio,
        data_fim_contratada: dataFim,
        tolerancia_desvio_pontos: tolerancia !== "" ? Number(tolerancia) : null,
        arquetipo,
      });
```

No formulário (dentro do bloco `{editing ? (...)}`), adicionar o campo antes do botão "Salvar" (depois do campo de tolerância):

```tsx
          <div>
            <label style={labelSmStyle}>Arquétipo do projeto</label>
            <select
              value={arquetipo}
              onChange={(e) => setArquetipo(e.target.value as "padrao" | "consultoria_discovery")}
              style={inputSmStyle}
            >
              <option value="padrao">Padrão</option>
              <option value="consultoria_discovery">Consultoria / Discovery</option>
            </select>
          </div>
```

- [ ] **Step 3: Verificar o typecheck**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros de TypeScript (o campo `arquetipo` novo bate com a interface `Project` atualizada no Step 1).

- [ ] **Step 4: Commit**

```bash
git add docudata-frontend/app/lib/api.ts docudata-frontend/app/components/PainelTab.tsx
git commit -m "feat(19-08): campo arquetipo no formulário de contrato do projeto (Bloco A)"
```

---

### Task 9: Frontend — tela `/performance`

**Files:**
- Create: `docudata-frontend/app/performance/page.tsx`
- Modify: `docudata-frontend/app/lib/api.ts` (tipos + `getPerformance`)
- Modify: `docudata-frontend/app/page.tsx` (link condicional pra líder)

**Interfaces:**
- Consumes: `GET /performance` (Task 7).

- [ ] **Step 1: Implementar — `app/lib/api.ts`**

Adicionar ao final do arquivo:

```typescript
export interface PerformanceOperacional {
  email: string;
  nome: string;
  score_final: number;
  entrega?: number | null;
  gerente?: number | null;
  qualidade?: number | null;
  autonomia?: number | null;
  evolucao?: number | null;
  janela_parcial: boolean;
  arquetipo_usado: string;
}

export interface PerformanceResponse {
  sprint: PerformanceOperacional[];
  quinzenal: PerformanceOperacional[];
  mensal: PerformanceOperacional[];
}

export async function getPerformance(): Promise<PerformanceResponse> {
  const res = await apiFetch(`${API}/performance`);
  if (!res.ok) throw new Error("Erro ao buscar ranking de performance");
  return res.json();
}
```

(`apiFetch` já é a função interna do arquivo, não exportada — usar exatamente como as demais funções do arquivo já fazem.)

- [ ] **Step 2: Implementar — `app/performance/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { getPerformance, type PerformanceResponse, type PerformanceOperacional } from "../lib/api";

const JANELA_LABEL: Record<string, string> = {
  sprint: "Última sprint",
  quinzenal: "Últimas 2 sprints",
  mensal: "Últimas 4 sprints",
};

const DIMENSAO_LABEL: Record<string, string> = {
  entrega: "Entrega",
  gerente: "Gerente",
  qualidade: "Qualidade",
  autonomia: "Autonomia",
  evolucao: "Evolução",
};

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "20px 24px",
  marginBottom: 20,
};

export default function PerformancePage() {
  const auth = useAuth();
  const [janela, setJanela] = useState<"sprint" | "quinzenal" | "mensal">("sprint");
  const [dados, setDados] = useState<PerformanceResponse | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!auth) return;
    getPerformance()
      .then(setDados)
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  if (auth && auth.cargo !== "lider") {
    return (
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
        <p style={{ color: "#dc2626" }}>Acesso restrito a Líder.</p>
      </main>
    );
  }

  const lista: PerformanceOperacional[] = dados ? dados[janela] : [];

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "52px 24px" }}>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#111116", marginBottom: 24 }}>Performance</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {(["sprint", "quinzenal", "mensal"] as const).map((j) => (
          <button
            key={j}
            onClick={() => setJanela(j)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: j === janela ? "2px solid #16a34a" : "1px solid #e8e8ed",
              background: j === janela ? "#f0fdf4" : "#fff",
              color: "#111116",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {JANELA_LABEL[j]}
          </button>
        ))}
      </div>

      {erro && <p style={{ color: "#dc2626" }}>{erro}</p>}

      {!dados && !erro && <p style={{ color: "#9696a0" }}>Carregando...</p>}

      {dados && lista.length === 0 && (
        <p style={{ color: "#9696a0" }}>Nenhum operacional com dado suficiente nesta janela.</p>
      )}

      {lista.map((op, i) => (
        <div key={op.email} style={card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: "#111116" }}>
              {i + 1}. {op.nome}
            </span>
            <span style={{ fontSize: 20, fontWeight: 800, color: "#16a34a" }}>{op.score_final}</span>
          </div>
          {op.janela_parcial && (
            <p style={{ fontSize: 12, color: "#d97706", marginBottom: 8 }}>Janela parcial — dado insuficiente ainda</p>
          )}
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {(["entrega", "gerente", "qualidade", "autonomia", "evolucao"] as const).map((dim) => (
              <div key={dim}>
                <p style={{ fontSize: 11, color: "#9696a0", textTransform: "uppercase", marginBottom: 2 }}>
                  {DIMENSAO_LABEL[dim]}
                </p>
                <p style={{ fontSize: 14, fontWeight: 600, color: "#111116" }}>{op[dim] ?? "—"}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </main>
  );
}
```

- [ ] **Step 3: Implementar — `app/page.tsx`**

Adicionar o import de `useAuth` (junto dos demais imports):

```typescript
import { useAuth } from "./components/AuthGuard";
```

Dentro do componente da página (antes do `return`), obter o auth:

```typescript
  const auth = useAuth();
```

No cabeçalho, junto do botão "+ Novo projeto" (linha ~105), adicionar o link condicional:

```tsx
          <div style={{ display: "flex", gap: 10 }}>
            {auth?.cargo === "lider" && (
              <Link href="/performance">
                <button style={{ ...btnPrimary, background: "#fff", color: "#111116", border: "1px solid #e8e8ed" }}>
                  Performance
                </button>
              </Link>
            )}
            <Link href="/projects/new">
              <button style={btnPrimary}>+ Novo projeto</button>
            </Link>
          </div>
```

(Isso substitui o `<Link href="/projects/new">...</Link>` que hoje é filho direto do container flex — envolvê-lo, junto do link novo, em uma `div` com `display: flex, gap: 10`.)

- [ ] **Step 4: Verificar o typecheck e o build**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros de TypeScript.

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/performance/page.tsx docudata-frontend/app/lib/api.ts docudata-frontend/app/page.tsx
git commit -m "feat(19-09): tela /performance — ranking por janela, breakdown por dimensão"
```

---

## Self-Review

**Cobertura da spec:**
- Correção `gerente_media` (7 respostas) → Task 2 ✅
- `qualidade_commit_media` no fechamento, mesmo `cutoff` das outras dimensões → Task 3 ✅
- `arquetipo` (2 valores) + `pesos_arquetipo` → Tasks 1, 4 ✅
- Pipeline de qualidade de commit via IA, estendendo `POST /ingest/commit`, só pra `padrao` → Task 5 ✅
- Correção descoberta no planejamento (`author` é nome, não e-mail — `author_email` adicionado) → Task 5 ✅
- Sequência pessoal cross-projeto por e-mail, janelas por contagem (1/2/4) → Task 6 (`listar_pessoas_ativas`) ✅
- Agregação em duas camadas por dimensão, replicando `calcular_spi_operacional` → Task 6 ✅
- Arquétipo da janela por contagem com empate por mais recente → Task 6 (`_arquetipo_dominante`) ✅
- Janela parcial sinalizada → Task 6 (`janela_parcial`) ✅
- `GET /performance` real, `require_role("lider")`, auditoria preservada → Task 7 ✅
- Sem botão de anúncio de top performer → nenhuma task implementa isso (descopado corretamente) ✅
- UI: campo arquétipo no contrato, tela `/performance` → Tasks 8, 9 ✅

**Placeholder scan:** nenhum "TBD"/"implementar depois" — todo código é completo e executável.

**Consistência de tipos:** `calcular_ranking_pessoa(client, pessoa: dict, pesos_por_arquetipo: dict[str, dict]) -> dict` (Task 6) é chamada exatamente assim em `routers/performance.py` (Task 7). `listar_pessoas_ativas(client) -> list[dict]` (Task 6) é iterada em `routers/performance.py` (Task 7) usando as chaves `email`/`nome`/`operacional_ids` que `Task 6` define. `PerformanceResponse`/`PerformanceOperacionalResponse` (Task 7) têm os mesmos nomes de campo que `_calcular_janela` produz (`entrega`, `gerente`, `qualidade`, `autonomia`, `evolucao`, `score_final`, `janela_parcial`, `arquetipo_usado`) mais `email`/`nome` adicionados no router. `qualidade_commit_media` (Task 3) é lido por `_qualidade_por_projeto` (Task 6) com o mesmo nome de campo. `AvaliacaoQualidadeCommit` (Task 5) tem `nota`/`evidencia` — mesmos nomes usados no insert em `commit_qualidade` (Task 5) e lidos por `_calcular_qualidade_commit` (Task 3, que roda ANTES da Task 5 na ordem do plano — mas ambas leem/escrevem a mesma tabela `commit_qualidade` criada na Task 1, então a ordem de implementação não quebra nada: a Task 3 simplesmente não terá dados reais até a Task 5 rodar em produção, o que é esperado e coberto pelos testes de cada task isoladamente com mocks).

---

**Plan complete and saved to `docs/superpowers/plans/2026-09-06-peso-arquetipo-performance.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
