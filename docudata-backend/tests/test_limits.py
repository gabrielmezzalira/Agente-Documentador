import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse


APP_KEY = os.environ["DOCUDATA_APP_SECRET"]
AUTH_HEADERS = {"X-Docudata-Key": APP_KEY}


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from core.rate_limit import limiter

    # O limiter fica ativo nos testes; só zeramos a memória para isolar cada caso.
    # Assim a suíte não mascara regressões de produção com um bypass ENV=test.
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def _empty_supabase():
    response = MagicMock()
    response.data = []
    query = MagicMock()
    for method in ("select", "eq", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value = response
    client = MagicMock()
    client.table.return_value = query
    return client


def test_defaults_sem_env():
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("MAX_UPLOAD_MB", None)
    env.pop("RATE_LIMIT_PER_MINUTE", None)
    env["DOCUDATA_APP_SECRET"] = APP_KEY
    codigo = (
        "import dotenv; "
        "dotenv.load_dotenv = lambda *args, **kwargs: False; "
        "import main; "
        "from core.rate_limit import RATE_LIMIT_PER_MINUTE; "
        "assert main.max_upload_mb == 20; "
        "assert RATE_LIMIT_PER_MINUTE == 20"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr


def test_content_length_acima_do_limite_retorna_413_antes_do_handler(
    client, monkeypatch
):
    import routers.ingest as ingest_router
    from main import max_upload_bytes

    get_client = MagicMock(side_effect=AssertionError("handler não deveria executar"))
    monkeypatch.setattr(ingest_router, "get_client", get_client)

    resposta = client.post(
        "/ingest",
        files={"arquivo": ("arquivo.txt", b"conteudo", "text/plain")},
        data={"sprint_numero": "1", "projeto_id": "projeto-teste"},
        headers={
            **AUTH_HEADERS,
            "Content-Length": str(max_upload_bytes + 1),
        },
    )

    assert resposta.status_code == 413
    assert "limite" in resposta.json()["detail"].lower()
    get_client.assert_not_called()


@pytest.mark.asyncio
async def test_sem_content_length_request_segue_para_handler():
    from main import reject_oversized_request

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/ingest",
            "headers": [],
        }
    )
    call_next = AsyncMock(return_value=JSONResponse({"status": "continuou"}))

    resposta = await reject_oversized_request(request, call_next)

    assert resposta.status_code == 200
    call_next.assert_awaited_once_with(request)


def test_rate_limit_retorna_429_na_requisicao_n_mais_1(client, monkeypatch):
    import routers.generate as generate_router
    from core.rate_limit import RATE_LIMIT_PER_MINUTE

    monkeypatch.setattr(generate_router, "get_client", _empty_supabase)
    headers = {**AUTH_HEADERS, "X-Forwarded-For": "203.0.113.10"}
    payload = {"projeto_id": "inexistente", "tipo_doc": "log_decisoes"}

    respostas = [
        client.post("/generate", json=payload, headers=headers)
        for _ in range(RATE_LIMIT_PER_MINUTE + 1)
    ]

    assert all(response.status_code == 404 for response in respostas[:-1])
    assert respostas[-1].status_code == 429
    assert respostas[-1].headers.get("Retry-After")


def test_x_forwarded_for_separa_clientes_atras_do_proxy(client, monkeypatch):
    import routers.generate as generate_router
    from core.rate_limit import RATE_LIMIT_PER_MINUTE

    monkeypatch.setattr(generate_router, "get_client", _empty_supabase)
    payload = {"projeto_id": "inexistente", "tipo_doc": "log_decisoes"}
    primeiro_ip = {**AUTH_HEADERS, "X-Forwarded-For": "203.0.113.20, 10.0.0.1"}
    segundo_ip = {**AUTH_HEADERS, "X-Forwarded-For": "203.0.113.21, 10.0.0.1"}

    for _ in range(RATE_LIMIT_PER_MINUTE):
        assert client.post("/generate", json=payload, headers=primeiro_ip).status_code == 404

    assert client.post("/generate", json=payload, headers=primeiro_ip).status_code == 429
    assert client.post("/generate", json=payload, headers=segundo_ip).status_code == 404


def test_get_client_ip_usa_primeiro_forwarded_for_e_fallback():
    from core.rate_limit import get_client_ip

    forwarded = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [(b"x-forwarded-for", b"198.51.100.5, 10.0.0.1")],
            "client": ("10.0.0.2", 1234),
        }
    )
    direto = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "client": ("198.51.100.6", 1234),
        }
    )

    assert get_client_ip(forwarded) == "198.51.100.5"
    assert get_client_ip(direto) == "198.51.100.6"


def test_apenas_os_nove_endpoints_gemini_tem_rate_limit():
    from core.rate_limit import limiter

    assert set(limiter._route_limits) == {
        "routers.ingest.ingest",
        "routers.generate.generate",
        "routers.enrich.enrich",
        "routers.commit_ingest.ingest_commit",
        "routers.sprint_docs.submit_planning",
        "routers.sprint_docs.submit_daily",
        "routers.sprint_docs.submit_ata_with_upload",
        "routers.sprint_docs.submit_review",
        "routers.sprint_docs.submit_retrospectiva",
    }


def test_endpoints_de_leitura_nao_tem_rate_limit(client, monkeypatch):
    import routers.ingestions as ingestions_router
    import routers.projects as projects_router
    from core.rate_limit import RATE_LIMIT_PER_MINUTE

    monkeypatch.setattr(projects_router, "get_client", _empty_supabase)
    monkeypatch.setattr(ingestions_router, "get_client", _empty_supabase)
    repeticoes = RATE_LIMIT_PER_MINUTE + 2
    headers = {**AUTH_HEADERS, "X-Forwarded-For": "192.0.2.50"}

    health = [client.get("/health") for _ in range(repeticoes)]
    projects = [
        client.get("/projects?subarea=dados", headers=headers)
        for _ in range(repeticoes)
    ]
    ingestions = [
        client.get("/ingestions/projeto-teste", headers=headers)
        for _ in range(repeticoes)
    ]

    assert all(response.status_code == 200 for response in health)
    assert all(response.status_code == 200 for response in projects)
    assert all(response.status_code == 200 for response in ingestions)
    assert all("X-RateLimit-Limit" not in response.headers for response in projects)
