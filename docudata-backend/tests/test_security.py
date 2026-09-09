import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


APP_KEY = os.environ["DOCUDATA_APP_SECRET"]
ERRO_CHAVE = "Chave de aplicação ausente ou inválida"


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def test_backend_falha_no_boot_sem_app_secret():
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("DOCUDATA_APP_SECRET", None)
    codigo = (
        "import os; "
        "os.environ.pop('DOCUDATA_APP_SECRET', None); "
        "import dotenv; "
        "dotenv.load_dotenv = lambda *args, **kwargs: False; "
        "import main"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode != 0
    assert "DOCUDATA_APP_SECRET deve estar definida" in resultado.stderr


def test_health_nao_exige_header(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"X-Docudata-Key": "errada"}, {"X-Docudata-Key": APP_KEY}])
def test_endpoint_do_frontend_rejeita_sessao_ausente(client, headers):
    resposta = client.get("/projects?subarea=dados", headers=headers)

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Não autenticado"}


def test_endpoint_do_frontend_aceita_cookie_de_sessao(client, monkeypatch, autenticar):
    import routers.projects as projects

    resposta_supabase = MagicMock()
    resposta_supabase.data = []
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.order.return_value.execute.return_value = (
        resposta_supabase
    )
    monkeypatch.setattr(projects, "get_client", lambda: supabase)

    resposta = autenticar(client).get("/projects?subarea=dados")

    assert resposta.status_code == 200
    assert resposta.json() == []


@pytest.mark.parametrize("headers", [{}, {"X-Docudata-Key": "errada"}])
def test_endpoint_de_automacao_rejeita_app_key_ausente_ou_errada(client, headers):
    resposta = client.post("/ingest/commit", headers=headers, json={})

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": ERRO_CHAVE}


def test_dependencias_separam_browser_automacoes_e_webhooks_publicos():
    from core.security import require_app_key
    from main import app
    from services.auth import get_current_pessoa, require_not_operacional

    routers_incluidos = [
        route for route in app.routes if hasattr(route, "include_context")
    ]

    def encontrar(path):
        return next(
            incluido
            for incluido in routers_incluidos
            if path in {rota.path for rota in incluido.original_router.routes}
        )

    def dependencias(incluido):
        return {dep.dependency for dep in incluido.include_context.dependencies}

    assert get_current_pessoa in dependencias(encontrar("/projects"))
    assert require_not_operacional in dependencias(encontrar("/settings/gemini"))
    assert require_not_operacional in dependencias(encontrar("/integrations/github/capabilities"))
    for path in ("/ingest/commit", "/ingest/revisao", "/ingest/aceite"):
        assert require_app_key in dependencias(encontrar(path))

    # Callback e webhook usam autenticação própria: state assinado e HMAC bruto.
    publico_github = encontrar("/webhooks/github")
    assert not publico_github.include_context.dependencies
    assert {route.path for route in publico_github.original_router.routes} == {
        "/integrations/github/callback",
        "/webhooks/github",
    }


def test_cors_aceita_apenas_origem_configurada_com_credentials(client):
    permitida = client.options(
        "/projects",
        headers={
            "Origin": "https://frontend.test",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Docudata-Key",
        },
    )
    nao_permitida = client.options(
        "/projects",
        headers={
            "Origin": "https://scanner.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert permitida.status_code == 200
    assert permitida.headers["access-control-allow-origin"] == "https://frontend.test"
    assert permitida.headers.get("access-control-allow-credentials") == "true"
    assert "access-control-allow-origin" not in nao_permitida.headers


def test_require_app_key_usa_compare_digest(monkeypatch):
    from core import security

    argumentos = []

    def comparar(recebida, esperada):
        argumentos.append((recebida, esperada))
        return True

    monkeypatch.setattr(security.secrets, "compare_digest", comparar)

    security.require_app_key(APP_KEY)

    assert argumentos == [(APP_KEY, security.APP_SECRET)]
