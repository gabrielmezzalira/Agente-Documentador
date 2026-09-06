"""GET /metodologia/{slug} — documento interno restrito a Líder e Gerente.

O conteúdo é a camada oculta do sistema de performance (pesos, fórmulas, notas
cruas), então o gate `require_not_operacional` é parte do contrato, não detalhe
de implementação.
"""
from fastapi.testclient import TestClient

from services.auth import criar_jwt

_SECRET = "test-secret-nao-usar-em-producao"


def test_sem_cookie_retorna_401():
    from main import app
    tc = TestClient(app)

    resp = tc.get("/metodologia/performance")

    assert resp.status_code == 401


def test_operacional_bloqueado(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    resp = tc.get("/metodologia/performance", cookies={"docudata_session": token})

    assert resp.status_code == 403


def test_gerente_recebe_o_documento(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")

    resp = tc.get("/metodologia/performance", cookies={"docudata_session": token})

    assert resp.status_code == 200
    body = resp.json()
    assert body["titulo"] == "Sistema de Acompanhamento de Performance"
    assert "Avaliação do Gerente" in body["conteudo"]


def test_lider_recebe_o_documento(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-lid-1", "lider@citi.com", "lider")

    resp = tc.get("/metodologia/performance", cookies={"docudata_session": token})

    assert resp.status_code == 200
    assert len(resp.json()["conteudo"]) > 1000


def test_slug_desconhecido_404(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-lid-1", "lider@citi.com", "lider")

    resp = tc.get("/metodologia/inexistente", cookies={"docudata_session": token})

    assert resp.status_code == 404
