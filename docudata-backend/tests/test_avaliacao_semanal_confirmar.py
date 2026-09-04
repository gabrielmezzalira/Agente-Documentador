"""Testes para POST /avaliacoes/{sprint_id}/confirmar (AVAL-02)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(tasks=None, operacionais=None, avaliacoes=None, sprint_update_ok=True):
    tasks = tasks or []
    operacionais = operacionais or []
    avaliacoes = avaliacoes or []
    client = MagicMock()
    calls = {"sprint_update": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
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
        elif name == "sprints":
            def update_side_effect(payload):
                calls["sprint_update"].append(payload)
                q = MagicMock()
                inner = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="sprint-1")] if sprint_update_ok else []
                inner.execute = MagicMock(return_value=resp)
                q.eq = MagicMock(return_value=inner)
                return q
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")
    tc.cookies.set("docudata_session", token)
    return tc


def test_confirma_com_todas_pendencias_resolvidas(monkeypatch):
    mock_sb, calls = _mock_client(
        tasks=[{"operacional_id": "op-1"}],
        operacionais=[{"id": "op-1", "nome": "Ana", "email": None, "project_id": "proj-1"}],
        avaliacoes=[{"operacional_id": "op-1", "sprint_id": "sprint-1"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/avaliacoes/sprint-1/confirmar")

    assert resp.status_code == 200
    assert len(calls["sprint_update"]) == 1
    assert "avaliacao_completa_em" in calls["sprint_update"][0]


def test_confirma_com_pendencia_retorna_409(monkeypatch):
    mock_sb, calls = _mock_client(
        tasks=[{"operacional_id": "op-1"}],
        operacionais=[{"id": "op-1", "nome": "Ana", "email": None, "project_id": "proj-1"}],
        avaliacoes=[],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/avaliacoes/sprint-1/confirmar")

    assert resp.status_code == 409
    assert "Ana" in resp.json()["detail"]
    assert len(calls["sprint_update"]) == 0
