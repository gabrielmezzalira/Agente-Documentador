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
