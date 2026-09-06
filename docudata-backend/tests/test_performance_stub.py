"""Testes para GET /performance (RBAC-04, RBAC-05).

Cobre só o gate de RBAC (401 sem cookie, 403 pra não-líder) — checks que não
dependem do corpo da rota, então continuam válidos após a Phase 19 substituir
o stub pelo ranking real. O teste de sucesso (200 + audit log) que existia
aqui testava a resposta placeholder do stub (`status == "ok"`) e foi removido:
esse comportamento não existe mais por design — o caso de sucesso real, com
o mesmo registro de audit log, agora é coberto por
test_performance_endpoint.py.
"""
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def test_performance_sem_cookie_401(monkeypatch):
    from main import app
    tc = TestClient(app)

    resp = tc.get("/performance")

    assert resp.status_code == 401


def test_performance_nao_lider_retorna_403(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")

    resp = tc.get("/performance", cookies={"docudata_session": token})

    assert resp.status_code == 403
