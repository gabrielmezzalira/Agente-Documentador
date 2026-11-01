from datetime import datetime, timezone

from services.piso import (
    mediana, piso, realizados_por_pessoa, squad, trimestre_anterior, trimestre_de, trimestre_do_instante,
)


def t(op, pontos=2, col="concluida", extra=False):
    return {"operacional_id": op, "pontos": pontos, "coluna_kanban": col, "extra": extra}


def test_mediana():
    assert mediana([]) is None
    assert mediana([5, 1, 3]) == 3.0
    assert mediana([1, 2, 3, 10]) == 2.5


def test_piso():
    assert piso(6.0, 10.0) == 5.0
    assert piso(6.0, None) == 3.0
    assert piso(None, 5.0) == 2.5
    assert piso(None, None) is None
    assert piso(3.0, 3.0) == 1.5
    assert piso(2.34, None) == 1.2  # 1.17 arredonda para 1 casa


def test_trimestre_de():
    assert trimestre_de({"avaliacao_completa_em": "2026-10-10T00:00:00+00:00", "data_fim": "2026-01-01"}) == "2026-T4"
    assert trimestre_de({"avaliacao_completa_em": None, "data_fim": "2026-05-02"}) == "2026-T2"
    assert trimestre_de({"avaliacao_completa_em": None, "data_fim": None}) is None
    assert trimestre_do_instante(datetime(2026, 3, 31, tzinfo=timezone.utc)) == "2026-T1"


def test_trimestre_anterior_com_virada_de_ano():
    assert trimestre_anterior("2026-T4") == "2026-T3"
    assert trimestre_anterior("2026-T1") == "2025-T4"


def test_realizados_por_pessoa_e_squad():
    tasks = [t("a", 3), t("a", 2), t("b", 4, col="em_andamento"), t("c", 5, extra=True), t(None, 7), t("d", 1)]
    assert realizados_por_pessoa(tasks) == {"a": 5, "d": 1}
    assert squad(tasks) == {"a", "b", "c", "d"}


def test_realizados_do_squad_conta_zero_para_quem_nao_concluiu():
    from services.piso import realizados_do_squad
    tasks = [t("a", 3), t("b", 4, col="em_andamento"), t("c", 5, extra=True)]
    assert realizados_do_squad(tasks) == {"a": 3, "b": 0.0, "c": 0.0}
