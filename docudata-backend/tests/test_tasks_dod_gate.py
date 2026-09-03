"""
Testes para o gate de DoD (Definition of Done) em PATCH /tasks/{id} (MET-08).

Casos cobertos (per PLAN.md <behavior>):
  1. checklist com item done=false -> 409, detail contém "DoD"
  2. checklist com todos os itens done=true -> 200
  3. checklist vazio ou item sem a chave "done" -> vazio permite (200);
     item sem "done" bloqueia (409), via semântica .get("done")
  4. mover para coluna != "concluida" não é afetado pelo gate
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data):
    """
    Mock do cliente Supabase para PATCH /tasks/{id}.

    task_data: dict representando a task atual retornada por
      tasks.select("*").eq("id", ...).execute()
    """
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
                resp.data = [payload]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif table_name in ("operacionais", "sprints"):
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
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


def _patch_and_client(monkeypatch, mock_supabase):
    """Injeta o mock via monkeypatch no módulo routers.tasks, que o router importa diretamente."""
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(app)


_BASE_TASK = {
    "id": "task-1",
    "project_id": "proj-1",
    "titulo": "Fazer algo",
    "pontos": 2,
    "coluna_kanban": "em_andamento",
    "ordem": 0,
    "sprint_id": "sprint-1",
    "operacional_id": None,
    "descricao": None,
    "bloqueado": False,
    "motivo_bloqueio": None,
    "checklist": [],
    "created_at": "2026-01-01T00:00:00+00:00",
}


def test_dod_bloqueia_com_item_pendente(monkeypatch):
    task = dict(_BASE_TASK, checklist=[{"texto": "item 1", "done": True}, {"texto": "item 2", "done": False}])
    mock_sb = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 409
    assert "DoD" in resp.json()["detail"]


def test_dod_permite_com_checklist_completo(monkeypatch):
    task = dict(_BASE_TASK, checklist=[{"texto": "item 1", "done": True}, {"texto": "item 2", "done": True}])
    mock_sb = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200


def test_dod_checklist_vazio_permite(monkeypatch):
    task = dict(_BASE_TASK, checklist=[])
    mock_sb = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200


def test_dod_item_sem_chave_done_bloqueia(monkeypatch):
    task = dict(_BASE_TASK, checklist=[{"texto": "item sem done"}])
    mock_sb = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 409
    assert "DoD" in resp.json()["detail"]


def test_dod_nao_afeta_movimento_para_outra_coluna(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="planejado", checklist=[{"texto": "item", "done": False}], sprint_id="sprint-1")
    mock_sb = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200
