"""Testes para services/performance.py (Phase 19).

Cobre: identidade cross-projeto por e-mail, janelas por contagem (1/2/4),
agregação em duas camadas por dimensão com projetos assimétricos, arquétipo
da janela por contagem de linhas (empate por mais recente), janela parcial,
blend de Qualidade com e sem qualidade_commit_media, score final como soma
ponderada re-normalizada pelos pesos disponíveis.
"""
from unittest.mock import MagicMock

from services.performance import listar_pessoas_ativas_por_projeto, calcular_ranking_pessoa, JANELAS


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
                state = {"ids": None}

                def in_side_effect(field, values):
                    state["ids"] = set(values)
                    return q

                def execute_side_effect():
                    resp = MagicMock()
                    if state["ids"] is None:
                        resp.data = pontuacao
                    else:
                        resp.data = [p for p in pontuacao if p["operacional_id"] in state["ids"]]
                    return resp

                q.in_ = MagicMock(side_effect=in_side_effect)
                q.gt = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.execute = MagicMock(side_effect=execute_side_effect)
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


def test_listar_pessoas_ativas_por_projeto_agrupa_por_projeto_e_email():
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-2", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-3", "nome": "Bia", "email": None, "ativo": True, "project_id": "proj-1"},
            {"id": "op-4", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-2"},
        ],
        projetos=[{"id": "proj-1", "name": "Projeto 1"}, {"id": "proj-2", "name": "Projeto 2"}],
    )

    por_projeto = listar_pessoas_ativas_por_projeto(client)

    assert set(por_projeto.keys()) == {"proj-1", "proj-2"}
    assert por_projeto["proj-1"]["projeto_nome"] == "Projeto 1"
    assert por_projeto["proj-2"]["projeto_nome"] == "Projeto 2"

    pessoas_proj1 = por_projeto["proj-1"]["pessoas"]
    ana_proj1 = next(p for p in pessoas_proj1 if p["email"] == "ana@citi.com")
    assert sorted(ana_proj1["operacional_ids"]) == ["op-1", "op-2"]
    bia_proj1 = next(p for p in pessoas_proj1 if p["nome"] == "Bia")
    assert bia_proj1["operacional_ids"] == ["op-3"]

    # Ana em proj-1 (op-1/op-2) e Ana em proj-2 (op-4) NÃO se juntam — a
    # mesma pessoa aparece separadamente em cada projeto (decisão de
    # 2026-09-23: o ranking deixou de juntar pessoas entre projetos).
    pessoas_proj2 = por_projeto["proj-2"]["pessoas"]
    ana_proj2 = next(p for p in pessoas_proj2 if p["email"] == "ana@citi.com")
    assert ana_proj2["operacional_ids"] == ["op-4"]


def test_pessoa_em_dois_projetos_aparece_separada_com_notas_diferentes():
    linhas = [
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-1", operacional_id="op-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-2", operacional_id="op-2", entrega_pontos_concluidos=2, entrega_pontos_alocados=10),
    ]
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-2", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-2"},
        ],
        pontuacao=linhas,
        projetos=[
            {"id": "proj-1", "arquetipo": "padrao", "name": "Projeto 1"},
            {"id": "proj-2", "arquetipo": "padrao", "name": "Projeto 2"},
        ],
    )

    por_projeto = listar_pessoas_ativas_por_projeto(client)
    ranking_proj1 = calcular_ranking_pessoa(client, por_projeto["proj-1"]["pessoas"][0], _PESOS)
    ranking_proj2 = calcular_ranking_pessoa(client, por_projeto["proj-2"]["pessoas"][0], _PESOS)

    # proj-1: Ana entregou 10/10 = 100; proj-2: Ana entregou 2/10 = 20 — notas
    # diferentes por projeto, sem nenhuma média cross-projeto. Antes desta
    # mudança essas duas linhas teriam virado UMA pessoa só, com entrega
    # média (100+20)/2 = 60.0.
    assert ranking_proj1["sprint"]["entrega"] == 100.0
    assert ranking_proj2["sprint"]["entrega"] == 20.0


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


# ── Revisão 2 da metodologia (2026-09-07) ────────────────────────────────────

def test_qualidade_sem_entrega_fica_indisponivel_em_vez_de_100():
    """Dar 100 a quem não concluiu nada premiava a ausência de entrega."""
    from services.performance import _qualidade_por_projeto

    linhas = [{"qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 0, "qualidade_commit_media": None}]

    assert _qualidade_por_projeto(linhas, 0.5) is None


def test_qualidade_sem_entrega_mas_com_commit_usa_o_commit():
    from services.performance import _qualidade_por_projeto

    linhas = [{"qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 0, "qualidade_commit_media": 8.0}]

    assert _qualidade_por_projeto(linhas, 0.5) == 80.0


def test_autonomia_sem_bloqueio_cai_na_pergunta_3():
    """Antes isso dava 100 fixo e a dimensão virava peso morto."""
    from services.performance import _autonomia_por_projeto

    linhas = [{
        "autonomia_bloqueios_resolvidos_proprio": 0,
        "autonomia_bloqueios_totais": 0,
        "gerente_pergunta3": 4,
    }]

    assert _autonomia_por_projeto(linhas, 0.5) == 80.0


def test_autonomia_combina_bloqueio_com_pergunta_3():
    from services.performance import _autonomia_por_projeto

    linhas = [{
        "autonomia_bloqueios_resolvidos_proprio": 1,
        "autonomia_bloqueios_totais": 2,   # 50
        "gerente_pergunta3": 5,            # 100
    }]

    assert _autonomia_por_projeto(linhas, 0.5) == 75.0


def test_autonomia_sem_nenhum_dos_dois_sinais_fica_indisponivel():
    from services.performance import _autonomia_por_projeto

    linhas = [{
        "autonomia_bloqueios_resolvidos_proprio": 0,
        "autonomia_bloqueios_totais": 0,
        "gerente_pergunta3": None,
    }]

    assert _autonomia_por_projeto(linhas, 0.5) is None


def test_bonus_de_task_extra_respeita_o_teto():
    from services.performance import _bonus_extra

    assert _bonus_extra([{"bonus_pontos_extra": 3}]) == 3.0
    assert _bonus_extra([{"bonus_pontos_extra": 4}, {"bonus_pontos_extra": 9}]) == 5.0
    assert _bonus_extra([{"bonus_pontos_extra": 0}]) == 0.0
    assert _bonus_extra([{}]) == 0.0


# ── Entrega 3 — Modos de trabalho (PONTOS_RELATIVO) ──────────────────────────

def test_entrega_por_projeto_usa_nota_relativa_quando_modo_e_relativo():
    from services.performance import _entrega_por_projeto
    linhas = [{"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 80.0}]
    assert _entrega_por_projeto(linhas) == 80.0


def test_entrega_por_projeto_media_relativa_entre_sprints_da_janela():
    from services.performance import _entrega_por_projeto
    linhas = [
        {"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 80.0},
        {"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 40.0},
    ]
    assert _entrega_por_projeto(linhas) == 60.0


def test_entrega_por_projeto_janela_mista_pondera_por_quantidade_de_sprints():
    from services.performance import _entrega_por_projeto
    # 2 sprints ATRIBUICAO (rate agregado 50%) + 1 sprint PULL (nota 80) —
    # média ponderada por contagem: (50*2 + 80*1) / 3 = 60.0
    linhas = [
        {"entrega_modo": "PONTOS_ATRIBUIDOS", "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 10, "entrega_pontos_penalizados": 0},
        {"entrega_modo": "PONTOS_ATRIBUIDOS", "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 10, "entrega_pontos_penalizados": 0},
        {"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 80.0},
    ]
    assert _entrega_por_projeto(linhas) == 60.0


def test_calcular_janela_nao_tem_mais_a_chave_evolucao():
    linhas = [_linha("2026-09-05T00:00:00+00:00", gerente_media=5.0)]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao", "name": "Projeto 1"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert "evolucao" not in ranking["sprint"]


def test_score_final_so_com_avaliacao_do_gerente_quando_zero_tasks():
    """Operacional vinculado ao projeto, zero tasks na sprint, avaliação do
    gerente completa. Entrega fica indisponível (alocados=0), Qualidade fica
    indisponível (sem task concluída nem commit), Autonomia só tem a
    pergunta 3 (sem bloqueio nenhum) — mas Gerente está disponível, então
    score_final não pode ser None (Evolução não existe mais como dimensão,
    ver Task 2 do plano de 2026-09-23)."""
    linha = {
        "projeto_id": "proj-1", "sprint_fim": "2026-09-01T00:00:00Z",
        "entrega_modo": "PONTOS_ATRIBUIDOS",
        "entrega_pontos_concluidos": 0, "entrega_pontos_alocados": 0, "entrega_pontos_penalizados": 0,
        "entrega_pontos_pessoa": None, "entrega_denominador": None, "entrega_nota_relativa": None,
        "bonus_pontos_extra": 0,
        "gerente_media": 4.0, "gerente_pergunta3": 4,
        "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 0, "qualidade_commit_media": None,
        "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
    }
    operacionais = [{"id": "op-a", "nome": "A", "email": "a@x.com", "ativo": True, "project_id": "proj-1"}]
    client = _mock_client(operacionais=operacionais, pontuacao=[dict(linha, operacional_id="op-a")], projetos=[{"id": "proj-1", "arquetipo": "padrao", "name": "Projeto 1"}])

    pessoa = list(listar_pessoas_ativas_por_projeto(client)["proj-1"]["pessoas"])[0]
    resultado = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert resultado["sprint"] is not None
    assert resultado["sprint"]["score_final"] is not None
    assert resultado["sprint"]["entrega"] is None
    assert resultado["sprint"]["qualidade"] is None
    assert resultado["sprint"]["gerente"] == 80.0  # 4.0 * 20
    assert "evolucao" not in resultado["sprint"]
    # score_final = (peso_gerente*80 + peso_autonomia*autonomia) / (peso_gerente+peso_autonomia)
    # autonomia (só pergunta3, sem bloqueio) = min(4*20,100) = 80
    peso_disponivel = 0.35 + 0.15
    esperado = round((0.35 * 80.0 + 0.15 * 80.0) / peso_disponivel, 2)
    assert resultado["sprint"]["score_final"] == esperado
