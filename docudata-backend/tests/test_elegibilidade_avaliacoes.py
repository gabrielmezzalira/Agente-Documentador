"""Testes para a redefinição de "elegível" em routers/avaliacoes.py e
services/avaliacoes.py (Entrega 2) — vinculado ao projeto, não mais "tem
task na sprint". Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
from unittest.mock import MagicMock

from routers.avaliacoes import _operacionais_elegiveis
from services.avaliacoes import contar_avaliacao_por_sprint


def _mock_client_router(sprint, operacionais):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [sprint] if sprint else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = operacionais
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_operacionais_elegiveis_inclui_vinculado_sem_task():
    """O ponto central da correção do bug de PULL: alguém vinculado, mas SEM
    nenhuma task na sprint, precisa aparecer como elegível."""
    sprint = {"project_id": "p1"}
    op_sem_task = {
        "id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    client = _mock_client_router(sprint, [op_sem_task])

    result = _operacionais_elegiveis(client, "sprint-1")

    assert [r["id"] for r in result] == ["op-1"]


def test_operacionais_elegiveis_sprint_inexistente_retorna_vazio():
    client = _mock_client_router(None, [])
    assert _operacionais_elegiveis(client, "sprint-x") == []


def _mock_client_service(operacionais, tasks, avaliacoes):
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
        elif name == "tasks":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "avaliacoes_gerente":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = avaliacoes
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_contar_avaliacao_por_sprint_conta_vinculado_sem_task_como_elegivel():
    op_sem_task = {
        "id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    client = _mock_client_service([op_sem_task], tasks=[], avaliacoes=[])

    resultado = contar_avaliacao_por_sprint(client, "p1", ["sprint-1"])

    assert resultado["sprint-1"]["elegiveis"] == 1
    assert resultado["sprint-1"]["avaliados"] == 0


def test_contar_avaliacao_por_sprint_lista_vazia_retorna_vazio():
    client = _mock_client_service([], tasks=[], avaliacoes=[])
    assert contar_avaliacao_por_sprint(client, "p1", []) == {}
