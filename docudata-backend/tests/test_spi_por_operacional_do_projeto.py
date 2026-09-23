"""GET /projects/{id}/spi — substitui /spi-evolucao (a dimensão Evolução foi
removida, ver docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(operacionais=None, pontuacao=None):
    operacionais = operacionais or []
    pontuacao = pontuacao or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "proj-1"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _client_as(monkeypatch, mock_supabase, cargo):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.pontuacao as pontuacao_router
    monkeypatch.setattr(pontuacao_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", cargo))
    return tc


def test_spi_do_projeto_nao_tem_mais_campo_evolucao(monkeypatch):
    mock_sb = _mock_client(
        operacionais=[{"id": "op-1", "nome": "Ana"}],
        pontuacao=[{
            "operacional_id": "op-1", "entrega_pontos_concluidos": 9,
            "entrega_pontos_alocados": 10, "entrega_pontos_penalizados": 0,
        }],
    )
    tc = _client_as(monkeypatch, mock_sb, "gerente")

    resp = tc.get("/projects/proj-1/spi")

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["spi"] == 90.0
    assert "evolucao" not in body[0]


def test_spi_do_projeto_operacional_recebe_403(monkeypatch):
    mock_sb = _mock_client()
    tc = _client_as(monkeypatch, mock_sb, "operacional")

    resp = tc.get("/projects/proj-1/spi")

    assert resp.status_code == 403


def test_baseline_evolucao_endpoint_nao_existe_mais(monkeypatch):
    mock_sb = _mock_client()
    tc = _client_as(monkeypatch, mock_sb, "lider")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-1", "ciclo": "2026-S2"})

    assert resp.status_code == 404
