"""Correções da auditoria 2026-11-17: tasks (Pull x Atribuição, RBAC, puxar/devolver)."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.test_pull_devolver import make_client  # noqa: F401  (fixture)
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


def test_operacional_edita_checklist_de_task_da_fila_em_pull_403(cliente_para):
    task = dict(_TASK_BASE, operacional_id=None, coluna_kanban="planejado", sprint_id="sp-1")
    resp = cliente_para("PULL", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"checklist": []})
    assert resp.status_code == 403


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


_OP = {"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"}


def _task(**kw):
    base = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False,
            "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
            "travado_automatico": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    base.update(kw)
    return base


def test_puxar_sem_sprint_da_409(make_client):
    resp = make_client(_task(), _OP).post("/tasks/t1/puxar")
    assert resp.status_code == 409
    assert "DoR" in resp.json()["detail"]


def test_puxar_com_sprint_funciona(make_client):
    resp = make_client(_task(sprint_id="sprint-1"), _OP).post("/tasks/t1/puxar")
    assert resp.status_code == 200


def test_devolver_task_concluida_da_422(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="concluida"), _OP).post("/tasks/t1/devolver")
    assert resp.status_code == 422


def test_devolver_em_projeto_atribuicao_da_422(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="em_andamento"), _OP,
                       modo_trabalho="ATRIBUICAO").post("/tasks/t1/devolver")
    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]


def test_devolver_planejado_com_dono_libera_para_fila(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="planejado", sprint_id="sprint-1"), _OP).post("/tasks/t1/devolver")
    assert resp.status_code == 200


def test_devolver_em_andamento_em_pull_continua_200(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="em_andamento"), _OP).post("/tasks/t1/devolver")
    assert resp.status_code == 200



def _capturar_dispensa(tc):
    capturas = []
    filtros = []
    original = tc._mock_sb.table.side_effect

    def tabela(nome):
        tbl = original(nome)
        if nome == "task_travamentos":
            def upd(payload):
                capturas.append(payload)
                q = MagicMock()
                def eq(col, val):
                    filtros.append((col, val))
                    return q
                q.eq = MagicMock(side_effect=eq)
                return q
            tbl.update = MagicMock(side_effect=upd)
        return tbl

    tc._mock_sb.table = MagicMock(side_effect=tabela)
    return capturas, filtros


def test_devolver_task_travada_dispensa_os_travamentos(make_client):
    task = _task(operacional_id="op-a", coluna_kanban="em_andamento", travado_automatico=True, sprint_id="sprint-1")
    tc = make_client(task, _OP, task_travamentos=[{"pontos": 3, "dispensado": False}])
    capturas, filtros = _capturar_dispensa(tc)
    resp = tc.post("/tasks/t1/devolver")
    assert resp.status_code == 200
    assert capturas == [{"dispensado": True}]
    assert filtros == [("task_id", "t1"), ("dispensado", False)]
