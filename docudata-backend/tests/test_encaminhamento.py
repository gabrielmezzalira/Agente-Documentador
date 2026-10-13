import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient

HEADERS = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}


def _row(subarea: str, pid: str = "p1") -> dict:
    return {
        "id": pid, "name": "Projeto", "client": "CITi", "subarea": subarea,
        "description": None, "squad": None, "is_delivered": False,
        "created_at": "2026-10-12T12:00:00+00:00",
    }


def test_patch_subarea_recusa_projeto_de_produto(monkeypatch, autenticar):
    from main import app
    fake = FakeClient({"projects": [_row("produto")]})
    monkeypatch.setattr("routers.projects.get_client", lambda: fake)
    client = autenticar(TestClient(app), "gerente")

    resp = client.patch("/projects/p1/subarea", json={"subarea": "dados"}, headers=HEADERS)

    assert resp.status_code == 409
    assert "encaminhar" in resp.json()["detail"]
    assert fake.tables["projects"][0]["subarea"] == "produto"


def test_patch_subarea_entre_dados_e_dev_continua_funcionando(monkeypatch, autenticar):
    from main import app
    fake = FakeClient({"projects": [_row("dados")]})
    monkeypatch.setattr("routers.projects.get_client", lambda: fake)
    client = autenticar(TestClient(app), "gerente")

    resp = client.patch("/projects/p1/subarea", json={"subarea": "dev"}, headers=HEADERS)

    assert resp.status_code == 200
    assert fake.tables["projects"][0]["subarea"] == "dev"
