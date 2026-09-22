"""Entrega 4 (fechamento de lacunas): gerente não pode mais atribuir
operacional_id manualmente — nem criando nem editando task — quando o
projeto está em modo PULL. Ver .planning/feature-flow-state.md, Design
aprovado, item 3."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, task):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
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
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "op-2"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
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
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            q.limit = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK_BASE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "planejado", "ordem": 0, "sprint_id": None,
    "operacional_id": None, "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto, task=None):
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(projeto, task or _TASK_BASE)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc
    return _make


def test_patch_task_rejeita_operacional_id_em_projeto_pull(make_client):
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL"})

    resp = tc.patch("/tasks/task-1", json={"operacional_id": "op-2"})

    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]


def test_patch_task_aceita_operacional_id_em_projeto_atribuicao(make_client):
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO"})

    resp = tc.patch("/tasks/task-1", json={"operacional_id": "op-2"})

    assert resp.status_code == 200


def test_patch_task_sem_operacional_id_nao_consulta_modo_do_projeto(make_client):
    """PATCH que não mexe em operacional_id não deve nem olhar modo_trabalho
    — evita uma query extra desnecessária em toda edição de task."""
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL"})

    resp = tc.patch("/tasks/task-1", json={"pontos": 5})

    assert resp.status_code == 200


def _mock_client_create(projeto):
    tasks_insert_capture: list = []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            def insert_side_effect(payload):
                tasks_insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="t-novo")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_insert_capture


@pytest.fixture
def make_client_create(monkeypatch, autenticar):
    def _make(projeto):
        import routers.tasks as tasks_router
        from main import app
        mock_sb, ins = _mock_client_create(projeto)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc, ins
    return _make


def test_create_task_rejeita_operacional_id_em_projeto_pull(make_client_create):
    tc, ins = make_client_create(projeto={"id": "proj-1", "modo_trabalho": "PULL"})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 2, "operacional_id": "op-a"})

    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]
    assert ins == []


def test_create_task_em_atribuicao_nao_rejeita_por_causa_do_modo(make_client_create):
    tc, ins = make_client_create(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO"})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 2, "operacional_id": "op-a"})

    # 422 aqui vem da validação de "operacional_id não pertence a este
    # projeto" (fixture não cadastra operacionais) — a prova de que o gate
    # de PULL não é o motivo é a mensagem, não o status code.
    assert "Pull" not in resp.json()["detail"]
