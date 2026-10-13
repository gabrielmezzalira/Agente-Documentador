import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.fake_supabase import FakeClient

HEADERS = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}


def _row(subarea: str, pid: str) -> dict:
    return {
        "id": pid, "name": f"P-{pid}", "client": "CITi", "subarea": subarea,
        "description": None, "squad": None, "is_delivered": False,
        "created_at": "2026-10-12T12:00:00+00:00",
    }


def test_project_create_aceita_produto():
    from models.schemas import ProjectCreate
    assert ProjectCreate(name="P", client="C", subarea="produto").subarea == "produto"


def test_project_create_recusa_subarea_desconhecida():
    from models.schemas import ProjectCreate
    with pytest.raises(ValidationError):
        ProjectCreate(name="P", client="C", subarea="outra")


def test_project_response_aceita_produto():
    from models.schemas import ProjectResponse
    resp = ProjectResponse(**_row("produto", "p1"))
    assert resp.subarea == "produto"


def test_subarea_update_continua_so_dados_dev():
    from models.schemas import ProjectSubareaUpdate
    with pytest.raises(ValidationError):
        ProjectSubareaUpdate(subarea="produto")


def test_listagem_por_subarea_produto_isola_projetos(monkeypatch, autenticar):
    from main import app
    fake = FakeClient({"projects": [_row("produto", "p1"), _row("dados", "d1"), _row("dev", "v1")]})
    monkeypatch.setattr("routers.projects.get_client", lambda: fake)
    client = autenticar(TestClient(app), "gerente")

    resp = client.get("/projects", params={"subarea": "produto"}, headers=HEADERS)
    assert resp.status_code == 200
    assert [p["id"] for p in resp.json()] == ["p1"]

    assert client.get("/projects", params={"subarea": "outra"}, headers=HEADERS).status_code == 422
    assert [p["id"] for p in client.get("/projects", params={"subarea": "dados"}, headers=HEADERS).json()] == ["d1"]
