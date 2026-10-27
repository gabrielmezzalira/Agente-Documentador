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


def test_tempo_zero_ou_nulo_so_rotula_e_nao_alimenta_parametros():
    r = recalcular([_ex(1, 3, 0)])
    assert r["rotulos"]["t1"]["nivel_real"] == 3
    assert r["rotulos"]["t1"]["tempo_normalizado_s"] == 0
    assert r["rotulos"]["t1"]["alerta"] is False
    assert not any(k[0] == "media_nivel" for k in r["parametros"])
    mistos = recalcular([_ex(1, 2, 4), _ex(2, 2, 0, op="b"), _ex(3, 2, 1, op="c", tempo_limpo_s=None), _ex(4, 2, 6, op="d")])
    assert mistos["parametros"][("media_nivel", "2")] == (5 * H, 2)
    assert ("ritmo_pessoa", "b") not in mistos["parametros"]
    assert mistos["parametros"][("vies_gerente", "g1")][1] == 2


def test_ritmo_diferente_de_um_normaliza_exemplo_posterior():
    # pessoa lenta: 8h num nível cuja média é 4h -> ritmo > 1 nas seguintes
    exs = [_ex(1, 2, 4, op="ref"), _ex(2, 2, 8, op="lenta"), _ex(3, 2, 8, op="lenta")]
    r = recalcular(exs)
    rit = r["rotulos"]["t3"]["ritmo_usado"]
    assert rit > 1.0
    assert abs(r["rotulos"]["t3"]["tempo_normalizado_s"] - 8 * H / rit) < 1e-6


def test_empate_entre_medias_fica_com_o_degrau_menor():
    exs = [_ex(1, 2, 4, op="a"), _ex(2, 3, 8, op="b"), _ex(3, 2, 6, op="c")]
    assert recalcular(exs)["rotulos"]["t3"]["nivel_pelo_tempo"] == 2


def test_acerto_de_opiniao_nao_conta_o_proprio_ajuste():
    base = [_ex(1, 2, 4, op="a"), _ex(2, 3, 8, op="b")]
    acertos = [_ex(i, 3, 8, op="z", opiniao_operacional=3) for i in range(3, 8)]
    nudged = [_ex(9, 2, 6, op="z", opiniao_operacional=3)]  # empurrado para 3; tempo diz 2
    r = recalcular(base + acertos + nudged)
    assert r["rotulos"]["t9"]["nivel_real"] == 3
    assert r["rotulos"]["t9"]["nivel_pelo_tempo"] == 2
    assert r["parametros"][("peso_opiniao_operacional", "z")] == (5 / 16, 6)


def test_peso_opiniao_gerente_limitado_ao_teto_e_pelo_tempo():
    exs = [_ex(i, 2, 4, op=f"o{i}", opiniao_gerente=2) for i in range(1, 41)]
    valor, n = recalcular(exs)["parametros"][("peso_opiniao_gerente", "g1")]
    assert n == 40
    assert valor == 0.15


def test_nnls_com_doze_exemplos_recupera_padrao_de_pesos():
    import itertools
    exs = []
    for i, (a, b) in enumerate(itertools.product([0, 1, 2, 3], [0, 1, 2]), start=1):
        sinais = {"partes": a, "novidade": b, "incerteza": 0, "dependencia": 0, "tamanho": 0, "risco": 0}
        exs.append(_ex(i, 3, 8, op=f"o{i}", sinais=sinais))
    r = recalcular(exs)["parametros"]
    assert r[("peso_sinal", "partes")][1] == 12
    assert all(r[("peso_sinal", s)][0] >= 0 for s in ("partes", "novidade", "incerteza"))
    assert r[("peso_sinal", "incerteza")][0] == 0.0
