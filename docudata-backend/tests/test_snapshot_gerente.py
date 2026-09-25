from services.pontuacao import campos_gerente, sincronizar_snapshot_gerente
from tests.fake_supabase import FakeClient

_AVAL = {
    "sprint_id": "sp-1", "operacional_id": "op-1",
    "resposta_1": 4, "resposta_2": 4, "resposta_3": 5, "resposta_4": 5,
    "resposta_5": 5, "resposta_6": 0, "resposta_7": 5,
}


def test_campos_gerente_ignora_resposta_6():
    assert campos_gerente(_AVAL) == {
        "gerente_media": 4.67,
        "gerente_pergunta6": 0,
        "gerente_pergunta3": 5,
    }


def test_sincroniza_linha_existente():
    fake = FakeClient({"pontuacao_operacional_sprint": [
        {"id": "p1", "sprint_id": "sp-1", "operacional_id": "op-1", "gerente_media": 5.0, "gerente_pergunta3": 5, "gerente_pergunta6": None},
        {"id": "p2", "sprint_id": "sp-1", "operacional_id": "op-2", "gerente_media": 3.0, "gerente_pergunta3": 3, "gerente_pergunta6": None},
    ]})

    sincronizar_snapshot_gerente(fake, _AVAL)

    linhas = {r["id"]: r for r in fake.tables["pontuacao_operacional_sprint"]}
    assert linhas["p1"]["gerente_media"] == 4.67
    assert linhas["p1"]["gerente_pergunta6"] == 0
    assert linhas["p2"]["gerente_media"] == 3.0  # outro operacional intacto


def test_sprint_aberta_sem_linha_e_no_op():
    fake = FakeClient({"pontuacao_operacional_sprint": []})

    sincronizar_snapshot_gerente(fake, _AVAL)

    assert fake.tables["pontuacao_operacional_sprint"] == []
