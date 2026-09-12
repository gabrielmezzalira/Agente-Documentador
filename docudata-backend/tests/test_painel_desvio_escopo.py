"""Testes da nova fórmula de desvio do Bloco A do Painel.

O desvio passa a ser `pct_prazo_consumido - pct_escopo_concluido`. Antes era
calculado contra a porcentagem aprovada pelo cliente — um campo que nenhuma
tela preenchia, logo sempre 0, fazendo todo projeto acusar desvio assim que
passava da tolerância do calendário.

`calcular_bloco_a` é função pura: não toca Supabase, não precisa de mock.
"""
from datetime import date, timedelta

from routers.painel import calcular_bloco_a


def _projeto(dias_corridos: int, dias_restantes: int, tolerancia: int) -> dict:
    hoje = date.today()
    return {
        "data_inicio": (hoje - timedelta(days=dias_corridos)).isoformat(),
        "data_fim_contratada": (hoje + timedelta(days=dias_restantes)).isoformat(),
        "tolerancia_desvio_pontos": tolerancia,
    }


def _funcs(total: int, concluidas: int) -> list[dict]:
    return [
        {"id": f"f-{i}", "titulo": f"Func {i}", "status": "concluida" if i < concluidas else "em_andamento"}
        for i in range(total)
    ]


def test_projeto_em_dia_nao_acusa_desvio():
    """50% do prazo consumido, 50% do escopo concluído → desvio zero."""
    bloco = calcular_bloco_a(_projeto(50, 50, tolerancia=20), _funcs(10, 5))

    assert bloco["sem_dados"] is False
    assert bloco["pct_prazo_consumido"] == 50.0
    assert bloco["pct_escopo_concluido"] == 50.0
    assert bloco["desvio_pontos"] == 0.0
    assert bloco["desvio_detectado"] is False


def test_projeto_atrasado_acusa_desvio():
    """80% do prazo consumido com 10% do escopo concluído → desvio de 70 pontos."""
    bloco = calcular_bloco_a(_projeto(80, 20, tolerancia=20), _funcs(10, 1))

    assert bloco["pct_prazo_consumido"] == 80.0
    assert bloco["pct_escopo_concluido"] == 10.0
    assert bloco["desvio_pontos"] == 70.0
    assert bloco["desvio_detectado"] is True


def test_escopo_todo_concluido_na_metade_do_prazo_nao_acusa_desvio():
    """O bug consertado: 50% do prazo, 100% do escopo, tolerância 0.

    Na fórmula antiga isso dava +50.0 e desvio_detectado=True, porque comparava
    contra a porcentagem aprovada pelo cliente (sempre 0). Agora dá -50.0.
    """
    bloco = calcular_bloco_a(_projeto(50, 50, tolerancia=0), _funcs(10, 10))

    assert bloco["pct_prazo_consumido"] == 50.0
    assert bloco["pct_escopo_concluido"] == 100.0
    assert bloco["desvio_pontos"] == -50.0
    assert bloco["desvio_detectado"] is False


def test_bloco_a_nao_expoe_mais_metrica_de_aprovacao_do_cliente():
    bloco = calcular_bloco_a(_projeto(50, 50, tolerancia=20), _funcs(10, 5))

    assert "pct_aprovado_cliente" not in bloco


def test_sem_datas_de_contrato_retorna_sem_dados():
    assert calcular_bloco_a({}, []) == {"sem_dados": True}
