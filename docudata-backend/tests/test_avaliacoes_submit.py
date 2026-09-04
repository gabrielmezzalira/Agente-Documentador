"""Testes para POST /avaliacoes (AVAL-01, AVAL-03)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(existing=None):
    client = MagicMock()
    calls = {"insert": [], "update": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [existing] if existing else []
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                calls["insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="aval-nova-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                calls["update"].append(payload)
                q = MagicMock()
                inner = MagicMock()
                resp = MagicMock()
                merged = dict(existing or {}, **payload)
                resp.data = [merged]
                inner.execute = MagicMock(return_value=resp)
                q.eq = MagicMock(return_value=inner)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")
    tc.cookies.set("docudata_session", token)
    return tc


_BODY_VALIDO = {
    "operacional_id": "op-1", "sprint_id": "sprint-1",
    "resposta_1": 5, "resposta_2": 4, "resposta_3": 3, "resposta_4": 2,
    "resposta_5": 1, "resposta_6": 0, "resposta_7": 5,
}


def test_cria_avaliacao_nova(monkeypatch):
    mock_sb, calls = _mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/avaliacoes", json=_BODY_VALIDO)

    assert resp.status_code == 201
    assert calls["insert"][0]["gerente_id"] == "pessoa-ger-1"
    assert "editavel_ate" in calls["insert"][0]
    assert len(calls["update"]) == 0


def test_upsert_dentro_de_48h_atualiza_mesma_linha(monkeypatch):
    editavel_ate = (datetime.now(timezone.utc) + timedelta(hours=40)).isoformat()
    existing = dict(_BODY_VALIDO, id="aval-1", gerente_id="pessoa-ger-1", editavel_ate=editavel_ate, reaproveitada_de=None, criado_em=datetime.now(timezone.utc).isoformat())
    mock_sb, calls = _mock_client(existing=existing)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/avaliacoes", json=dict(_BODY_VALIDO, resposta_1=3))

    assert resp.status_code == 201
    assert len(calls["update"]) == 1
    assert len(calls["insert"]) == 0
    assert calls["update"][0]["resposta_1"] == 3


def test_fora_de_48h_retorna_409(monkeypatch):
    editavel_ate = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    existing = dict(_BODY_VALIDO, id="aval-1", gerente_id="pessoa-ger-1", editavel_ate=editavel_ate, reaproveitada_de=None, criado_em=datetime.now(timezone.utc).isoformat())
    mock_sb, calls = _mock_client(existing=existing)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/avaliacoes", json=_BODY_VALIDO)

    assert resp.status_code == 409
    assert len(calls["update"]) == 0
    assert len(calls["insert"]) == 0


def test_resposta_fora_de_0_5_retorna_422(monkeypatch):
    mock_sb, calls = _mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/avaliacoes", json=dict(_BODY_VALIDO, resposta_1=6))

    assert resp.status_code == 422
    assert len(calls["insert"]) == 0
