import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


AGENTE = Path(__file__).resolve().parents[1] / "hooks" / "docudata_agent.py"
SEGREDO = "segredo-compartilhado-do-teste"


@pytest.fixture
def repositorio_git(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Squad Dev"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "dev@example.test"], cwd=tmp_path, check=True)
    (tmp_path / "app.txt").write_text("primeiro commit\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "feat: iniciar projeto"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.fixture
def servidor_docudata():
    requisicoes = []

    class Handler(BaseHTTPRequestHandler):
        def responder(self, status, payload):
            conteudo = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)

        def registrar(self):
            requisicoes.append((self.command, self.path, self.headers.get("X-Docudata-Key")))
            return self.headers.get("X-Docudata-Key") == SEGREDO

        def do_GET(self):
            if self.registrar():
                self.responder(200, {"sprint_number": 3})
            else:
                self.responder(401, {"detail": "Chave de aplicação ausente ou inválida"})

        def do_POST(self):
            tamanho = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(tamanho)
            if self.registrar():
                self.responder(201, {"status": "ok"})
            else:
                self.responder(401, {"detail": "Chave de aplicação ausente ou inválida"})

        def log_message(self, format, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{servidor.server_port}", requisicoes
    servidor.shutdown()
    thread.join()
    servidor.server_close()


def executar_agente(repositorio, api_url, app_secret=None):
    env = os.environ.copy()
    env.update({
        "DOCUDATA_API_URL": api_url,
        "DOCUDATA_PROJECT_ID": "projeto-dev-teste",
        "GITHUB_TOKEN": "",
        "GITHUB_REPOSITORY": "",
        "GITHUB_SHA": "",
    })
    if app_secret is None:
        env.pop("DOCUDATA_APP_SECRET", None)
    else:
        env["DOCUDATA_APP_SECRET"] = app_secret

    return subprocess.run(
        [sys.executable, str(AGENTE)],
        cwd=repositorio,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_tracker_autentica_get_e_post(repositorio_git, servidor_docudata):
    api_url, requisicoes = servidor_docudata

    resultado = executar_agente(repositorio_git, api_url, SEGREDO)

    assert resultado.returncode == 0
    assert "Sprint detectada automaticamente: Sprint 3" in resultado.stdout
    assert "registrado na Sprint 3" in resultado.stdout
    assert requisicoes == [
        ("GET", "/projects/projeto-dev-teste/current-sprint", SEGREDO),
        ("POST", "/ingest/commit", SEGREDO),
    ]


def test_tracker_sem_segredo_nao_quebra_o_push(repositorio_git, servidor_docudata):
    api_url, requisicoes = servidor_docudata

    resultado = executar_agente(repositorio_git, api_url)

    assert resultado.returncode == 0
    assert "Aviso: falha ao registrar (HTTP 401) — continuando" in resultado.stdout
    assert requisicoes == [
        ("GET", "/projects/projeto-dev-teste/current-sprint", None),
        ("POST", "/ingest/commit", None),
    ]
