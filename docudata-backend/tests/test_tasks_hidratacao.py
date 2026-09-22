# tests/test_tasks_hidratacao.py (novo)
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, tasks_insert_capture=None, tasks_update_capture=None):
    tasks_insert_capture = tasks_insert_capture if tasks_insert_capture is not None else []
    tasks_update_capture = tasks_update_capture if tasks_update_capture is not None else []
    existente = {
        "id": "t1", "project_id": "proj-1", "titulo": "X", "pontos": 1,
        "coluna_kanban": "planejado", "operacional_id": None,
        "created_at": "2026-09-01T00:00:00+00:00",
        "updated_at": "2026-09-01T00:00:00+00:00", "bloqueado": False,
    }
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
                resp.data = [existente]
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                tasks_insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(existente, **payload, id="t-novo")]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                tasks_update_capture.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(existente, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
            tbl.insert = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_insert_capture, tasks_update_capture


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto):
        import routers.tasks as tasks_router
        from main import app
        client, ins, upd = _mock_client(projeto)
        monkeypatch.setattr(tasks_router, "get_client", lambda: client)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc, ins, upd
    return _make


def test_create_task_marca_rascunho_em_projeto_pull_com_hidratacao_exigida(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": True})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Sem descrição", "pontos": 2})

    assert resp.status_code == 201
    assert ins[0]["rascunho"] is True
    assert ins[0]["motivo_rascunho"] == "Faltam: descrição, checklist"


def test_create_task_nao_marca_rascunho_em_projeto_atribuicao(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Sem descrição", "pontos": 2})

    assert resp.status_code == 201
    assert "rascunho" not in ins[0]


def test_create_task_rejeita_operacional_id_em_projeto_pull(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": False})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 2, "operacional_id": "op-a"})

    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]
    assert ins == []


def test_create_task_em_atribuicao_nao_rejeita_por_causa_do_modo(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": False})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 2, "operacional_id": "op-a"})

    # 422 aqui vem da validação de "operacional_id não pertence a este
    # projeto" (fixture não cadastra operacionais) — a prova de que o gate
    # de PULL não é o motivo é a mensagem, não o status code.
    assert "Pull" not in resp.json()["detail"]
