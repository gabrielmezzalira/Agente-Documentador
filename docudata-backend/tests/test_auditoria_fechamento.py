from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient

FECHADA_EM = "2026-11-01T10:00:00+00:00"


@pytest.fixture
def api(monkeypatch, autenticar):
    def _make(fake, cargo="lider"):
        import routers.avaliacoes as router
        from main import app
        monkeypatch.setattr(router, "get_client", lambda: fake)
        return autenticar(TestClient(app), cargo=cargo)
    return _make


def _base():
    return FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": True,
                     "avaliacao_completa_em": FECHADA_EM}],
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS"}],
        "operacionais": [],
        "tasks": [],
        "pontuacao_operacional_sprint": [{"id": "l1", "sprint_id": "s1", "projeto_id": "p1",
                                           "operacional_id": "op-1", "finalizado_em": FECHADA_EM}],
        "pontuacao_eventos": [
            {"id": "e1", "sprint_id": "s1", "tipo": "entrega_concluida", "pontos": 3},
            {"id": "e2", "sprint_id": "s1", "tipo": "travamento_penalidade", "pontos": -2},
            {"id": "e3", "sprint_id": "s1", "tipo": "devolucao_penalidade", "pontos": -1},
        ],
        "eventos_pontuacao_tardios": [],
    })


def test_reconfirmar_sprint_fechada_nao_regrava_a_data(api):
    fake = _base()
    resp = api(fake, cargo="gerente").post("/avaliacoes/s1/confirmar")
    assert resp.status_code == 200
    # o response_model normaliza o offset (+00:00 -> Z); compara como instante
    assert datetime.fromisoformat(resp.json()["avaliacao_completa_em"]) == datetime.fromisoformat(FECHADA_EM)
    assert fake.tables["sprints"][0]["avaliacao_completa_em"] == FECHADA_EM


def test_reabrir_apaga_eventos_gerados_no_fechamento_e_preserva_devolucao(api):
    fake = _base()
    resp = api(fake).delete("/avaliacoes/s1/confirmar")
    assert resp.status_code == 200
    tipos = [e["tipo"] for e in fake.tables["pontuacao_eventos"]]
    assert tipos == ["devolucao_penalidade"]
    assert fake.tables["sprints"][0]["avaliacao_completa_em"] is None
