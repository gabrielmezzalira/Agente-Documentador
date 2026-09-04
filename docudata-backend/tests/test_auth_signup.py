"""Testes para POST /auth/signup/claim e /auth/signup/novo."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.auth as auth_router
    monkeypatch.setattr(auth_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(app)


def _mock_client(operacional_row=None, pessoa_existente=None):
    client = MagicMock()
    calls = {"pessoa_insert": [], "operacionais_update": []}

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "operacionais":
            def select_side_effect(cols):
                query = MagicMock()

                def eq_side_effect(field, value):
                    resp = MagicMock()
                    resp.data = [operacional_row] if operacional_row and operacional_row.get(field) == value else []
                    q = MagicMock()
                    q.execute = MagicMock(return_value=resp)
                    return q

                query.eq = MagicMock(side_effect=eq_side_effect)
                return query

            def update_side_effect(payload):
                calls["operacionais_update"].append(payload)
                q = MagicMock()
                inner = MagicMock()
                resp = MagicMock()
                resp.data = [dict(operacional_row or {}, **payload)]
                inner.execute = MagicMock(return_value=resp)
                q.eq = MagicMock(return_value=inner)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)

        elif name == "pessoa":
            def select_side_effect(cols):
                query = MagicMock()

                def eq_side_effect(field, value):
                    resp = MagicMock()
                    resp.data = [pessoa_existente] if pessoa_existente and pessoa_existente.get(field) == value else []
                    q = MagicMock()
                    q.execute = MagicMock(return_value=resp)
                    return q

                query.eq = MagicMock(side_effect=eq_side_effect)
                return query

            def insert_side_effect(payload):
                calls["pessoa_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="pessoa-nova-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


_OPERACIONAL = {"id": "op-1", "nome": "Ana Op", "email": "ana@citi.com", "project_id": "proj-1"}


def test_claim_com_email_batendo_cria_pessoa_e_loga(monkeypatch):
    mock_sb, calls = _mock_client(operacional_row=_OPERACIONAL)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/signup/claim", json={
        "operacional_id": "op-1", "email": "ana@citi.com", "senha": "senha123",
    })

    assert resp.status_code == 201
    assert resp.json() == {"nome": "Ana Op", "cargo": "operacional"}
    assert resp.cookies.get("docudata_session") is not None
    assert calls["pessoa_insert"][0]["cargo"] == "operacional"
    assert calls["pessoa_insert"][0]["email"] == "ana@citi.com"


def test_claim_email_nao_bate_403(monkeypatch):
    mock_sb, calls = _mock_client(operacional_row=_OPERACIONAL)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/signup/claim", json={
        "operacional_id": "op-1", "email": "outra@citi.com", "senha": "senha123",
    })

    assert resp.status_code == 403
    assert len(calls["pessoa_insert"]) == 0


def test_claim_email_duplicado_409(monkeypatch):
    pessoa_existente = {"id": "pessoa-x", "email": "ana@citi.com"}
    mock_sb, calls = _mock_client(operacional_row=_OPERACIONAL, pessoa_existente=pessoa_existente)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/signup/claim", json={
        "operacional_id": "op-1", "email": "ana@citi.com", "senha": "senha123",
    })

    assert resp.status_code == 409
    assert len(calls["pessoa_insert"]) == 0


def test_signup_novo_cria_pessoa_sem_operacionais(monkeypatch):
    mock_sb, calls = _mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/signup/novo", json={
        "nome": "Bruno Novo", "email": "bruno@citi.com", "senha": "senha123",
    })

    assert resp.status_code == 201
    assert resp.json() == {"nome": "Bruno Novo", "cargo": "operacional"}
    assert calls["pessoa_insert"][0]["cargo"] == "operacional"
    assert len(calls["operacionais_update"]) == 0


def test_signup_novo_email_duplicado_409(monkeypatch):
    pessoa_existente = {"id": "pessoa-x", "email": "bruno@citi.com"}
    mock_sb, calls = _mock_client(pessoa_existente=pessoa_existente)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/signup/novo", json={
        "nome": "Bruno Novo", "email": "bruno@citi.com", "senha": "senha123",
    })

    assert resp.status_code == 409
    assert len(calls["pessoa_insert"]) == 0
