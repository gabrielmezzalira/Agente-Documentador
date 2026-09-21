"""Testes para avaliados_count/elegiveis_avaliacao_count em
GET /projects/{id}/sprints (Entrega 1, extra do usuário: contador "N/M" de
avaliação semanal)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(sprints_data=None, tasks_data=None, avaliacoes_data=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "proj-1", "valor_por_ponto": None}]
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
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(tasks_data) if tasks_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name in ("ingestions", "generated_docs"):
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(avaliacoes_data) if avaliacoes_data is not None else []
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


_SPRINT_ROW = {
    "id": "sprint-1", "project_id": "proj-1", "numero": 1,
    "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00",
}


def test_contador_avaliacao_reflete_elegiveis_e_avaliados(monkeypatch):
    mock_sb = _make_mock_client(
        sprints_data=[_SPRINT_ROW],
        tasks_data=[
            {"sprint_id": "sprint-1", "pontos": 5, "operacional_id": "op-1"},
            {"sprint_id": "sprint-1", "pontos": 3, "operacional_id": "op-2"},
        ],
        avaliacoes_data=[{"sprint_id": "sprint-1", "operacional_id": "op-1"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    data = resp.json()[0]
    assert data["elegiveis_avaliacao_count"] == 2
    assert data["avaliados_count"] == 1


def test_contador_zero_a_zero_sem_ninguem_com_task(monkeypatch):
    mock_sb = _make_mock_client(sprints_data=[_SPRINT_ROW], tasks_data=[], avaliacoes_data=[])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    data = resp.json()[0]
    assert data["elegiveis_avaliacao_count"] == 0
    assert data["avaliados_count"] == 0
