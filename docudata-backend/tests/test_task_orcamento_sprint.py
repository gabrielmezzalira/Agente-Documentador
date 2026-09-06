"""Testes para validação de orçamento de sprint (pontos_orcamento) ao criar/editar task."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(
    project_exists=True,
    sprint_data=None,
    tasks_na_sprint=None,
    task_atual=None,
    task_exists=True,
):
    client = MagicMock()
    calls = {"insert": [], "update": []}

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
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(sprint_data)] if sprint_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.neq = MagicMock(return_value=q)
                resp = MagicMock()
                if cols == "*":
                    resp.data = [dict(task_atual)] if task_exists and task_atual else []
                else:
                    resp.data = list(tasks_na_sprint) if tasks_na_sprint is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                calls["insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(
                    payload,
                    id="task-nova",
                    bloqueado=False,
                    created_at="2026-09-06T00:00:00+00:00",
                    updated_at="2026-09-06T00:00:00+00:00",
                )]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                calls["update"].append(payload)
                q = MagicMock()

                def eq_side_effect(field, value):
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(task_atual or {}, **payload, id=value)]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
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
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_create_task_bloqueado_quando_estoura_orcamento_da_sprint(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 7}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Nova task", "pontos": 5, "sprint_id": "sprint-1",
    })

    assert resp.status_code == 409
    assert "3" in resp.json()["detail"]
    assert calls["insert"] == []


def test_create_task_permitido_dentro_do_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 7}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Nova task", "pontos": 3, "sprint_id": "sprint-1",
    })

    assert resp.status_code == 201
    assert len(calls["insert"]) == 1


def test_create_task_sem_validacao_quando_sprint_sem_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": None},
        tasks_na_sprint=[{"pontos": 999}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Nova task", "pontos": 50, "sprint_id": "sprint-1",
    })

    assert resp.status_code == 201


def test_patch_task_bloqueado_quando_aumentar_pontos_estoura_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 6}],  # outras tasks, não inclui a própria
        task_atual={"id": "task-1", "project_id": "proj-1", "sprint_id": "sprint-1", "pontos": 4, "titulo": "Task existente", "coluna_kanban": "planejado", "operacional_id": None, "checklist": [], "bloqueado": False, "bloqueado_manual": False, "ordem": 0, "created_at": "2026-09-06T00:00:00+00:00"},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"pontos": 5})

    assert resp.status_code == 409
    assert calls["update"] == []


def test_patch_task_permitido_quando_dentro_do_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 6}],
        task_atual={"id": "task-1", "project_id": "proj-1", "sprint_id": "sprint-1", "pontos": 4, "titulo": "Task existente", "coluna_kanban": "planejado", "operacional_id": None, "checklist": [], "bloqueado": False, "bloqueado_manual": False, "ordem": 0, "created_at": "2026-09-06T00:00:00+00:00"},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"pontos": 4})

    assert resp.status_code == 200
    assert len(calls["update"]) == 1
