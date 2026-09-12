"""Testes para o cálculo automático de 'planejado vs. entregue' a partir do kanban."""
from unittest.mock import MagicMock

from services.sprints import compute_planejado_vs_entregue


def _make_mock_client(sprint_data=None, tasks=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(sprint_data) if sprint_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(tasks) if tasks is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_marca_entregue_sim_para_tasks_concluidas():
    client = _make_mock_client(
        sprint_data=[{"id": "sprint-1"}],
        tasks=[{"titulo": "Ajustar endpoint de login", "coluna_kanban": "concluida"}],
    )

    resultado = compute_planejado_vs_entregue(client, "proj-1", 3)

    assert resultado == [{
        "item": "Ajustar endpoint de login",
        "entregue": "S",
        "motivo_nao": "",
        "causa_raiz_num": "",
    }]


def test_marca_entregue_nao_para_tasks_nao_concluidas():
    client = _make_mock_client(
        sprint_data=[{"id": "sprint-1"}],
        tasks=[{"titulo": "Configurar CI", "coluna_kanban": "em_andamento"}],
    )

    resultado = compute_planejado_vs_entregue(client, "proj-1", 3)

    assert resultado[0]["entregue"] == "N"
    assert resultado[0]["motivo_nao"] == ""
    assert resultado[0]["causa_raiz_num"] == ""


def test_lista_vazia_quando_sprint_nao_existe():
    client = _make_mock_client(sprint_data=[], tasks=[])

    resultado = compute_planejado_vs_entregue(client, "proj-1", 99)

    assert resultado == []


def test_lista_vazia_quando_sprint_sem_tasks():
    client = _make_mock_client(sprint_data=[{"id": "sprint-1"}], tasks=[])

    resultado = compute_planejado_vs_entregue(client, "proj-1", 3)

    assert resultado == []
