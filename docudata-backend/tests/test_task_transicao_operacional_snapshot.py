"""Testes para o snapshot de operacional_id em task_transicoes (Phase 18).

O snapshot grava, em toda transição registrada, quem estava alocado na task
ANTES da mudança — necessário pro Motor de Score reconstruir "quem completou"
mesmo que a task tenha sido reatribuída depois.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data):
    client = MagicMock()
    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]
    updated_row = dict(task_data)

    calls = {"tasks_update": [], "task_transicoes_insert": []}

    def table_side_effect(table_name):
        tbl = MagicMock()

        if table_name == "tasks":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.execute = MagicMock(return_value=task_select_resp)
                return query

            def update_side_effect(updates):
                calls["tasks_update"].append(updates)
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

            def insert_side_effect(payload):
                calls["task_transicoes_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id=f"transicao-{len(calls['task_transicoes_insert'])}")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif table_name == "operacionais":
            def select_side_effect(cols):
                query = MagicMock()
                # Mock returns data for any operacional_id check (allowing validation to pass)
                matching_op = MagicMock()
                matching_op.data = [{"id": "op-antigo"}, {"id": "op-novo"}]
                query.eq = MagicMock(return_value=query)
                query.execute = MagicMock(return_value=matching_op)
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
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", "test@citi.com", "gerente"))
    return tc


_BASE_TASK = {
    "id": "task-1",
    "project_id": "proj-1",
    "titulo": "Fazer algo",
    "pontos": 2,
    "coluna_kanban": "planejado",
    "ordem": 0,
    "sprint_id": "sprint-1",
    "operacional_id": "op-1",
    "descricao": None,
    "bloqueado": False,
    "motivo_bloqueio": None,
    "checklist": [],
    "contador_reaberturas": 0,
    "created_at": "2026-01-01T00:00:00+00:00",
}


def test_transicao_de_coluna_grava_operacional_id_anterior(monkeypatch):
    task = dict(_BASE_TASK)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 200
    assert len(calls["task_transicoes_insert"]) == 1
    assert calls["task_transicoes_insert"][0]["operacional_id"] == "op-1"


def test_transicao_de_reatribuicao_grava_operacional_id_antigo_nao_o_novo(monkeypatch):
    task = dict(_BASE_TASK, operacional_id="op-antigo")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"operacional_id": "op-novo"})

    assert resp.status_code == 200
    transicao = next(t for t in calls["task_transicoes_insert"] if t["campo"] == "operacional_id")
    assert transicao["operacional_id"] == "op-antigo"
