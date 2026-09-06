"""Testes para pontos_usados/faturamento_previsto derivados em GET /projects/{id}/sprints."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(project_data=None, sprints_data=None, tasks_data=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(project_data)] if project_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(sprints_data) if sprints_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name in ("tasks", "ingestions", "generated_docs"):
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                if name == "tasks":
                    resp.data = list(tasks_data) if tasks_data is not None else []
                else:
                    resp.data = []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.sprints as sprints_router
    monkeypatch.setattr(sprints_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_pontos_usados_soma_tasks_da_sprint(monkeypatch):
    mock_sb = _make_mock_client(
        project_data={"id": "proj-1", "valor_por_ponto": None},
        sprints_data=[{"id": "sprint-1", "project_id": "proj-1", "numero": 1, "pontos_orcamento": 20, "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00"}],
        tasks_data=[{"sprint_id": "sprint-1", "pontos": 5}, {"sprint_id": "sprint-1", "pontos": 3}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["pontos_usados"] == 8
    assert data[0]["pontos_orcamento"] == 20


def test_faturamento_previsto_deriva_de_valor_por_ponto(monkeypatch):
    mock_sb = _make_mock_client(
        project_data={"id": "proj-1", "valor_por_ponto": 350.0},
        sprints_data=[{"id": "sprint-1", "project_id": "proj-1", "numero": 1, "pontos_orcamento": 20, "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00"}],
        tasks_data=[],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    assert resp.json()[0]["faturamento_previsto"] == 7000.0


def test_faturamento_previsto_none_sem_valor_por_ponto_ou_sem_orcamento(monkeypatch):
    mock_sb = _make_mock_client(
        project_data={"id": "proj-1", "valor_por_ponto": None},
        sprints_data=[{"id": "sprint-1", "project_id": "proj-1", "numero": 1, "pontos_orcamento": None, "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00"}],
        tasks_data=[],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    assert resp.json()[0]["faturamento_previsto"] is None
    assert resp.json()[0]["pontos_usados"] == 0
