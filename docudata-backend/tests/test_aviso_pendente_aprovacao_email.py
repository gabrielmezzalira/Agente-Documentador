"""Entrega Pendente de aprovação: aviso por email ao entrar em aprovação
(gerente/líder) e ao rejeitar (operacional). Mesmo padrão best-effort de
_avisar_gerente_task_concluida. Ver spec §7."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.email_service import email_task_pendente_aprovacao, email_task_rejeitada


def test_email_task_pendente_aprovacao_conteudo():
    subject, html = email_task_pendente_aprovacao("Projeto X", "Davi", "Fazer algo")
    assert "Fazer algo" in subject
    assert "Davi" in html
    assert "Projeto X" in html


def test_email_task_rejeitada_conteudo():
    subject, html = email_task_rejeitada("Projeto X", "Fazer algo", "Faltou o teste unitário")
    assert "Fazer algo" in subject
    assert "Faltou o teste unitário" in html
    assert "Projeto X" in html


def _mock_client(task):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"nome": "Davi", "email": "davi@citi.com"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"name": "Projeto X"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "pessoa":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"email": "ger@citi.com"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "em_andamento", "ordem": 0, "sprint_id": "sprint-1",
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": False, "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(cargo="gerente"):
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(_TASK)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        envios = []
        monkeypatch.setattr(
            tasks_router, "send_email",
            lambda to, subject, html: envios.append((to, subject, html)),
        )
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, envios
    return _make


def test_entrar_em_pendente_aprovacao_avisa_gerente(make_client):
    tc, envios = make_client()

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 200
    assert len(envios) == 1
    to, subject, html = envios[0]
    assert to == "ger@citi.com"
    assert "Fazer algo" in subject
