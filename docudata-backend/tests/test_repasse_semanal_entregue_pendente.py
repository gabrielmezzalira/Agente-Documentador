"""Testes para o bloco 'Entregue vs Pendente' injetado no contexto do
Repasse Semanal — reaproveita compute_planejado_vs_entregue (mesma fonte
que pré-preenche a Review), sem depender de nenhuma Review já ter sido
gerada para a sprint."""
from unittest.mock import MagicMock

from graphs.generation_graph import compilar_contexto


def _make_mock_client(tasks):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "sprint-1"}]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_BASE_STATE = {
    "projeto_id": "proj-1",
    "projeto_nome": "Projeto X",
    "cliente": "Cliente Y",
    "tipo_doc": "repasse_semanal",
    "sprint_numero": 3,
    "ingestion_id": None,
    "observacoes": None,
    "api_key": "fake-key",
    "data_atual": "12/09/2026",
    "ingestions": [],
    "contexto": "",
    "documento": "",
    "erro_contexto": None,
}


def test_repasse_semanal_inclui_bloco_entregue_pendente_do_kanban(monkeypatch):
    import graphs.generation_graph as gg
    mock_sb = _make_mock_client([
        {"titulo": "Ajustar login", "coluna_kanban": "concluida"},
        {"titulo": "Subir ambiente", "coluna_kanban": "em_andamento"},
    ])
    monkeypatch.setattr(gg, "get_client", lambda: mock_sb)

    resultado = compilar_contexto(dict(_BASE_STATE))

    assert "Entregue vs Pendente da Sprint 3 (calculado do kanban)" in resultado["contexto"]
    assert "[Entregue] Ajustar login" in resultado["contexto"]
    assert "[Pendente] Subir ambiente" in resultado["contexto"]


def test_bloco_entregue_pendente_ausente_quando_sprint_sem_tasks(monkeypatch):
    import graphs.generation_graph as gg
    mock_sb = _make_mock_client([])
    monkeypatch.setattr(gg, "get_client", lambda: mock_sb)

    resultado = compilar_contexto(dict(_BASE_STATE))

    assert "Entregue vs Pendente" not in resultado["contexto"]


def test_bloco_entregue_pendente_nao_aparece_em_outros_tipos_de_doc(monkeypatch):
    import graphs.generation_graph as gg
    mock_sb = _make_mock_client([
        {"titulo": "Ajustar login", "coluna_kanban": "concluida"},
    ])
    monkeypatch.setattr(gg, "get_client", lambda: mock_sb)

    estado = dict(_BASE_STATE, tipo_doc="review")
    resultado = compilar_contexto(estado)

    assert "Entregue vs Pendente" not in resultado["contexto"]
