"""Revisão final, achado crítico #1: `requer_aprovacao` era aceito pelos
schemas e enviado pelo frontend, mas nem create_task nem patch_task o
colocavam no payload que vai pro Supabase — a coluna ficava eternamente no
default `false` e o gate de patch_task (`coluna_nova == "concluida" and
task.get("requer_aprovacao")`) nunca disparava.

Estes testes capturam o payload real de insert/update (não injetam a flag num
dict de task mockado, que é exatamente como o bug passou despercebido nos
testes existentes de pendente_aprovacao).
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task=None, tasks_insert=None, tasks_update=None):
    tasks_insert = tasks_insert if tasks_insert is not None else []
    tasks_update = tasks_update if tasks_update is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.neq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)] if task else []
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                tasks_insert.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(
                    payload,
                    id="task-nova",
                    bloqueado=False,
                    created_at="2026-01-01T00:00:00+00:00",
                    updated_at="2026-01-01T00:00:00+00:00",
                )]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                tasks_update.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task or {}, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "wip_config": {}}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            q.limit = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "em_andamento", "ordem": 0, "sprint_id": None,
    "operacional_id": None, "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": False, "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task=None, cargo="gerente"):
        import routers.tasks as tasks_router
        from main import app
        tasks_insert: list = []
        tasks_update: list = []
        mock_sb = _mock_client(task, tasks_insert, tasks_update)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, tasks_insert, tasks_update
    return _make


def test_create_task_persiste_requer_aprovacao_true(make_client):
    tc, tasks_insert, _ = make_client()

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Task com aprovação", "pontos": 3,
        "requer_aprovacao": True,
    })

    assert resp.status_code == 201
    assert len(tasks_insert) == 1
    assert tasks_insert[0]["requer_aprovacao"] is True


def test_create_task_persiste_requer_aprovacao_false_por_default(make_client):
    tc, tasks_insert, _ = make_client()

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Task normal", "pontos": 3,
    })

    assert resp.status_code == 201
    # A chave tem que ir explicitamente no insert (não ficar de fora "porque o
    # banco tem default") — assim o contrato vale mesmo se o default mudar.
    assert tasks_insert[0]["requer_aprovacao"] is False


def test_patch_task_persiste_requer_aprovacao_true(make_client):
    tc, _, tasks_update = make_client(task=_TASK)

    resp = tc.patch("/tasks/task-1", json={"requer_aprovacao": True})

    assert resp.status_code == 200
    assert len(tasks_update) == 1
    assert tasks_update[0]["requer_aprovacao"] is True
    assert resp.json()["requer_aprovacao"] is True


def test_patch_task_persiste_requer_aprovacao_false(make_client):
    """False é valor real, não "campo não enviado" — desmarcar o checkbox tem
    que chegar ao banco."""
    task = {**_TASK, "requer_aprovacao": True}
    tc, _, tasks_update = make_client(task=task)

    resp = tc.patch("/tasks/task-1", json={"requer_aprovacao": False})

    assert resp.status_code == 200
    assert tasks_update[0]["requer_aprovacao"] is False


def test_patch_task_sem_requer_aprovacao_nao_toca_no_campo(make_client):
    tc, _, tasks_update = make_client(task=_TASK)

    resp = tc.patch("/tasks/task-1", json={"titulo": "Outro título"})

    assert resp.status_code == 200
    assert "requer_aprovacao" not in tasks_update[0]


def test_gate_de_conclusao_direta_dispara_com_a_flag_persistida(make_client):
    """Fecha o circuito: com requer_aprovacao=true no banco, o caminho rápido
    em_andamento -> concluida é recusado com 422."""
    task = {**_TASK, "requer_aprovacao": True}
    tc, _, tasks_update = make_client(task=task)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 422
    assert "aprovação" in resp.json()["detail"]
    assert tasks_update == []
