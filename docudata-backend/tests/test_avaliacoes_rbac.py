"""Testes de RBAC do avaliacoes.router (AVAL-05)."""
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def test_operacional_403_em_pendencias(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    resp = tc.get("/avaliacoes/sprint-1/pendencias", cookies={"docudata_session": token})

    assert resp.status_code == 403


def test_operacional_403_em_post_avaliacao(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    resp = tc.post("/avaliacoes", json={
        "operacional_id": "op-1", "sprint_id": "sprint-1",
        "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_6": 5, "resposta_7": 5,
    }, cookies={"docudata_session": token})

    assert resp.status_code == 403


def test_sem_cookie_401(monkeypatch):
    from main import app
    tc = TestClient(app)

    resp = tc.get("/avaliacoes/sprint-1/pendencias")

    assert resp.status_code == 401
