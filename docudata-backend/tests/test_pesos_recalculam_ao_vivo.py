"""Prova a afirmação da spec §3: score_final nunca é persistido, é sempre
calculado na hora a partir de pesos_arquetipo — então mudar os pesos muda o
ranking no próximo GET /performance, sem precisar reabrir nenhuma sprint.
Ver docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md §3."""
from unittest.mock import MagicMock

from services.performance import calcular_ranking_pessoa


def _mock_client(pontuacao):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pontuacao_operacional_sprint":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = pontuacao
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "proj-1", "arquetipo": "padrao"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_LINHA_TRAVADA = {
    "operacional_id": "op-1", "sprint_id": "sprint-1", "projeto_id": "proj-1",
    "sprint_fim": "2026-09-05T00:00:00+00:00", "gerente_media": 5.0,
    "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 10,
    "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 1,
    "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
    "qualidade_commit_media": None,
}


def test_score_muda_quando_pesos_mudam_sem_tocar_na_linha_travada():
    """A MESMA linha de pontuacao_operacional_sprint (já 'travada', como
    se tivesse sido escrita antes da migração de pesos) produz score_final
    diferente dependendo só de qual pesos_arquetipo é passado — prova que o
    cálculo é ao vivo, não lido de um valor congelado."""
    client = _mock_client(pontuacao=[_LINHA_TRAVADA])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    pesos_antigos = {"padrao": {
        "arquetipo": "padrao", "peso_gerente": 0.35, "peso_entrega": 0.20,
        "peso_qualidade": 0.20, "peso_autonomia": 0.15, "peso_evolucao": 0.10,
        "peso_commit_qualidade": 0.50,
    }}
    pesos_novos = {"padrao": {
        "arquetipo": "padrao", "peso_gerente": 0.50, "peso_entrega": 0.18,
        "peso_qualidade": 0.18, "peso_autonomia": 0.14, "peso_evolucao": 0.00,
        "peso_commit_qualidade": 0.50,
    }}

    score_com_pesos_antigos = calcular_ranking_pessoa(client, pessoa, pesos_antigos)["sprint"]["score_final"]
    score_com_pesos_novos = calcular_ranking_pessoa(client, pessoa, pesos_novos)["sprint"]["score_final"]

    assert score_com_pesos_antigos != score_com_pesos_novos
