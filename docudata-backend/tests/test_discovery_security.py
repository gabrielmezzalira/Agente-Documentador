import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.security import require_discovery_key


@pytest.fixture
def client():
    app = FastAPI()

    @app.get("/x", dependencies=[Depends(require_discovery_key)])
    def _x():
        return {"ok": True}

    return TestClient(app)


def test_sem_variavel_configurada_falha_fechado(client, monkeypatch):
    monkeypatch.delenv("DOCUDATA_DISCOVERY_KEY", raising=False)
    resp = client.get("/x", headers={"X-Discovery-Key": "qualquer"})
    assert resp.status_code == 503


def test_sem_header_ou_header_errado_retorna_401(client, monkeypatch):
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", "chave-forte-de-teste")
    assert client.get("/x").status_code == 401
    assert client.get("/x", headers={"X-Discovery-Key": "errada"}).status_code == 401


def test_header_correto_passa(client, monkeypatch):
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", "chave-forte-de-teste")
    assert client.get("/x", headers={"X-Discovery-Key": "chave-forte-de-teste"}).status_code == 200


def test_a_chave_do_app_nao_serve_para_o_discovery(client, monkeypatch):
    import os
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", "chave-forte-de-teste")
    assert client.get("/x", headers={"X-Discovery-Key": os.environ["DOCUDATA_APP_SECRET"]}).status_code == 401


def test_header_com_caractere_nao_ascii_retorna_401_e_nao_500(client, monkeypatch):
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", "chave-forte-de-teste")
    resp = client.get("/x", headers={"X-Discovery-Key": "chavé".encode("latin-1")})
    assert resp.status_code == 401
