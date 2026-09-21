"""Testes para os endpoints de comparação de modos (Entrega 2)."""
from unittest.mock import MagicMock

from routers.metricas import get_comparacao_modos, get_comparacao_modos_entre_projetos


async def test_get_comparacao_modos_404_se_projeto_nao_existe():
    from fastapi import HTTPException
    client = MagicMock()
    q = MagicMock()
    q.eq = MagicMock(return_value=q)
    resp = MagicMock()
    resp.data = []
    q.execute = MagicMock(return_value=resp)
    client.table = MagicMock(return_value=MagicMock(select=MagicMock(return_value=q)))
    import routers.metricas as mod
    mod.get_client = lambda: client

    try:
        await get_comparacao_modos("proj-x")
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404


async def test_get_comparacao_modos_entre_projetos_exige_ao_menos_2_ids():
    from fastapi import HTTPException
    try:
        await get_comparacao_modos_entre_projetos(projeto_ids="proj-1")
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 422
