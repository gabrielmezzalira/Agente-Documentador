"""Testes para GET /operacionais/{id}/spi (Phase 18, SCORE-04).

RBAC: restrito a cargo=lider — nem gerente nem operacional podem ler score
(decisão RBAC Phase 16, .planning/intel/decisions.md #4).
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(linhas):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = linhas
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


def test_spi_de_um_projeto_e_o_spi_daquele_projeto(monkeypatch):
    client = _mock_client([
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 8, "entrega_pontos_alocados": 10},
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 2, "entrega_pontos_alocados": 5},
    ])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    body = resp.json()
    assert body["spi"] == round(10 / 15 * 100, 2)
    assert len(body["por_projeto"]) == 1


def test_spi_de_dois_projetos_e_media_simples_entre_projetos(monkeypatch):
    client = _mock_client([
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 10, "entrega_pontos_alocados": 10},
        {"projeto_id": "proj-2", "entrega_pontos_concluidos": 0, "entrega_pontos_alocados": 10},
    ])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    assert resp.json()["spi"] == 50.0


def test_spi_com_alocacoes_assimetricas_usa_media_de_spi_por_projeto(monkeypatch):
    """proj-1 (10/10=SPI 100) e proj-2 (5/20=SPI 25) têm alocações
    diferentes: a média correta de SPIs por projeto é (100+25)/2=62.5,
    diferente do que daria uma soma agrupada incorreta ((10+5)/(10+20)*100=50.0).
    Este teste só passa com a fórmula de duas camadas correta."""
    client = _mock_client([
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 10, "entrega_pontos_alocados": 10},
        {"projeto_id": "proj-2", "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 20},
    ])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    assert resp.json()["spi"] == 62.5


def test_projeto_com_zero_alocados_e_excluido_da_media(monkeypatch):
    """proj-2 tem entrega_pontos_alocados=0 — seu spi deve ser None e ele
    deve ser EXCLUÍDO da média entre projetos (não contado como zero)."""
    client = _mock_client([
        {"projeto_id": "proj-1", "entrega_pontos_concluidos": 8, "entrega_pontos_alocados": 10},
        {"projeto_id": "proj-2", "entrega_pontos_concluidos": 0, "entrega_pontos_alocados": 0},
    ])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    body = resp.json()
    assert body["spi"] == 80.0
    por_projeto = {p["projeto_id"]: p["spi"] for p in body["por_projeto"]}
    assert por_projeto["proj-2"] is None


def test_sem_nenhuma_linha_spi_e_none(monkeypatch):
    client = _mock_client([])
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 200
    assert resp.json()["spi"] is None
    assert resp.json()["por_projeto"] == []


def test_gerente_recebe_403(monkeypatch):
    client = _mock_client([])
    tc = _client_as(monkeypatch, client, "gerente")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 403


def test_operacional_recebe_403(monkeypatch):
    client = _mock_client([])
    tc = _client_as(monkeypatch, client, "operacional")

    resp = tc.get("/operacionais/op-1/spi")

    assert resp.status_code == 403
