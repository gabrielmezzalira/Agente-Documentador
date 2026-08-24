import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


HEADERS = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}


class SearchQuery:
    def __init__(self, table_name, calls):
        self.table_name = table_name
        self.calls = calls
        self.filter_name = None
        self.filter_value = None

    def select(self, _columns):
        return self

    def eq(self, column, value):
        self.calls.append((self.table_name, "eq", column, value))
        self.filter_name = column
        self.filter_value = value
        return self

    def in_(self, column, values):
        values = list(values)
        self.calls.append((self.table_name, "in", column, values))
        self.filter_name = column
        self.filter_value = values
        return self

    def execute(self):
        if self.table_name == "projects" and self.filter_name == "subarea":
            return SimpleNamespace(data=[{"id": f"{self.filter_value}-id"}])
        if self.table_name == "ingestions":
            rows = {
                "dados-id": {
                    "project_id": "dados-id",
                    "sprint_number": 1,
                    "extracted_content": {"tecnologias": ["Python"], "resumo": "Dados"},
                },
                "dev-id": {
                    "project_id": "dev-id",
                    "sprint_number": 2,
                    "extracted_content": {"tecnologias": ["Python"], "resumo": "Dev"},
                },
            }
            return SimpleNamespace(data=[rows[project_id] for project_id in self.filter_value])
        if self.table_name == "projects" and self.filter_name == "id":
            projects = {
                "dados-id": {"id": "dados-id", "name": "Projeto Dados", "client": "CITi"},
                "dev-id": {"id": "dev-id", "name": "Projeto Dev", "client": "CITi"},
            }
            return SimpleNamespace(data=[projects[project_id] for project_id in self.filter_value])
        raise AssertionError("Consulta inesperada no mock")


class SearchSupabase:
    def __init__(self):
        self.calls = []

    def table(self, table_name):
        return SearchQuery(table_name, self.calls)


@pytest.mark.parametrize(
    "path",
    ["/search?q=python", "/search?q=python&subarea=lixo"],
)
def test_search_exige_subarea_valida(path):
    from main import app

    response = TestClient(app).get(path, headers=HEADERS)

    assert response.status_code == 422


def test_search_considera_somente_projetos_da_subarea(monkeypatch):
    import routers.search as search_router
    from main import app

    supabase = SearchSupabase()
    monkeypatch.setattr(search_router, "get_client", lambda: supabase)

    response = TestClient(app).get(
        "/search?q=python&subarea=dev",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert [result["project_id"] for result in response.json()["results"]] == ["dev-id"]
    assert ("projects", "eq", "subarea", "dev") in supabase.calls
    assert ("ingestions", "in", "project_id", ["dev-id"]) in supabase.calls
