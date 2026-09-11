"""Contratos da Spec 08 sem rede, banco real ou consumo de Gemini."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
import urllib.parse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient


APP_KEY = os.environ["DOCUDATA_APP_SECRET"]
AUTH = {"X-Docudata-Key": APP_KEY}


class Resposta:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.valores = None
        self.filtros = []
        self.ordem = None
        self.limite = None

    def select(self, *_args):
        self.acao = "select"
        return self

    def insert(self, valores):
        self.acao = "insert"
        self.valores = deepcopy(valores)
        return self

    def update(self, valores):
        self.acao = "update"
        self.valores = deepcopy(valores)
        return self

    def delete(self):
        self.acao = "delete"
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def order(self, campo, desc=False):
        self.ordem = (campo, desc)
        return self

    def limit(self, quantidade):
        self.limite = quantidade
        return self

    def _filtradas(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        resultado = [linha for linha in linhas if all(linha.get(campo) == valor for campo, valor in self.filtros)]
        if self.ordem:
            campo, desc = self.ordem
            resultado.sort(key=lambda linha: str(linha.get(campo, "")), reverse=desc)
        if self.limite is not None:
            resultado = resultado[:self.limite]
        return resultado

    def execute(self):
        self.banco.tabelas_consultadas.append(self.tabela)
        if self.acao == "select":
            return Resposta(deepcopy(self._filtradas()))
        if self.acao == "insert":
            agora = datetime.now(timezone.utc).isoformat()
            entradas = self.valores if isinstance(self.valores, list) else [self.valores]
            salvas = []
            for entrada in entradas:
                row = deepcopy(entrada)
                row.setdefault("id", str(uuid4()))
                row.setdefault("created_at", agora)
                row.setdefault("connected_at", agora)
                row.setdefault("updated_at", agora)
                self.banco.dados.setdefault(self.tabela, []).append(row)
                salvas.append(deepcopy(row))
            return Resposta(salvas)
        afetadas = self._filtradas()
        if self.acao == "update":
            for row in afetadas:
                row.update(deepcopy(self.valores))
            return Resposta(deepcopy(afetadas))
        for row in afetadas:
            self.banco.dados[self.tabela].remove(row)
        return Resposta([])


class BancoFalso:
    def __init__(self, dados=None):
        self.dados = deepcopy(dados or {})
        self.tabelas_consultadas = []

    def table(self, tabela):
        return Query(self, tabela)


@pytest.fixture
def github_env(monkeypatch):
    valores = {
        "GITHUB_INTEGRATION_ENABLED": "true",
        "GITHUB_INTEGRATION_SUBAREAS": "dados,dev",
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_SLUG": "citi-documentador-test",
        "GITHUB_APP_PRIVATE_KEY": "pem-mockado-nos-testes",
        "GITHUB_WEBHOOK_SECRET": "segredo-webhook-teste",
        "GITHUB_CONNECTION_STATE_SECRET": "segredo-state-teste-com-entropia",
    }
    for chave, valor in valores.items():
        monkeypatch.setenv(chave, valor)
    return valores


@pytest.fixture
def client(autenticar):
    from main import app

    return autenticar(TestClient(app))


def assinatura(corpo: bytes, segredo: str) -> str:
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


def headers_webhook(corpo: bytes, segredo: str, delivery="delivery-1", evento="push"):
    return {
        "X-Hub-Signature-256": assinatura(corpo, segredo),
        "X-GitHub-Delivery": delivery,
        "X-GitHub-Event": evento,
        "Content-Type": "application/json",
    }


def test_feature_desligada_inicia_sem_envs_e_migration():
    backend = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    for nome in list(env):
        if nome.startswith("GITHUB_"):
            env.pop(nome)
    env["GITHUB_INTEGRATION_ENABLED"] = "false"
    codigo = (
        "import dotenv; dotenv.load_dotenv=lambda *a,**k: False; "
        "import main; from services.github_app import configuracao_publica_github; "
        "assert configuracao_publica_github()['enabled'] is False"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], cwd=backend, env=env,
        capture_output=True, text=True, check=False,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_rollout_padrao_cobre_dados_e_dev(monkeypatch):
    from services.github_app import subareas_github_habilitadas

    monkeypatch.delenv("GITHUB_INTEGRATION_SUBAREAS", raising=False)
    assert subareas_github_habilitadas() == {"dados", "dev"}


def test_jwt_github_app_assinado_com_rs256():
    import base64
    from services.github_app import GitHubConfig, criar_jwt_github

    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = chave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    token = criar_jwt_github(GitHubConfig("123", "app", pem, "webhook", "state"))
    cabecalho, payload, assinatura_token = token.split(".")
    dados_cabecalho = json.loads(base64.urlsafe_b64decode(cabecalho + "=" * (-len(cabecalho) % 4)))
    dados_payload = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    chave.public_key().verify(
        base64.urlsafe_b64decode(assinatura_token + "=" * (-len(assinatura_token) % 4)),
        f"{cabecalho}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256(),
    )
    assert dados_cabecalho["alg"] == "RS256"
    assert dados_payload["iss"] == "123"
    assert dados_payload["exp"] - dados_payload["iat"] <= 600


def test_feature_desligada_nao_consulta_tabelas_novas(client, monkeypatch):
    import routers.github_integration as router

    monkeypatch.setenv("GITHUB_INTEGRATION_ENABLED", "false")
    monkeypatch.setattr(router, "get_client", lambda: (_ for _ in ()).throw(AssertionError("não deve consultar")))
    capability = client.get("/integrations/github/capabilities", headers=AUTH)
    sessao = client.post("/projects/dev/repositories/github/session", headers=AUTH)
    webhook = client.post("/webhooks/github", content=b"{}")
    assert capability.status_code == 200
    assert capability.json() == {"enabled": False, "configured": False, "subareas": [], "app_slug": None}
    assert sessao.status_code == 404
    assert webhook.status_code == 404


def test_dados_e_dev_iniciam_sessao(client, monkeypatch, github_env):
    import routers.github_integration as router

    banco = BancoFalso({
        "projects": [
            {"id": "dados-1", "name": "Dados", "subarea": "dados"},
            {"id": "dev-1", "name": "Dev", "subarea": "dev"},
        ]
    })
    monkeypatch.setattr(router, "get_client", lambda: banco)

    dados = client.post("/projects/dados-1/repositories/github/session", headers=AUTH)
    dev = client.post("/projects/dev-1/repositories/github/session", headers=AUTH)

    assert dados.status_code == 200
    assert dev.status_code == 200
    assert dados.json()["install_url"].startswith("https://github.com/apps/citi-documentador-test/")
    assert dev.json()["install_url"].startswith("https://github.com/apps/citi-documentador-test/")
    assert len(banco.dados["github_connection_sessions"]) == 2
    assert {sessao["project_id"] for sessao in banco.dados["github_connection_sessions"]} == {
        "dados-1",
        "dev-1",
    }

    capabilities = client.get("/integrations/github/capabilities", headers=AUTH)
    assert capabilities.json()["subareas"] == ["dados", "dev"]


@pytest.mark.parametrize("subarea", ["dados", "dev"])
def test_callback_state_uso_unico_e_token_nao_expoe_ids(
    client, monkeypatch, github_env, subarea
):
    import routers.github_integration as router

    project_id = f"{subarea}-secreto"
    banco = BancoFalso({
        "projects": [{"id": project_id, "name": subarea.title(), "subarea": subarea}],
    })
    monkeypatch.setattr(router, "get_client", lambda: banco)
    inicio = client.post(f"/projects/{project_id}/repositories/github/session", headers=AUTH)
    state = urllib.parse.parse_qs(urllib.parse.urlparse(inicio.json()["install_url"]).query)["state"][0]
    assert project_id not in state

    callback = client.get(
        "/integrations/github/callback",
        params={"state": state, "installation_id": 77},
        follow_redirects=False,
    )
    repetido = client.get(
        "/integrations/github/callback",
        params={"state": state, "installation_id": 77},
        follow_redirects=False,
    )
    assert callback.status_code == 307
    assert f"/{subarea}/projects/{project_id}" in callback.headers["location"]
    assert "github_connection=" in callback.headers["location"]
    assert project_id not in callback.headers["location"].split("github_connection=")[1]
    assert repetido.status_code == 410


@pytest.mark.parametrize("assinatura_recebida", [None, "sha256=invalida"])
def test_webhook_invalido_rejeita_antes_de_query(client, monkeypatch, github_env, assinatura_recebida):
    import routers.github_integration as router

    monkeypatch.setattr(router, "get_client", lambda: (_ for _ in ()).throw(AssertionError("não deve consultar")))
    headers = {"X-GitHub-Delivery": "d", "X-GitHub-Event": "push"}
    if assinatura_recebida:
        headers["X-Hub-Signature-256"] = assinatura_recebida
    resposta = client.post("/webhooks/github", content=b"{}", headers=headers)
    assert resposta.status_code == 401


def test_assinatura_valida_aceita_evento_ignorado(client, monkeypatch, github_env):
    import routers.github_integration as router

    banco = BancoFalso()
    monkeypatch.setattr(router, "get_client", lambda: banco)
    corpo = json.dumps({"zen": "seguro"}).encode()
    resposta = client.post(
        "/webhooks/github", content=corpo,
        headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], evento="ping"),
    )
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ignored"
    assert banco.dados["github_webhook_deliveries"][0]["status"] == "ignored"


def payload_push(repo_id=101, commits=None, project_id_malicioso="outro-projeto"):
    commits = commits or [
        {"id": "a" * 40, "message": "feat: primeiro", "author": {"name": "Ana"}, "timestamp": "2026-08-25T10:00:00Z"},
        {"id": "b" * 40, "message": "fix: segundo [sprint:4]", "author": {"name": "Bia"}, "timestamp": "2026-08-25T10:01:00Z"},
    ]
    return {
        "project_id": project_id_malicioso,
        "ref": "refs/heads/feature/spec-08",
        "deleted": False,
        "before": "0" * 40,
        "after": commits[-1]["id"],
        "size": len(commits),
        "commits": commits,
        "repository": {"id": repo_id, "full_name": f"citi/repo-{repo_id}", "html_url": f"https://github.com/citi/repo-{repo_id}"},
        "installation": {"id": 77},
        "pusher": {"name": "push-user"},
        "sender": {"login": "sender-user"},
    }


def banco_com_repo(
    repo_id=101,
    active=True,
    project_id="dev-1",
    repo_row_id="repo-link-1",
    subarea="dev",
):
    return BancoFalso({
        "projects": [{"id": project_id, "name": f"Projeto {subarea.title()}", "subarea": subarea}],
        "project_repositories": [{
            "id": repo_row_id, "project_id": project_id, "github_repository_id": repo_id,
            "installation_id": 77, "full_name": f"citi/repo-{repo_id}",
            "html_url": f"https://github.com/citi/repo-{repo_id}", "active": active,
        }],
        "ingestions": [],
    })


def configurar_processamento_mock(monkeypatch, router):
    async def extrair(client_db, dados):
        if any(row.get("source_repository_id") == dados.repositorio_id and row.get("source_commit_sha") == dados.sha for row in client_db.dados["ingestions"]):
            return {"status": "duplicado", "ingestion_id": None, "sprint_number": None}
        client_db.table("ingestions").insert({
            "project_id": dados.projeto_id,
            "source_repository_id": dados.repositorio_id,
            "source_repository_full_name": dados.repositorio_nome,
            "source_commit_sha": dados.sha,
            "source_branch": dados.branch,
            "source_url": dados.url,
            "extracted_content": {"_meta_autor": dados.autor, "_meta_commit_msg": dados.mensagem},
        }).execute()
        return {"status": "ok", "ingestion_id": dados.sha, "sprint_number": 4}

    def buscar(_installation_id, nome, sha):
        return ({
            "html_url": f"https://github.com/{nome}/commit/{sha}",
            "commit": {"message": f"mensagem {sha[:1]}", "author": {"name": "Autora", "date": "2026-08-25T10:00:00Z"}, "committer": {"name": "Committer"}},
            "author": {"login": "autora-login"}, "committer": {"login": "committer-login"},
        }, "1 arquivo, +2 -1", "diff efêmero")

    monkeypatch.setattr(router, "extrair_e_salvar_commit", extrair)
    monkeypatch.setattr(router, "buscar_commit", buscar)


@pytest.mark.parametrize("subarea", ["dados", "dev"])
def test_push_multicommit_resolve_vinculo_e_redelivery_nao_duplica(
    client, monkeypatch, github_env, subarea
):
    import routers.github_integration as router

    project_id = f"{subarea}-1"
    banco = banco_com_repo(project_id=project_id, subarea=subarea)
    monkeypatch.setattr(router, "get_client", lambda: banco)
    configurar_processamento_mock(monkeypatch, router)
    statuses = []
    monkeypatch.setattr(router, "criar_status_commit", lambda *args: statuses.append(args))
    corpo = json.dumps(payload_push()).encode()

    primeira = client.post("/webhooks/github", content=corpo, headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], f"push-1-{subarea}"))
    segunda = client.post("/webhooks/github", content=corpo, headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], f"push-2-{subarea}"))

    assert primeira.json() == {"status": "succeeded", "processed": 2}
    assert segunda.json() == {"status": "ignored", "processed": 0}
    assert len(banco.dados["ingestions"]) == 2
    assert {row["project_id"] for row in banco.dados["ingestions"]} == {project_id}
    assert {row["source_commit_sha"] for row in banco.dados["ingestions"]} == {"a" * 40, "b" * 40}
    assert {row["source_branch"] for row in banco.dados["ingestions"]} == {"feature/spec-08"}
    assert len(statuses) == 2


def test_compare_pagina_lista_truncada_sem_perder_commits(monkeypatch):
    import services.github_app as github

    monkeypatch.setattr(github, "criar_token_instalacao", lambda _id: "token-curto")
    chamadas = []
    def request(_metodo, caminho, _token):
        chamadas.append(caminho)
        return {"commits": [{"sha": str(i)} for i in range(100)]} if caminho.endswith("&page=1") else {"commits": [{"sha": "ultimo"}]}
    monkeypatch.setattr(github, "_request_github", request)
    commits = github.comparar_commits(77, "citi/repo", "base", "head")
    assert len(commits) == 101
    assert len(chamadas) == 2


@pytest.mark.parametrize("active", [False, None])
def test_repo_inativo_ou_nao_associado_nao_ingere(client, monkeypatch, github_env, active):
    import routers.github_integration as router

    banco = banco_com_repo(active=False) if active is False else BancoFalso({"project_repositories": [], "ingestions": []})
    monkeypatch.setattr(router, "get_client", lambda: banco)
    chamado = []
    async def nao_extrair(*args):
        chamado.append(args)
    monkeypatch.setattr(router, "extrair_e_salvar_commit", nao_extrair)
    corpo = json.dumps(payload_push()).encode()
    resposta = client.post("/webhooks/github", content=corpo, headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], f"inactive-{active}"))
    assert resposta.json()["status"] == "ignored"
    assert chamado == []
    assert banco.dados.get("ingestions", []) == []


def test_dois_repositorios_alimentam_mesmo_projeto(client, monkeypatch, github_env):
    import routers.github_integration as router

    banco = banco_com_repo()
    banco.dados["project_repositories"].append({
        **banco.dados["project_repositories"][0], "id": "repo-link-2",
        "github_repository_id": 202, "full_name": "citi/repo-202",
        "html_url": "https://github.com/citi/repo-202",
    })
    monkeypatch.setattr(router, "get_client", lambda: banco)
    configurar_processamento_mock(monkeypatch, router)
    monkeypatch.setattr(router, "criar_status_commit", lambda *args: None)
    for repo_id in (101, 202):
        corpo = json.dumps(payload_push(repo_id, commits=[{
            "id": str(repo_id) * 13 + "x", "message": "feat", "author": {"name": "Dev"}, "timestamp": "2026-08-25T10:00:00Z"
        }])).encode()
        resposta = client.post("/webhooks/github", content=corpo, headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], f"repo-{repo_id}"))
        assert resposta.json()["processed"] == 1
    assert len(banco.dados["ingestions"]) == 2
    assert {row["project_id"] for row in banco.dados["ingestions"]} == {"dev-1"}
    assert {row["source_repository_id"] for row in banco.dados["ingestions"]} == {"repo-link-1", "repo-link-2"}


def test_falha_no_status_nao_desfaz_ingestao(client, monkeypatch, github_env):
    import routers.github_integration as router

    from services.github_app import GitHubApiError
    banco = banco_com_repo()
    monkeypatch.setattr(router, "get_client", lambda: banco)
    configurar_processamento_mock(monkeypatch, router)
    monkeypatch.setattr(router, "criar_status_commit", lambda *args: (_ for _ in ()).throw(GitHubApiError("status")))
    corpo = json.dumps(payload_push(commits=[payload_push()["commits"][0]])).encode()
    resposta = client.post("/webhooks/github", content=corpo, headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], "status-fail"))
    assert resposta.json()["status"] == "succeeded"
    assert len(banco.dados["ingestions"]) == 1


def test_associacao_multipla_e_conflito_entre_projetos(client, monkeypatch, github_env):
    import routers.github_integration as router

    banco = BancoFalso({"projects": [
        {"id": "dev-1", "name": "Projeto Um", "subarea": "dev"},
        {"id": "dev-2", "name": "Projeto Dois", "subarea": "dev"},
    ]})
    monkeypatch.setattr(router, "get_client", lambda: banco)
    monkeypatch.setattr(router, "_validar_sessao_conexao", lambda _client, token: ({}, {
        "id": f"session-{token}", "project_id": "dev-1" if token == "token-1" else "dev-2", "installation_id": 77,
    }))
    repos = [
        {"id": 101, "full_name": "citi/front", "html_url": "https://github.com/citi/front", "default_branch": "main"},
        {"id": 202, "full_name": "citi/back", "html_url": "https://github.com/citi/back", "default_branch": "develop"},
    ]
    monkeypatch.setattr(router, "listar_repositorios_instalacao", lambda _id: repos)

    multipla = client.post("/projects/dev-1/repositories", headers=AUTH, json={"connection_token": "token-1", "repository_ids": [101, 202]})
    conflito = client.post("/projects/dev-2/repositories", headers=AUTH, json={"connection_token": "token-2", "repository_ids": [101]})

    assert multipla.status_code == 201
    assert len(multipla.json()) == 2
    assert conflito.status_code == 409
    assert "Projeto Um" in conflito.json()["detail"]
    assert {row["project_id"] for row in banco.dados["project_repositories"]} == {"dev-1"}


def test_desconectar_preserva_historico_e_impede_novos_pushes(client, monkeypatch, github_env):
    import routers.github_integration as router

    banco = banco_com_repo()
    banco.dados["ingestions"].append({
        "id": "historico", "project_id": "dev-1", "source_repository_id": "repo-link-1",
        "source_commit_sha": "antigo",
    })
    monkeypatch.setattr(router, "get_client", lambda: banco)
    resposta = client.delete("/projects/dev-1/repositories/repo-link-1", headers=AUTH)
    assert resposta.status_code == 204
    assert banco.dados["project_repositories"][0]["active"] is False
    assert banco.dados["project_repositories"][0]["inactive_reason"] == "disconnected"
    assert banco.dados["ingestions"][0]["id"] == "historico"

    corpo = json.dumps(payload_push()).encode()
    webhook = client.post("/webhooks/github", content=corpo, headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], "depois-disconnect"))
    assert webhook.json()["status"] == "ignored"
    assert len(banco.dados["ingestions"]) == 1


def test_evento_de_permissao_removida_marca_vinculo_revogado(client, monkeypatch, github_env):
    import routers.github_integration as router

    banco = banco_com_repo()
    monkeypatch.setattr(router, "get_client", lambda: banco)
    payload = {
        "action": "removed",
        "installation": {"id": 77},
        "repositories_removed": [{"id": 101, "full_name": "citi/repo-101"}],
        "repositories_added": [],
    }
    corpo = json.dumps(payload).encode()
    resposta = client.post(
        "/webhooks/github", content=corpo,
        headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], "permission-removed", "installation_repositories"),
    )
    assert resposta.json()["status"] == "succeeded"
    assert banco.dados["project_repositories"][0]["active"] is False
    assert banco.dados["project_repositories"][0]["inactive_reason"] == "revoked"


def test_renome_atualiza_exibicao_sem_mudar_identidade(client, monkeypatch, github_env):
    import routers.github_integration as router

    banco = banco_com_repo()
    monkeypatch.setattr(router, "get_client", lambda: banco)
    payload = {
        "action": "renamed",
        "repository": {"id": 101, "full_name": "citi/novo-nome", "html_url": "https://github.com/citi/novo-nome"},
    }
    corpo = json.dumps(payload).encode()
    resposta = client.post(
        "/webhooks/github", content=corpo,
        headers=headers_webhook(corpo, github_env["GITHUB_WEBHOOK_SECRET"], "repo-renamed", "repository"),
    )
    assert resposta.json()["status"] == "succeeded"
    assert banco.dados["project_repositories"][0]["github_repository_id"] == 101
    assert banco.dados["project_repositories"][0]["full_name"] == "citi/novo-nome"


def test_sprint_override_e_sprint_vigente():
    from services.commit_extraction import DadosCommit, resolver_sprint_commit

    banco = BancoFalso({
        "sprints": [{"project_id": "p", "numero": 2}, {"project_id": "p", "numero": 3}],
        "ingestions": [{"project_id": "p", "sprint_number": 3, "tipo_documentacao": "planning", "created_at": "2026-08-25"}],
    })
    override = DadosCommit(projeto_id="p", sha="a", mensagem="fix [sprint:7]", autor="A", data="hoje")
    vigente = DadosCommit(projeto_id="p", sha="b", mensagem="fix", autor="A", data="hoje")
    assert resolver_sprint_commit(banco, override) == 7
    assert resolver_sprint_commit(banco, vigente) == 3


@pytest.mark.asyncio
async def test_extracao_persiste_origem_sem_diff(monkeypatch):
    import services.commit_extraction as service
    from models.schemas import ConteudoEstruturado

    class LlmFalso:
        def __init__(self, **_kwargs):
            pass
        def with_structured_output(self, *_args, **_kwargs):
            return self
        async def ainvoke(self, _messages):
            return {
                "parsed": ConteudoEstruturado(
                    resumo="Resumo", tarefas=["Tarefa"], decisoes=["Decisão"], problemas=[],
                    contexto_cliente="", proximos_passos=["Próximo"], tecnologias=["Python"],
                    tecnologias_removidas=[],
                ),
                "raw": SimpleNamespace(usage_metadata={"input_tokens": 10, "output_tokens": 5}),
            }

    banco = BancoFalso({"projects": [{"id": "p"}], "sprints": [{"project_id": "p", "numero": 1}], "ingestions": []})
    monkeypatch.setattr(service, "get_gemini_api_key", lambda: "gemini-mock")
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", LlmFalso)
    resultado = await service.extrair_e_salvar_commit(banco, service.DadosCommit(
        projeto_id="p", sha="f" * 40, mensagem="feat", autor="Ana", data="2026-08-25",
        branch="main", diff_stat="+2 -1", diff="SEGREDO_NO_DIFF",
        repositorio_id="repo-1", repositorio_nome="citi/repo", url="https://github.com/citi/repo/commit/f",
    ))
    row = banco.dados["ingestions"][0]
    assert resultado["status"] == "ok"
    assert row["source_repository_full_name"] == "citi/repo"
    assert row["source_commit_sha"] == "f" * 40
    assert row["source_branch"] == "main"
    assert row["source_url"].startswith("https://github.com/")
    assert row["extracted_content"]["_meta_autor"] == "Ana"
    assert "SEGREDO_NO_DIFF" not in json.dumps(row)


def test_contexto_commit_serializa_origem_e_tecnologias_sem_diff():
    from graphs.generation_graph import compilar_contexto

    state = {"ingestions": [{
        "sprint_number": 2, "file_name": "commit:abcdef0", "tipo_documentacao": "commit",
        "source_repository_full_name": "citi/api", "source_branch": "main",
        "source_commit_sha": "abcdef012345", "source_url": "https://github.com/citi/api/commit/abcdef012345",
        "source_diff_stat": "3 arquivos, +20 -4",
        "extracted_content": {
            "resumo": "Implementou endpoint", "tarefas": ["Criar rota"], "decisoes": ["Usar FastAPI"],
            "problemas": [], "contexto_cliente": "", "proximos_passos": ["Testar"],
            "tecnologias": ["FastAPI"], "tecnologias_removidas": ["Flask"],
            "_meta_autor": "Ana", "_meta_autor_login": "ana-dev",
            "_meta_committer": "Bia", "_meta_committer_login": "bia-dev",
            "_meta_pusher": "ana-push", "_meta_data_commit": "2026-08-25",
            "_meta_commit_msg": "feat: rota",
        },
    }]}
    contexto = compilar_contexto(state)["contexto"]
    for trecho in (
        "Origem: citi/api", "Branch: main", "abcdef012345", "Ana (@ana-dev)",
        "Committer: Bia (@bia-dev)", "Push enviado por: ana-push",
        "Resumo das alterações: 3 arquivos, +20 -4", "feat: rota", "FastAPI", "Flask",
    ):
        assert trecho in contexto
    assert "diff" not in contexto.lower()


def test_escopo_de_documentos_inclui_commit_sem_invadir_ingestion_only(monkeypatch):
    import graphs.generation_graph as graph

    banco = BancoFalso({"ingestions": [
        {"id": "daily", "project_id": "p", "sprint_number": 2, "tipo_documentacao": "daily", "extracted_content": {"resumo": "Daily"}},
        {"id": "commit", "project_id": "p", "sprint_number": 2, "tipo_documentacao": "commit", "extracted_content": {"resumo": "Commit", "decisoes": ["Decisão"]}},
    ]})
    monkeypatch.setattr(graph, "get_client", lambda: banco)
    daily = graph.buscar_ingestions({"tipo_doc": "daily", "ingestion_id": "daily"})
    sprint = graph.buscar_ingestions({"tipo_doc": "repasse_semanal", "projeto_id": "p", "sprint_numero": 2})
    projeto = graph.buscar_ingestions({"tipo_doc": "onboarding", "projeto_id": "p"})
    assert [row["id"] for row in daily["ingestions"]] == ["daily"]
    assert {row["id"] for row in sprint["ingestions"]} == {"daily", "commit"}
    assert {row["id"] for row in projeto["ingestions"]} == {"daily", "commit"}


def test_matriz_de_documentos_combina_fontes_manuais_e_commits(monkeypatch):
    import graphs.generation_graph as graph

    ingestions = [
        {
            "id": "manual-s2", "project_id": "p", "sprint_number": 2,
            "file_name": "daily-manual", "tipo_documentacao": "daily",
            "extracted_content": {
                "resumo": "Validação manual do cliente",
                "decisoes": ["Manter autenticação por cookie"],
                "tecnologias": ["Next.js"],
            },
        },
        {
            "id": "commit-s2", "project_id": "p", "sprint_number": 2,
            "file_name": "commit:abc1234", "tipo_documentacao": "commit",
            "source_repository_full_name": "citi/frontend", "source_branch": "feature/login",
            "source_commit_sha": "abc123456789", "source_diff_stat": "2 arquivos, +12 -3",
            "extracted_content": {
                "resumo": "Implementou proteção da rota", "decisoes": ["Usar cookie httpOnly"],
                "tecnologias": ["React"], "_meta_autor": "Ana Silva",
                "_meta_autor_login": "ana", "_meta_data_commit": "2026-08-25T10:00:00Z",
                "_meta_commit_msg": "feat: protege rota",
            },
        },
        {
            "id": "commit-s3", "project_id": "p", "sprint_number": 3,
            "file_name": "commit:def5678", "tipo_documentacao": "commit",
            "source_repository_full_name": "citi/backend", "source_branch": "main",
            "source_commit_sha": "def567890123", "source_diff_stat": "1 arquivo, +5 -1",
            "extracted_content": {
                "resumo": "Ajustou endpoint", "decisoes": ["Validar payload no backend"],
                "tecnologias": ["FastAPI"], "_meta_autor": "Bruno Lima",
                "_meta_autor_login": "bruno", "_meta_data_commit": "2026-09-01T09:00:00Z",
                "_meta_commit_msg": "fix: valida payload",
            },
        },
        {
            "id": "outro-projeto", "project_id": "outro", "sprint_number": 2,
            "tipo_documentacao": "commit", "extracted_content": {"resumo": "Não pode vazar"},
        },
    ]
    banco = BancoFalso({
        "ingestions": ingestions,
        "sprints": [{"id": "sprint-row-2", "project_id": "p", "numero": 2}],
        "tasks": [{
            "sprint_id": "sprint-row-2", "titulo": "Validar login", "pontos": 3,
            "coluna_kanban": "em_andamento", "bloqueado": False,
            "operacional_id": "op-1", "ordem": 1,
        }],
    })
    monkeypatch.setattr(graph, "get_client", lambda: banco)

    for tipo in ("planning", "daily", "ata_reuniao"):
        resultado = graph.buscar_ingestions({
            "tipo_doc": tipo, "ingestion_id": "manual-s2", "projeto_id": "p",
        })
        assert [row["id"] for row in resultado["ingestions"]] == ["manual-s2"]

    for tipo in ("repasse_semanal", "review", "retrospectiva"):
        resultado = graph.buscar_ingestions({
            "tipo_doc": tipo, "projeto_id": "p", "sprint_numero": 2,
        })
        assert {row["id"] for row in resultado["ingestions"]} == {"manual-s2", "commit-s2"}

    for tipo in ("log_decisoes", "adr", "onboarding", "documentacao_final"):
        resultado = graph.buscar_ingestions({"tipo_doc": tipo, "projeto_id": "p"})
        assert {row["id"] for row in resultado["ingestions"]} == {
            "manual-s2", "commit-s2", "commit-s3",
        }

    contexto = graph.compilar_contexto({
        "tipo_doc": "repasse_semanal", "projeto_id": "p", "sprint_numero": 2,
        "ingestions": ingestions[:2],
    })["contexto"]
    for trecho in (
        "Validação manual do cliente", "Manter autenticação por cookie",
        "Implementou proteção da rota", "citi/frontend", "feature/login",
        "Ana Silva (@ana)", "feat: protege rota", "2 arquivos, +12 -3",
        "Backlog Kanban da Sprint 2", "Validar login (3pt)",
    ):
        assert trecho in contexto


@pytest.mark.asyncio
async def test_contexto_compilado_chega_ao_prompt_sem_consumir_gemini(monkeypatch):
    import graphs.generation_graph as graph

    chamadas = []

    class LlmFalso:
        async def ainvoke(self, prompt):
            chamadas.append(prompt.to_string())
            return SimpleNamespace(content="# Repasse gerado no teste")

    monkeypatch.setattr(graph, "_make_llm", lambda _api_key: LlmFalso())
    contexto = (
        "Resumo manual: cliente aprovou a entrega.\n"
        "Origem: citi/api\nBranch: main\nCommit: abc123\n"
        "Autor e data: Ana (@ana) — 2026-08-25\nMensagem do commit: feat: endpoint"
    )
    resultado = await graph.gerar_documento({
        "tipo_doc": "repasse_semanal", "api_key": "chave-falsa-nunca-enviada",
        "projeto_nome": "Projeto", "cliente": "Cliente", "sprint_numero": 2,
        "data_atual": "25/08/2026", "contexto": contexto, "observacoes": None,
    })

    assert resultado["documento"] == "# Repasse gerado no teste"
    assert len(chamadas) == 1
    for trecho in ("cliente aprovou", "citi/api", "Ana (@ana)", "feat: endpoint"):
        assert trecho in chamadas[0]


def test_insight_de_tecnologias_considera_ingestao_manual_e_commit():
    from services.tech_timeline import build_tech_timeline

    resultado = build_tech_timeline([
        {"sprint_number": 1, "tipo_documentacao": "outro", "extracted_content": {"tecnologias": ["Python"]}},
        {
            "sprint_number": 2, "tipo_documentacao": "commit",
            "extracted_content": {
                "tecnologias": ["FastAPI"], "tecnologias_removidas": ["Python"],
                "_meta_autor": "Ana",
            },
        },
    ])

    assert resultado["em_uso_atual"] == ["FastAPI"]
    timeline = {item["tecnologia"]: item for item in resultado["timeline"]}
    assert timeline["Python"] == {
        "tecnologia": "Python", "introduzida_em": 1, "abandonada_em": 2,
    }
    assert timeline["FastAPI"]["introduzida_em"] == 2


def test_registro_antigo_com_origem_nula_continua_valido():
    from models.schemas import IngestionResponse

    antigo = IngestionResponse(
        id="i", project_id="p", sprint_number=1, created_at=datetime.now(timezone.utc)
    )
    assert antigo.source_repository_id is None
    assert antigo.source_commit_sha is None


def test_migration_v5_e_somente_aditiva_e_comentada():
    sql = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text()
    bloco = sql.split("-- Migration v5:", 1)[1]
    comandos = [linha.strip().removeprefix("--").strip().upper() for linha in bloco.splitlines()]
    assert all(not comando.startswith(("DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER COLUMN")) for comando in comandos)
    assert "CREATE TABLE IF NOT EXISTS PROJECT_REPOSITORIES (" in comandos
    assert "CREATE TABLE IF NOT EXISTS GITHUB_WEBHOOK_DELIVERIES (" in comandos
    assert "ALTER TABLE INGESTIONS ADD COLUMN IF NOT EXISTS SOURCE_COMMIT_SHA TEXT;" in comandos
    assert all(not linha or linha.lstrip().startswith("--") for linha in bloco.splitlines()[1:])


def test_capabilities_nao_expoe_segredos(client, github_env):
    resposta = client.get("/integrations/github/capabilities", headers=AUTH)
    serializado = json.dumps(resposta.json())
    assert resposta.status_code == 200
    assert resposta.json()["enabled"] is True
    for segredo in (
        github_env["GITHUB_APP_PRIVATE_KEY"],
        github_env["GITHUB_WEBHOOK_SECRET"],
        github_env["GITHUB_CONNECTION_STATE_SECRET"],
    ):
        assert segredo not in serializado
