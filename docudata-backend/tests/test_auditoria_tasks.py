"""Correções da auditoria 2026-11-17: tasks (Pull x Atribuição, RBAC, puxar/devolver)."""
import pytest
from fastapi.testclient import TestClient

from tests.test_tasks_pull_lock_atribuicao import _TASK_BASE, _mock_client


@pytest.fixture
def cliente_para(monkeypatch, autenticar):
    def _make(modo, task, cargo="gerente", meu_operacional="op-9"):
        import routers.tasks as tasks_router
        from main import app
        monkeypatch.setattr(tasks_router, "get_client",
                            lambda: _mock_client({"id": "proj-1", "modo_trabalho": modo}, task))
        monkeypatch.setattr(tasks_router, "_resolver_operacional_id_da_pessoa", lambda *a: meu_operacional)
        return autenticar(TestClient(app), cargo=cargo)
    return _make


def test_pull_aceita_operacional_id_igual_ao_atual(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("PULL", task).patch("/tasks/task-1", json={"operacional_id": "op-2", "bloqueado": False})
    assert resp.status_code == 200


def test_pull_continua_recusando_trocar_responsavel(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("PULL", task).patch("/tasks/task-1", json={"operacional_id": "op-3"})
    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]


def test_atribuicao_null_explicito_desatribui(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2")
    resp = cliente_para("ATRIBUICAO", task).patch("/tasks/task-1", json={"operacional_id": None})
    assert resp.status_code == 200
    assert resp.json()["operacional_id"] is None


def test_atribuicao_sem_o_campo_nao_desatribui(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2")
    resp = cliente_para("ATRIBUICAO", task).patch("/tasks/task-1", json={"titulo": "Novo título"})
    assert resp.json()["operacional_id"] == "op-2"


def test_pull_null_explicito_em_task_com_dono_e_422(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2")
    resp = cliente_para("PULL", task).patch("/tasks/task-1", json={"operacional_id": None})
    assert resp.status_code == 422


def test_operacional_nao_move_task_de_colega(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 403


def test_operacional_move_a_propria_task(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-9", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200


def test_operacional_fora_da_equipe_e_403(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-9", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional=None).patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 403


def test_operacional_puxa_da_fila_em_pull_arrastando(cliente_para):
    task = dict(_TASK_BASE, operacional_id=None, coluna_kanban="planejado", sprint_id="sp-1")
    resp = cliente_para("PULL", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200
    assert resp.json()["operacional_id"] == "op-9"


def test_operacional_nao_move_task_sem_dono_fora_da_fila(cliente_para):
    task = dict(_TASK_BASE, operacional_id=None, coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("PULL", task, cargo="operacional").patch("/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 403


def test_mover_endpoint_tambem_barra_task_de_colega(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional="op-9").post(
        "/tasks/task-1/mover", params={"coluna_destino": "planejado"})
    assert resp.status_code == 403


def test_gerente_continua_movendo_qualquer_task(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="gerente", meu_operacional=None).patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200
