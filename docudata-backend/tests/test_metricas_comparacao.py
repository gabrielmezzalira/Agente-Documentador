"""Testes para services/metricas_comparacao.py (Entrega 2). Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §3."""
from unittest.mock import MagicMock

from services.metricas_comparacao import comparar_modos_do_projeto, comparar_modos_entre_projetos


def _mock_client(sprints, tasks, pontuacoes):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = sprints
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "pontuacao_operacional_sprint":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = pontuacoes
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_agrupa_sprints_por_modo_congelado_dentro_do_projeto():
    sprints = [
        {"id": "s1", "project_id": "p1", "numero": 1, "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pontos_orcamento": 10},
        {"id": "s2", "project_id": "p1", "numero": 2, "modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pontos_orcamento": 10},
    ]
    tasks = [
        {"sprint_id": "s1", "pontos": 10, "coluna_kanban": "concluida"},
        {"sprint_id": "s2", "pontos": 5, "coluna_kanban": "concluida"},
    ]
    pontuacoes = [
        {"sprint_id": "s1", "entrega_pontos_alocados": 10, "entrega_pontos_concluidos": 10},
        {"sprint_id": "s2", "entrega_pontos_alocados": 8, "entrega_pontos_concluidos": 5},
    ]
    client = _mock_client(sprints, tasks, pontuacoes)

    resultado = comparar_modos_do_projeto(client, "p1")

    grupos = {(r["modo_trabalho"], r["modo_avaliacao"]): r for r in resultado}
    assert ("ATRIBUICAO", "PONTOS_ATRIBUIDOS") in grupos
    assert ("PULL", "PONTOS_RELATIVO") in grupos
    assert grupos[("ATRIBUICAO", "PONTOS_ATRIBUIDOS")]["sprints_count"] == 1
    assert grupos[("PULL", "PONTOS_RELATIVO")]["pontos_realizados_total"] == 5


def test_ignora_sprint_ainda_nao_fechada_sem_modo_congelado():
    sprints = [
        {"id": "s1", "project_id": "p1", "numero": 1, "modo_trabalho": None, "modo_avaliacao": None, "pontos_orcamento": 10},
    ]
    client = _mock_client(sprints, tasks=[], pontuacoes=[])

    resultado = comparar_modos_do_projeto(client, "p1")

    assert resultado == []


def test_comparar_modos_entre_projetos_junta_sprints_de_varios_projetos():
    sprints = [
        {"id": "s1", "project_id": "p1", "numero": 1, "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pontos_orcamento": 10},
        {"id": "s2", "project_id": "p2", "numero": 1, "modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pontos_orcamento": 10},
    ]
    client = _mock_client(sprints, tasks=[], pontuacoes=[])

    resultado = comparar_modos_entre_projetos(client, ["p1", "p2"])

    grupos = {(r["modo_trabalho"], r["modo_avaliacao"]) for r in resultado}
    assert grupos == {("ATRIBUICAO", "PONTOS_ATRIBUIDOS"), ("PULL", "PONTOS_RELATIVO")}
