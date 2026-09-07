"""Testes para services/performance.py (Phase 19).

Cobre: identidade cross-projeto por e-mail, janelas por contagem (1/2/4),
agregação em duas camadas por dimensão com projetos assimétricos, arquétipo
da janela por contagem de linhas (empate por mais recente), janela parcial,
blend de Qualidade com e sem qualidade_commit_media, score final como soma
ponderada re-normalizada pelos pesos disponíveis.
"""
from unittest.mock import MagicMock

from services.performance import listar_pessoas_ativas, calcular_ranking_pessoa, JANELAS


_PESOS = {
    "padrao": {
        "arquetipo": "padrao", "peso_gerente": 0.35, "peso_entrega": 0.20,
        "peso_qualidade": 0.20, "peso_autonomia": 0.15, "peso_evolucao": 0.10,
        "peso_commit_qualidade": 0.50,
    },
    "consultoria_discovery": {
        "arquetipo": "consultoria_discovery", "peso_gerente": 0.35, "peso_entrega": 0.20,
        "peso_qualidade": 0.20, "peso_autonomia": 0.15, "peso_evolucao": 0.10,
        "peso_commit_qualidade": 0.50,
    },
}


def _mock_client(operacionais=None, pontuacao=None, projetos=None):
    operacionais = operacionais or []
    pontuacao = pontuacao or []
    projetos = projetos or []
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
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                q.gt = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = projetos
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _linha(sprint_fim, projeto_id="proj-1", **overrides):
    base = {
        "operacional_id": "op-1", "sprint_id": f"sprint-{sprint_fim}", "projeto_id": projeto_id,
        "sprint_fim": sprint_fim, "gerente_media": 5.0, "gerente_pergunta6": 5,
        "entrega_pontos_concluidos": 10, "entrega_pontos_alocados": 10,
        "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 2,
        "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
        "qualidade_commit_media": None,
    }
    base.update(overrides)
    return base


def test_listar_pessoas_ativas_agrupa_por_email():
    client = _mock_client(operacionais=[
        {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
        {"id": "op-2", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
        {"id": "op-3", "nome": "Bia", "email": None, "ativo": True},
    ])

    pessoas = listar_pessoas_ativas(client)

    ana = next(p for p in pessoas if p["email"] == "ana@citi.com")
    assert sorted(ana["operacional_ids"]) == ["op-1", "op-2"]
    bia = next(p for p in pessoas if p["nome"] == "Bia")
    assert bia["operacional_ids"] == ["op-3"]


def test_janela_sprint_usa_so_a_ultima_linha():
    linhas = [_linha("2026-09-05T00:00:00+00:00"), _linha("2026-09-04T00:00:00+00:00")]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert ranking["sprint"]["janela_parcial"] is False
    assert ranking["sprint"]["entrega"] == 100.0


def test_janela_parcial_quando_menos_linhas_que_o_tamanho():
    linhas = [_linha("2026-09-05T00:00:00+00:00")]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert ranking["quinzenal"]["janela_parcial"] is True
    assert ranking["mensal"]["janela_parcial"] is True


def test_agregacao_duas_camadas_com_dois_projetos_assimetricos():
    linhas = [
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
        _linha("2026-09-04T00:00:00+00:00", projeto_id="proj-2", entrega_pontos_concluidos=5, entrega_pontos_alocados=20),
    ]
    client = _mock_client(
        pontuacao=linhas,
        projetos=[{"id": "proj-1", "arquetipo": "padrao"}, {"id": "proj-2", "arquetipo": "padrao"}],
    )
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # proj-1: SPI=100, proj-2: SPI=25 -> média simples = 62.5 (não pooled-sum = 50.0)
    assert ranking["quinzenal"]["entrega"] == 62.5


def test_arquetipo_da_janela_por_contagem_com_empate_por_mais_recente():
    linhas = [
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-recente"),
        _linha("2026-09-04T00:00:00+00:00", projeto_id="proj-antigo"),
        _linha("2026-09-03T00:00:00+00:00", projeto_id="proj-antigo"),
        _linha("2026-09-02T00:00:00+00:00", projeto_id="proj-recente"),
    ]
    client = _mock_client(
        pontuacao=linhas,
        projetos=[
            {"id": "proj-recente", "arquetipo": "consultoria_discovery"},
            {"id": "proj-antigo", "arquetipo": "padrao"},
        ],
    )
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # 2 linhas cada -> empate -> desempate pela mais recente (proj-recente, 09-05)
    assert ranking["mensal"]["arquetipo_usado"] == "consultoria_discovery"


def test_qualidade_com_blend_de_commit():
    linhas = [_linha("2026-09-05T00:00:00+00:00", qualidade_reaberturas=0, qualidade_tasks_concluidas=2, qualidade_commit_media=10)]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # retrabalho = 100 (0 reaberturas), commit = 10*10=100 -> blend 0.5*100+0.5*100=100
    assert ranking["sprint"]["qualidade"] == 100.0


def test_qualidade_sem_commit_usa_so_retrabalho():
    linhas = [_linha("2026-09-05T00:00:00+00:00", qualidade_reaberturas=1, qualidade_tasks_concluidas=2, qualidade_commit_media=None)]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert ranking["sprint"]["qualidade"] == 50.0


def test_score_final_e_soma_ponderada():
    linhas = [_linha(
        "2026-09-05T00:00:00+00:00",
        gerente_media=5.0, gerente_pergunta6=5,
        entrega_pontos_concluidos=10, entrega_pontos_alocados=10,
        qualidade_reaberturas=0, qualidade_tasks_concluidas=2,
        autonomia_bloqueios_resolvidos_proprio=0, autonomia_bloqueios_totais=0,
    )]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    # todas as dimensões = 100 -> score final = 100
    assert ranking["sprint"]["score_final"] == 100.0


def test_entrega_desconta_pontos_penalizados_por_travamento():
    """Travamento automático não vira bloqueio (Autonomia intacta) — ele corta
    a Entrega, tirando os pontos da task travada dos concluídos."""
    from services.performance import _entrega_por_projeto

    linhas = [{
        "entrega_pontos_concluidos": 10,
        "entrega_pontos_alocados": 20,
        "entrega_pontos_penalizados": 5,
    }]

    assert _entrega_por_projeto(linhas) == 25.0


def test_entrega_nunca_fica_negativa_com_penalidade_maior_que_o_concluido():
    from services.performance import _entrega_por_projeto

    linhas = [{
        "entrega_pontos_concluidos": 3,
        "entrega_pontos_alocados": 10,
        "entrega_pontos_penalizados": 9,
    }]

    assert _entrega_por_projeto(linhas) == 0.0


def test_entrega_sem_penalidade_mantem_o_calculo_antigo():
    from services.performance import _entrega_por_projeto

    linhas = [{"entrega_pontos_concluidos": 12, "entrega_pontos_alocados": 24}]

    assert _entrega_por_projeto(linhas) == 50.0
