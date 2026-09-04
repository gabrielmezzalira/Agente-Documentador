"""Testes para GET /performance (RBAC-04, RBAC-05)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_audit_client():
    client = MagicMock()
    calls = {"audit_insert": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "audit_log":
            def insert_side_effect(payload):
                calls["audit_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="audit-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def test_performance_sem_cookie_401(monkeypatch):
    from main import app
    tc = TestClient(app)

    resp = tc.get("/performance")

    assert resp.status_code == 401


def test_performance_nao_lider_retorna_403(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")

    resp = tc.get("/performance", cookies={"docudata_session": token})

    assert resp.status_code == 403


def test_performance_lider_200_grava_audit_log(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb, calls = _mock_audit_client()
    import services.audit as audit_service
    monkeypatch.setattr(audit_service, "get_client", lambda: mock_sb)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-lid-1", "lider@citi.com", "lider")

    resp = tc.get("/performance", cookies={"docudata_session": token})

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert len(calls["audit_insert"]) == 1
    assert calls["audit_insert"][0]["pessoa_email"] == "lider@citi.com"
    assert calls["audit_insert"][0]["rota"] == "/performance"
    assert calls["audit_insert"][0]["acao"] == "acesso"
