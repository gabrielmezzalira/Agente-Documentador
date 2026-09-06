"""Testes para POST /operacionais (duplicata case-insensitive) e DELETE /operacionais/{id} (cascade)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_create_mock_client(project_exists=True, existing_operacionais=None, insert_ok=True):
    existing_operacionais = existing_operacionais or []
    client = MagicMock()
    calls = {"insert": []}

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
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(existing_operacionais)
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                calls["insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = (
                    [dict(payload, id="new-op-id", ativo=True, created_at="2026-09-06T00:00:00+00:00")]
                    if insert_ok else []
                )
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.operacionais as operacionais_router
    monkeypatch.setattr(operacionais_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", "test@citi.com", "gerente"))
    return tc


def test_create_operacional_bloqueia_nome_duplicado_case_insensitive(monkeypatch):
    mock_sb, calls = _make_create_mock_client(
        existing_operacionais=[{"nome": "Gabriel Teste"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/operacionais", json={"project_id": "proj-1", "nome": "gabriel teste"})

    assert resp.status_code == 409
    assert "gabriel teste" in resp.json()["detail"]
    assert calls["insert"] == []


def test_create_operacional_bloqueia_nome_duplicado_com_espacos_extras(monkeypatch):
    mock_sb, calls = _make_create_mock_client(
        existing_operacionais=[{"nome": "Ana Silva"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/operacionais", json={"project_id": "proj-1", "nome": "  ANA SILVA  "})

    assert resp.status_code == 409
    assert calls["insert"] == []


def test_create_operacional_permite_nome_novo(monkeypatch):
    mock_sb, calls = _make_create_mock_client(
        existing_operacionais=[{"nome": "Ana Silva"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/operacionais", json={"project_id": "proj-1", "nome": "Bruno Costa"})

    assert resp.status_code == 201
    assert len(calls["insert"]) == 1
    assert calls["insert"][0]["nome"] == "Bruno Costa"


def _make_delete_mock_client(operacional_exists=True):
    client = MagicMock()
    calls = {"tasks_update": [], "operacionais_delete": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "op-1"}] if operacional_exists else []
                q.execute = MagicMock(return_value=resp)
                return q

            def delete_side_effect():
                q = MagicMock()

                def eq_side_effect(field, value):
                    calls["operacionais_delete"].append((field, value))
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [{"id": value}]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.delete = MagicMock(side_effect=delete_side_effect)
        elif name == "tasks":
            def update_side_effect(payload):
                q = MagicMock()

                def eq_side_effect(field, value):
                    calls["tasks_update"].append((payload, field, value))
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = []
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def test_delete_operacional_desvincula_tasks_e_apaga(monkeypatch):
    mock_sb, calls = _make_delete_mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/operacionais/op-1")

    assert resp.status_code == 204
    assert calls["tasks_update"] == [({"operacional_id": None}, "operacional_id", "op-1")]
    assert calls["operacionais_delete"] == [("id", "op-1")]


def test_delete_operacional_not_found(monkeypatch):
    mock_sb, calls = _make_delete_mock_client(operacional_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/operacionais/does-not-exist")

    assert resp.status_code == 404
    assert calls["tasks_update"] == []
    assert calls["operacionais_delete"] == []
