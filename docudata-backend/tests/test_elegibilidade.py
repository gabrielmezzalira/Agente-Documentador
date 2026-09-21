"""Testes para services/elegibilidade.py::listar_vinculados_no_projeto.
Ver docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.3."""
from unittest.mock import MagicMock

from services.elegibilidade import listar_vinculados_no_projeto


def _mock_client(operacionais):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_inclui_quem_entrou_antes_e_ainda_nao_saiu():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert [r["id"] for r in result] == ["op-1"]


def test_exclui_quem_entrou_depois_do_momento():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-06-15T00:00:00+00:00", "data_saida": None}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert result == []


def test_exclui_quem_ja_saiu_antes_do_momento():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": "2026-05-01T00:00:00+00:00"}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert result == []


def test_inclui_quem_saiu_depois_do_momento():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": "2026-07-01T00:00:00+00:00"}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert [r["id"] for r in result] == ["op-1"]


def test_data_entrada_igual_ao_momento_inclui():
    """"Já passou" é inclusivo — entrada exatamente igual ao momento conta."""
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-06-01T00:00:00+00:00", "data_saida": None}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert [r["id"] for r in result] == ["op-1"]


def test_data_saida_igual_ao_momento_exclui():
    """"Posterior" é estrito — saida exatamente igual ao momento NÃO conta."""
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": "2026-06-01T00:00:00+00:00"}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert result == []
