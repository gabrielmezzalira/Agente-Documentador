"""Pull: arrastar uma task da fila (sem dono) de Planejado para Em andamento é
puxar — quem arrastou vira o responsável. Antes a coluna mudava e a task ficava
sem dono (caso real do projeto ARA em 2026-11-11)."""
import pytest
from fastapi.testclient import TestClient

from tests.test_tasks_pull_lock_atribuicao import _TASK_BASE, _mock_client

_TASK = dict(_TASK_BASE, sprint_id="sp-1")


@pytest.fixture
def cliente(monkeypatch, autenticar):
    def _make(modo="PULL", cargo="operacional", vinculado=True):
        import routers.tasks as tasks_router
        from main import app
        monkeypatch.setattr(tasks_router, "get_client", lambda: _mock_client({"id": "proj-1", "modo_trabalho": modo}, _TASK))
        monkeypatch.setattr(tasks_router, "_resolver_operacional_id_da_pessoa",
                            lambda *a: "op-9" if vinculado else None)
        return autenticar(TestClient(app), cargo=cargo)
    return _make


def test_arrastar_para_em_andamento_em_pull_atribui_quem_arrastou(cliente):
    resp = cliente().patch("/tasks/task-1", json={"coluna_kanban": "em_andamento", "autor": "Victor"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["operacional_id"] == "op-9"
    assert corpo["coluna_kanban"] == "em_andamento"
    assert corpo["pull_em"]


def test_arrastar_da_fila_direto_para_pendente_em_pull_e_recusado(cliente):
    resp = cliente().patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 422
    assert "puxada" in resp.json()["detail"]


def test_quem_nao_esta_no_projeto_nao_puxa_arrastando(cliente):
    resp = cliente(cargo="gerente", vinculado=False).patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 422
    assert "Peça para a pessoa puxar" in resp.json()["detail"]


def test_em_atribuicao_arrastar_continua_sem_atribuir(cliente):
    resp = cliente(modo="ATRIBUICAO", cargo="gerente").patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 200
    assert resp.json()["operacional_id"] is None
