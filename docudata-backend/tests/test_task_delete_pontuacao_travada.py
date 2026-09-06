"""Testes para DELETE /tasks/{id} bloqueando exclusão quando a pontuação da sprint já está travada."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data=None, sprint_data=None, task_exists=True):
    client = MagicMock()
    calls = {"tasks_delete": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task_data)] if task_exists else []
                q.execute = MagicMock(return_value=resp)
                return q

            def delete_side_effect():
                q = MagicMock()

                def eq_side_effect(field, value):
                    calls["tasks_delete"].append((field, value))
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [{"id": value}]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.delete = MagicMock(side_effect=delete_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(sprint_data)] if sprint_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

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


def test_delete_task_bloqueado_quando_pontuacao_ja_travada(monkeypatch):
    mock_sb, calls = _make_mock_client(
        task_data={"id": "task-1", "sprint_id": "sprint-1"},
        sprint_data={"avaliacao_completa_em": "2026-09-01T00:00:00+00:00"},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/task-1")

    assert resp.status_code == 409
    assert "travad" in resp.json()["detail"].lower()
    assert calls["tasks_delete"] == []


def test_delete_task_permitido_quando_sprint_sem_avaliacao_confirmada(monkeypatch):
    mock_sb, calls = _make_mock_client(
        task_data={"id": "task-1", "sprint_id": "sprint-1"},
        sprint_data={"avaliacao_completa_em": None},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/task-1")

    assert resp.status_code == 204
    assert calls["tasks_delete"] == [("id", "task-1")]


def test_delete_task_permitido_quando_task_sem_sprint(monkeypatch):
    mock_sb, calls = _make_mock_client(
        task_data={"id": "task-1", "sprint_id": None},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/task-1")

    assert resp.status_code == 204
    assert calls["tasks_delete"] == [("id", "task-1")]


def test_delete_task_not_found(monkeypatch):
    mock_sb, calls = _make_mock_client(task_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/does-not-exist")

    assert resp.status_code == 404
