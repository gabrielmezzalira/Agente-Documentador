# Entrega "sem dado" em vez de 0 — Dependência do cliente e sprint PULL vazia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A dimensão Entrega nunca vira 0 quando não havia o que entregar: task travada por dependência do cliente sai da conta no fechamento, e sprint PULL sem nada pra puxar fica "sem dado" em vez de 0 — com correção retroativa via SQL manual.

**Architecture:** O bloqueio manual existente (`tasks.bloqueado_manual`) ganha um tipo (`tasks.bloqueio_tipo`: `interno` | `cliente`). O fechamento (`services/pontuacao.py::calcular_e_travar_pontuacao`) ignora tasks ainda bloqueadas por cliente ao somar pontos alocados e ao montar a média do PULL. `services/performance.py` já devolve Entrega `None` quando `alocados == 0` e `_score_final` já renormaliza — nada muda lá. Bloqueio de cliente também não conta em Autonomia e pausa o relógio de travamento.

**Tech Stack:** FastAPI + Pydantic + supabase-py (testes com `unittest.mock.MagicMock`); Next.js 15 / React 19, inline styles; testes de frontend estruturais em `node --test tests/*.test.mjs`.

**Spec:** Design aprovado na conversa de 2026-09-23 (bounded, sem spec file). Resumo das decisões do usuário: só o gerente marca tipo cliente; tipo cliente fica DENTRO do bloqueio existente; corrige retroativo via SQL que o usuário roda; contador "sprints avaliadas" NÃO muda (conta sprints avaliadas pelo gerente = referencial de top performer). Decisões adicionais aprovadas: bloqueio de cliente não conta em Autonomia (destravar não pergunta "quem resolveu"); marcar como cliente dispensa penalidade de travamento pendente e pausa o relógio, destravar reinicia o prazo; no PULL, quem não concluiu nada e só tinha task bloqueada por cliente fica "sem dado" e sai da média do time; PULL com backlog e ninguém puxou continua 0.

## Global Constraints

- Migração de schema é manual (bloco SQL que o usuário cola no Supabase), nunca destrutiva — sem `DROP COLUMN`/`DROP TABLE`. Avisar o usuário explicitamente no fim.
- `score_final` nunca é persistido; ranking recalcula ao vivo. Correção retroativa mexe só em `pontuacao_operacional_sprint` (colunas congeladas no fechamento) e `tasks`.
- Operacional já não pode tocar em nenhum campo de bloqueio (`_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL` em `routers/tasks.py:41-46`, 403). `bloqueio_tipo` entra nesse conjunto.
- Contador "sprints avaliadas" (`services/pontuacao.py::listar_spi_do_projeto`, `len(minhas)`) NÃO muda.
- Comportamento de ATRIBUICAO sem bloqueio de cliente não muda — os golden tests existentes de `tests/test_pontuacao_fechamento.py` têm que passar sem alteração.
- Frontend: rodar `npx tsc --noEmit` **e** `npm test`.
- Commits diretos em `main`, um por task.

---

## ONDA 1 — Backend

### Task 1: Coluna `bloqueio_tipo` — schema SQL + Pydantic

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (append no fim do bloco de 2026-09-23, antes de `-- Migration v5`)
- Modify: `docudata-backend/models/schemas.py:480-545` (TaskUpdate, TaskResponse)
- Test: `docudata-backend/tests/test_dependencia_cliente.py` (novo)

**Interfaces:**
- Produces: `TaskUpdate.bloqueio_tipo: Optional[str]` validado em `{"interno", "cliente"}`; `TaskResponse.bloqueio_tipo: Optional[str] = None`; coluna `tasks.bloqueio_tipo text`.

- [x] **Step 1: Testes falhando**

```python
"""Bloqueio do tipo 'cliente' — dependência do cliente não pode zerar a Entrega
de ninguém (design aprovado 2026-09-23)."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.schemas import TaskUpdate, TaskResponse

SCHEMA = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text()


def test_schema_adiciona_bloqueio_tipo_nao_destrutivo():
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS bloqueio_tipo text" in SCHEMA
    assert "CHECK (bloqueio_tipo IN ('interno','cliente'))" in SCHEMA


def test_task_update_aceita_bloqueio_tipo_valido():
    assert TaskUpdate(bloqueio_tipo="cliente").bloqueio_tipo == "cliente"
    assert TaskUpdate(bloqueio_tipo="interno").bloqueio_tipo == "interno"


def test_task_update_rejeita_bloqueio_tipo_invalido():
    with pytest.raises(ValidationError):
        TaskUpdate(bloqueio_tipo="fornecedor")


def test_task_response_expoe_bloqueio_tipo_opcional():
    assert "bloqueio_tipo" in TaskResponse.model_fields
    assert TaskResponse.model_fields["bloqueio_tipo"].default is None
```

- [x] **Step 2: Rodar e ver falhar** — `cd docudata-backend && .venv/bin/python -m pytest tests/test_dependencia_cliente.py -q` → FAIL.

- [x] **Step 3: Implementar**

`supabase_schema.sql`, logo após `ALTER TABLE avaliacoes_gerente ALTER COLUMN resposta_6 DROP NOT NULL;`:

```sql

-- Entrega "Dependência do cliente" (2026-09-23): bloqueio manual ganha tipo.
-- 'cliente' = task parada esperando o cliente — no fechamento da sprint ela
-- sai dos pontos alocados (não zera a Entrega de ninguém), não conta em
-- Autonomia e pausa o relógio de travamento. NULL/'interno' = comportamento
-- de sempre. Só o gerente marca (operacional já não mexe em bloqueio).
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS bloqueio_tipo text
    CHECK (bloqueio_tipo IN ('interno','cliente'));
```

`models/schemas.py`: acima de `class TaskUpdate`, `_BLOQUEIO_TIPOS_VALIDOS = {"interno", "cliente"}`. Em `TaskUpdate`, depois de `bloqueado_resolvido_por`: `bloqueio_tipo: Optional[str] = None` e validator:

```python
    @field_validator("bloqueio_tipo")
    @classmethod
    def bloqueio_tipo_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _BLOQUEIO_TIPOS_VALIDOS:
            raise ValueError("bloqueio_tipo deve ser interno | cliente")
        return v
```

Em `TaskResponse`, depois de `bloqueado_resolvido_em`: `bloqueio_tipo: Optional[str] = None`.

- [x] **Step 4: Rodar e ver passar.**
- [x] **Step 5: Commit** — `feat(tasks): bloqueio manual ganha tipo (interno | cliente)`

---

### Task 2: `PATCH /tasks/{id}` grava o tipo, dispensa travamento e não conta em Autonomia

**Files:**
- Modify: `docudata-backend/routers/tasks.py:41-46` (set de campos negados ao operacional), `:851-862` (gate "quem resolveu"), `:933-960` (bloco bloqueado_manual)
- Test: `docudata-backend/tests/test_dependencia_cliente.py` (append; reaproveita `_make_mock_client`/`_patch_and_client`/`_BASE_TASK` de `tests/test_bloqueio_manual.py` via import)

**Interfaces:**
- Consumes: `TaskUpdate.bloqueio_tipo` (Task 1).
- Produces: regra — task com `bloqueado_manual=True` e `bloqueio_tipo='cliente'` é "dependência do cliente". Ao destravar uma task de cliente: `bloqueio_tipo=None`, sem `bloqueado_resolvido_por`/`bloqueado_resolvido_em` (é isso que a mantém fora de Autonomia no fechamento, que só conta `bloqueado_resolvido_em`), relógio reancorado.

Regras:
1. `bloqueio_tipo` entra em `_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL` → 403 pro operacional.
2. Gate "quem resolveu" (422) não se aplica quando a task atual é de cliente.
3. Marcar bloqueio (`bloqueado_manual: True`) grava `bloqueio_tipo` (default `interno`).
4. Trocar tipo com a task já bloqueada (`bloqueio_tipo` sozinho) é permitido.
5. Ao virar `cliente` (marcação nova ou troca): `travado_automatico=False` e `task_travamentos` não dispensados da task viram `dispensado=True` (mesma lógica de `override_travamento`, `routers/tasks.py:1036-1045`).
6. Destravar task de cliente: `bloqueado_manual=False`, `bloqueio_tipo=None`, sem campos de resolução, sem `rotear_evento_pos_fechamento` de autonomia; se `entrou_em_andamento_em` estava setado, reancora em agora e `travado_automatico=False`.

- [x] **Step 1: Testes falhando** (append)

```python
from tests.test_bloqueio_manual import _BASE_TASK, _make_mock_client, _patch_and_client


def test_gerente_marca_bloqueio_de_cliente(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=False)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": True, "bloqueio_tipo": "cliente"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert updates["bloqueado_manual"] is True
    assert updates["bloqueio_tipo"] == "cliente"
    assert updates["travado_automatico"] is False


def test_marcar_bloqueio_sem_tipo_grava_interno(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=False)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": True})

    assert resp.status_code == 200
    assert calls["tasks_update"][-1]["bloqueio_tipo"] == "interno"


def test_trocar_tipo_de_task_ja_bloqueada_para_cliente(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueio_tipo="interno")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueio_tipo": "cliente"})

    assert resp.status_code == 200
    assert calls["tasks_update"][-1]["bloqueio_tipo"] == "cliente"


def test_destravar_bloqueio_de_cliente_nao_exige_quem_resolveu_e_nao_conta_autonomia(monkeypatch):
    task = dict(
        _BASE_TASK, bloqueado_manual=True, bloqueio_tipo="cliente",
        entrou_em_andamento_em="2026-09-01T00:00:00+00:00",
    )
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": False})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert updates["bloqueado_manual"] is False
    assert updates["bloqueio_tipo"] is None
    assert "bloqueado_resolvido_por" not in updates
    assert "bloqueado_resolvido_em" not in updates
    assert updates["entrou_em_andamento_em"] != "2026-09-01T00:00:00+00:00"
    assert updates["travado_automatico"] is False


def test_destravar_bloqueio_interno_continua_exigindo_quem_resolveu(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueio_tipo="interno")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": False})

    assert resp.status_code == 422
    assert len(calls["tasks_update"]) == 0


def test_operacional_nao_pode_mexer_no_tipo_de_bloqueio(monkeypatch):
    from services.auth import criar_jwt
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueio_tipo="interno")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-op-1", "op@citi.com", "operacional"))

    resp = tc.patch("/tasks/task-1", json={"bloqueio_tipo": "cliente"})

    assert resp.status_code == 403
    assert len(calls["tasks_update"]) == 0
```

Observação para quem executa: se `get_current_pessoa` com cargo `operacional` precisar de linha em `pessoa`/`operacionais` no mock, ver como `tests/test_task_rbac_operacional.py` monta o cookie de operacional e copiar o mesmo padrão — o que importa é o 403 antes de qualquer escrita.

- [x] **Step 2: Rodar e ver falhar.**

- [x] **Step 3: Implementar em `routers/tasks.py`**

(a) Adicionar `"bloqueio_tipo"` em `_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL`.

(b) Antes do gate TRANS-05, calcular `era_bloqueio_cliente = bool(task.get("bloqueado_manual")) and task.get("bloqueio_tipo") == "cliente"` e acrescentar `and not era_bloqueio_cliente` à condição do 422.

(c) Substituir o bloco `# TRANS-04/TRANS-05: bloqueado_manual ...` por:

```python
    # TRANS-04/TRANS-05: bloqueado_manual (gate 422 acima já garantiu que, ao
    # desmarcar um bloqueio interno, bloqueado_resolvido_por veio válido).
    # Bloqueio de cliente (2026-09-23): não conta em Autonomia — ao destravar
    # não grava resolvido_por/_em (o fechamento só conta bloqueado_resolvido_em)
    # e reinicia o prazo do relógio de travamento, que ficou pausado.
    virou_cliente = False
    if data.bloqueado_manual is not None and data.bloqueado_manual != task.get("bloqueado_manual", False):
        updates["bloqueado_manual"] = data.bloqueado_manual
        if data.bloqueado_manual is True:
            updates["bloqueado_em"] = agora.isoformat()
            updates["bloqueado_por"] = data.bloqueado_por
            updates["bloqueio_tipo"] = data.bloqueio_tipo or "interno"
            virou_cliente = updates["bloqueio_tipo"] == "cliente"
        elif era_bloqueio_cliente:
            updates["bloqueio_tipo"] = None
            if task.get("entrou_em_andamento_em"):
                updates["entrou_em_andamento_em"] = agora.isoformat()
                updates["travado_automatico"] = False
        else:
            updates["bloqueado_resolvido_por"] = data.bloqueado_resolvido_por
            updates["bloqueado_resolvido_em"] = agora.isoformat()
            houve_bloqueio_resolvido = True
    elif (
        data.bloqueio_tipo is not None
        and task.get("bloqueado_manual")
        and data.bloqueio_tipo != task.get("bloqueio_tipo")
    ):
        updates["bloqueio_tipo"] = data.bloqueio_tipo
        virou_cliente = data.bloqueio_tipo == "cliente"

    if virou_cliente:
        updates["travado_automatico"] = False
```

(d) Depois do `result = client.table("tasks").update(updates)...execute()`:

```python
    if virou_cliente:
        # Mesma válvula do override de travamento: atraso por espera do
        # cliente não é culpa do operacional e não pode penalizar Entrega.
        try:
            (
                client.table("task_travamentos")
                .update({"dispensado": True})
                .eq("task_id", task_id)
                .eq("dispensado", False)
                .execute()
            )
        except Exception:
            pass  # best-effort
```

- [x] **Step 4: Rodar `tests/test_dependencia_cliente.py` e `tests/test_bloqueio_manual.py`** → PASS.
- [x] **Step 5: Commit** — `feat(tasks): bloqueio de cliente dispensa travamento e fica fora de Autonomia`

---

### Task 3: Relógio de travamento pausa em bloqueio de cliente

**Files:**
- Modify: `docudata-backend/services/travamento_checker.py:42-55`
- Test: `docudata-backend/tests/test_dependencia_cliente.py` (append; reaproveita `_make_job_mock_client` e `_iso` de `tests/test_travamento_job_override.py`)

- [x] **Step 1: Teste falhando**

```python
def test_job_de_travamento_pula_task_bloqueada_por_cliente(monkeypatch):
    import services.travamento_checker as checker
    from tests.test_travamento_job_override import _iso, _make_job_mock_client
    task = {
        "id": "task-1", "pontos": 1, "entrou_em_andamento_em": _iso(30),
        "travado_automatico": False, "bloqueado_manual": True, "bloqueio_tipo": "cliente",
    }
    mock_sb, calls = _make_job_mock_client([task])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert calls["tasks_update"] == []


def test_job_de_travamento_continua_travando_bloqueio_interno(monkeypatch):
    import services.travamento_checker as checker
    from tests.test_travamento_job_override import _iso, _make_job_mock_client
    task = {
        "id": "task-1", "pontos": 1, "entrou_em_andamento_em": _iso(30),
        "travado_automatico": False, "bloqueado_manual": True, "bloqueio_tipo": "interno",
    }
    mock_sb, calls = _make_job_mock_client([task])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert len(calls["tasks_update"]) == 1
```

- [x] **Step 2: Rodar e ver falhar** (o primeiro).
- [x] **Step 3: Implementar** — no select, acrescentar `bloqueado_manual, bloqueio_tipo`; no loop, logo após o `if task.get("travado_automatico")`:

```python
        if task.get("bloqueado_manual") and task.get("bloqueio_tipo") == "cliente":
            # Esperando o cliente: relógio pausado. Ao destravar, o PATCH
            # reancora entrou_em_andamento_em e o prazo recomeça do zero.
            continue
```

E acrescentar ao docstring do módulo uma linha: "Bloqueio de cliente (2026-09-23) pausa o relógio."

- [x] **Step 4: Rodar `tests/test_dependencia_cliente.py tests/test_travamento_job_override.py`** → PASS.
- [x] **Step 5: Commit** — `feat(travamento): relógio pausa enquanto a task espera o cliente`

---

### Task 4: Fechamento — task de cliente fora da Entrega; PULL vazio vira "sem dado"

**Files:**
- Modify: `docudata-backend/services/pontuacao.py:65-71` (select), `:97-130` (loop), `:203-235` (bloco PONTOS_RELATIVO)
- Test: `docudata-backend/tests/test_pontuacao_dependencia_cliente.py` (novo; reaproveita `_mock_client` de `tests/test_pontuacao_fechamento.py`)

**Interfaces:**
- Produces: em `pontuacao_operacional_sprint`, `entrega_pontos_alocados` não inclui tasks de cliente não concluídas; `entrega_nota_relativa`/`entrega_denominador` = `None` quando a Entrega não é medível.

Regras:
- `aguardando_cliente(task) = task.bloqueado_manual and task.bloqueio_tipo == "cliente" and coluna != "concluida"`.
- ATRIBUICAO: task aguardando cliente não soma em `pontos_alocados`. Operacional cujas únicas tasks eram de cliente fica com `alocados == 0` → `services/performance.py::_entrega_atribuicao` já devolve `None`.
- PULL (`PONTOS_RELATIVO`):
  - `isentos = {op | op tem ≥1 task aguardando cliente e pontos_concluidos.get(op, 0) == 0}`.
  - `tem_o_que_puxar = any(not t.extra and not aguardando_cliente(t) for t in tasks)`.
  - Se `not tem_o_que_puxar`: todos ficam com `entrega_nota_relativa=None`, `entrega_denominador=None`.
  - Senão: média calculada só sobre `vinculados_ids - isentos`; isentos ficam com nota `None`; o resto usa a fórmula atual (piso/teto inalterados).

- [x] **Step 1: Testes falhando**

```python
"""Fechamento da sprint não pode zerar a Entrega de quem não tinha o que
entregar (dependência do cliente / sprint PULL vazia) — design 2026-09-23."""
from services.pontuacao import calcular_e_travar_pontuacao
from tests.test_pontuacao_fechamento import _mock_client

_SPRINT = {"id": "sprint-1", "project_id": "proj-1"}
_PULL = {"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pull_piso_pontos": 1, "pull_teto": 1.5}


def _op(op_id):
    return {"id": op_id, "nome": op_id, "email": None, "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None}


def _task(tid, op, pontos, coluna="em_andamento", **extra):
    base = {
        "id": tid, "operacional_id": op, "pontos": pontos, "coluna_kanban": coluna, "extra": False,
        "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None,
        "bloqueado_manual": False, "bloqueio_tipo": None,
    }
    base.update(extra)
    return base


def _por_op(resultado):
    return {r["operacional_id"]: r for r in resultado}


def test_atribuicao_task_unica_aguardando_cliente_nao_entra_em_alocados():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 5, bloqueado_manual=True, bloqueio_tipo="cliente")],
        operacionais=[_op("op-a")],
    )
    linha = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]
    assert linha["entrega_pontos_alocados"] == 0
    assert linha["entrega_pontos_concluidos"] == 0


def test_atribuicao_bloqueio_interno_continua_contando_em_alocados():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 5, bloqueado_manual=True, bloqueio_tipo="interno")],
        operacionais=[_op("op-a")],
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_pontos_alocados"] == 5


def test_atribuicao_task_de_cliente_concluida_conta_normal():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 5, coluna="concluida", bloqueado_manual=True, bloqueio_tipo="cliente")],
        task_transicoes=[{"task_id": "t1", "operacional_id": "op-a", "timestamp": "2026-09-02T00:00:00Z"}],
        operacionais=[_op("op-a")],
    )
    linha = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 5


def test_atribuicao_mistura_cliente_e_normal_so_tira_a_de_cliente():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            _task("t1", "op-a", 5, bloqueado_manual=True, bloqueio_tipo="cliente"),
            _task("t2", "op-a", 3),
        ],
        operacionais=[_op("op-a")],
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_pontos_alocados"] == 3


def test_pull_sprint_sem_nenhuma_task_fica_sem_dado_pra_todos():
    client = _mock_client(sprint=_SPRINT, tasks=[], operacionais=[_op("op-a"), _op("op-b")], projeto=_PULL)
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-a"]["entrega_nota_relativa"] is None
    assert por_op["op-b"]["entrega_nota_relativa"] is None
    assert por_op["op-a"]["entrega_denominador"] is None


def test_pull_sprint_so_com_task_extra_fica_sem_dado():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", None, 2, extra=True)],
        operacionais=[_op("op-a")],
        projeto=_PULL,
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_nota_relativa"] is None


def test_pull_backlog_com_task_e_ninguem_puxou_continua_zero():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", None, 3, coluna="planejado")],
        operacionais=[_op("op-a")],
        projeto=_PULL,
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_nota_relativa"] == 0.0


def test_pull_quem_nao_puxou_enquanto_outro_puxou_continua_zero():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 4, coluna="concluida")],
        task_transicoes=[{"task_id": "t1", "operacional_id": "op-a", "timestamp": "2026-09-02T00:00:00Z"}],
        operacionais=[_op("op-a"), _op("op-b")],
        projeto=_PULL,
    )
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-b"]["entrega_nota_relativa"] == 0.0
    assert por_op["op-a"]["entrega_nota_relativa"] == 100.0


def test_pull_quem_so_tinha_task_de_cliente_fica_sem_dado_e_sai_da_media():
    """op-a concluiu 4; op-b só tinha task esperando cliente; op-c não puxou.
    Média sem op-b = (4 + 0) / 2 = 2 -> op-a: 4/2=2 -> teto 1.5 -> 100; op-c: 0."""
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            _task("t1", "op-a", 4, coluna="concluida"),
            _task("t2", "op-b", 3, bloqueado_manual=True, bloqueio_tipo="cliente"),
        ],
        task_transicoes=[{"task_id": "t1", "operacional_id": "op-a", "timestamp": "2026-09-02T00:00:00Z"}],
        operacionais=[_op("op-a"), _op("op-b"), _op("op-c")],
        projeto=_PULL,
    )
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-b"]["entrega_nota_relativa"] is None
    assert por_op["op-a"]["entrega_denominador"] == 2.0
    assert por_op["op-a"]["entrega_nota_relativa"] == 100.0
    assert por_op["op-c"]["entrega_nota_relativa"] == 0.0


def test_pull_so_task_de_cliente_na_sprint_fica_sem_dado_pra_todos():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 3, bloqueado_manual=True, bloqueio_tipo="cliente")],
        operacionais=[_op("op-a"), _op("op-b")],
        projeto=_PULL,
    )
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-a"]["entrega_nota_relativa"] is None
    assert por_op["op-b"]["entrega_nota_relativa"] is None
```

- [x] **Step 2: Rodar e ver falhar.**

- [x] **Step 3: Implementar em `services/pontuacao.py`**

(a) Select de tasks: acrescentar `bloqueado_manual, bloqueio_tipo`.

(b) Função de módulo (perto de `_resolver_quem_completou`):

```python
def _aguardando_cliente(task: dict) -> bool:
    """Task parada esperando o cliente no momento do fechamento: não conta
    como pontos alocados de ninguém — atraso do cliente não pode zerar a
    Entrega do operacional (design 2026-09-23). Se o cliente destravou e a
    task foi concluída, ela conta normalmente."""
    return (
        bool(task.get("bloqueado_manual"))
        and task.get("bloqueio_tipo") == "cliente"
        and task.get("coluna_kanban") != "concluida"
    )
```

(c) Antes do loop: `aguardando_cliente_por_op: set[str] = set()`. No ramo `else:` (não concluída, não extra), trocar por:

```python
        else:
            operacional_id = task.get("operacional_id")
            if operacional_id:
                if _aguardando_cliente(task):
                    aguardando_cliente_por_op.add(operacional_id)
                else:
                    pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos
```

(d) Substituir o bloco `denominador_relativo = None / if modo_avaliacao == "PONTOS_RELATIVO": ...` por:

```python
    denominador_relativo = None
    isentos_relativo: set[str] = set()
    entrega_relativa_medivel = False
    if modo_avaliacao == "PONTOS_RELATIVO":
        # Sem nenhuma task regular disponível (só extra, ou só esperando o
        # cliente, ou sprint vazia) não havia o que entregar: Entrega fica sem
        # dado pra todos, não 0. Quem só tinha task esperando o cliente e não
        # concluiu nada também fica sem dado e sai da média do time.
        tem_o_que_puxar = any(not t.get("extra") and not _aguardando_cliente(t) for t in tasks)
        isentos_relativo = {op for op in aguardando_cliente_por_op if pontos_concluidos.get(op, 0) == 0}
        base_media = vinculados_ids - isentos_relativo
        if tem_o_que_puxar and base_media:
            valores_concluidos = [pontos_concluidos.get(op, 0) for op in base_media]
            denominador_bruto = sum(valores_concluidos) / len(valores_concluidos)
            piso = float(projeto_row.get("pull_piso_pontos") or 1)
            denominador_relativo = max(denominador_bruto, piso)
            entrega_relativa_medivel = True
```


(e) No loop de linhas, trocar `if modo_avaliacao == "PONTOS_RELATIVO":` por:

```python
        if modo_avaliacao == "PONTOS_RELATIVO":
            entrega_pontos_pessoa = pontos_concluidos.get(operacional_id, 0)
            if entrega_relativa_medivel and operacional_id not in isentos_relativo:
                teto = float(projeto_row.get("pull_teto") or 1.5)
                entrega_denominador = round(denominador_relativo, 2)
                entrega_bruta = entrega_pontos_pessoa / denominador_relativo if denominador_relativo else 0
                entrega_nota_relativa = round(min(entrega_bruta, teto) * 100 / teto, 2)
```

- [x] **Step 4: Rodar `tests/test_pontuacao_dependencia_cliente.py tests/test_pontuacao_fechamento.py`** → PASS (golden tests inalterados).
- [x] **Step 5: Commit** — `feat(pontuacao): dependência do cliente e sprint PULL vazia não zeram a Entrega`

---

### Task 5: Prova ponta a ponta no ranking + SQL retroativo

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (append ao bloco da Task 1)
- Test: `docudata-backend/tests/test_dependencia_cliente.py` (append)

- [x] **Step 1: Testes falhando**

```python
def test_performance_trata_alocados_zero_como_sem_dado_e_renormaliza():
    """Prova que a linha gravada pelo fechamento (alocados=0 porque a única
    task esperava o cliente) vira Entrega None — não 0 — e a nota final usa
    só as dimensões com dado."""
    from services.performance import _entrega_atribuicao, _score_final
    linha = {"entrega_pontos_concluidos": 0, "entrega_pontos_alocados": 0, "entrega_pontos_penalizados": 0}
    assert _entrega_atribuicao([linha]) is None
    pesos = {"peso_entrega": 0.18, "peso_gerente": 0.50, "peso_qualidade": 0.18, "peso_autonomia": 0.14}
    assert _score_final({"entrega": None, "gerente": 80.0, "qualidade": None, "autonomia": None}, pesos) == 80.0


def test_schema_traz_sql_retroativo_da_pull_vazia():
    assert "UPDATE pontuacao_operacional_sprint p" in SCHEMA
    assert "entrega_modo = 'PONTOS_RELATIVO'" in SCHEMA
```

- [x] **Step 2: Rodar e ver falhar** (o segundo).
- [x] **Step 3: Append em `supabase_schema.sql`, logo após o ALTER da Task 1:**

```sql

-- Correção retroativa (2026-09-23): sprint PULL já fechada sem nenhuma task
-- regular (só extra, ou vazia) gravou Entrega 0 pra todo mundo. Passa a ser
-- "sem dado" — o ranking recalcula ao vivo no próximo GET /performance.
-- Idempotente: rodar de novo não muda nada.
UPDATE pontuacao_operacional_sprint p
SET entrega_nota_relativa = NULL,
    entrega_denominador = NULL
WHERE p.entrega_modo = 'PONTOS_RELATIVO'
  AND NOT EXISTS (
      SELECT 1 FROM tasks t
      WHERE t.sprint_id = p.sprint_id
        AND COALESCE(t.extra, false) = false
  );

-- Correção retroativa de task que esperava o cliente numa sprint JÁ FECHADA
-- (rodar à mão, uma task por vez). 1) Achar candidatas:
--
-- SELECT pr.name AS projeto, s.numero AS sprint, o.nome AS operacional,
--        t.id AS task_id, t.titulo, t.pontos, t.coluna_kanban, t.motivo_bloqueio,
--        p.entrega_modo, p.entrega_pontos_concluidos, p.entrega_pontos_alocados,
--        p.entrega_nota_relativa
-- FROM pontuacao_operacional_sprint p
-- JOIN tasks t        ON t.sprint_id = p.sprint_id AND t.operacional_id = p.operacional_id
-- JOIN sprints s      ON s.id = p.sprint_id
-- JOIN projects pr    ON pr.id = p.projeto_id
-- JOIN operacionais o ON o.id = p.operacional_id
-- WHERE t.coluna_kanban <> 'concluida'
--   AND COALESCE(t.extra, false) = false
-- ORDER BY pr.name, s.numero, o.nome;
--
-- 2) Aplicar pra uma task (troque <TASK_ID>). Idempotente: só desconta se a
--    task ainda não estiver marcada como cliente.
--
-- WITH alvo AS (
--     SELECT id, sprint_id, operacional_id, pontos FROM tasks
--     WHERE id = '<TASK_ID>' AND bloqueio_tipo IS DISTINCT FROM 'cliente'
-- )
-- UPDATE pontuacao_operacional_sprint p
-- SET entrega_pontos_alocados = GREATEST(p.entrega_pontos_alocados - alvo.pontos, 0),
--     entrega_nota_relativa = CASE
--         WHEN p.entrega_modo = 'PONTOS_RELATIVO' AND p.entrega_pontos_concluidos = 0 THEN NULL
--         ELSE p.entrega_nota_relativa END,
--     entrega_denominador = CASE
--         WHEN p.entrega_modo = 'PONTOS_RELATIVO' AND p.entrega_pontos_concluidos = 0 THEN NULL
--         ELSE p.entrega_denominador END
-- FROM alvo
-- WHERE p.sprint_id = alvo.sprint_id AND p.operacional_id = alvo.operacional_id;
--
-- UPDATE tasks SET bloqueio_tipo = 'cliente' WHERE id = '<TASK_ID>';
```

- [x] **Step 4: Rodar a suíte completa do backend** — `cd docudata-backend && .venv/bin/python -m pytest -q` → PASS.
- [x] **Step 5: Commit** — `feat(pontuacao): SQL retroativo pra Entrega sem dado (PULL vazia e dependência do cliente)`

---

## ONDA 2 — Frontend (só começa com a Onda 1 verde)

### Task 6: TaskModal — tipo do bloqueio, card e texto de ajuda

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts:1636-1660` (`TaskKanbanResponse`), `:1730-1745` (payload de `patchTaskKanban`)
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx:132-136` (state), `:165-170` (validação), `:195-201` (payload), `:449-500` (UI), `:731-735` (chip do modal de visualização), `:942-944` (chip do card), `:1154` (ajuda)
- Test: `docudata-frontend/tests/dependencia-cliente.test.mjs` (novo)

TaskModal só é aberto por gerente/líder (operacional abre `TaskViewModal`, `TasksKanbanTab.tsx:1429`), e o backend dá 403 pro operacional — não precisa de trava extra de UI.

- [x] **Step 1: Teste falhando**

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const KANBAN = readFileSync(new URL("../app/components/TasksKanbanTab.tsx", import.meta.url), "utf-8");
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");

test("api.ts expõe bloqueio_tipo na task e no PATCH", () => {
  assert.match(API, /bloqueio_tipo\?: "interno" \| "cliente" \| null;/);
  assert.match(API, /bloqueio_tipo\?: "interno" \| "cliente";/);
});

test("TaskModal oferece Dependência do cliente dentro do bloqueio", () => {
  assert.match(KANBAN, /Dependência do cliente/);
  assert.match(KANBAN, /bloqueio_tipo: bloqueado \? bloqueioTipo : undefined/);
});

test("destravar bloqueio de cliente não pergunta quem resolveu", () => {
  assert.match(KANBAN, /jaEstavaBloqueadoManual && !eraBloqueioCliente && !bloqueado/);
});

test("card mostra que a task espera o cliente", () => {
  assert.match(KANBAN, /Aguardando cliente/);
});
```

- [x] **Step 2: `cd docudata-frontend && npm test`** → FAIL no arquivo novo.

- [x] **Step 3: Implementar**

`api.ts` — em `TaskKanbanResponse`, depois de `bloqueado_resolvido_em`: `bloqueio_tipo?: "interno" | "cliente" | null;`. No payload de `patchTaskKanban`, depois de `bloqueado_resolvido_por?: string;`: `bloqueio_tipo?: "interno" | "cliente";`.

`TasksKanbanTab.tsx`:

State (após `jaEstavaBloqueadoManual`):
```tsx
  const eraBloqueioCliente = jaEstavaBloqueadoManual && task?.bloqueio_tipo === "cliente";
  const [bloqueioTipo, setBloqueioTipo] = useState<"interno" | "cliente">(
    task?.bloqueio_tipo === "cliente" ? "cliente" : "interno"
  );
```

Validação: `if (jaEstavaBloqueadoManual && !eraBloqueioCliente && !bloqueado && !bloqueadoResolvidoPor)`.

Payload do PATCH: depois de `bloqueado_manual: bloqueado,` acrescentar `bloqueio_tipo: bloqueado ? bloqueioTipo : undefined,` e trocar a linha de `bloqueado_resolvido_por` por
`bloqueado_resolvido_por: (!bloqueado && jaEstavaBloqueadoManual && !eraBloqueioCliente) ? bloqueadoResolvidoPor : undefined,`.

UI — dentro de `{bloqueado && (`, antes do grid de motivo, um bloco:
```tsx
                <div>
                  <label style={labelSt}>Tipo do bloqueio</label>
                  <select
                    value={bloqueioTipo}
                    onChange={(e) => setBloqueioTipo(e.target.value as "interno" | "cliente")}
                    style={inputSt}
                  >
                    <option value="interno">Interno (equipe, acesso, outra task)</option>
                    <option value="cliente">Dependência do cliente</option>
                  </select>
                  {bloqueioTipo === "cliente" && (
                    <p style={{ fontSize: 12, color: "#64748b", margin: "6px 0 0" }}>
                      Se a sprint fechar com a task ainda esperando o cliente, ela não conta na Entrega de ninguém e o relógio de atraso fica pausado.
                    </p>
                  )}
                </div>
```
(os dois blocos — tipo e grid de motivo — ficam dentro de um `<>...</>` sob `bloqueado &&`.)

"Quem resolveu?": trocar a condição `{jaEstavaBloqueadoManual && !bloqueado && (` por `{jaEstavaBloqueadoManual && !eraBloqueioCliente && !bloqueado && (`.

Chip no `TaskViewModal` (~731): texto vira ``{task.bloqueio_tipo === "cliente" ? "Aguardando cliente" : "Bloqueada"}{task.motivo_bloqueio ? `: ${task.motivo_bloqueio}` : ""}``.

Chip no card (~942): `{task.bloqueio_tipo === "cliente" ? "Aguardando cliente" : "Bloqueada"}`.

Ajuda (~1154): acrescentar ao final do `body` de "Bloqueio: quem marca é quem trava": `" Se o motivo for o cliente, o gerente escolhe 'Dependência do cliente': se a sprint fechar com a task ainda esperando, ela sai da conta de Entrega de todo mundo, não conta na Autonomia e o relógio de atraso fica pausado."`.

- [x] **Step 4: `npx tsc --noEmit && npm test`** → limpo e verde.
- [x] **Step 5: Commit** — `feat(kanban): gerente marca bloqueio como dependência do cliente`

---

### Task 7: Verificação final

- [x] Backend completo: `cd docudata-backend && .venv/bin/python -m pytest -q` → PASS.
- [x] Frontend: `cd docudata-frontend && npx tsc --noEmit && npm test` → limpo/verde.
- [ ] Relatar ao usuário:
  1. Migração manual: `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS bloqueio_tipo ...` + `UPDATE` retroativo da PULL vazia — rodar ANTES do deploy (sem a coluna, o select do fechamento quebra).
  2. Queries de candidatos/aplicação da dependência do cliente retroativa (comentadas no schema) — ele roda uma task por vez.
  3. Checklist manual: marcar task como "Dependência do cliente" (chip "Aguardando cliente" no card); destravar sem pergunta "quem resolveu"; operacional não vê/alterna o tipo; após fechar uma sprint com task de cliente pendente, Entrega da pessoa aparece "—" no /performance.

---

## Self-Review

**Cobertura:** tipo cliente no bloqueio → T1/T2/T6. Só gerente → T2 (403) + T6 (modal gerente-only). Fora de Entrega no fechamento → T4. Única task → None → T4 + T5 (prova em performance). Travamento dispensado/pausado/reiniciado → T2/T3. Fora de Autonomia → T2 (sem resolvido_em). PULL vazio → T4. PULL "ninguém puxou com backlog" continua 0 → T4. Retroativo → T5. "Sprints avaliadas" inalterado → nenhuma task toca `listar_spi_do_projeto` (Global Constraints).

**Placeholders:** `<TASK_ID>` no SQL é parâmetro intencional que o usuário preenche, não placeholder de plano.

**Consistência:** `bloqueio_tipo` (`"interno" | "cliente"`, nullable) igual em SQL, Pydantic e TS. `_aguardando_cliente(task)` usado em T4 nos dois pontos. `eraBloqueioCliente` (TS) espelha `era_bloqueio_cliente` (Python).
