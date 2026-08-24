import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


HEADERS = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}


class ExportQuery:
    def __init__(self, table_name: str, subarea: str):
        self.table_name = table_name
        self.subarea = subarea

    def select(self, _columns):
        return self

    def eq(self, _column, _value):
        return self

    def execute(self):
        if self.table_name == "generated_docs":
            return SimpleNamespace(data=[{
                "id": "doc-id",
                "project_id": "project-id",
                "doc_type": "planning",
                "sprint_number": 1,
                "content": "# Planning",
                "created_at": "2026-08-24T12:00:00+00:00",
            }])
        if self.table_name == "projects":
            return SimpleNamespace(data=[{
                "id": "project-id",
                "name": "Projeto Teste",
                "client": "CITi",
                "squad": None,
                "subarea": self.subarea,
            }])
        raise AssertionError(f"Tabela inesperada: {self.table_name}")


class ExportSupabase:
    def __init__(self, subarea: str):
        self.subarea = subarea

    def table(self, table_name: str):
        return ExportQuery(table_name, self.subarea)


@pytest.mark.parametrize("subarea", ["dados", "dev"])
def test_export_repassa_subarea_do_projeto(monkeypatch, subarea):
    import routers.export as export_router
    from main import app

    captured = {}
    monkeypatch.setattr(export_router, "get_client", lambda: ExportSupabase(subarea))
    monkeypatch.setattr(
        export_router,
        "export_to_gdocs",
        lambda **kwargs: captured.update(kwargs) or "https://docs.google.com/document/d/doc-id",
    )

    response = TestClient(app).post("/docs/doc-id/export-gdocs", headers=HEADERS)

    assert response.status_code == 200
    assert captured["subarea"] == subarea


def test_pasta_raiz_de_dados_mantem_variavel_existente(monkeypatch):
    from services.google_docs import _get_root_folder_id

    monkeypatch.setenv("GDRIVE_FOLDER_ID", "folder-dados")
    monkeypatch.setenv("GDRIVE_FOLDER_ID_DEV", "folder-dev")

    assert _get_root_folder_id("dados") == "folder-dados"


def test_pasta_raiz_de_dev_usa_variavel_com_sufixo(monkeypatch):
    from services.google_docs import _get_root_folder_id

    monkeypatch.setenv("GDRIVE_FOLDER_ID", "folder-dados")
    monkeypatch.setenv("GDRIVE_FOLDER_ID_DEV", "folder-dev")

    assert _get_root_folder_id("dev") == "folder-dev"


def test_dev_sem_pasta_configurada_nao_cai_em_dados(monkeypatch):
    from services.google_docs import _get_root_folder_id

    monkeypatch.setenv("GDRIVE_FOLDER_ID", "folder-dados")
    monkeypatch.delenv("GDRIVE_FOLDER_ID_DEV", raising=False)

    with pytest.raises(RuntimeError, match="GDRIVE_FOLDER_ID_DEV não configurado"):
        _get_root_folder_id("dev")


def test_template_planning_de_dados_mantem_variavel_existente(monkeypatch):
    from services.google_docs import _get_template_id

    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING", "template-planning-dados")
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING_DEV", "template-planning-dev")

    assert _get_template_id("planning", "dados") == "template-planning-dados"


def test_template_planning_de_dev_usa_variavel_com_sufixo(monkeypatch):
    from services.google_docs import _get_template_id

    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING", "template-planning-dados")
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING_DEV", "template-planning-dev")

    assert _get_template_id("planning", "dev") == "template-planning-dev"


def test_dev_sem_template_proprio_reutiliza_template_do_tipo_de_dados(monkeypatch):
    from services.google_docs import _get_template_id

    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING", "template-planning-dados")
    monkeypatch.setenv("GDOCS_TEMPLATE_ID", "template-geral-dados")
    monkeypatch.delenv("GDOCS_TEMPLATE_ID_PLANNING_DEV", raising=False)
    monkeypatch.delenv("GDOCS_TEMPLATE_ID_DEV", raising=False)

    assert _get_template_id("planning", "dev") == "template-planning-dados"


def test_dev_sem_template_do_tipo_reutiliza_template_geral_de_dados(monkeypatch):
    from services.google_docs import _get_template_id

    monkeypatch.setenv("GDOCS_TEMPLATE_ID", "template-geral-dados")
    monkeypatch.delenv("GDOCS_TEMPLATE_ID_PLANNING", raising=False)
    monkeypatch.delenv("GDOCS_TEMPLATE_ID_PLANNING_DEV", raising=False)
    monkeypatch.delenv("GDOCS_TEMPLATE_ID_DEV", raising=False)

    assert _get_template_id("planning", "dev") == "template-geral-dados"


def test_google_drive_usa_refresh_token_da_subarea(monkeypatch):
    import services.google_docs as google_docs

    credentials_calls = []
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "refresh-dados")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN_DEV", "refresh-dev")

    class FakeCredentials:
        def __init__(self, **kwargs):
            credentials_calls.append(kwargs)

        def refresh(self, _request):
            return None

    monkeypatch.setattr(google_docs, "OAuthCredentials", FakeCredentials)
    monkeypatch.setattr(google_docs, "Request", lambda: object())
    monkeypatch.setattr(google_docs, "build", lambda service, *_args, **_kwargs: service)

    google_docs._get_services("dados")
    google_docs._get_services("dev")

    assert credentials_calls[0]["refresh_token"] == "refresh-dados"
    assert credentials_calls[1]["refresh_token"] == "refresh-dev"
