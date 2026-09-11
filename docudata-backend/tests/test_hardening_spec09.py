"""Spec 09 — hardening compatível: erros sanitizados, guardas de arquivo,
documentação desligável, limite de autenticação e consultas restritas.
"""
import io
import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.auth import hash_senha


BACKEND_DIR = Path(__file__).resolve().parents[1]
SEGREDO_VAZADO = "postgresql://usuario:senha-secreta@db.interno/postgres"


@pytest.fixture
def client(autenticar):
    from main import app

    # raise_server_exceptions=False faz o TestClient devolver a resposta do
    # handler global em vez de repropagar a exceção, que é justamente o que
    # o navegador recebe em produção.
    return autenticar(TestClient(app, raise_server_exceptions=False))


def _rodar_no_subprocesso(codigo: str, env_extra: dict[str, str]):
    env = os.environ.copy()
    env.update(env_extra)
    prelude = (
        "import dotenv; dotenv.load_dotenv = lambda *a, **k: False\n"
        "from fastapi.testclient import TestClient\n"
        "import main\n"
        "cliente = TestClient(main.app)\n"
    )
    return subprocess.run(
        [sys.executable, "-c", prelude + codigo],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


# ── 1 e 2 · exceção não tratada não vaza detalhe interno ────────────────────

def test_excecao_nao_tratada_devolve_mensagem_generica_e_request_id(
    client, monkeypatch, caplog
):
    import routers.projects as projects

    caplog.set_level(logging.ERROR, logger="docudata.request")

    def explodir():
        raise RuntimeError(SEGREDO_VAZADO)

    monkeypatch.setattr(projects, "get_client", explodir)

    resposta = client.get("/projects?subarea=dados")

    assert resposta.status_code == 500
    corpo = resposta.json()
    assert corpo["detail"] == "Erro interno no servidor. Tente novamente em instantes."
    assert corpo["request_id"]
    assert resposta.headers["X-Request-ID"] == corpo["request_id"]
    assert SEGREDO_VAZADO not in resposta.text
    assert "RuntimeError" not in resposta.text
    assert "Traceback" not in resposta.text
    assert SEGREDO_VAZADO not in caplog.text
    assert corpo["request_id"] in caplog.text
    assert "status=500" in caplog.text
    assert "stack=" in caplog.text


def test_request_id_recebido_e_reaproveitado_quando_tem_formato_seguro(client):
    resposta = client.get("/health", headers={"X-Request-ID": "req-abc-123456"})

    assert resposta.headers["X-Request-ID"] == "req-abc-123456"


def test_request_id_de_resposta_bem_sucedida_e_pesquisavel_no_log(client, caplog):
    caplog.set_level(logging.INFO, logger="docudata.request")

    resposta = client.get("/health", headers={"X-Request-ID": "req-health-12345"})

    assert resposta.status_code == 200
    assert "request_id=req-health-12345" in caplog.text
    assert "method=GET" in caplog.text
    assert "path=/health" in caplog.text
    assert "status=200" in caplog.text


@pytest.mark.parametrize(
    "recebido",
    [
        "curto",                       # abaixo do mínimo
        "x" * 200,                     # acima do máximo
        "abc def ghi",                 # espaço
        "valido\r\nX-Injetado: sim",   # tentativa de header injection
    ],
)
def test_request_id_malformado_e_substituido(client, recebido):
    from core.observability import normalizar_request_id

    gerado = normalizar_request_id(recebido)

    assert gerado != recebido
    assert len(gerado) == 32
    assert gerado.isalnum()


def test_toda_resposta_carrega_request_id(client, monkeypatch):
    import routers.projects as projects

    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    monkeypatch.setattr(projects, "get_client", lambda: supabase)

    from main import max_upload_bytes

    grande_demais = client.post(
        "/ingest",
        files={"arquivo": ("a.txt", b"x", "text/plain")},
        data={"sprint_numero": "1", "projeto_id": "p"},
        headers={"Content-Length": str(max_upload_bytes + 1)},
    )

    respostas = {
        "health": client.get("/health"),
        "404": client.get("/projects/inexistente"),
        "413": grande_demais,
    }
    assert respostas["413"].status_code == 413
    for nome, resposta in respostas.items():
        assert resposta.headers.get("X-Request-ID"), nome


def test_resposta_429_tambem_carrega_request_id(monkeypatch):
    import routers.auth as auth_router
    from core.rate_limit import AUTH_LOGIN_PER_MINUTE
    from main import app

    monkeypatch.setattr(auth_router, "get_client", lambda: _supabase_com_pessoa(None))
    cliente = TestClient(app)

    for _ in range(AUTH_LOGIN_PER_MINUTE):
        _login(cliente, "alguem@citi.org.br", "203.0.113.90")
    bloqueada = _login(cliente, "alguem@citi.org.br", "203.0.113.90")

    assert bloqueada.status_code == 429
    assert bloqueada.headers.get("X-Request-ID")


def test_falhas_externas_viram_mensagem_estavel_sem_detalhe_do_servico(caplog):
    from core.observability import falha_externa
    from routers.github_integration import _erro_indisponivel
    from services.github_app import GitHubApiError, GitHubConfigurationError

    caplog.set_level(logging.WARNING, logger="docudata.request")
    interno = "token ghs_secreto rejeitado por https://api.github.com/app/installations/42"

    erro_api = _erro_indisponivel(GitHubApiError(interno))
    erro_config = _erro_indisponivel(
        GitHubConfigurationError("GITHUB_APP_PRIVATE_KEY não é uma chave PEM válida.")
    )
    erro_gemini = falha_externa(
        "gemini.teste", RuntimeError("API key AIzaSyFAKE rejeitada"), "Não foi possível analisar"
    )

    assert erro_api.status_code == 503
    assert erro_api.detail == "Não foi possível consultar o GitHub. Tente novamente em instantes."
    assert erro_config.detail == erro_api.detail
    assert "ghs_secreto" not in str(erro_api.detail)
    assert "PRIVATE_KEY" not in str(erro_config.detail)
    assert erro_gemini.detail == "Não foi possível analisar"
    assert "AIzaSy" not in str(erro_gemini.detail)
    assert "ghs_secreto" not in caplog.text
    assert "PRIVATE_KEY" not in caplog.text
    assert "AIzaSy" not in caplog.text


def test_nenhuma_rota_interpola_excecao_na_resposta():
    """Guarda de regressão: a busca da spec não pode voltar a encontrar nada."""
    import re

    interpolacao = r"detail=f[\"'][^\"']*\{(?:e" + r"xc|e|err|pe)[.}]"
    string_direta = "detail=" + r"str\("
    padrao = re.compile(interpolacao + "|" + string_direta)
    ofensores = []
    for arquivo in list(BACKEND_DIR.glob("routers/*.py")) + list(BACKEND_DIR.glob("graphs/*.py")) + [BACKEND_DIR / "main.py"]:
        for numero, linha in enumerate(arquivo.read_text().splitlines(), 1):
            if padrao.search(linha):
                ofensores.append(f"{arquivo.name}:{numero}")

    assert ofensores == []


# ── 3 · erros de negócio mantêm status e mensagem ───────────────────────────

def test_erros_de_negocio_mantem_status_e_mensagem(client, monkeypatch):
    import routers.projects as projects

    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    monkeypatch.setattr(projects, "get_client", lambda: supabase)

    resposta = client.get("/projects/inexistente")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Project not found"


def _supabase_de_operacionais(existentes, erro_no_insert=None):
    """Mock por tabela: `projects` acha o projeto, `operacionais` responde a
    checagem de nome duplicado e, opcionalmente, falha no insert."""
    supabase = MagicMock()

    def tabela(nome):
        consulta = MagicMock()
        resposta = MagicMock()
        resposta.data = [{"id": "projeto-1"}] if nome == "projects" else existentes
        for metodo in ("select", "eq"):
            getattr(consulta, metodo).return_value = consulta
        consulta.execute.return_value = resposta
        if erro_no_insert is not None:
            consulta.insert.return_value.execute.side_effect = erro_no_insert
        return consulta

    supabase.table.side_effect = tabela
    return supabase


def test_conflito_de_operacional_continua_409_com_mensagem_amigavel(client, monkeypatch):
    import routers.operacionais as operacionais

    monkeypatch.setattr(
        operacionais, "get_client", lambda: _supabase_de_operacionais([{"nome": "Ana"}])
    )

    resposta = client.post(
        "/operacionais", json={"project_id": "projeto-1", "nome": "Ana"}
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "Já existe um operacional com o nome 'Ana' neste projeto"


def test_falha_inesperada_de_insert_nao_expoe_erro_do_supabase(client, monkeypatch):
    import routers.operacionais as operacionais

    monkeypatch.setattr(
        operacionais,
        "get_client",
        lambda: _supabase_de_operacionais([], erro_no_insert=Exception(SEGREDO_VAZADO)),
    )

    resposta = client.post(
        "/operacionais", json={"project_id": "projeto-1", "nome": "Ana"}
    )

    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "Não foi possível criar o operacional"
    assert SEGREDO_VAZADO not in resposta.text


# ── 5 · documentação da API desligável ──────────────────────────────────────

def test_docs_disponiveis_com_a_flag_ligada():
    resultado = _rodar_no_subprocesso(
        "assert cliente.get('/docs').status_code == 200\n"
        "assert cliente.get('/openapi.json').status_code == 200\n"
        "assert cliente.get('/redoc').status_code == 200\n"
        "print('OK')\n",
        {"API_DOCS_ENABLED": "true"},
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "OK" in resultado.stdout


def test_docs_retornam_404_com_a_flag_desligada_sem_afetar_health():
    resultado = _rodar_no_subprocesso(
        "assert cliente.get('/docs').status_code == 404\n"
        "assert cliente.get('/openapi.json').status_code == 404\n"
        "assert cliente.get('/redoc').status_code == 404\n"
        "saude = cliente.get('/health')\n"
        "assert saude.status_code == 200 and saude.json() == {'status': 'ok'}\n"
        "print('OK')\n",
        {"API_DOCS_ENABLED": "false"},
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "OK" in resultado.stdout


# ── 6 · limite de autenticação sem revelar existência de e-mail ─────────────

_PESSOA = {
    "id": "pessoa-1",
    "email": "existe@citi.org.br",
    "nome": "Pessoa Um",
    "senha_hash": hash_senha("senha-correta"),
    "cargo": "gerente",
}


def _supabase_com_pessoa(pessoa_row):
    supabase = MagicMock()

    def por_email(campo, valor):
        resposta = MagicMock()
        resposta.data = [pessoa_row] if pessoa_row and pessoa_row[campo] == valor else []
        consulta = MagicMock()
        consulta.execute.return_value = resposta
        return consulta

    supabase.table.return_value.select.return_value.eq.side_effect = por_email
    return supabase


def _login(cliente, email, ip):
    return cliente.post(
        "/auth/login",
        json={"email": email, "senha": "errada"},
        headers={"X-Forwarded-For": ip},
    )


def test_login_bem_sucedido_dentro_do_limite_continua_identico(monkeypatch):
    import routers.auth as auth_router
    from main import app

    monkeypatch.setattr(auth_router, "get_client", lambda: _supabase_com_pessoa(_PESSOA))
    cliente = TestClient(app)

    resposta = cliente.post(
        "/auth/login", json={"email": _PESSOA["email"], "senha": "senha-correta"}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"nome": "Pessoa Um", "cargo": "gerente"}
    assert resposta.cookies.get("docudata_session")


def test_login_bloqueia_apos_o_limite_por_ip(monkeypatch):
    import routers.auth as auth_router
    from core.rate_limit import AUTH_LOGIN_PER_MINUTE
    from main import app

    monkeypatch.setattr(auth_router, "get_client", lambda: _supabase_com_pessoa(_PESSOA))
    cliente = TestClient(app)

    dentro = [_login(cliente, _PESSOA["email"], "203.0.113.77") for _ in range(AUTH_LOGIN_PER_MINUTE)]
    excedente = _login(cliente, _PESSOA["email"], "203.0.113.77")
    outro_ip = _login(cliente, _PESSOA["email"], "203.0.113.78")

    assert all(r.status_code == 401 for r in dentro)
    assert excedente.status_code == 429
    assert outro_ip.status_code == 401


def test_429_de_login_nao_revela_se_o_email_existe(monkeypatch):
    import routers.auth as auth_router
    from core.rate_limit import AUTH_LOGIN_PER_MINUTE, limiter
    from main import app

    monkeypatch.setattr(auth_router, "get_client", lambda: _supabase_com_pessoa(_PESSOA))
    cliente = TestClient(app)

    for _ in range(AUTH_LOGIN_PER_MINUTE):
        _login(cliente, _PESSOA["email"], "198.51.100.7")
    bloqueio_existente = _login(cliente, _PESSOA["email"], "198.51.100.7")

    limiter.reset()
    for _ in range(AUTH_LOGIN_PER_MINUTE):
        _login(cliente, "naoexiste@citi.org.br", "198.51.100.8")
    bloqueio_inexistente = _login(cliente, "naoexiste@citi.org.br", "198.51.100.8")

    assert bloqueio_existente.status_code == bloqueio_inexistente.status_code == 429
    assert bloqueio_existente.text == bloqueio_inexistente.text
    assert _PESSOA["email"] not in bloqueio_existente.text


def test_cadastro_publico_tem_limite_por_hora(monkeypatch):
    import routers.auth as auth_router
    from core.rate_limit import AUTH_SIGNUP_PER_HOUR
    from main import app

    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "ja-existe"}
    ]
    monkeypatch.setattr(auth_router, "get_client", lambda: supabase)
    cliente = TestClient(app)
    payload = {
        "nome": "Novo",
        "email": "novo@citi.org.br",
        "senha": "senha-boa-123",
        "github_login": "novo-dev",
        "github_email": "novo@users.noreply.github.com",
    }
    cabecalhos = {"X-Forwarded-For": "192.0.2.99"}

    dentro = [
        cliente.post("/auth/signup/novo", json=payload, headers=cabecalhos)
        for _ in range(AUTH_SIGNUP_PER_HOUR)
    ]
    excedente = cliente.post("/auth/signup/novo", json=payload, headers=cabecalhos)

    assert all(r.status_code == 409 for r in dentro)
    assert excedente.status_code == 429


def test_claim_publico_tambem_tem_limite_por_hora(monkeypatch):
    import routers.auth as auth_router
    from core.rate_limit import AUTH_SIGNUP_PER_HOUR
    from main import app

    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    monkeypatch.setattr(auth_router, "get_client", lambda: supabase)
    cliente = TestClient(app)
    payload = {
        "operacional_id": "operacional-inexistente",
        "email": "novo@citi.org.br",
        "senha": "senha-boa-123",
        "github_login": "novo-dev",
        "github_email": "novo@users.noreply.github.com",
    }
    cabecalhos = {"X-Forwarded-For": "192.0.2.100"}

    dentro = [
        cliente.post("/auth/signup/claim", json=payload, headers=cabecalhos)
        for _ in range(AUTH_SIGNUP_PER_HOUR)
    ]
    excedente = cliente.post("/auth/signup/claim", json=payload, headers=cabecalhos)

    assert all(r.status_code == 404 for r in dentro)
    assert excedente.status_code == 429


def test_health_nunca_recebe_rate_limit(client):
    from core.rate_limit import AUTH_LOGIN_PER_MINUTE, RATE_LIMIT_PER_MINUTE

    repeticoes = max(AUTH_LOGIN_PER_MINUTE, RATE_LIMIT_PER_MINUTE) + 5
    respostas = [client.get("/health") for _ in range(repeticoes)]

    assert all(r.status_code == 200 for r in respostas)
    assert all("X-RateLimit-Limit" not in r.headers for r in respostas)


# ── 8, 9 e 10 · guardas de imagem e PDF ─────────────────────────────────────

def _png(largura: int, altura: int) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (largura, altura), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_imagem_valida_continua_sendo_processada():
    import base64

    from PIL import Image

    from services.file_parser import parse_image

    b64 = parse_image(_png(40, 30))
    reaberta = Image.open(io.BytesIO(base64.b64decode(b64)))

    assert reaberta.format == "PNG"
    assert reaberta.size == (40, 30)


def test_imagem_grande_continua_sendo_reduzida_para_o_lado_maximo():
    import base64

    from PIL import Image

    from services.file_parser import parse_image

    reaberta = Image.open(io.BytesIO(base64.b64decode(parse_image(_png(2048, 1024)))))

    assert max(reaberta.size) == 1024


def test_imagem_acima_do_teto_de_pixels_e_recusada_sem_crash(monkeypatch):
    from services.file_parser import ArquivoExcedeLimite, parse_image

    monkeypatch.setenv("MAX_IMAGE_PIXELS", "100")

    with pytest.raises(ArquivoExcedeLimite):
        parse_image(_png(200, 200))


def test_imagem_corrompida_e_recusada_sem_crash():
    from services.file_parser import ArquivoInvalido, parse_image

    truncada = _png(60, 60)[:40]

    with pytest.raises(ArquivoInvalido):
        parse_image(truncada)

    with pytest.raises(ArquivoInvalido):
        parse_image(b"isso nao e uma imagem")


def test_formato_fora_do_que_a_interface_aceita_e_recusado():
    from PIL import Image

    from services.file_parser import ArquivoInvalido, parse_image

    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="GIF")

    with pytest.raises(ArquivoInvalido):
        parse_image(buffer.getvalue())


def test_timeout_do_poppler_vira_erro_amigavel(monkeypatch):
    import pdf2image
    from pdf2image.exceptions import PDFPopplerTimeoutError

    from services.file_parser import ProcessamentoDemorouDemais, _pdf_page_to_base64

    def estourar(*args, **kwargs):
        assert kwargs["timeout"] > 0, "o timeout precisa chegar no Poppler"
        raise PDFPopplerTimeoutError("Run poppler timeout exceeded")

    monkeypatch.setattr(pdf2image, "convert_from_bytes", estourar)

    with pytest.raises(ProcessamentoDemorouDemais) as erro:
        _pdf_page_to_base64(b"%PDF-1.4 conteudo")

    assert str(erro.value) == "O PDF demorou demais para ser processado"


def test_guarda_de_arquivo_encerra_o_grafo_com_status_amigavel(monkeypatch):
    import services.file_parser as file_parser
    from graphs.extraction_graph import preprocessar_arquivo

    monkeypatch.setenv("MAX_IMAGE_PIXELS", "100")
    estado_imagem = {
        "tipo": "imagem",
        "arquivo_bytes": _png(200, 200),
        "arquivo_nome": "kanban.png",
        "mime_type": "image/png",
    }

    resultado = preprocessar_arquivo(estado_imagem)

    assert resultado["erro_status"] == 413
    assert resultado["erro"] == "Imagem grande demais para processamento"
    assert resultado["tentativas"] == 2

    def travar(_bytes):
        raise file_parser.ProcessamentoDemorouDemais("O PDF demorou demais para ser processado")

    monkeypatch.setattr(file_parser, "parse_pdf", travar)
    resultado_pdf = preprocessar_arquivo(
        {
            "tipo": "pdf",
            "arquivo_bytes": b"%PDF-1.4",
            "arquivo_nome": "scan.pdf",
            "mime_type": "application/pdf",
        }
    )

    assert resultado_pdf["erro_status"] == 422
    assert resultado_pdf["erro"] == "O PDF demorou demais para ser processado"


def test_upload_de_imagem_corrompida_responde_422_sem_chamar_a_ia(client, monkeypatch):
    import routers.ingest as ingest

    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"name": "Projeto", "client": "Cliente", "description": ""}
    ]
    monkeypatch.setattr(ingest, "get_client", lambda: supabase)
    monkeypatch.setattr(ingest, "get_gemini_api_key", lambda: "chave-que-nao-sera-usada")
    monkeypatch.setattr(ingest, "ensure_sprint_row", lambda *a, **k: None)

    resposta = client.post(
        "/ingest",
        files={"arquivo": ("print.png", b"nao e um png", "image/png")},
        # force=true pula o classificador (que chamaria o Gemini) e leva
        # direto ao pré-processamento, onde a guarda de arquivo atua.
        data={"sprint_numero": "1", "projeto_id": "projeto-1", "force": "true"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Imagem inválida ou corrompida"


# ── 11, 12 e 13 · listagem de projetos ──────────────────────────────────────

class _ConsultaFake:
    def __init__(self, registrador, tabela, dados):
        self._registrador = registrador
        self._tabela = tabela
        self._dados = dados
        self.filtro_in = None

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def in_(self, coluna, valores):
        self._registrador.append((self._tabela, coluna, list(valores)))
        self.filtro_in = list(valores)
        return self

    def execute(self):
        resposta = MagicMock()
        dados = self._dados
        if self.filtro_in is not None:
            dados = [linha for linha in dados if linha["project_id"] in self.filtro_in]
        resposta.data = dados
        return resposta


def _supabase_de_projetos(registrador, projetos, ingestoes):
    supabase = MagicMock()

    def tabela(nome):
        if nome == "projects":
            return _ConsultaFake(registrador, nome, projetos)
        if nome == "ingestions":
            return _ConsultaFake(registrador, nome, ingestoes)
        return _ConsultaFake(registrador, nome, [])

    supabase.table.side_effect = tabela
    return supabase


_PROJETOS = [
    {
        "id": "proj-dados-1",
        "name": "Alpha",
        "client": "Cliente A",
        "subarea": "dados",
        "created_at": "2026-01-02T00:00:00+00:00",
        "github_token": "ghs_token_super_secreto",
        "github_repo": "citi/alpha",
        "gemini_api_key": "AIzaSyCHAVELEGADADEPROJETO",
    },
    {
        "id": "proj-dados-2",
        "name": "Beta",
        "client": "Cliente B",
        "subarea": "dados",
        "created_at": "2026-01-01T00:00:00+00:00",
    },
]

_INGESTOES = [
    {"project_id": "proj-dados-1", "created_at": "2026-03-10T12:00:00+00:00"},
    {"project_id": "proj-dados-1", "created_at": "2026-02-01T12:00:00+00:00"},
    {"project_id": "proj-dados-2", "created_at": "2026-03-01T12:00:00+00:00"},
    {"project_id": "proj-de-outra-subarea", "created_at": "2026-04-01T12:00:00+00:00"},
]


def test_listagem_nao_consulta_ingestoes_fora_dos_ids_devolvidos(client, monkeypatch):
    import routers.projects as projects

    chamadas: list = []
    monkeypatch.setattr(
        projects, "get_client", lambda: _supabase_de_projetos(chamadas, _PROJETOS, _INGESTOES)
    )

    resposta = client.get("/projects?subarea=dados")

    assert resposta.status_code == 200
    filtros_de_ingestao = [c for c in chamadas if c[0] == "ingestions"]
    assert filtros_de_ingestao == [("ingestions", "project_id", ["proj-dados-1", "proj-dados-2"])]


def test_last_ingestion_at_mantem_o_resultado_anterior(client, monkeypatch):
    import routers.projects as projects

    monkeypatch.setattr(
        projects, "get_client", lambda: _supabase_de_projetos([], _PROJETOS, _INGESTOES)
    )

    corpo = client.get("/projects?subarea=dados").json()
    por_id = {p["id"]: p for p in corpo}

    # Mesma regra de antes: a ingestão mais recente de cada projeto.
    assert por_id["proj-dados-1"]["last_ingestion_at"].startswith("2026-03-10T12:00:00")
    assert por_id["proj-dados-2"]["last_ingestion_at"].startswith("2026-03-01T12:00:00")
    assert [p["id"] for p in corpo] == ["proj-dados-1", "proj-dados-2"]


def test_campos_sensiveis_do_projeto_nao_aparecem_na_resposta(client, monkeypatch):
    import routers.projects as projects

    monkeypatch.setattr(
        projects, "get_client", lambda: _supabase_de_projetos([], _PROJETOS, _INGESTOES)
    )

    resposta = client.get("/projects?subarea=dados")
    corpo = resposta.json()

    assert "ghs_token_super_secreto" not in resposta.text
    assert "AIzaSyCHAVELEGADADEPROJETO" not in resposta.text
    for projeto in corpo:
        assert "github_token" not in projeto
        assert "gemini_api_key" not in projeto
    # O status derivado do token continua exposto, como antes.
    assert corpo[0]["has_github_config"] is True
    assert corpo[1]["has_github_config"] is False


def test_leitura_de_projeto_nao_pede_a_chave_gemini_legada(client, monkeypatch):
    import routers.projects as projects

    assert "gemini_api_key" not in projects._CAMPOS_PROJETO
    assert "github_token" in projects._CAMPOS_PROJETO
