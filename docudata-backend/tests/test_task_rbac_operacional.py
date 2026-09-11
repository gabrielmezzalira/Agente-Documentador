"""Operacional só executa a task (move status no kanban, marca checklist) —
não edita pontos/sprint/responsável/título/descrição, não cria e não exclui
tasks, e não redistribui pontos da sprint. Gerente/líder continuam livres."""
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


def test_operacional_nao_pode_alterar_pontos(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.patch("/tasks/task-1", json={"pontos": 5})
    assert resp.status_code == 403
    assert "pontos" in resp.json()["detail"]


def test_operacional_nao_pode_reatribuir_responsavel(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.patch("/tasks/task-1", json={"operacional_id": "op-2"})
    assert resp.status_code == 403
    assert "operacional_id" in resp.json()["detail"]


def test_operacional_nao_pode_excluir_task(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.delete("/tasks/task-1")
    assert resp.status_code == 403


def test_operacional_nao_pode_criar_task(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 1})
    assert resp.status_code == 403


def test_operacional_nao_pode_redistribuir_pontos(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.post("/tasks/redistribuir-pontos", json={"sprint_id": "sprint-1", "pontos_novos": 2})
    assert resp.status_code == 403


def test_operacional_pode_mover_coluna_kanban(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200


def test_operacional_pode_marcar_checklist(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.patch("/tasks/task-1", json={"checklist": [{"texto": "item", "done": True}]})
    assert resp.status_code == 200


def test_gerente_ainda_pode_alterar_pontos(monkeypatch):
    mock_sb = _make_mock_client(_BASE_TASK)
    tc = _client_como(monkeypatch, mock_sb, "gerente")

    resp = tc.patch("/tasks/task-1", json={"pontos": 5})
    assert resp.status_code == 200
