"""Testes para POST /auth/login (RBAC-01)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import hash_senha


def _mock_client_com_pessoa(pessoa_row):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pessoa":
            def select_side_effect(cols):
                query = MagicMock()

                def eq_side_effect(field, value):
                    resp = MagicMock()
                    resp.data = [pessoa_row] if pessoa_row and pessoa_row.get(field) == value else []
                    q = MagicMock()
                    q.execute = MagicMock(return_value=resp)
                    return q

                query.eq = MagicMock(side_effect=eq_side_effect)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.auth as auth_router
    monkeypatch.setattr(auth_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(app)


_PESSOA = {
    "id": "pessoa-1",
    "email": "gerente@citi.com",
    "nome": "Gerente Um",
    "senha_hash": hash_senha("senha-correta"),
    "cargo": "gerente",
}


def test_login_valido_seta_cookie_e_retorna_nome_cargo(monkeypatch):
    mock_sb = _mock_client_com_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/login", json={"email": "gerente@citi.com", "senha": "senha-correta"})

    assert resp.status_code == 200
    assert resp.json() == {"nome": "Gerente Um", "cargo": "gerente"}
    assert resp.cookies.get("docudata_session") is not None


def test_login_senha_errada_401(monkeypatch):
    mock_sb = _mock_client_com_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/login", json={"email": "gerente@citi.com", "senha": "errada"})

    assert resp.status_code == 401


def test_login_email_inexistente_401(monkeypatch):
    mock_sb = _mock_client_com_pessoa(None)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/login", json={"email": "ninguem@citi.com", "senha": "qualquer"})

    assert resp.status_code == 401
