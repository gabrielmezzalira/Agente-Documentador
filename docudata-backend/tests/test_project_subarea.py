import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


APP_KEY = os.environ["DOCUDATA_APP_SECRET"]
HEADERS = {"X-Docudata-Key": APP_KEY}


def _project_row(subarea: str = "dados") -> dict:
    return {
        "id": f"{subarea}-project-id",
        "name": "Projeto Teste",
        "client": "CITi",
        "subarea": subarea,
        "description": None,
        "squad": None,
        "budget_usd": None,
        "is_delivered": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _mock_supabase():
    client = MagicMock()

    def table_side_effect(table_name):
        table = MagicMock()

        if table_name == "projects":
            def insert(payload):
                query = MagicMock()
                response = MagicMock()
                response.data = [_project_row(payload["subarea"])]
                query.execute.return_value = response
                return query

            def select(_columns):
                query = MagicMock()
                detail_response = MagicMock()
                detail_response.data = [_project_row("dev")]

                def eq(column, value):
                    if column == "subarea":
                        list_response = MagicMock()
                        list_response.data = [_project_row(value)]
                        query.order.return_value.execute.return_value = list_response
                    else:
                        query.execute.return_value = detail_response
                    return query

                query.eq.side_effect = eq
                return query

            table.insert.side_effect = insert
            table.select.side_effect = select
        elif table_name == "ingestions":
            query = MagicMock()
            query.order.return_value = query
            response = MagicMock()
            response.data = []
            query.execute.return_value = response
            table.select.return_value = query

        return table

    client.table.side_effect = table_side_effect
    return client


@pytest.fixture
def client(monkeypatch):
    import routers.projects as projects_router
    from main import app

    monkeypatch.setattr(projects_router, "get_client", _mock_supabase)
    return TestClient(app, headers=HEADERS)


def test_post_projects_sem_subarea_retorna_422(client):
    response = client.post(
        "/projects",
        json={"name": "Projeto sem subárea", "client": "CITi"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("subarea", ["dados", "dev"])
def test_post_projects_aceita_subareas_validas(client, subarea):
    response = client.post(
        "/projects",
        json={"name": "Projeto Teste", "client": "CITi", "subarea": subarea},
    )

    assert response.status_code == 201
    assert response.json()["subarea"] == subarea


def test_post_projects_rejeita_subarea_fora_do_enum(client):
    response = client.post(
        "/projects",
        json={"name": "Projeto inválido", "client": "CITi", "subarea": "outraCoisa"},
    )

    assert response.status_code == 422


def test_get_projects_sem_subarea_retorna_422(client):
    response = client.get("/projects")

    assert response.status_code == 422


@pytest.mark.parametrize("subarea", ["dados", "dev"])
def test_get_projects_filtra_por_subarea(client, subarea):
    response = client.get(f"/projects?subarea={subarea}")

    assert response.status_code == 200
    assert [project["subarea"] for project in response.json()] == [subarea]


def test_get_projects_rejeita_subarea_invalida(client):
    response = client.get("/projects?subarea=lixo")

    assert response.status_code == 422


def test_get_project_por_id_inclui_subarea(client):
    response = client.get("/projects/project-id")

    assert response.status_code == 200
    assert response.json()["subarea"] == "dev"


def test_migration_v3_esta_comentada_no_final_do_schema():
    schema_path = Path(__file__).resolve().parents[1] / "supabase_schema.sql"
    expected = """-- Migration v3: subárea do projeto (dados | dev)
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS subarea text NOT NULL DEFAULT 'dados';
-- ALTER TABLE projects ADD CONSTRAINT projects_subarea_check
--   CHECK (subarea IN ('dados','dev'));"""

    assert expected in schema_path.read_text()
