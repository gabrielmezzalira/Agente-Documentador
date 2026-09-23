"""POST /tasks/{id}/aprovar — só gerente/líder, só sai de pendente_aprovacao
pra concluida. Ver spec §4, §6, §8."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task):
    tasks_update = []
    transicoes_insert = []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                tasks_update.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                transicoes_insert.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_update, transicoes_insert


_TASK_PENDENTE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "pendente_aprovacao", "ordem": 0, "sprint_id": "sprint-1",
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": True, "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task=None, cargo="gerente"):
        import routers.tasks as tasks_router
        from main import app
        mock_sb, tasks_update, transicoes_insert = _mock_client(task or _TASK_PENDENTE)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, tasks_update, transicoes_insert
    return _make


def test_aprovar_move_para_concluida(make_client):
    tc, tasks_update, transicoes_insert = make_client()

    resp = tc.post("/tasks/task-1/aprovar")

    assert resp.status_code == 200
    assert resp.json()["coluna_kanban"] == "concluida"
    assert tasks_update[-1]["coluna_kanban"] == "concluida"


def test_aprovar_grava_transicao_para_concluida(make_client):
    tc, tasks_update, transicoes_insert = make_client()

    tc.post("/tasks/task-1/aprovar")

    assert len(transicoes_insert) == 1
    assert transicoes_insert[0]["campo"] == "coluna_kanban"
    assert transicoes_insert[0]["para"] == "concluida"


def test_aprovar_rejeita_task_que_nao_esta_pendente(make_client):
    task = {**_TASK_PENDENTE, "coluna_kanban": "em_andamento"}
    tc, tasks_update, _ = make_client(task=task)

    resp = tc.post("/tasks/task-1/aprovar")

    assert resp.status_code == 409
    assert tasks_update == []


def test_aprovar_bloqueia_operacional(make_client):
    tc, tasks_update, _ = make_client(cargo="operacional")

    resp = tc.post("/tasks/task-1/aprovar")

    assert resp.status_code == 403
    assert tasks_update == []
