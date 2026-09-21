"""Testes para services/avaliacoes.py::contar_avaliacao_por_sprint.

Extra do usuário (não faz parte do SDD original): contador "N/M" de
avaliação semanal por sprint.

Entrega 2: elegibilidade passa a ser vínculo temporal com o projeto
(operacional vinculado ao project_id, via services.elegibilidade), não mais
"tem task na sprint". Por isso "elegiveis" agora é o MESMO valor para todas
as sprints de uma mesma chamada (é um contador por projeto, não por sprint)
— as fixtures abaixo usam a tabela `operacionais` para modelar quem está
vinculado, em vez de `tasks`. Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
from unittest.mock import MagicMock

from services.avaliacoes import contar_avaliacao_por_sprint


def _mock_client(operacionais=None, avaliacoes=None):
    operacionais = operacionais or []
    avaliacoes = avaliacoes or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = operacionais
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
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
    # op-1/op-2/op-3 eram os operacionais com task em sprint-1/sprint-1/sprint-2
    # no teste original (elegibilidade por task). Agora todos os três estão
    # vinculados ao projeto, e elegibilidade é por projeto, não por sprint —
    # então "elegiveis" vale 3 (o total de vinculados) para AMBAS as sprints
    # consultadas na mesma chamada, não mais 2 e 1 separadamente.
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None},
            {"id": "op-2", "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None},
            {"id": "op-3", "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None},
        ],
        avaliacoes=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
        ],
    )

    resultado = contar_avaliacao_por_sprint(client, "p1", ["sprint-1", "sprint-2"])

    assert resultado["sprint-1"] == {"elegiveis": 3, "avaliados": 1}
    assert resultado["sprint-2"] == {"elegiveis": 3, "avaliados": 0}


def test_sprint_sem_operacional_vinculado_fica_zero_a_zero():
    client = _mock_client(operacionais=[], avaliacoes=[])

    resultado = contar_avaliacao_por_sprint(client, "p1", ["sprint-1"])

    assert resultado["sprint-1"] == {"elegiveis": 0, "avaliados": 0}


def test_lista_vazia_de_sprints_retorna_dict_vazio():
    client = _mock_client()
    assert contar_avaliacao_por_sprint(client, "p1", []) == {}


def test_avaliacao_orfa_nao_conta_se_pessoa_nao_esta_mais_vinculada():
    """Se alguém foi avaliado mas não está mais vinculado ao projeto (dado
    inconsistente/legado, ou já desativado), não pode fazer avaliados >
    elegíveis."""
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None},
        ],
        avaliacoes=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
            {"sprint_id": "sprint-1", "operacional_id": "op-orfao"},
        ],
    )

    resultado = contar_avaliacao_por_sprint(client, "p1", ["sprint-1"])

    assert resultado["sprint-1"] == {"elegiveis": 1, "avaliados": 1}
