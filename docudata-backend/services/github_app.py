"""Configuração, autenticação e chamadas do GitHub App."""

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
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


GITHUB_API_URL = "https://api.github.com"
_SUBAREAS_SUPORTADAS = {"dados", "dev"}
_TTL_INSTALACOES_SEGUNDOS = 60.0
_TTL_REPOSITORIOS_RECENTES_SEGUNDOS = 45.0
_cache_instalacoes: tuple[float, list[dict[str, Any]]] | None = None
_cache_repositorios_recentes: dict[
    tuple[int, str, int], tuple[float, list[dict[str, Any]], bool]
] = {}


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


def subarea_github_habilitada(subarea: str) -> bool:
    return subarea in _SUBAREAS_SUPORTADAS


def obter_config_github() -> GitHubConfig:
    """Valida as credenciais somente no primeiro fluxo que realmente usa o App."""
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
    configurada = False
    slug = None
    try:
        config = obter_config_github()
        configurada = True
        slug = config.app_slug
    except GitHubConfigurationError:
        pass
    return {
        # Mantido no contrato público para clientes antigos; a integração agora é permanente.
        "enabled": True,
        "configured": configurada,
        "subareas": sorted(_SUBAREAS_SUPORTADAS),
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


def criar_token_instalacao(
    installation_id: int,
    repository_ids: list[int] | None = None,
) -> str:
    corpo = {"repository_ids": repository_ids} if repository_ids else {}
    resposta = _request_github(
        "POST",
        f"/app/installations/{installation_id}/access_tokens",
        criar_jwt_github(),
        corpo,
    )
    token = resposta.get("token")
    if not token:
        raise GitHubApiError("O GitHub não retornou uma credencial temporária da instalação.")
    return token


def buscar_repositorios_instalacao(
    installation_id: int,
    repository_ids: list[int],
) -> list[dict[str, Any]]:
    """Valida poucos IDs com um token temporário limitado aos próprios repositórios."""
    token = criar_token_instalacao(installation_id, repository_ids=repository_ids)
    repositorios = []
    for repository_id in repository_ids:
        resposta = _request_github("GET", f"/repositories/{repository_id}", token)
        if not isinstance(resposta, dict) or int(resposta.get("id") or 0) != repository_id:
            raise GitHubApiError("O GitHub retornou um repositório inválido.")
        repositorios.append(resposta)
    return repositorios


def listar_instalacoes_app() -> list[dict[str, Any]]:
    """Lista instalações ativas para reutilizar a autorização já concedida."""
    global _cache_instalacoes
    agora = time.monotonic()
    if (
        _cache_instalacoes
        and agora - _cache_instalacoes[0] < _TTL_INSTALACOES_SEGUNDOS
    ):
        return deepcopy(_cache_instalacoes[1])

    instalacoes: list[dict[str, Any]] = []
    pagina = 1
    token = criar_jwt_github()
    while True:
        lote = _request_github(
            "GET", f"/app/installations?per_page=100&page={pagina}", token
        )
        if not isinstance(lote, list):
            raise GitHubApiError("O GitHub retornou instalações em formato inválido.")
        instalacoes.extend(item for item in lote if not item.get("suspended_at"))
        if len(lote) < 100:
            break
        pagina += 1
    # O cache guarda apenas metadados da instalação; credenciais nunca são retidas.
    _cache_instalacoes = (agora, deepcopy(instalacoes))
    return instalacoes


def obter_instalacao_app(installation_id: int) -> dict[str, Any]:
    resposta = _request_github(
        "GET",
        f"/app/installations/{installation_id}",
        criar_jwt_github(),
    )
    if not isinstance(resposta, dict) or not resposta.get("id"):
        raise GitHubApiError("O GitHub retornou uma instalação inválida.")
    return resposta


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


def listar_repositorios_para_selecao(
    instalacao: dict[str, Any],
    consulta: str = "",
    limite: int = 30,
) -> tuple[list[dict[str, Any]], bool]:
    """Busca só o necessário para o seletor; o fluxo completo fica na validação final."""
    installation_id = int(instalacao["id"])
    conta = instalacao.get("account") or {}
    login = str(conta.get("login") or "").strip()
    organizacao = conta.get("type") == "Organization"
    acesso_total = instalacao.get("repository_selection") == "all"
    termo = consulta.strip()

    if acesso_total and organizacao and login:
        cache_key = (installation_id, login.casefold(), limite)
        agora = time.monotonic()
        cache_recente = _cache_repositorios_recentes.get(cache_key)
        if (
            not termo
            and cache_recente
            and agora - cache_recente[0] < _TTL_REPOSITORIOS_RECENTES_SEGUNDOS
        ):
            return deepcopy(cache_recente[1]), cache_recente[2]

        token = criar_token_instalacao(installation_id)
        if termo:
            query = f"{termo} in:name org:{login}"
            resposta = _request_github(
                "GET",
                "/search/repositories?" + urllib.parse.urlencode({
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": limite,
                }),
                token,
            )
            repositorios = resposta.get("items") or []
            return repositorios[:limite], int(resposta.get("total_count") or 0) > limite

        caminho = f"/orgs/{urllib.parse.quote(login)}/repos?" + urllib.parse.urlencode({
            "type": "all",
            "sort": "pushed",
            "direction": "desc",
            "per_page": limite,
        })
        repositorios = _request_github("GET", caminho, token)
        if not isinstance(repositorios, list):
            raise GitHubApiError("O GitHub retornou repositórios em formato inválido.")
        recentes = repositorios[:limite]
        tem_mais = len(repositorios) == limite
        _cache_repositorios_recentes[cache_key] = (
            agora,
            deepcopy(recentes),
            tem_mais,
        )
        return recentes, tem_mais

    # Instalações pessoais ou limitadas costumam ter poucos repositórios; aqui
    # priorizamos não exibir um repositório fora da permissão efetiva do App.
    repositorios = listar_repositorios_instalacao(installation_id)
    if termo:
        termo_normalizado = termo.casefold()
        repositorios = [
            repo for repo in repositorios
            if termo_normalizado in str(repo.get("full_name") or "").casefold()
        ]
    repositorios.sort(
        key=lambda repo: repo.get("pushed_at") or repo.get("updated_at") or "",
        reverse=True,
    )
    return repositorios[:limite], len(repositorios) > limite


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
