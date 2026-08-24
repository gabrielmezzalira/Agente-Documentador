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


@pytest.mark.parametrize("headers", [{}, {"X-Docudata-Key": "errada"}])
def test_endpoint_protegido_rejeita_chave_ausente_ou_errada(client, headers):
    resposta = client.get("/projects", headers=headers)

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": ERRO_CHAVE}


def test_endpoint_protegido_aceita_chave_correta(client, monkeypatch):
    import routers.projects as projects

    resposta_supabase = MagicMock()
    resposta_supabase.data = []
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.order.return_value.execute.return_value = (
        resposta_supabase
    )
    monkeypatch.setattr(projects, "get_client", lambda: supabase)

    resposta = client.get(
        "/projects?subarea=dados",
        headers={"X-Docudata-Key": APP_KEY},
    )

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_todas_as_rotas_de_negocio_exigem_app_key():
    from core.security import require_app_key
    from main import app

    routers_incluidos = [
        route for route in app.routes if hasattr(route, "include_context")
    ]

    assert len(routers_incluidos) == 11
    for router_incluido in routers_incluidos:
        dependencies = [
            dependency.dependency
            for dependency in router_incluido.include_context.dependencies
        ]
        assert require_app_key in dependencies


def test_cors_aceita_apenas_origem_configurada_sem_credentials(client):
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
    assert permitida.headers.get("access-control-allow-credentials") is None
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
