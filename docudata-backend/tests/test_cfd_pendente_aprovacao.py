"""GET /metricas/{id}/cfd soma a faixa pendente_aprovacao — senão essas
tasks somem silenciosamente do gráfico. Ver spec §10."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client():
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "proj-1"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "sprint-1", "numero": 1}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [
                {"coluna_kanban": "planejado"},
                {"coluna_kanban": "em_andamento"},
                {"coluna_kanban": "pendente_aprovacao"},
                {"coluna_kanban": "pendente_aprovacao"},
                {"coluna_kanban": "concluida"},
            ]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    import routers.metricas as metricas_router
    from main import app
    mock_sb = _mock_client()
    monkeypatch.setattr(metricas_router, "get_client", lambda: mock_sb)
    client = TestClient(app)
    return autenticar(client, cargo="gerente")


def test_cfd_soma_pendente_aprovacao(make_client):
    resp = make_client.get("/metricas/proj-1/cfd")

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["pendente_aprovacao"] == 2
    assert body[0]["planejado"] == 1
    assert body[0]["em_andamento"] == 1
    assert body[0]["concluida"] == 1
