"""Configuração, autenticação e chamadas do GitHub App.

As credenciais são lidas apenas quando a integração está habilitada. Assim, o
deploy com a flag desligada não depende da migration nem de segredos do GitHub.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


GITHUB_API_URL = "https://api.github.com"


class GitHubConfigurationError(RuntimeError):
    """Configuração incompleta da integração."""


class GitHubApiError(RuntimeError):
    """Falha sanitizada ao consultar o GitHub."""


@dataclass(frozen=True)
class GitHubConfig:
    app_id: str
    app_slug: str
    private_key: str
    webhook_secret: str
    state_secret: str


def integracao_github_habilitada() -> bool:
    return os.environ.get("GITHUB_INTEGRATION_ENABLED", "false").strip().lower() == "true"


def subareas_github_habilitadas() -> set[str]:
    valor = os.environ.get("GITHUB_INTEGRATION_SUBAREAS", "dev")
    return {item.strip() for item in valor.split(",") if item.strip() in {"dados", "dev"}}


def subarea_github_habilitada(subarea: str) -> bool:
    return integracao_github_habilitada() and subarea in subareas_github_habilitadas()


def obter_config_github() -> GitHubConfig:
    """Valida credenciais somente no primeiro fluxo que realmente usa o App."""
    if not integracao_github_habilitada():
        raise GitHubConfigurationError("A integração com GitHub está desabilitada.")

    nomes = {
        "app_id": "GITHUB_APP_ID",
        "app_slug": "GITHUB_APP_SLUG",
        "private_key": "GITHUB_APP_PRIVATE_KEY",
        "webhook_secret": "GITHUB_WEBHOOK_SECRET",
        "state_secret": "GITHUB_CONNECTION_STATE_SECRET",
    }
    valores = {campo: os.environ.get(nome, "").strip() for campo, nome in nomes.items()}
    ausentes = [nome for campo, nome in nomes.items() if not valores[campo]]
    if ausentes:
        raise GitHubConfigurationError(
            "Configuração do GitHub App incompleta: " + ", ".join(ausentes)
        )

    # Railway costuma armazenar PEM em uma única linha com \n escapado.
    valores["private_key"] = valores["private_key"].replace("\\n", "\n")
    return GitHubConfig(**valores)


def configuracao_publica_github() -> dict[str, Any]:
    habilitada = integracao_github_habilitada()
    configurada = False
    slug = None
    if habilitada:
        try:
            config = obter_config_github()
            configurada = True
            slug = config.app_slug
        except GitHubConfigurationError:
            pass
    return {
        "enabled": habilitada,
        "configured": configurada,
        "subareas": sorted(subareas_github_habilitadas()) if habilitada else [],
        "app_slug": slug,
    }


def _base64url(valor: bytes) -> str:
    return base64.urlsafe_b64encode(valor).rstrip(b"=").decode("ascii")


def criar_jwt_github(config: GitHubConfig | None = None) -> str:
    config = config or obter_config_github()
    agora = int(time.time())
    cabecalho = _base64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _base64url(json.dumps({
        "iat": agora - 60,
        "exp": agora + 540,
        "iss": config.app_id,
    }, separators=(",", ":")).encode())
    mensagem = f"{cabecalho}.{payload}".encode()
    try:
        chave = serialization.load_pem_private_key(config.private_key.encode(), password=None)
        assinatura = chave.sign(mensagem, padding.PKCS1v15(), hashes.SHA256())
    except Exception as exc:
        raise GitHubConfigurationError("GITHUB_APP_PRIVATE_KEY não é uma chave PEM válida.") from exc
    return f"{cabecalho}.{payload}.{_base64url(assinatura)}"


def criar_token_assinado(tipo: str, validade_segundos: int = 600) -> str:
    config = obter_config_github()
    payload = {
        "tipo": tipo,
        "exp": int(time.time()) + validade_segundos,
        # O browser recebe apenas um nonce; IDs ficam associados no Supabase.
        "nonce": secrets.token_urlsafe(32),
    }
    corpo = _base64url(json.dumps(payload, separators=(",", ":")).encode())
    assinatura = hmac.new(config.state_secret.encode(), corpo.encode(), hashlib.sha256).hexdigest()
    return f"{corpo}.{assinatura}"


def validar_token_assinado(token: str, tipo: str) -> dict[str, Any]:
    config = obter_config_github()
    try:
        corpo, recebida = token.rsplit(".", 1)
        esperada = hmac.new(config.state_secret.encode(), corpo.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(esperada, recebida):
            raise ValueError
        padding_base64 = "=" * (-len(corpo) % 4)
        dados = json.loads(base64.urlsafe_b64decode(corpo + padding_base64))
        if dados.get("tipo") != tipo or int(dados.get("exp", 0)) < int(time.time()):
            raise ValueError
        return dados
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise GitHubConfigurationError("Token de conexão inválido ou expirado.") from exc


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validar_assinatura_webhook(corpo: bytes, assinatura: str | None) -> bool:
    config = obter_config_github()
    if not assinatura or not assinatura.startswith("sha256="):
        return False
    esperada = "sha256=" + hmac.new(
        config.webhook_secret.encode(), corpo, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperada, assinatura)


def url_instalacao(state: str) -> str:
    slug = obter_config_github().app_slug
    return f"https://github.com/apps/{urllib.parse.quote(slug)}/installations/new?state={urllib.parse.quote(state)}"


def _request_github(
    metodo: str,
    caminho: str,
    token: str,
    corpo: dict[str, Any] | None = None,
) -> Any:
    dados = json.dumps(corpo).encode() if corpo is not None else None
    request = urllib.request.Request(
        f"{GITHUB_API_URL}{caminho}",
        data=dados,
        method=metodo,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "CITi-commit-documenter",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as resposta:
            conteudo = resposta.read()
            return json.loads(conteudo) if conteudo else {}
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        # A resposta remota pode conter detalhes sensíveis; não a propagamos.
        status = getattr(exc, "code", None)
        sufixo = f" (HTTP {status})" if status else ""
        raise GitHubApiError(f"Não foi possível consultar o GitHub{sufixo}.") from exc


def criar_token_instalacao(installation_id: int) -> str:
    resposta = _request_github(
        "POST",
        f"/app/installations/{installation_id}/access_tokens",
        criar_jwt_github(),
        {},
    )
    token = resposta.get("token")
    if not token:
        raise GitHubApiError("O GitHub não retornou uma credencial temporária da instalação.")
    return token


def listar_repositorios_instalacao(installation_id: int) -> list[dict[str, Any]]:
    token = criar_token_instalacao(installation_id)
    repositorios: list[dict[str, Any]] = []
    pagina = 1
    while True:
        resposta = _request_github(
            "GET", f"/installation/repositories?per_page=100&page={pagina}", token
        )
        lote = resposta.get("repositories") or []
        repositorios.extend(lote)
        if len(lote) < 100:
            break
        pagina += 1
    return repositorios


def buscar_commit(
    installation_id: int, nome_completo: str, sha: str
) -> tuple[dict[str, Any], str, str]:
    token = criar_token_instalacao(installation_id)
    repo = urllib.parse.quote(nome_completo, safe="/")
    commit = _request_github("GET", f"/repos/{repo}/commits/{sha}?per_page=100", token)
    arquivos = commit.get("files") or []
    stats = commit.get("stats") or {}
    diff_stat = (
        f"{len(arquivos)} arquivo(s), +{stats.get('additions', 0)} "
        f"-{stats.get('deletions', 0)}"
    )
    trechos: list[str] = []
    for arquivo in arquivos:
        cabecalho = (
            f"Arquivo: {arquivo.get('filename', '?')} "
            f"({arquivo.get('status', '?')}, +{arquivo.get('additions', 0)} "
            f"-{arquivo.get('deletions', 0)})"
        )
        trechos.append(f"{cabecalho}\n{arquivo.get('patch') or '[diff indisponível]'}")
    return commit, diff_stat, "\n\n".join(trechos)[:8000]


def comparar_commits(installation_id: int, nome_completo: str, base: str, head: str) -> list[dict[str, Any]]:
    token = criar_token_instalacao(installation_id)
    repo = urllib.parse.quote(nome_completo, safe="/")
    commits: list[dict[str, Any]] = []
    pagina = 1
    while True:
        resposta = _request_github(
            "GET",
            f"/repos/{repo}/compare/{urllib.parse.quote(base)}...{urllib.parse.quote(head)}"
            f"?per_page=100&page={pagina}",
            token,
        )
        lote = resposta.get("commits") or []
        commits.extend(lote)
        if len(lote) < 100:
            break
        pagina += 1
    return commits


def criar_status_commit(
    installation_id: int,
    nome_completo: str,
    sha: str,
    estado: str,
    descricao: str,
) -> None:
    token = criar_token_instalacao(installation_id)
    repo = urllib.parse.quote(nome_completo, safe="/")
    _request_github(
        "POST",
        f"/repos/{repo}/statuses/{sha}",
        token,
        {"state": estado, "description": descricao[:140], "context": "CITi/documentacao"},
    )
