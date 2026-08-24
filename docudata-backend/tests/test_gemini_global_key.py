import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient


APP_HEADERS = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}


class MemorySettingsTable:
    def __init__(self, store):
        self.store = store
        self.columns = ""
        self.payload = None

    def select(self, columns):
        self.columns = columns
        return self

    def eq(self, _column, _value):
        return self

    def limit(self, _value):
        return self

    def upsert(self, payload, on_conflict):
        assert on_conflict == "key"
        self.payload = payload
        return self

    def execute(self):
        if self.payload is not None:
            self.store.clear()
            self.store.update(self.payload)
            return SimpleNamespace(data=[self.payload])
        if not self.store:
            return SimpleNamespace(data=[])
        requested = [column.strip() for column in self.columns.split(",")]
        return SimpleNamespace(data=[{column: self.store.get(column) for column in requested}])


class MemorySettingsClient:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        assert name == "app_settings"
        return MemorySettingsTable(self.store)


@pytest.fixture
def settings_store(monkeypatch):
    import services.gemini_key as service

    store = {}
    monkeypatch.setenv("DOCUDATA_SECRETS_KEY", Fernet.generate_key().decode("utf-8"))
    monkeypatch.setattr(service, "get_client", lambda: MemorySettingsClient(store))
    return store


def test_servico_sem_chave_levanta_erro_controlado(settings_store):
    from services.gemini_key import GeminiApiKeyNotConfigured, get_gemini_api_key

    with pytest.raises(GeminiApiKeyNotConfigured):
        get_gemini_api_key()


def test_servico_criptografa_recupera_substitui_e_expoe_somente_hint(settings_store):
    from services.gemini_key import (
        get_gemini_api_key,
        get_gemini_api_key_status,
        set_gemini_api_key,
    )

    first = "fake-gemini-key-1111"
    set_gemini_api_key(first)
    assert settings_store["encrypted_value"] != first
    assert first not in settings_store["encrypted_value"]
    assert get_gemini_api_key() == first

    second = "fake-gemini-key-2222"
    set_gemini_api_key(second)
    assert get_gemini_api_key() == second
    status = get_gemini_api_key_status()
    assert status["key_hint"] == "••••••••2222"
    assert set(status) == {"configured", "key_hint", "updated_at"}
    assert second not in str(status)


@pytest.mark.parametrize("invalid_secret", ["", "not-a-fernet-key"])
def test_secret_de_criptografia_ausente_ou_invalida_e_controlada(settings_store, monkeypatch, invalid_secret):
    from services.gemini_key import GeminiApiKeyStorageError, set_gemini_api_key

    monkeypatch.setenv("DOCUDATA_SECRETS_KEY", invalid_secret)
    with pytest.raises(GeminiApiKeyStorageError) as error:
        set_gemini_api_key("gemini-secret-that-must-not-leak")
    assert "gemini-secret-that-must-not-leak" not in str(error.value)


def test_endpoints_de_settings_nao_expoem_segredo_e_substituem(monkeypatch):
    import routers.settings as settings_router
    from main import app

    state = {"configured": False, "key_hint": None, "updated_at": None}
    received = []

    def fake_set(api_key):
        received.append(api_key)
        state.update({
            "configured": True,
            "key_hint": f"••••••••{api_key[-4:]}",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return dict(state)

    monkeypatch.setattr(settings_router, "get_gemini_api_key_status", lambda: dict(state))
    monkeypatch.setattr(settings_router, "set_gemini_api_key", fake_set)
    client = TestClient(app)

    assert client.get("/settings/gemini", headers=APP_HEADERS).json() == state
    assert client.put("/settings/gemini/api-key", json={"api_key": "first-secret-1111"}).status_code == 401

    first = client.put(
        "/settings/gemini/api-key",
        headers=APP_HEADERS,
        json={"api_key": "first-secret-1111"},
    )
    second = client.put(
        "/settings/gemini/api-key",
        headers=APP_HEADERS,
        json={"api_key": "second-secret-2222"},
    )
    assert first.status_code == second.status_code == 200
    assert received == ["first-secret-1111", "second-secret-2222"]
    assert first.json()["key_hint"] == "••••••••1111"
    assert second.json()["key_hint"] == "••••••••2222"
    assert "secret" not in first.text and "secret" not in second.text
    assert set(second.json()) == {"configured", "key_hint", "updated_at"}


@pytest.mark.parametrize("api_key", ["", "   "])
def test_put_rejeita_chave_vazia_ou_so_espacos(settings_store, api_key):
    from main import app

    response = TestClient(app).put(
        "/settings/gemini/api-key",
        headers=APP_HEADERS,
        json={"api_key": api_key},
    )
    assert response.status_code == 422


def test_fluxo_generate_usa_mesma_chave_global_para_projetos_de_subareas_distintas(monkeypatch):
    import graphs.generation_graph as generation_graph_module
    import routers.generate as generate_router
    from main import app

    projects = {
        "dados-id": {"id": "dados-id", "name": "Dados", "client": "CITi", "subarea": "dados"},
        "dev-id": {"id": "dev-id", "name": "Dev", "client": "CITi", "subarea": "dev"},
    }
    states = []
    constructor_keys = []

    class ProjectQuery:
        def __init__(self):
            self.project_id = None
        def select(self, _columns): return self
        def eq(self, column, value):
            if column == "id": self.project_id = value
            return self
        def execute(self): return SimpleNamespace(data=[projects[self.project_id]])

    class DocsQuery:
        def select(self, _columns): return self
        def eq(self, _column, _value): return self
        def order(self, *_args, **_kwargs): return self
        def limit(self, _value): return self
        def execute(self):
            return SimpleNamespace(data=[{
                "id": "doc-id", "doc_type": "onboarding", "sprint_number": None,
                "content": "ok", "created_at": datetime.now(timezone.utc).isoformat(),
            }])

    fake_client = MagicMock()
    fake_client.table.side_effect = lambda name: ProjectQuery() if name == "projects" else DocsQuery()

    async def fake_ainvoke(state):
        states.append(state)
        generation_graph_module._make_llm(state["api_key"])
        return {"erro_contexto": None}

    monkeypatch.setattr(
        generation_graph_module,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: constructor_keys.append(kwargs["google_api_key"]) or MagicMock(),
    )
    monkeypatch.setattr(generate_router, "get_client", lambda: fake_client)
    monkeypatch.setattr(generate_router, "get_gemini_api_key", lambda: "global-test-key")
    monkeypatch.setattr(generate_router.generation_graph, "ainvoke", fake_ainvoke)
    client = TestClient(app)

    for project_id in projects:
        response = client.post(
            "/generate",
            headers=APP_HEADERS,
            json={"projeto_id": project_id, "tipo_doc": "onboarding"},
        )
        assert response.status_code == 200

    assert [state["api_key"] for state in states] == ["global-test-key", "global-test-key"]
    assert constructor_keys == ["global-test-key", "global-test-key"]
    assert all("subarea" not in state for state in states)


def test_ausencia_da_chave_global_retorna_422_amigavel(monkeypatch):
    import routers.generate as generate_router
    from main import app
    from services.gemini_key import GeminiApiKeyNotConfigured

    query = MagicMock()
    query.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": "project-id", "name": "Projeto", "client": "CITi"}]
    )
    client_mock = MagicMock()
    client_mock.table.return_value = query
    monkeypatch.setattr(generate_router, "get_client", lambda: client_mock)
    monkeypatch.setattr(
        generate_router,
        "get_gemini_api_key",
        lambda: (_ for _ in ()).throw(GeminiApiKeyNotConfigured()),
    )

    response = TestClient(app).post(
        "/generate",
        headers=APP_HEADERS,
        json={"projeto_id": "project-id", "tipo_doc": "onboarding"},
    )
    assert response.status_code == 422
    assert "ainda não está configurada" in response.json()["detail"]


def test_fluxos_gemini_usam_resolucao_global_sem_coluna_legada():
    backend = Path(__file__).resolve().parents[1]
    router_files = ["ingest.py", "generate.py", "enrich.py", "commit_ingest.py", "sprint_docs.py"]
    for filename in router_files:
        source = (backend / "routers" / filename).read_text()
        assert "get_gemini_api_key" in source
        assert 'project.get("gemini_api_key")' not in source
        assert 'select("gemini_api_key' not in source


def test_projeto_nao_tem_campos_gemini_e_endpoint_antigo_nao_existe(monkeypatch):
    import routers.projects as projects_router
    from main import app
    from models.schemas import ProjectCreate, ProjectResponse

    assert "gemini_api_key" not in ProjectCreate.model_fields
    assert "has_api_key" not in ProjectResponse.model_fields

    inserted = {}
    table = MagicMock()
    def insert(payload):
        inserted.update(payload)
        query = MagicMock()
        query.execute.return_value = SimpleNamespace(data=[{
            **payload,
            "id": "project-id",
            "is_delivered": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }])
        return query
    table.insert.side_effect = insert
    db = MagicMock()
    db.table.return_value = table
    monkeypatch.setattr(projects_router, "get_client", lambda: db)
    client = TestClient(app)

    created = client.post(
        "/projects",
        headers=APP_HEADERS,
        json={"name": "Projeto", "client": "CITi", "subarea": "dados"},
    )
    assert created.status_code == 201
    assert all("gemini" not in key for key in inserted)
    assert all("gemini" not in key for key in created.json())
    assert client.patch(
        "/projects/project-id/api-key",
        headers=APP_HEADERS,
        json={"gemini_api_key": "legacy"},
    ).status_code == 404


def test_migration_global_esta_comentada_e_preserva_coluna_legada():
    schema = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text()
    assert "gemini_api_key  text" in schema
    assert "-- CREATE TABLE IF NOT EXISTS app_settings" in schema
    assert "-- ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;" in schema
