"""Testes para routers/operacionais.py — grava/limpa data_saida quando ativo
muda (Entrega 2). Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.3."""
from unittest.mock import MagicMock

from routers.operacionais import update_operacional, remover_do_projeto
from models.schemas import OperacionalUpdate


def _mock_client_update(existing_row, update_capture):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [existing_row]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                update_capture.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(existing_row, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "tasks":
            q = MagicMock()
            q.update = MagicMock(return_value=q)
            q.eq = MagicMock(return_value=q)
            q.neq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.update = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


async def test_desativar_via_patch_grava_data_saida():
    capture = []
    client = _mock_client_update({"id": "op-1", "ativo": True}, capture)
    import routers.operacionais as mod
    mod.get_client = lambda: client

    await update_operacional("op-1", OperacionalUpdate(ativo=False))

    assert capture[0]["ativo"] is False
    assert capture[0]["data_saida"] is not None


async def test_reativar_via_patch_limpa_data_saida():
    capture = []
    client = _mock_client_update({"id": "op-1", "ativo": False, "data_saida": "2026-01-01T00:00:00+00:00"}, capture)
    import routers.operacionais as mod
    mod.get_client = lambda: client

    await update_operacional("op-1", OperacionalUpdate(ativo=True))

    assert capture[0]["ativo"] is True
    assert capture[0]["data_saida"] is None


async def test_remover_do_projeto_grava_data_saida():
    capture = []
    client = _mock_client_update({"id": "op-1", "ativo": True}, capture)
    import routers.operacionais as mod
    mod.get_client = lambda: client

    await remover_do_projeto("op-1")

    assert capture[0]["ativo"] is False
    assert capture[0]["data_saida"] is not None
