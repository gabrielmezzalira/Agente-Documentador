"""Testes para GET /avaliacoes/{sprint_id}/elegiveis (RF-C7, Entrega 2)."""
from unittest.mock import MagicMock

from routers.avaliacoes import listar_elegiveis


def _mock_client(sprint, operacionais, tasks, avaliacoes):
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
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "avaliacoes_gerente":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = avaliacoes
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


async def test_lista_vinculado_sem_task_com_zero_e_nao_avaliado():
    sprint = {"id": "sprint-1", "project_id": "p1"}
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None}
    client = _mock_client(sprint, [op], tasks=[], avaliacoes=[])
    import routers.avaliacoes as mod
    mod.get_client = lambda: client

    resultado = await listar_elegiveis("sprint-1")

    assert resultado == [{"operacional_id": "op-1", "nome": "Ana", "tasks_na_sprint": 0, "avaliado": False}]


async def test_conta_tasks_e_avaliacao_corretamente():
    sprint = {"id": "sprint-1", "project_id": "p1"}
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None}
    client = _mock_client(
        sprint, [op],
        tasks=[{"operacional_id": "op-1"}, {"operacional_id": "op-1"}],
        avaliacoes=[{"operacional_id": "op-1"}],
    )
    import routers.avaliacoes as mod
    mod.get_client = lambda: client

    resultado = await listar_elegiveis("sprint-1")

    assert resultado[0]["tasks_na_sprint"] == 2
    assert resultado[0]["avaliado"] is True


async def test_sprint_inexistente_retorna_404():
    from fastapi import HTTPException
    client = _mock_client(None, [], [], [])
    import routers.avaliacoes as mod
    mod.get_client = lambda: client

    try:
        await listar_elegiveis("sprint-x")
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404
