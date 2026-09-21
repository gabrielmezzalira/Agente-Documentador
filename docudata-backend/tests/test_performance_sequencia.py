"""services/performance.py::_sequencia_pessoal deve incluir linhas com 0
pontos alocados (Entrega 2 — vinculado que não puxou nada em PULL). Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
from unittest.mock import MagicMock

from services.performance import _sequencia_pessoal


def test_sequencia_pessoal_inclui_linha_com_zero_pontos_alocados():
    linha_zerada = {
        "operacional_id": "op-1", "entrega_pontos_alocados": 0,
        "entrega_pontos_concluidos": 0, "projeto_id": "p1", "sprint_fim": "2026-06-01T00:00:00+00:00",
    }
    client = MagicMock()
    q = MagicMock()
    q.in_ = MagicMock(return_value=q)
    q.order = MagicMock(return_value=q)
    resp = MagicMock()
    resp.data = [linha_zerada]
    q.execute = MagicMock(return_value=resp)
    client.table = MagicMock(return_value=MagicMock(select=MagicMock(return_value=q)))

    resultado = _sequencia_pessoal(client, ["op-1"])

    assert len(resultado) == 1
    assert resultado[0]["operacional_id"] == "op-1"
