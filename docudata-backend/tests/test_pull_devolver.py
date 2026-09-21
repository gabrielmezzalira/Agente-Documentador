from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task, operacional_da_pessoa=None, wip_config=None, update_rowcount=1):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [task] if task else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()

                def eq_effect(*a, **kw):
                    return q

                def execute_effect():
                    resp = MagicMock()
                    if update_rowcount == 0:
                        resp.data = []
                    else:
                        resp.data = [dict(task, **payload)]
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [operacional_da_pessoa] if operacional_da_pessoa else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"wip_config": wip_config or {}}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task, operacional_da_pessoa, cargo="operacional", wip_config=None, update_rowcount=1):
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(task, operacional_da_pessoa, wip_config, update_rowcount)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        # A fixture `autenticar` (tests/conftest.py) sempre autentica como
        # "pessoa@citi.org.br", sem parâmetro de e-mail — por isso o
        # `operacional_da_pessoa` de cada teste usa esse mesmo e-mail (é
        # como o mock resolve "qual operacional é o usuário logado").
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc
    return _make


def test_puxar_task_disponivel_atribui_a_quem_puxou(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 200
    assert resp.json()["operacional_id"] == "op-a"


def test_puxar_task_ja_puxada_da_409(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"}, update_rowcount=0)

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 409


def test_puxar_task_rascunho_da_403(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": True, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 403
