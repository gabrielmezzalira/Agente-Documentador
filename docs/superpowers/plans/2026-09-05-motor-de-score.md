# Phase 18 — Motor de Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a linha travada `pontuacao_operacional_sprint` (dado bruto de score por operacional/sprint/projeto) e `baseline_evolucao`, calculadas de forma determinística no momento do fechamento de sprint, sem quebrar nenhum fluxo existente de Kanban/reabertura/bloqueio/avaliação.

**Architecture:** Um novo módulo `services/pontuacao.py` concentra toda a lógica de cálculo pura (recebe `client` + ids, devolve dicts/listas — sem HTTP, sem LLM). `routers/avaliacoes.py` chama esse módulo dentro de `POST /avaliacoes/{sprint_id}/confirmar` (Phase 17) pra calcular e travar as linhas no mesmo request que já bloqueia por avaliação pendente. `routers/tasks.py` ganha dois pontos de integração pequenos: gravar snapshot de `operacional_id` em toda transição, e rotear reabertura/bloqueio-resolvido pra um ledger quando a sprint de origem já fechou. Um router novo (`routers/pontuacao.py`) expõe leitura de SPI e o snapshot manual de baseline, ambos restritos a `cargo=lider`.

**Tech Stack:** FastAPI (Python) + Supabase PostgreSQL (supabase-py v2, sync). Sem LangGraph/Gemini nesta fase — cálculo 100% determinístico em Python.

**Spec:** `docs/superpowers/specs/2026-09-05-motor-de-score-design.md`

## Global Constraints

- Migrações em `docudata-backend/supabase_schema.sql` são idempotentes (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`) mas **não rodam sozinhas** — precisam ser aplicadas manualmente no dashboard do Supabase (memória do projeto).
- Endpoints de score/SPI são restritos a `cargo=lider` via `services.auth.require_role("lider")` — **nunca** `require_not_operacional` (que também deixa `gerente` passar). Decisão RBAC Phase 16, `.planning/intel/decisions.md` #4.
- Testes seguem o padrão já estabelecido no projeto: `pytest` + `unittest.mock.MagicMock` pra simular `client.table(...)`, `fastapi.testclient.TestClient` + `services.auth.criar_jwt(...)` pra endpoints HTTP. Cada arquivo de teste define seu próprio helper de mock local (o projeto não usa `conftest.py` compartilhado pra isso) — siga essa convenção, não introduza uma nova.
- Todo cálculo em `services/pontuacao.py` lê o estado final das tabelas no momento do fechamento — nunca mantém contador incremental.

---

### Task 1: Migração SQL — tabelas e coluna novas

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (apenda ao final)

**Interfaces:**
- Produces: colunas/tabelas `task_transicoes.operacional_id`, `pontuacao_operacional_sprint`, `baseline_evolucao`, `eventos_pontuacao_tardios` — consumidas por todas as tasks seguintes.

- [ ] **Step 1: Apendar a migração ao final de `supabase_schema.sql`**

```sql

-- ═══════════════════════════════════════════════════════════════
-- Phase 18: Motor de Score — Dado Bruto por Sprint + SPI do
-- Operacional + Baseline de Evolução (SCORE-01..05)
-- ═══════════════════════════════════════════════════════════════

-- Snapshot do operacional no momento de cada transição — permite saber
-- "quem estava com a task" em qualquer ponto do histórico, mesmo após
-- reatribuição posterior (necessário pro cálculo de entrega_pontos_concluidos).
ALTER TABLE task_transicoes ADD COLUMN IF NOT EXISTS operacional_id uuid REFERENCES operacionais(id);

CREATE TABLE IF NOT EXISTS pontuacao_operacional_sprint (
    id                                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id                          uuid        NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    sprint_id                               uuid        NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    projeto_id                              uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_fim                              timestamptz NOT NULL,
    gerente_media                           numeric(4,2),
    gerente_pergunta6                       int,
    entrega_pontos_concluidos               int         NOT NULL DEFAULT 0,
    entrega_pontos_alocados                 int         NOT NULL DEFAULT 0,
    qualidade_reaberturas                   int         NOT NULL DEFAULT 0,
    qualidade_tasks_concluidas              int         NOT NULL DEFAULT 0,
    autonomia_bloqueios_resolvidos_proprio  int         NOT NULL DEFAULT 0,
    autonomia_bloqueios_totais              int         NOT NULL DEFAULT 0,
    arquetipo                               text,
    finalizado_em                           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (operacional_id, sprint_id)
);
CREATE INDEX IF NOT EXISTS idx_pontuacao_operacional_sprint_sprint ON pontuacao_operacional_sprint(sprint_id);
CREATE INDEX IF NOT EXISTS idx_pontuacao_operacional_sprint_operacional ON pontuacao_operacional_sprint(operacional_id);

CREATE TABLE IF NOT EXISTS baseline_evolucao (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id  uuid        NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    ciclo           text        NOT NULL,
    data_snapshot   timestamptz NOT NULL DEFAULT now(),
    nota_inicial    numeric(5,2),
    observacoes     text
);

-- Ledger desacoplado para eventos de qualidade/autonomia ocorridos numa task
-- cujo sprint de origem já fechou (pontuacao_operacional_sprint travada).
-- Existe pra não precisar reatribuir task.sprint_id (usado por outras telas)
-- nem tratar bloqueio como histórico repetível (hoje é campo único na task).
CREATE TABLE IF NOT EXISTS eventos_pontuacao_tardios (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id  uuid        NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    sprint_id_alvo  uuid        NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    dimensao        text        NOT NULL CHECK (dimensao IN (
                        'qualidade_reaberturas',
                        'autonomia_bloqueios_totais',
                        'autonomia_bloqueios_resolvidos_proprio'
                    )),
    task_id         uuid        REFERENCES tasks(id),
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_eventos_pontuacao_tardios_sprint_alvo ON eventos_pontuacao_tardios(sprint_id_alvo);
```

- [ ] **Step 2: Commit**

```bash
git add docudata-backend/supabase_schema.sql
git commit -m "feat(18-01): migração SQL — pontuacao_operacional_sprint, baseline_evolucao, eventos_pontuacao_tardios"
```

Sem teste automatizado (é uma migração SQL — o projeto não roda migrações em CI, precisa ser aplicada manualmente no Supabase antes dos testes de integração real; os testes das tasks seguintes usam mocks e não dependem da migração ter sido aplicada de fato).

---

### Task 2: Snapshot de `operacional_id` em toda transição de task

**Files:**
- Modify: `docudata-backend/routers/tasks.py:26-58` (`_registrar_task_transicao`)
- Test: `docudata-backend/tests/test_task_transicao_operacional_snapshot.py`

**Interfaces:**
- Consumes: nenhuma interface nova — só adiciona um campo ao insert já existente.
- Produces: toda linha de `task_transicoes` passa a ter `operacional_id` = quem estava alocado na task **antes** da mudança que gerou a transição. Consumido pela Task 4 (`_resolver_quem_completou`).

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para o snapshot de operacional_id em task_transicoes (Phase 18).

O snapshot grava, em toda transição registrada, quem estava alocado na task
ANTES da mudança — necessário pro Motor de Score reconstruir "quem completou"
mesmo que a task tenha sido reatribuída depois.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data):
    client = MagicMock()
    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]
    updated_row = dict(task_data)

    calls = {"tasks_update": [], "task_transicoes_insert": []}

    def table_side_effect(table_name):
        tbl = MagicMock()

        if table_name == "tasks":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.execute = MagicMock(return_value=task_select_resp)
                return query

            def update_side_effect(updates):
                calls["tasks_update"].append(updates)
                query = MagicMock()

                def eq_then_execute(field, value):
                    exec_query = MagicMock()
                    merged = dict(updated_row)
                    merged.update(updates)
                    resp = MagicMock()
                    resp.data = [merged]
                    exec_query.execute = MagicMock(return_value=resp)
                    return exec_query

                query.eq = MagicMock(side_effect=eq_then_execute)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)

        elif table_name == "task_transicoes":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.order = MagicMock(return_value=query)
                query.limit = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            def insert_side_effect(payload):
                calls["task_transicoes_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id=f"transicao-{len(calls['task_transicoes_insert'])}")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        else:
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", "test@citi.com", "gerente"))
    return tc


_BASE_TASK = {
    "id": "task-1",
    "project_id": "proj-1",
    "titulo": "Fazer algo",
    "pontos": 2,
    "coluna_kanban": "planejado",
    "ordem": 0,
    "sprint_id": "sprint-1",
    "operacional_id": "op-1",
    "descricao": None,
    "bloqueado": False,
    "motivo_bloqueio": None,
    "checklist": [],
    "contador_reaberturas": 0,
    "created_at": "2026-01-01T00:00:00+00:00",
}


def test_transicao_de_coluna_grava_operacional_id_anterior(monkeypatch):
    task = dict(_BASE_TASK)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 200
    assert len(calls["task_transicoes_insert"]) == 1
    assert calls["task_transicoes_insert"][0]["operacional_id"] == "op-1"


def test_transicao_de_reatribuicao_grava_operacional_id_antigo_nao_o_novo(monkeypatch):
    task = dict(_BASE_TASK, operacional_id="op-antigo")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"operacional_id": "op-novo"})

    assert resp.status_code == 200
    transicao = next(t for t in calls["task_transicoes_insert"] if t["campo"] == "operacional_id")
    assert transicao["operacional_id"] == "op-antigo"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_task_transicao_operacional_snapshot.py -v`
Expected: FAIL — `assert calls["task_transicoes_insert"][0]["operacional_id"] == "op-1"` falha com `KeyError` ou `None == "op-1"` (campo ainda não gravado).

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/tasks.py`, dentro de `_registrar_task_transicao` (linha ~50), adicionar `"operacional_id"` ao dict passado pro `.insert(...)`:

```python
    resp = client.table("task_transicoes").insert({
        "task_id": task_id,
        "campo": campo,
        "de": str(task_atual.get(campo)) if task_atual.get(campo) is not None else None,
        "para": str(novo_valor) if novo_valor is not None else None,
        "autor": autor,
        "timestamp": agora.isoformat(),
        "motivo": motivo,
        "duracao_fase_anterior_segundos": duracao,
        "operacional_id": task_atual.get("operacional_id"),
    }).execute()
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_task_transicao_operacional_snapshot.py -v`
Expected: PASS (2 testes)

- [ ] **Step 5: Rodar a suíte inteira pra garantir que nada quebrou**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS — os testes existentes de `task_transicoes` (`test_task_reabertura.py`, `test_bloqueio_manual.py`, etc.) não fazem assert sobre ausência do campo `operacional_id`, então continuam passando com o campo extra no payload.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_task_transicao_operacional_snapshot.py
git commit -m "feat(18-02): snapshot de operacional_id em toda task_transicao"
```

---

### Task 3: `services/sprints.py` — `get_current_sprint_id`

**Files:**
- Modify: `docudata-backend/services/sprints.py`
- Test: `docudata-backend/tests/test_get_current_sprint_id.py`

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `get_current_sprint_id(client, project_id: str) -> str | None` — usado pela Task 5 (`services/pontuacao.py::rotear_evento_pos_fechamento`).

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para get_current_sprint_id (Phase 18) — mesma lógica de resolução
de GET /projects/{id}/current-sprint (routers/commit_ingest.py, Phase 4),
mas devolvendo o id (uuid) da sprint em vez do número. Mantida como
implementação paralela e não como import cruzado de um router: extrair pra
cá evita duplicar também o endpoint HTTP, e o router antigo não precisa mudar.
"""
from unittest.mock import MagicMock

from services.sprints import get_current_sprint_id


def _mock_client(sprints, ingestions):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = sprints
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "ingestions":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = ingestions
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_retorna_none_sem_nenhuma_sprint():
    client = _mock_client(sprints=[], ingestions=[])
    assert get_current_sprint_id(client, "proj-1") is None


def test_retorna_sprint_da_ultima_planning_ingestion():
    client = _mock_client(
        sprints=[{"id": "sprint-1", "numero": 1}, {"id": "sprint-2", "numero": 2}],
        ingestions=[{"sprint_number": 2, "created_at": "2026-09-01T00:00:00Z"}],
    )
    assert get_current_sprint_id(client, "proj-1") == "sprint-2"


def test_fallback_maior_numero_sem_planning():
    client = _mock_client(
        sprints=[{"id": "sprint-1", "numero": 1}, {"id": "sprint-3", "numero": 3}],
        ingestions=[],
    )
    assert get_current_sprint_id(client, "proj-1") == "sprint-3"


def test_ignora_planning_de_sprint_ja_deletada():
    client = _mock_client(
        sprints=[{"id": "sprint-1", "numero": 1}],
        ingestions=[{"sprint_number": 5, "created_at": "2026-09-01T00:00:00Z"}],
    )
    assert get_current_sprint_id(client, "proj-1") == "sprint-1"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_get_current_sprint_id.py -v`
Expected: FAIL com `ImportError: cannot import name 'get_current_sprint_id'`

- [ ] **Step 3: Implementar**

Em `docudata-backend/services/sprints.py`, adicionar ao final do arquivo:

```python
from typing import Optional


def get_current_sprint_id(client, project_id: str) -> Optional[str]:
    """Resolve o id (uuid) da sprint atual do projeto — mesma lógica de
    GET /projects/{id}/current-sprint (routers/commit_ingest.py), mas devolve
    o id em vez do número. Usado pelo Motor de Score (Phase 18) pra rotear
    eventos tardios (services/pontuacao.py)."""
    sprints_resp = client.table("sprints").select("id, numero").eq("project_id", project_id).execute()
    sprints_rows = sprints_resp.data or []
    if not sprints_rows:
        return None
    numero_para_id = {row["numero"]: row["id"] for row in sprints_rows}

    plannings = (
        client.table("ingestions")
        .select("sprint_number, created_at")
        .eq("project_id", project_id)
        .eq("tipo_documentacao", "planning")
        .order("created_at", desc=True)
        .execute()
    )
    for row in (plannings.data or []):
        if row["sprint_number"] in numero_para_id:
            return numero_para_id[row["sprint_number"]]

    maior_numero = max(numero_para_id)
    return numero_para_id[maior_numero]
```

Mover o `from typing import Optional` pro topo do arquivo (junto de outros imports), não repetir inline.

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_get_current_sprint_id.py -v`
Expected: PASS (4 testes)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/sprints.py docudata-backend/tests/test_get_current_sprint_id.py
git commit -m "feat(18-03): get_current_sprint_id em services/sprints.py"
```

---

### Task 4: `services/pontuacao.py` — motor de cálculo e fechamento

**Files:**
- Create: `docudata-backend/services/pontuacao.py`
- Test: `docudata-backend/tests/test_pontuacao_fechamento.py`

**Interfaces:**
- Consumes: nada de tasks anteriores diretamente (mocka as tabelas).
- Produces: `calcular_e_travar_pontuacao(client, sprint_id: str) -> list[dict]` — usado pela Task 5 (`rotear_evento_pos_fechamento`, no mesmo módulo) e pela Task 6 (`routers/avaliacoes.py`).

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para services/pontuacao.py::calcular_e_travar_pontuacao (Phase 18).

Cobre: cálculo básico de entrega/qualidade/autonomia/gerente, idempotência
(chamar duas vezes não duplica nem recalcula), e a mecânica de reatribuição
mid-sprint decidida no brainstorming ("transferência só do que falta": pontos
concluídos ficam com quem entregou, via snapshot em task_transicoes;
pontos ainda alocados seguem o operacional atual).
"""
from unittest.mock import MagicMock

from services.pontuacao import calcular_e_travar_pontuacao


def _mock_client(
    pontuacao_existente=None,
    sprint=None,
    tasks=None,
    task_transicoes=None,
    task_reaberturas=None,
    eventos_tardios=None,
    avaliacoes=None,
    insert_capture=None,
):
    pontuacao_existente = pontuacao_existente or []
    tasks = tasks or []
    task_transicoes = task_transicoes or []
    task_reaberturas = task_reaberturas or []
    eventos_tardios = eventos_tardios or []
    avaliacoes = avaliacoes or []
    insert_capture = insert_capture if insert_capture is not None else []

    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao_existente
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(row, id=f"pont-{i}") for i, row in enumerate(payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [sprint] if sprint else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = task_transicoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_reaberturas":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = task_reaberturas
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "eventos_pontuacao_tardios":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = eventos_tardios
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = avaliacoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_SPRINT = {"id": "sprint-1", "project_id": "proj-1"}
_AVALIACAO_OP1 = {
    "operacional_id": "op-1",
    "resposta_1": 5, "resposta_2": 4, "resposta_3": 3, "resposta_4": 4, "resposta_5": 5,
    "resposta_6": 2, "resposta_7": 3,
}


def test_calcula_entrega_qualidade_autonomia_gerente_para_task_simples(monkeypatch):
    insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{
            "id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida",
            "bloqueado_resolvido_por": "operacional", "bloqueado_resolvido_em": "2026-09-01T00:00:00Z",
        }],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_reaberturas=[{"operacional_id": "op-1"}],
        avaliacoes=[_AVALIACAO_OP1],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert len(resultado) == 1
    linha = resultado[0]
    assert linha["operacional_id"] == "op-1"
    assert linha["projeto_id"] == "proj-1"
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 5
    assert linha["qualidade_tasks_concluidas"] == 1
    assert linha["qualidade_reaberturas"] == 1
    assert linha["autonomia_bloqueios_totais"] == 1
    assert linha["autonomia_bloqueios_resolvidos_proprio"] == 1
    assert linha["gerente_media"] == round((5 + 4 + 3 + 4 + 5 + 3) / 6, 2)
    assert linha["gerente_pergunta6"] == 2
    assert linha["arquetipo"] is None
    assert len(insert_capture) == 1


def test_idempotente_nao_recalcula_se_ja_existir_linha(monkeypatch):
    existente = [{"id": "pont-1", "operacional_id": "op-1", "sprint_id": "sprint-1"}]
    client = _mock_client(pontuacao_existente=existente, sprint=_SPRINT)

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert resultado == existente
    # Não deve nem consultar "tasks" — a checagem de idempotência é a primeira coisa que roda.
    client.table.assert_any_call("pontuacao_operacional_sprint")


def test_reatribuicao_mid_sprint_pontos_concluidos_ficam_com_quem_entregou(monkeypatch):
    """Task foi concluída pelo op-A e só depois reatribuída pro op-B — os pontos
    concluídos ficam com op-A (quem entregou), não com op-B (quem está com a
    task agora)."""
    insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-B", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-A", "timestamp": "2026-09-01T00:00:00Z"}],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    por_operacional = {linha["operacional_id"]: linha for linha in resultado}
    assert por_operacional["op-A"]["entrega_pontos_concluidos"] == 8
    assert por_operacional["op-A"]["entrega_pontos_alocados"] == 8
    assert "op-B" not in por_operacional


def test_reatribuicao_mid_sprint_task_ainda_aberta_fica_com_operacional_atual(monkeypatch):
    """Task ainda não concluída, reatribuída de op-A pra op-B — os pontos
    alocados (ainda não entregues) seguem o operacional atual (op-B)."""
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-B", "pontos": 3, "coluna_kanban": "em_andamento"}],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    por_operacional = {linha["operacional_id"]: linha for linha in resultado}
    assert por_operacional["op-B"]["entrega_pontos_alocados"] == 3
    assert por_operacional["op-B"]["entrega_pontos_concluidos"] == 0
    assert "op-A" not in por_operacional


def test_eventos_tardios_somam_na_contagem_normal(monkeypatch):
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "em_andamento"}],
        eventos_tardios=[
            {"operacional_id": "op-1", "dimensao": "qualidade_reaberturas"},
            {"operacional_id": "op-1", "dimensao": "autonomia_bloqueios_totais"},
            {"operacional_id": "op-1", "dimensao": "autonomia_bloqueios_resolvidos_proprio"},
        ],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["qualidade_reaberturas"] == 1
    assert linha["autonomia_bloqueios_totais"] == 1
    assert linha["autonomia_bloqueios_resolvidos_proprio"] == 1


def test_sprint_inexistente_retorna_lista_vazia(monkeypatch):
    client = _mock_client(sprint=None)
    assert calcular_e_travar_pontuacao(client, "sprint-inexistente") == []


def test_sprint_sem_nenhuma_task_retorna_lista_vazia(monkeypatch):
    client = _mock_client(sprint=_SPRINT, tasks=[])
    assert calcular_e_travar_pontuacao(client, "sprint-1") == []
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_pontuacao_fechamento.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'services.pontuacao'`

- [ ] **Step 3: Implementar**

Criar `docudata-backend/services/pontuacao.py`:

```python
"""Motor de cálculo do Motor de Score (Phase 18).

Fecha pontuacao_operacional_sprint no momento em que o gerente confirma a
avaliação semanal (routers/avaliacoes.py::confirmar_avaliacao_semanal).

O cálculo é feito uma única vez, a partir do estado final de
tasks/task_transicoes/task_reaberturas/avaliacoes_gerente — não é um contador
incremental mantido ao longo da sprint. Por isso reatribuição mid-sprint não
precisa de tratamento especial: o cálculo simplesmente lê o estado atual (e o
histórico de transições, pra "quem completou") quando roda.
"""
from datetime import datetime, timezone


def calcular_e_travar_pontuacao(client, sprint_id: str) -> list[dict]:
    """Calcula e trava uma linha de pontuacao_operacional_sprint por operacional
    com task na sprint. Idempotente: se já existir alguma linha para esta
    sprint, retorna as existentes sem recalcular."""
    existentes = (
        client.table("pontuacao_operacional_sprint")
        .select("*")
        .eq("sprint_id", sprint_id)
        .execute()
        .data
    )
    if existentes:
        return existentes

    sprint_resp = client.table("sprints").select("id, project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        return []
    project_id = sprint_resp.data[0]["project_id"]

    tasks = (
        client.table("tasks")
        .select("id, operacional_id, pontos, coluna_kanban, bloqueado_resolvido_por, bloqueado_resolvido_em")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    if not tasks:
        return []

    task_ids_concluidas = [t["id"] for t in tasks if t.get("coluna_kanban") == "concluida"]
    quem_completou = _resolver_quem_completou(client, task_ids_concluidas)

    pontos_concluidos: dict[str, int] = {}
    pontos_alocados: dict[str, int] = {}
    tasks_concluidas: dict[str, int] = {}
    bloqueios_totais: dict[str, int] = {}
    bloqueios_proprio: dict[str, int] = {}

    for task in tasks:
        pontos = task.get("pontos") or 0
        if task.get("coluna_kanban") == "concluida":
            operacional_id = quem_completou.get(task["id"]) or task.get("operacional_id")
            if operacional_id:
                pontos_concluidos[operacional_id] = pontos_concluidos.get(operacional_id, 0) + pontos
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos
                tasks_concluidas[operacional_id] = tasks_concluidas.get(operacional_id, 0) + 1
        else:
            operacional_id = task.get("operacional_id")
            if operacional_id:
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos

        if task.get("bloqueado_resolvido_em") and task.get("operacional_id"):
            op = task["operacional_id"]
            bloqueios_totais[op] = bloqueios_totais.get(op, 0) + 1
            if task.get("bloqueado_resolvido_por") == "operacional":
                bloqueios_proprio[op] = bloqueios_proprio.get(op, 0) + 1

    reaberturas = _contar_reaberturas(client, [t["id"] for t in tasks])

    eventos_tardios = (
        client.table("eventos_pontuacao_tardios")
        .select("operacional_id, dimensao")
        .eq("sprint_id_alvo", sprint_id)
        .execute()
        .data or []
    )
    for evento in eventos_tardios:
        op = evento["operacional_id"]
        if evento["dimensao"] == "qualidade_reaberturas":
            reaberturas[op] = reaberturas.get(op, 0) + 1
        elif evento["dimensao"] == "autonomia_bloqueios_totais":
            bloqueios_totais[op] = bloqueios_totais.get(op, 0) + 1
        elif evento["dimensao"] == "autonomia_bloqueios_resolvidos_proprio":
            bloqueios_proprio[op] = bloqueios_proprio.get(op, 0) + 1

    avaliacoes = (
        client.table("avaliacoes_gerente")
        .select("operacional_id, resposta_1, resposta_2, resposta_3, resposta_4, resposta_5, resposta_6, resposta_7")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    avaliacao_por_operacional = {a["operacional_id"]: a for a in avaliacoes}

    operacional_ids = (
        set(pontos_alocados)
        | set(pontos_concluidos)
        | set(reaberturas)
        | set(bloqueios_totais)
        | set(avaliacao_por_operacional)
    )
    if not operacional_ids:
        return []

    agora = datetime.now(timezone.utc).isoformat()
    linhas = []
    for operacional_id in operacional_ids:
        aval = avaliacao_por_operacional.get(operacional_id)
        gerente_media = None
        gerente_pergunta6 = None
        if aval:
            notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_7"]]
            gerente_media = round(sum(notas) / len(notas), 2)
            gerente_pergunta6 = aval["resposta_6"]

        linhas.append({
            "operacional_id": operacional_id,
            "sprint_id": sprint_id,
            "projeto_id": project_id,
            "sprint_fim": agora,
            "gerente_media": gerente_media,
            "gerente_pergunta6": gerente_pergunta6,
            "entrega_pontos_concluidos": pontos_concluidos.get(operacional_id, 0),
            "entrega_pontos_alocados": pontos_alocados.get(operacional_id, 0),
            "qualidade_reaberturas": reaberturas.get(operacional_id, 0),
            "qualidade_tasks_concluidas": tasks_concluidas.get(operacional_id, 0),
            "autonomia_bloqueios_resolvidos_proprio": bloqueios_proprio.get(operacional_id, 0),
            "autonomia_bloqueios_totais": bloqueios_totais.get(operacional_id, 0),
            "arquetipo": None,
            "finalizado_em": agora,
        })

    resp = client.table("pontuacao_operacional_sprint").insert(linhas).execute()
    return resp.data or []


def _resolver_quem_completou(client, task_ids: list[str]) -> dict[str, str]:
    """Pra cada task_id concluída, acha quem estava alocado no momento da
    transição pra 'concluida' (via snapshot gravado por _registrar_task_transicao,
    Task 2). Se a task tiver sido concluída mais de uma vez (reabertura), pega
    a transição mais recente."""
    if not task_ids:
        return {}
    transicoes = (
        client.table("task_transicoes")
        .select("task_id, operacional_id, timestamp")
        .in_("task_id", task_ids)
        .eq("campo", "coluna_kanban")
        .eq("para", "concluida")
        .order("timestamp", desc=True)
        .execute()
        .data or []
    )
    resultado: dict[str, str] = {}
    for row in transicoes:
        if row["task_id"] not in resultado and row.get("operacional_id"):
            resultado[row["task_id"]] = row["operacional_id"]
    return resultado


def _contar_reaberturas(client, task_ids: list[str]) -> dict[str, int]:
    if not task_ids:
        return {}
    rows = (
        client.table("task_reaberturas")
        .select("operacional_id")
        .in_("task_id", task_ids)
        .execute()
        .data or []
    )
    contagem: dict[str, int] = {}
    for row in rows:
        op = row.get("operacional_id")
        if op:
            contagem[op] = contagem.get(op, 0) + 1
    return contagem
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS (7 testes)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "feat(18-04): motor de cálculo calcular_e_travar_pontuacao"
```

---

### Task 5: Roteamento de eventos pós-fechamento (reabertura/bloqueio tardios)

**Files:**
- Modify: `docudata-backend/services/pontuacao.py` (adiciona `rotear_evento_pos_fechamento`)
- Modify: `docudata-backend/routers/tasks.py` (chama a nova função em `patch_task`)
- Test: `docudata-backend/tests/test_evento_pontuacao_tardio.py`

**Interfaces:**
- Consumes: `get_current_sprint_id` (Task 3, `services/sprints.py`).
- Produces: `rotear_evento_pos_fechamento(client, task: dict, dimensao: str) -> None` em `services/pontuacao.py`, chamada por `routers/tasks.py::patch_task`.

**Nota importante:** os testes existentes que exercitam `patch_task` (`test_task_reabertura.py`, `test_bloqueio_manual.py`) **não precisam ser modificados**. O mock genérico desses arquivos (branch `else` no `table_side_effect`, que devolve `.data = []` pra qualquer tabela não listada explicitamente) já cobre a consulta nova a `pontuacao_operacional_sprint` — como ela vem vazia, `rotear_evento_pos_fechamento` retorna cedo (sprint de origem não travada = fluxo normal, nada a fazer), exatamente o comportamento correto pra esses testes (nenhum deles fecha sprint). Por isso este `Step` usa `.eq(...).execute()` sem `.limit(...)` — mantém a consulta compatível com o mock genérico já existente.

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Testes para services/pontuacao.py::rotear_evento_pos_fechamento (Phase 18).

Cobre a Pergunta 3 do brainstorming: reabertura/bloqueio resolvido numa task
cujo sprint de origem já fechou (pontuacao_operacional_sprint travada) é
roteado pra sprint ativa via get_current_sprint_id, através do ledger
eventos_pontuacao_tardios — sem tocar task.sprint_id.
"""
from unittest.mock import MagicMock

from services.pontuacao import rotear_evento_pos_fechamento


def _mock_client(sprint_origem_travada, sprint_ativa_id, sprint_ativa_travada, insert_capture):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "pontuacao_operacional_sprint":
            # Mesmo objeto `q` é reusado nas duas chamadas de rotear_evento_pos_fechamento
            # (checagem da sprint de origem, depois da sprint ativa) — `.eq(...)` grava
            # o valor recebido em `q._last_eq` pra `_resp` saber qual das duas responder.
            def _resp():
                if q._last_eq == "sprint-origem":
                    return MagicMock(data=[{"id": "pont-1"}] if sprint_origem_travada else [])
                return MagicMock(data=[{"id": "pont-2"}] if sprint_ativa_travada else [])

            def _eq_side_effect(field, value):
                q._last_eq = value
                return q

            q = MagicMock()
            q._last_eq = None
            q.eq = MagicMock(side_effect=_eq_side_effect)
            q.execute = MagicMock(side_effect=_resp)
            tbl.select = MagicMock(return_value=q)

        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": sprint_ativa_id, "numero": 2}] if sprint_ativa_id else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "ingestions":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "eventos_pontuacao_tardios":
            def insert_side_effect(payload):
                insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="evento-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK = {"id": "task-1", "project_id": "proj-1", "sprint_id": "sprint-origem", "operacional_id": "op-1"}


def test_sprint_origem_nao_travada_nao_faz_nada(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=False, sprint_ativa_id="sprint-ativa", sprint_ativa_travada=False, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "qualidade_reaberturas")

    assert insert_capture == []


def test_sprint_origem_travada_e_ativa_livre_grava_no_ledger(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=True, sprint_ativa_id="sprint-ativa", sprint_ativa_travada=False, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "qualidade_reaberturas")

    assert len(insert_capture) == 1
    assert insert_capture[0]["operacional_id"] == "op-1"
    assert insert_capture[0]["sprint_id_alvo"] == "sprint-ativa"
    assert insert_capture[0]["dimensao"] == "qualidade_reaberturas"
    assert insert_capture[0]["task_id"] == "task-1"


def test_sprint_origem_e_ativa_ambas_travadas_nao_grava_nada(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=True, sprint_ativa_id="sprint-ativa", sprint_ativa_travada=True, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "autonomia_bloqueios_totais")

    assert insert_capture == []


def test_sem_sprint_ativa_nao_grava_nada(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=True, sprint_ativa_id=None, sprint_ativa_travada=False, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "qualidade_reaberturas")

    assert insert_capture == []
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_evento_pontuacao_tardio.py -v`
Expected: FAIL com `ImportError: cannot import name 'rotear_evento_pos_fechamento'`

- [ ] **Step 3: Implementar — adicionar em `services/pontuacao.py`**

Adicionar ao topo do arquivo `from services.sprints import get_current_sprint_id`, e ao final:

```python
def rotear_evento_pos_fechamento(client, task: dict, dimensao: str) -> None:
    """Se a sprint de origem da task já tiver pontuacao_operacional_sprint
    travada, redireciona o evento de qualidade/autonomia pra sprint ativa do
    projeto (via ledger eventos_pontuacao_tardios) em vez de descartá-lo.

    Sem efeito se a sprint de origem ainda não fechou (fluxo normal — o
    evento será capturado no próprio fechamento dessa sprint) ou se a sprint
    ativa também já estiver travada (evento fica só no histórico de
    task_transicoes/task_reaberturas, sem afetar nenhuma pontuação)."""
    sprint_id_origem = task.get("sprint_id")
    if not sprint_id_origem:
        return

    travada = (
        client.table("pontuacao_operacional_sprint")
        .select("id")
        .eq("sprint_id", sprint_id_origem)
        .execute()
        .data
    )
    if not travada:
        return

    sprint_ativa_id = get_current_sprint_id(client, task["project_id"])
    if not sprint_ativa_id:
        return

    sprint_ativa_travada = (
        client.table("pontuacao_operacional_sprint")
        .select("id")
        .eq("sprint_id", sprint_ativa_id)
        .execute()
        .data
    )
    if sprint_ativa_travada:
        return

    operacional_id = task.get("operacional_id")
    if not operacional_id:
        return

    client.table("eventos_pontuacao_tardios").insert({
        "operacional_id": operacional_id,
        "sprint_id_alvo": sprint_ativa_id,
        "dimensao": dimensao,
        "task_id": task.get("id"),
    }).execute()
```

- [ ] **Step 4: Implementar — chamar em `routers/tasks.py::patch_task`**

Adicionar o import no topo do arquivo:

```python
from services.pontuacao import rotear_evento_pos_fechamento
```

Localizar (por volta da linha 340) a variável `houve_reabertura = False` (já existe, inicializada antes do loop de campos monitorados) e adicionar ao lado uma flag nova:

```python
    houve_reabertura = False
    houve_bloqueio_resolvido = False
```

No bloco que já trata `bloqueado_manual` (por volta da linha 400), marcar a flag no `else` (ramo de "desmarcar", ou seja, bloqueio resolvido):

```python
    if data.bloqueado_manual is not None and data.bloqueado_manual != task.get("bloqueado_manual", False):
        updates["bloqueado_manual"] = data.bloqueado_manual
        if data.bloqueado_manual is True:
            updates["bloqueado_em"] = agora.isoformat()
            updates["bloqueado_por"] = data.bloqueado_por
        else:
            updates["bloqueado_resolvido_por"] = data.bloqueado_resolvido_por
            updates["bloqueado_resolvido_em"] = agora.isoformat()
            houve_bloqueio_resolvido = True
```

Logo depois de `result = client.table("tasks").update(updates).eq("id", task_id).execute()`, adicionar:

```python
    if houve_reabertura:
        rotear_evento_pos_fechamento(client, task, "qualidade_reaberturas")
    if houve_bloqueio_resolvido:
        rotear_evento_pos_fechamento(client, task, "autonomia_bloqueios_totais")
        if data.bloqueado_resolvido_por == "operacional":
            rotear_evento_pos_fechamento(client, task, "autonomia_bloqueios_resolvidos_proprio")
```

(Usa `task`, o dict original buscado no início da função — reflete o `operacional_id`/`sprint_id` vigentes no momento do evento, antes desta mesma atualização.)

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_evento_pontuacao_tardio.py -v`
Expected: PASS (4 testes)

- [ ] **Step 6: Rodar a suíte inteira pra garantir que nada quebrou**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS — em especial `test_task_reabertura.py` e `test_bloqueio_manual.py` continuam passando sem modificação (ver nota acima).

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/routers/tasks.py docudata-backend/tests/test_evento_pontuacao_tardio.py
git commit -m "feat(18-05): roteamento de reabertura/bloqueio pós-fechamento pro ledger de eventos tardios"
```

---

### Task 6: Ligar o fechamento ao `POST /avaliacoes/{sprint_id}/confirmar`

**Files:**
- Modify: `docudata-backend/models/schemas.py` (novo `PontuacaoOperacionalSprintResponse`, estende `ConfirmarAvaliacaoResponse`)
- Modify: `docudata-backend/routers/avaliacoes.py`
- Modify: `docudata-backend/tests/test_avaliacao_semanal_confirmar.py` (helper `_patch_and_client` ganha parâmetro novo)

**Interfaces:**
- Consumes: `calcular_e_travar_pontuacao` (Task 4, `services/pontuacao.py`).
- Produces: `ConfirmarAvaliacaoResponse.pontuacao_operacional_sprint: list[PontuacaoOperacionalSprintResponse]` — campo novo na resposta do endpoint, consumido só pelo cliente HTTP (nenhuma task depende disso).

**Nota de design do teste:** este teste verifica a *ligação* (wiring) entre o endpoint e o motor de cálculo — não recalcula o algoritmo inteiro de novo (isso já está coberto, com todos os casos de borda, pela Task 4). Por isso `calcular_e_travar_pontuacao` é substituído por um stub via `monkeypatch` neste arquivo, evitando remontar mocks de 5 tabelas só pra testar que o valor retornado aparece na resposta.

- [ ] **Step 1: Escrever o teste que falha**

Editar `docudata-backend/tests/test_avaliacao_semanal_confirmar.py` — trocar a definição de `_patch_and_client` por:

```python
def _patch_and_client(monkeypatch, mock_supabase, pontuacao_stub=None):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: mock_supabase)
    monkeypatch.setattr(
        avaliacoes_router,
        "calcular_e_travar_pontuacao",
        lambda client, sprint_id: pontuacao_stub if pontuacao_stub is not None else [],
    )
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")
    tc.cookies.set("docudata_session", token)
    return tc
```

(Os dois testes existentes continuam chamando `_patch_and_client(monkeypatch, mock_sb)` sem o parâmetro novo — `pontuacao_stub=None` faz o stub devolver `[]`, então continuam passando sem nenhuma outra mudança.)

Adicionar ao final do arquivo:

```python
def test_confirma_inclui_pontuacao_calculada_no_response(monkeypatch):
    mock_sb, calls = _mock_client(
        tasks=[{"operacional_id": "op-1"}],
        operacionais=[{"id": "op-1", "nome": "Ana", "email": None, "project_id": "proj-1"}],
        avaliacoes=[{"operacional_id": "op-1", "sprint_id": "sprint-1"}],
    )
    linha_calculada = {
        "id": "pont-1", "operacional_id": "op-1", "sprint_id": "sprint-1", "projeto_id": "proj-1",
        "sprint_fim": "2026-09-05T00:00:00+00:00", "gerente_media": 3.0, "gerente_pergunta6": 3,
        "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 5,
        "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 2,
        "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
        "arquetipo": None, "finalizado_em": "2026-09-05T00:00:00+00:00",
    }
    tc = _patch_and_client(monkeypatch, mock_sb, pontuacao_stub=[linha_calculada])

    resp = tc.post("/avaliacoes/sprint-1/confirmar")

    assert resp.status_code == 200
    body = resp.json()
    assert body["pontuacao_operacional_sprint"][0]["operacional_id"] == "op-1"
    assert body["pontuacao_operacional_sprint"][0]["entrega_pontos_concluidos"] == 5
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_avaliacao_semanal_confirmar.py -v`
Expected: FAIL — `AttributeError: <module 'routers.avaliacoes'> does not have the attribute 'calcular_e_travar_pontuacao'` (monkeypatch falha porque o símbolo ainda não existe no módulo).

- [ ] **Step 3: Implementar — `models/schemas.py`**

Localizar `class ConfirmarAvaliacaoResponse` (final do arquivo) e substituir por:

```python
class PontuacaoOperacionalSprintResponse(BaseModel):
    id: str
    operacional_id: str
    sprint_id: str
    projeto_id: str
    sprint_fim: datetime
    gerente_media: Optional[float] = None
    gerente_pergunta6: Optional[int] = None
    entrega_pontos_concluidos: int
    entrega_pontos_alocados: int
    qualidade_reaberturas: int
    qualidade_tasks_concluidas: int
    autonomia_bloqueios_resolvidos_proprio: int
    autonomia_bloqueios_totais: int
    arquetipo: Optional[str] = None
    finalizado_em: datetime


class ConfirmarAvaliacaoResponse(BaseModel):
    sprint_id: str
    avaliacao_completa_em: datetime
    pontuacao_operacional_sprint: list[PontuacaoOperacionalSprintResponse] = []
```

- [ ] **Step 4: Implementar — `routers/avaliacoes.py`**

Adicionar o import (junto dos demais imports de `services`):

```python
from services.pontuacao import calcular_e_travar_pontuacao
```

Substituir o corpo de `confirmar_avaliacao_semanal`:

```python
@router.post("/{sprint_id}/confirmar", response_model=ConfirmarAvaliacaoResponse)
async def confirmar_avaliacao_semanal(sprint_id: str):
    client = get_client()
    pendencias = await listar_pendencias(sprint_id)
    if pendencias:
        nomes = ", ".join(p["nome"] for p in pendencias)
        raise HTTPException(status_code=409, detail=f"Ainda há avaliações pendentes: {nomes}")

    pontuacoes = calcular_e_travar_pontuacao(client, sprint_id)

    agora_iso = datetime.now(timezone.utc).isoformat()
    resp = client.table("sprints").update({"avaliacao_completa_em": agora_iso}).eq("id", sprint_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return {
        "sprint_id": sprint_id,
        "avaliacao_completa_em": resp.data[0]["avaliacao_completa_em"],
        "pontuacao_operacional_sprint": pontuacoes,
    }
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_avaliacao_semanal_confirmar.py -v`
Expected: PASS (3 testes — os 2 existentes + o novo)

- [ ] **Step 6: Rodar a suíte inteira**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/routers/avaliacoes.py docudata-backend/tests/test_avaliacao_semanal_confirmar.py
git commit -m "feat(18-06): confirmar avaliação semanal calcula e trava pontuacao_operacional_sprint"
```

---

### Task 7: `GET /operacionais/{id}/spi` e `POST /baseline-evolucao`

**Files:**
- Modify: `docudata-backend/services/pontuacao.py` (adiciona `calcular_spi_operacional`)
- Modify: `docudata-backend/models/schemas.py` (novos: `BaselineEvolucaoCreate`, `BaselineEvolucaoResponse`, `SpiPorProjetoResponse`, `SpiOperacionalResponse`)
- Create: `docudata-backend/routers/pontuacao.py`
- Modify: `docudata-backend/main.py` (registra o router novo)
- Test: `docudata-backend/tests/test_spi_operacional.py`
- Test: `docudata-backend/tests/test_baseline_evolucao.py`

**Interfaces:**
- Consumes: nenhuma task anterior diretamente além da tabela `pontuacao_operacional_sprint` (Task 1).
- Produces: `GET /operacionais/{id}/spi`, `POST /baseline-evolucao` — endpoints terminais, nada depende deles.

- [ ] **Step 1: Escrever os testes que falham**

`docudata-backend/tests/test_spi_operacional.py`:

```python
"""Testes para GET /operacionais/{id}/spi (Phase 18, SCORE-04).

RBAC: restrito a cargo=lider — nem gerente nem operacional podem ler score
(decisão RBAC Phase 16, .planning/intel/decisions.md #4).
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(linhas):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = linhas
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _client_as(monkeypatch, mock_supabase, cargo):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.pontuacao as pontuacao_router
    monkeypatch.setattr(pontuacao_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", cargo))
    return tc


def test_spi_de_um_projeto_e_o_spi_daquele_projeto(monkeypatch):
    client = _mock_client([
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 8, "entrega_pontos_alocados": 10},
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 2, "entrega_pontos_alocados": 5},
    ])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    body = resp.json()
    assert body["spi"] == round(10 / 15 * 100, 2)
    assert len(body["por_projeto"]) == 1


def test_spi_de_dois_projetos_e_media_simples_entre_projetos(monkeypatch):
    client = _mock_client([
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 10, "entrega_pontos_alocados": 10},
        {"projeto_id": "proj-2", "entrega_pontos_concluidos": 0, "entrega_pontos_alocados": 10},
    ])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    assert resp.json()["spi"] == 50.0


def test_sem_nenhuma_linha_spi_e_none(monkeypatch):
    client = _mock_client([])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    assert resp.json()["spi"] is None
    assert resp.json()["por_projeto"] == []


def test_gerente_recebe_403(monkeypatch):
    client = _mock_client([])
    tc = _client_as(monkeypatch, client, "gerente")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 403


def test_operacional_recebe_403(monkeypatch):
    client = _mock_client([])
    tc = _client_as(monkeypatch, client, "operacional")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 403
```

`docudata-backend/tests/test_baseline_evolucao.py`:

```python
"""Testes para POST /baseline-evolucao (Phase 18, SCORE-05).

Ciclo é texto livre informado pelo Líder no momento do snapshot manual (sem
calendário fixo — decisão do brainstorming). nota_inicial = SPI calculado
on-the-fly no momento do request.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(operacional_existe=True, pontuacao_linhas=None, insert_capture=None):
    pontuacao_linhas = pontuacao_linhas or []
    insert_capture = insert_capture if insert_capture is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "op-1"}] if operacional_existe else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao_linhas
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "baseline_evolucao":
            def insert_side_effect(payload):
                insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="baseline-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, insert_capture


def _client_as(monkeypatch, mock_supabase, cargo):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.pontuacao as pontuacao_router
    monkeypatch.setattr(pontuacao_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", cargo))
    return tc


def test_lider_cria_baseline_com_nota_inicial_calculada(monkeypatch):
    mock_sb, insert_capture = _mock_client(
        pontuacao_linhas=[{"projeto_id": "proj-1", "entrega_pontos_concluidos": 9, "entrega_pontos_alocados": 10}],
    )
    tc = _client_as(monkeypatch, mock_sb, "lider")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-1", "ciclo": "2026-S2"})

    assert resp.status_code == 201
    assert insert_capture[0]["ciclo"] == "2026-S2"
    assert insert_capture[0]["nota_inicial"] == 90.0
    assert resp.json()["nota_inicial"] == 90.0


def test_operacional_inexistente_retorna_404(monkeypatch):
    mock_sb, insert_capture = _mock_client(operacional_existe=False)
    tc = _client_as(monkeypatch, mock_sb, "lider")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-inexistente", "ciclo": "2026-S2"})

    assert resp.status_code == 404
    assert insert_capture == []


def test_gerente_recebe_403(monkeypatch):
    mock_sb, _ = _mock_client()
    tc = _client_as(monkeypatch, mock_sb, "gerente")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-1", "ciclo": "2026-S2"})

    assert resp.status_code == 403
```

- [ ] **Step 2: Rodar e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_spi_operacional.py tests/test_baseline_evolucao.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'routers.pontuacao'`

- [ ] **Step 3: Implementar — `services/pontuacao.py`**

Adicionar ao final do arquivo:

```python
def calcular_spi_operacional(client, operacional_id: str) -> dict:
    """SPI em duas camadas: soma dentro de cada projeto, depois média simples
    entre projetos se o operacional atuou em mais de um. Teto 100."""
    linhas = (
        client.table("pontuacao_operacional_sprint")
        .select("projeto_id, entrega_pontos_concluidos, entrega_pontos_alocados")
        .eq("operacional_id", operacional_id)
        .execute()
        .data or []
    )

    por_projeto_raw: dict[str, dict] = {}
    for linha in linhas:
        acumulado = por_projeto_raw.setdefault(linha["projeto_id"], {"concluidos": 0, "alocados": 0})
        acumulado["concluidos"] += linha["entrega_pontos_concluidos"]
        acumulado["alocados"] += linha["entrega_pontos_alocados"]

    por_projeto = []
    for projeto_id, soma in por_projeto_raw.items():
        spi_projeto = None
        if soma["alocados"] > 0:
            spi_projeto = round(min(soma["concluidos"] / soma["alocados"] * 100, 100), 2)
        por_projeto.append({"projeto_id": projeto_id, "spi": spi_projeto})

    validos = [p["spi"] for p in por_projeto if p["spi"] is not None]
    spi_operacional = round(sum(validos) / len(validos), 2) if validos else None

    return {"operacional_id": operacional_id, "spi": spi_operacional, "por_projeto": por_projeto}
```

- [ ] **Step 4: Implementar — `models/schemas.py`**

Adicionar ao final do arquivo:

```python
class BaselineEvolucaoCreate(BaseModel):
    operacional_id: str
    ciclo: str
    observacoes: Optional[str] = None


class BaselineEvolucaoResponse(BaseModel):
    id: str
    operacional_id: str
    ciclo: str
    data_snapshot: datetime
    nota_inicial: Optional[float] = None
    observacoes: Optional[str] = None


class SpiPorProjetoResponse(BaseModel):
    projeto_id: str
    spi: Optional[float] = None


class SpiOperacionalResponse(BaseModel):
    operacional_id: str
    spi: Optional[float] = None
    por_projeto: list[SpiPorProjetoResponse] = []
```

- [ ] **Step 5: Implementar — `routers/pontuacao.py`**

```python
"""Router do Motor de Score (Phase 18): SPI do operacional e baseline de
evolução. Acesso restrito a cargo=lider (RBAC Phase 16,
.planning/intel/decisions.md #4) — nenhum payload de score/SPI é exposto a
Gerente ou Operacional."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    BaselineEvolucaoCreate,
    BaselineEvolucaoResponse,
    SpiOperacionalResponse,
)
from services.auth import require_role
from services.pontuacao import calcular_spi_operacional
from services.supabase_client import get_client

router = APIRouter(tags=["pontuacao"])


@router.get(
    "/operacionais/{operacional_id}/spi",
    response_model=SpiOperacionalResponse,
    dependencies=[Depends(require_role("lider"))],
)
async def get_spi_operacional(operacional_id: str):
    client = get_client()
    return calcular_spi_operacional(client, operacional_id)


@router.post(
    "/baseline-evolucao",
    response_model=BaselineEvolucaoResponse,
    status_code=201,
    dependencies=[Depends(require_role("lider"))],
)
async def criar_baseline_evolucao(data: BaselineEvolucaoCreate):
    client = get_client()
    op_check = client.table("operacionais").select("id").eq("id", data.operacional_id).execute()
    if not op_check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    spi = calcular_spi_operacional(client, data.operacional_id)
    payload = {
        "operacional_id": data.operacional_id,
        "ciclo": data.ciclo,
        "data_snapshot": datetime.now(timezone.utc).isoformat(),
        "nota_inicial": spi["spi"],
        "observacoes": data.observacoes,
    }
    resp = client.table("baseline_evolucao").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar baseline")
    return resp.data[0]
```

- [ ] **Step 6: Registrar o router em `main.py`**

Adicionar o import junto dos demais routers:

```python
from routers import pontuacao
```

Adicionar o registro junto dos demais `include_router` (após `avaliacoes.router`):

```python
app.include_router(pontuacao.router, dependencies=[Depends(get_current_pessoa)])
```

(Autenticação simples no nível do router — a restrição a `cargo=lider` já está em cada rota individualmente via `require_role("lider")`, mesmo padrão de `sprints.router`.)

- [ ] **Step 7: Rodar e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/pytest tests/test_spi_operacional.py tests/test_baseline_evolucao.py -v`
Expected: PASS (8 testes)

- [ ] **Step 8: Rodar a suíte inteira**

Run: `cd docudata-backend && .venv/bin/pytest tests/ -v`
Expected: PASS — todos os testes, incluindo os das Tasks 1-6.

- [ ] **Step 9: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/models/schemas.py docudata-backend/routers/pontuacao.py docudata-backend/main.py docudata-backend/tests/test_spi_operacional.py docudata-backend/tests/test_baseline_evolucao.py
git commit -m "feat(18-07): GET /operacionais/{id}/spi e POST /baseline-evolucao"
```

---

## Self-Review

**Cobertura da spec:**
- Trigger de fechamento (extensão do confirmar) → Task 6 ✅
- Recálculo mid-sprint ("transferência só do que falta") → Task 4, testado explicitamente ✅
- Snapshot de `operacional_id` em `task_transicoes` → Task 2 ✅
- Ledger `eventos_pontuacao_tardios` + roteamento via `current-sprint` → Tasks 3 e 5 ✅
- `baseline_evolucao` manual (ciclo texto livre, `require_role("lider")`) → Task 7 ✅
- `GET /operacionais/{id}/spi` (duas camadas, teto 100, `require_role("lider")`) → Task 7 ✅
- Migração SQL completa (4 objetos novos) → Task 1 ✅
- Idempotência do fechamento → testada em Task 4 ✅
- `arquetipo` fica `null` nesta phase (fora de escopo, documentado na spec) → refletido em `calcular_e_travar_pontuacao` (`"arquetipo": None`) ✅

**Placeholder scan:** nenhum "TBD"/"implementar depois" — todo código é completo e executável, todo teste tem asserts concretos.

**Consistência de tipos:** `calcular_e_travar_pontuacao(client, sprint_id: str) -> list[dict]` (Task 4) é chamada exatamente assim em `routers/avaliacoes.py` (Task 6) e monkeypatchada com a mesma assinatura `lambda client, sprint_id: ...` no teste. `rotear_evento_pos_fechamento(client, task: dict, dimensao: str) -> None` (Task 5) é chamada com esses 3 argumentos posicionais em `routers/tasks.py`. `get_current_sprint_id(client, project_id: str) -> Optional[str]` (Task 3) é importada e usada com essa assinatura dentro de `rotear_evento_pos_fechamento` (Task 5). Nomes de dimensão (`"qualidade_reaberturas"`, `"autonomia_bloqueios_totais"`, `"autonomia_bloqueios_resolvidos_proprio"`) são idênticos entre a `CHECK` constraint da migração (Task 1), `rotear_evento_pos_fechamento` (Task 5) e a leitura do ledger em `calcular_e_travar_pontuacao` (Task 4).

---

**Plan complete and saved to `docs/superpowers/plans/2026-09-05-motor-de-score.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
