"""Testes para services/avaliacoes.py::contar_avaliacao_por_sprint.

Extra do usuário (não faz parte do SDD original): contador "N/M" de
avaliação semanal por sprint. Reusa a MESMA derivação de hoje (operacional
com task na sprint) usada por routers/avaliacoes.py — não a elegibilidade
temporal nova da Entrega 2. Ver spec §3 "Entrega 1"."""
from unittest.mock import MagicMock

from services.avaliacoes import contar_avaliacao_por_sprint


def _mock_client(tasks=None, avaliacoes=None):
    tasks = tasks or []
    avaliacoes = avaliacoes or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = avaliacoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_conta_elegiveis_e_avaliados_por_sprint():
    client = _mock_client(
        tasks=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
            {"sprint_id": "sprint-1", "operacional_id": "op-2"},
            {"sprint_id": "sprint-2", "operacional_id": "op-3"},
        ],
        avaliacoes=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
        ],
    )

    resultado = contar_avaliacao_por_sprint(client, ["sprint-1", "sprint-2"])

    assert resultado["sprint-1"] == {"elegiveis": 2, "avaliados": 1}
    assert resultado["sprint-2"] == {"elegiveis": 1, "avaliados": 0}


def test_sprint_sem_task_fica_zero_a_zero():
    client = _mock_client(tasks=[], avaliacoes=[])

    resultado = contar_avaliacao_por_sprint(client, ["sprint-1"])

    assert resultado["sprint-1"] == {"elegiveis": 0, "avaliados": 0}


def test_lista_vazia_de_sprints_retorna_dict_vazio():
    client = _mock_client()
    assert contar_avaliacao_por_sprint(client, []) == {}


def test_avaliacao_orfa_nao_conta_se_pessoa_nao_tem_mais_task():
    """Se alguém foi avaliado mas não tem mais task na sprint (dado
    inconsistente/legado), não pode fazer avaliados > elegíveis."""
    client = _mock_client(
        tasks=[{"sprint_id": "sprint-1", "operacional_id": "op-1"}],
        avaliacoes=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
            {"sprint_id": "sprint-1", "operacional_id": "op-orfao"},
        ],
    )

    resultado = contar_avaliacao_por_sprint(client, ["sprint-1"])

    assert resultado["sprint-1"] == {"elegiveis": 1, "avaliados": 1}
