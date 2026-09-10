"""Pedido de task extra aceita um texto livre opcional de sugestão, que é
persistido em solicitacoes_task.sugestao e vai junto no e-mail pro gerente."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _chain(data):
    q = MagicMock()
    q.eq = MagicMock(return_value=q)
    q.neq = MagicMock(return_value=q)
    q.order = MagicMock(return_value=q)
    q.limit = MagicMock(return_value=q)
    q.in_ = MagicMock(return_value=q)
    resp = MagicMock()
    resp.data = data
    q.execute = MagicMock(return_value=resp)
    return q


def _make_mock_client(insert_row):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            tbl.select = MagicMock(return_value=_chain([
                {"id": "op-1", "nome": "Davi", "project_id": "proj-1"}
            ]))
        elif name == "tasks":
            tbl.select = MagicMock(return_value=_chain([]))  # sem tasks abertas
        elif name == "solicitacoes_task":
            tbl.select = MagicMock(return_value=_chain([]))  # sem pedido pendente
            tbl.insert = MagicMock(return_value=_chain([insert_row]))
        elif name == "projects":
            tbl.select = MagicMock(return_value=_chain([{"name": "Projeto X"}]))
        elif name == "pessoa":
            tbl.select = MagicMock(return_value=_chain([{"email": "ger@citi.com"}]))
        else:
            tbl.select = MagicMock(return_value=_chain([]))
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.solicitacoes as solicitacoes_router
    monkeypatch.setattr(solicitacoes_router, "get_client", lambda: mock_supabase)
    monkeypatch.setattr(solicitacoes_router, "get_current_sprint_id", lambda client, project_id: None)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-op-1", "davi@citi.com", "operacional"))
    return tc


def test_solicitacao_com_sugestao_e_persistida_e_retornada(monkeypatch):
    insert_row = {
        "id": "sol-1", "project_id": "proj-1", "sprint_id": None, "operacional_id": "op-1",
        "sugestao": "Acho que faltou revisar o ROPA da Sprint 2",
        "status": "pendente", "criado_em": "2026-01-01T00:00:00+00:00", "respondido_em": None,
    }
    mock_sb = _make_mock_client(insert_row)
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/solicitacoes-task", json={
        "operacional_id": "op-1",
        "sugestao": "Acho que faltou revisar o ROPA da Sprint 2",
    })

    assert resp.status_code == 201
    assert resp.json()["sugestao"] == "Acho que faltou revisar o ROPA da Sprint 2"


def test_solicitacao_envia_email_com_sugestao(monkeypatch):
    insert_row = {
        "id": "sol-1", "project_id": "proj-1", "sprint_id": None, "operacional_id": "op-1",
        "sugestao": "Dá pra automatizar o relatório semanal",
        "status": "pendente", "criado_em": "2026-01-01T00:00:00+00:00", "respondido_em": None,
    }
    mock_sb = _make_mock_client(insert_row)
    tc = _client(monkeypatch, mock_sb)

    import routers.solicitacoes as solicitacoes_router
    envios = []
    monkeypatch.setattr(
        solicitacoes_router, "send_email",
        lambda to, subject, html: envios.append((to, subject, html)),
    )

    resp = tc.post("/solicitacoes-task", json={
        "operacional_id": "op-1",
        "sugestao": "Dá pra automatizar o relatório semanal",
    })

    assert resp.status_code == 201
    assert len(envios) == 1
    to, subject, html = envios[0]
    assert to == "ger@citi.com"
    assert "Dá pra automatizar o relatório semanal" in html


def test_solicitacao_sem_sugestao_continua_funcionando(monkeypatch):
    insert_row = {
        "id": "sol-1", "project_id": "proj-1", "sprint_id": None, "operacional_id": "op-1",
        "sugestao": None,
        "status": "pendente", "criado_em": "2026-01-01T00:00:00+00:00", "respondido_em": None,
    }
    mock_sb = _make_mock_client(insert_row)
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/solicitacoes-task", json={"operacional_id": "op-1"})

    assert resp.status_code == 201
    assert resp.json()["sugestao"] is None
