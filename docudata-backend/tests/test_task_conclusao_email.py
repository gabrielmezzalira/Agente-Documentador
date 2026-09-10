"""Gerente/líder recebe e-mail quando um operacional marca uma task como
concluída. Se for o próprio gerente a mover a task, nenhum e-mail é disparado."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _make_mock_client(task_data):
    client = MagicMock()
    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]
    updated_row = dict(task_data)

    def table_side_effect(table_name):
        tbl = MagicMock()

        if table_name == "tasks":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.execute = MagicMock(return_value=task_select_resp)
                return query

            def update_side_effect(updates):
                query = MagicMock()

                def eq_then_execute(field, value):
                    exec_query = MagicMock()
                    merged = dict(updated_row)
                    merged.update(updates)
                    resp = MagicMock()
                    resp.data = [merged]
                    exec_query.execute = MagicMock(return_value=resp)
                    return exec_query

                query.eq = MagicMock(side_effect=eq_then_execute)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif table_name == "task_transicoes":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.order = MagicMock(return_value=query)
                query.limit = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)

            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif table_name == "operacionais":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"nome": "Davi"}]
                query.execute = MagicMock(return_value=resp)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
        elif table_name == "projects":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"name": "Projeto X"}]
                query.execute = MagicMock(return_value=resp)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
        elif table_name == "sprints":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"numero": 3}]
                query.execute = MagicMock(return_value=resp)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
        elif table_name == "pessoa":
            def select_side_effect(cols):
                query = MagicMock()
                query.in_ = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"email": "ger@citi.com"}]
                query.execute = MagicMock(return_value=resp)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
        else:
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _client_como(monkeypatch, mock_supabase, cargo: str):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", f"{cargo}@citi.com", cargo))
    return tc


_BASE_TASK = {
    "id": "task-1",
    "project_id": "proj-1",
    "titulo": "Fazer algo",
    "pontos": 2,
    "coluna_kanban": "em_andamento",
    "ordem": 0,
    "sprint_id": "sprint-1",
    "operacional_id": "op-1",
    "descricao": None,
    "bloqueado": False,
    "motivo_bloqueio": None,
    "checklist": [],
    "created_at": "2026-01-01T00:00:00+00:00",
}


def test_operacional_conclui_task_dispara_email_pro_gerente(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    import routers.tasks as tasks_router
    envios = []
    monkeypatch.setattr(
        tasks_router, "send_email",
        lambda to, subject, html: envios.append((to, subject, html)),
    )

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 200
    assert len(envios) == 1
    to, subject, html = envios[0]
    assert to == "ger@citi.com"
    assert "Fazer algo" in subject
    assert "Davi" in html


def test_gerente_conclui_task_nao_dispara_email(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "gerente")

    import routers.tasks as tasks_router
    envios = []
    monkeypatch.setattr(
        tasks_router, "send_email",
        lambda to, subject, html: envios.append((to, subject, html)),
    )

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 200
    assert len(envios) == 0
