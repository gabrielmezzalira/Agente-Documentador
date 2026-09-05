"""Testes para POST /baseline-evolucao (Phase 18, SCORE-05).

Ciclo é texto livre informado pelo Líder no momento do snapshot manual (sem
calendário fixo — decisão do brainstorming). nota_inicial = SPI calculado
on-the-fly no momento do request.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(operacional_existe=True, pontuacao_linhas=None, insert_capture=None):
    pontuacao_linhas = pontuacao_linhas or []
    insert_capture = insert_capture if insert_capture is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "op-1"}] if operacional_existe else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao_linhas
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "baseline_evolucao":
            def insert_side_effect(payload):
                insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="baseline-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, insert_capture


def _client_as(monkeypatch, mock_supabase, cargo):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.pontuacao as pontuacao_router
    monkeypatch.setattr(pontuacao_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", cargo))
    return tc


def test_lider_cria_baseline_com_nota_inicial_calculada(monkeypatch):
    mock_sb, insert_capture = _mock_client(
        pontuacao_linhas=[{"projeto_id": "proj-1", "entrega_pontos_concluidos": 9, "entrega_pontos_alocados": 10}],
    )
    tc = _client_as(monkeypatch, mock_sb, "lider")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-1", "ciclo": "2026-S2"})

    assert resp.status_code == 201
    assert insert_capture[0]["ciclo"] == "2026-S2"
    assert insert_capture[0]["nota_inicial"] == 90.0
    assert resp.json()["nota_inicial"] == 90.0


def test_operacional_inexistente_retorna_404(monkeypatch):
    mock_sb, insert_capture = _mock_client(operacional_existe=False)
    tc = _client_as(monkeypatch, mock_sb, "lider")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-inexistente", "ciclo": "2026-S2"})

    assert resp.status_code == 404
    assert insert_capture == []


def test_gerente_recebe_403(monkeypatch):
    mock_sb, _ = _mock_client()
    tc = _client_as(monkeypatch, mock_sb, "gerente")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-1", "ciclo": "2026-S2"})

    assert resp.status_code == 403
