# docudata-backend/tests/test_classificador_estatistica.py
"""Recálculo do aprendizado (spec A2 §4)."""
from services.classificador_estatistica import metricas_acuracia, nnls, pesos_iniciais, recalcular

H = 3600


def _ex(i, nivel, horas, op="ana", ger="g1", **kw):
    base = {"task_id": f"t{i}", "concluida_em": f"2026-10-01T{i:02d}:00:00+00:00", "nivel_sugerido": nivel,
            "tempo_limpo_s": horas * H, "operacional_id": op, "gerente_id": ger,
            "opiniao_operacional": None, "excluida": False, "sinais": None}
    base.update(kw)
    return base


def test_sem_historico_nivel_real_e_o_sugerido_e_cria_media():
    r = recalcular([_ex(1, 3, 10)])
    assert r["rotulos"]["t1"]["nivel_real"] == 3
    assert r["parametros"][("media_nivel", "3")] == (10 * H, 1)


def test_nivel_pelo_tempo_usa_media_anterior_mais_proxima():
    exs = [_ex(1, 1, 2, op="x1"), _ex(2, 5, 40, op="x2"), _ex(3, 1, 35, op="x3")]
    r = recalcular(exs)
    assert r["rotulos"]["t3"]["nivel_pelo_tempo"] == 5
    assert r["rotulos"]["t3"]["nivel_real"] == 5


def test_ritmo_encolhido_normaliza_o_tempo():
    exs = [_ex(i, 2, 4, op="rapido") for i in range(1, 6)] + [_ex(6, 2, 8, op="rapido")]
    r = recalcular(exs)
    assert r["rotulos"]["t6"]["ritmo_usado"] == 1.0
    assert r["parametros"][("ritmo_pessoa", "rapido")][1] == 6


def test_excluida_nao_entra_na_media_nem_no_ritmo():
    exs = [_ex(1, 2, 4), _ex(2, 2, 100, excluida=True)]
    r = recalcular(exs)
    assert r["parametros"][("media_nivel", "2")] == (4 * H, 1)


def test_alerta_acima_de_3x_media():
    r = recalcular([_ex(1, 2, 4, op="a"), _ex(2, 2, 13, op="b")])
    assert r["rotulos"]["t2"]["nivel_real"] == 2   # único degrau com média
    assert r["rotulos"]["t2"]["alerta"] is True    # 13h > 3 × 4h


def test_vies_do_gerente_encolhido():
    exs = [_ex(1, 1, 2, op="a", ger="g"), _ex(2, 5, 40, op="b", ger="h")] + [
        _ex(i, 1, 40, op=f"o{i}", ger="g") for i in range(3, 13)
    ]
    r = recalcular(exs)
    valor, n = r["parametros"][("vies_gerente", "g")]
    assert n == 11
    assert 1.0 < valor < 3.0   # sugere 1 e o tempo diz 5 (+3 degraus) em 10 de 11, encolhido


def test_opiniao_do_operacional_move_um_degrau_perto_da_fronteira_se_tiver_peso():
    # constrói médias 2→4h e 3→8h e um operacional "opina" cuja opinião costuma acertar
    base = [_ex(1, 2, 4, op="a"), _ex(2, 3, 8, op="b")]
    acertos = [_ex(i, 3, 8, op="z", opiniao_operacional=3) for i in range(3, 8)]
    alvo = [_ex(9, 2, 6, op="z", opiniao_operacional=3)]  # tn ≈ 6h, fronteira = 6h
    r = recalcular(base + acertos + alvo)
    assert r["rotulos"]["t9"]["nivel_pelo_tempo"] in (2, 3)
    assert r["rotulos"]["t9"]["nivel_real"] == 3


def test_pesos_iniciais_e_nnls_nao_negativo():
    assert pesos_iniciais() == {s: 0.25 for s in ("partes", "novidade", "incerteza", "dependencia", "tamanho", "risco")}
    w = nnls([[1, 0], [0, 1], [1, 1]], [2, -1, 1])
    assert all(x >= 0 for x in w)
    assert abs(w[0] - 1.5) < 0.1


def test_metricas_acuracia():
    m = metricas_acuracia([(2, 2), (2, 3), (3, 3), (1, 5)])
    assert m["n"] == 4
    assert m["exata"] == 0.5
    assert m["mais_menos_um"] == 0.75
    assert m["erro_medio_degraus"] == (0 + 1 + 0 + 3) / 4
    assert m["matriz"][2][3] == 1
    assert m["por_nivel"][2] == {"precisao": 0.5, "cobertura": 1.0}
    assert m["por_nivel"][5] == {"precisao": None, "cobertura": 0.0}
    assert metricas_acuracia([])["n"] == 0
