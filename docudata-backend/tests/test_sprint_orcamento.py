"""Testes para PATCH /sprints/{id}/orcamento (substitui o antigo baseline manual)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(sprint_exists=True, sprint_data=None, tasks_na_sprint=None, outras_sprints=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.neq = MagicMock(return_value=q)
                resp = MagicMock()
                if "*" in cols:
                    resp.data = [dict(sprint_data)] if sprint_exists else []
                else:
                    resp.data = list(outras_sprints) if outras_sprints is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()

                def eq_side_effect(field, value):
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(sprint_data, **payload)]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(tasks_na_sprint) if tasks_na_sprint is not None else []
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


def test_define_orcamento_dentro_do_limite(monkeypatch):
    mock_sb = _make_mock_client(
        sprint_data={"id": "sprint-1", "project_id": "proj-1", "numero": 1, "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00"},
        tasks_na_sprint=[],
        outras_sprints=[{"pontos_orcamento": 30}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/sprint-1/orcamento", json={"pontos_orcamento": 20})

    assert resp.status_code == 200
    assert resp.json()["pontos_orcamento"] == 20


def test_bloqueia_se_soma_do_projeto_passar_de_100(monkeypatch):
    mock_sb = _make_mock_client(
        sprint_data={"id": "sprint-1", "project_id": "proj-1", "numero": 1, "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00"},
        tasks_na_sprint=[],
        outras_sprints=[{"pontos_orcamento": 90}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/sprint-1/orcamento", json={"pontos_orcamento": 20})

    assert resp.status_code == 409
    assert "10" in resp.json()["detail"]


def test_bloqueia_reducao_abaixo_do_ja_usado_em_tasks(monkeypatch):
    mock_sb = _make_mock_client(
        sprint_data={"id": "sprint-1", "project_id": "proj-1", "numero": 1, "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00"},
        tasks_na_sprint=[{"pontos": 8}, {"pontos": 5}],
        outras_sprints=[],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/sprint-1/orcamento", json={"pontos_orcamento": 10})

    assert resp.status_code == 409
    assert "13" in resp.json()["detail"]


def test_sprint_not_found(monkeypatch):
    mock_sb = _make_mock_client(sprint_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/does-not-exist/orcamento", json={"pontos_orcamento": 10})

    assert resp.status_code == 404
