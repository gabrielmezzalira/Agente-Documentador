"""Conexão de projetos ao GitHub App e recebimento dos webhooks assinados."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from models.schemas import (
    GitHubCapabilities,
    GitHubConnectionSession,
    GitHubRepositoriesAvailable,
    ProjectRepositoryCreate,
    ProjectRepositoryResponse,
)
from services.commit_extraction import DadosCommit, commit_ja_ingerido, extrair_e_salvar_commit
from services.github_app import (
    GitHubApiError,
    GitHubConfigurationError,
    buscar_commit,
    comparar_commits,
    configuracao_publica_github,
    criar_status_commit,
    criar_token_assinado,
    hash_token,
    integracao_github_habilitada,
    listar_repositorios_instalacao,
    subarea_github_habilitada,
    url_instalacao,
    validar_assinatura_webhook,
    validar_token_assinado,
)
from services.supabase_client import get_client


router = APIRouter(tags=["github-integration"])
public_router = APIRouter(tags=["github-webhook"])


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: datetime) -> str:
    return valor.isoformat()


def _erro_indisponivel(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


def _obter_projeto(client: Any, project_id: str) -> dict[str, Any]:
    resposta = client.table("projects").select("id, name, subarea").eq("id", project_id).execute()
    if not resposta.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return resposta.data[0]


def _exigir_subarea_habilitada(projeto: dict[str, Any]) -> None:
    if not subarea_github_habilitada(projeto.get("subarea", "")):
        raise HTTPException(
            status_code=403,
            detail="A integração com GitHub não está habilitada para esta subárea.",
        )


def _validar_sessao_conexao(client: Any, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        dados = validar_token_assinado(token, "connection")
    except GitHubConfigurationError as exc:
        raise HTTPException(status_code=410, detail="A conexão com o GitHub expirou. Tente novamente.") from exc
    resposta = (
        client.table("github_connection_sessions")
        .select("*")
        .eq("connection_token_hash", hash_token(token))
        .execute()
    )
    if not resposta.data:
        raise HTTPException(status_code=410, detail="A conexão com o GitHub expirou. Tente novamente.")
    sessao = resposta.data[0]
    if sessao.get("status") != "ready" or sessao.get("connection_token_hash") != hash_token(token):
        raise HTTPException(status_code=410, detail="A conexão com o GitHub já foi usada ou expirou.")
    try:
        if datetime.fromisoformat(str(sessao["expires_at"]).replace("Z", "+00:00")) < _agora():
            raise HTTPException(status_code=410, detail="A conexão com o GitHub expirou. Tente novamente.")
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=410, detail="A conexão com o GitHub é inválida.") from exc
    return dados, sessao


def _repositorio_publico(row: dict[str, Any]) -> dict[str, Any]:
    status = "active" if row.get("active") else row.get("inactive_reason") or "revoked"
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "github_repository_id": row["github_repository_id"],
        "full_name": row["full_name"],
        "html_url": row["html_url"],
        "default_branch": row.get("default_branch"),
        "active": bool(row.get("active")),
        "permission_status": status,
        "connected_at": row["connected_at"],
        "updated_at": row["updated_at"],
    }


@router.get("/integrations/github/capabilities", response_model=GitHubCapabilities)
async def github_capabilities():
    """Expõe apenas flags efetivas; nunca retorna credenciais."""
    return configuracao_publica_github()


@router.post(
    "/projects/{project_id}/repositories/github/session",
    response_model=GitHubConnectionSession,
)
async def iniciar_conexao_github(project_id: str):
    if not integracao_github_habilitada():
        raise HTTPException(status_code=404, detail="Integração com GitHub indisponível.")
    client = get_client()
    projeto = _obter_projeto(client, project_id)
    _exigir_subarea_habilitada(projeto)
    try:
        state = criar_token_assinado("state")
        resposta = client.table("github_connection_sessions").insert({
            "project_id": project_id,
            "state_hash": hash_token(state),
            "status": "pending",
            "expires_at": _iso(_agora() + timedelta(minutes=10)),
        }).execute()
        if not resposta.data:
            raise RuntimeError
        return {"install_url": url_instalacao(state)}
    except (GitHubConfigurationError, RuntimeError) as exc:
        raise _erro_indisponivel(exc) from exc


@public_router.get("/integrations/github/callback")
async def callback_github(
    state: str = Query(...),
    installation_id: int | None = Query(default=None),
    setup_action: str | None = Query(default=None),
):
    if not integracao_github_habilitada():
        raise HTTPException(status_code=404, detail="Integração com GitHub indisponível.")
    try:
        validar_token_assinado(state, "state")
    except GitHubConfigurationError as exc:
        raise HTTPException(status_code=410, detail="A conexão com o GitHub expirou. Tente novamente.") from exc

    client = get_client()
    resposta = (
        client.table("github_connection_sessions")
        .select("*")
        .eq("state_hash", hash_token(state))
        .execute()
    )
    if not resposta.data or resposta.data[0].get("status") != "pending":
        raise HTTPException(status_code=410, detail="Esta conexão já foi usada ou expirou.")
    sessao = resposta.data[0]
    try:
        if datetime.fromisoformat(str(sessao["expires_at"]).replace("Z", "+00:00")) < _agora():
            raise HTTPException(status_code=410, detail="A conexão com o GitHub expirou. Tente novamente.")
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=410, detail="Esta conexão é inválida.") from exc

    origem = next(
        (item.strip() for item in os.environ.get("ALLOWED_ORIGINS", "").split(",") if item.strip()),
        "http://localhost:3000",
    ).rstrip("/")
    projeto = _obter_projeto(client, sessao["project_id"])
    caminho = f"/{projeto['subarea']}/projects/{projeto['id']}"

    if installation_id is None or setup_action == "request":
        client.table("github_connection_sessions").update({
            "status": "cancelled", "updated_at": _iso(_agora())
        }).eq("id", sessao["id"]).execute()
        return RedirectResponse(f"{origem}{caminho}?tab=config&github_error=cancelled")

    token = criar_token_assinado("connection")
    client.table("github_connection_sessions").update({
        "status": "ready",
        "installation_id": installation_id,
        "connection_token_hash": hash_token(token),
        "expires_at": _iso(_agora() + timedelta(minutes=10)),
        "updated_at": _iso(_agora()),
    }).eq("id", sessao["id"]).execute()
    query = urlencode({"tab": "config", "github_connection": token})
    return RedirectResponse(f"{origem}{caminho}?{query}")


@router.get(
    "/integrations/github/repositories",
    response_model=GitHubRepositoriesAvailable,
)
async def listar_repositorios_disponiveis(connection_token: str = Query(...)):
    if not integracao_github_habilitada():
        raise HTTPException(status_code=404, detail="Integração com GitHub indisponível.")
    client = get_client()
    _, sessao = _validar_sessao_conexao(client, connection_token)
    projeto = _obter_projeto(client, sessao["project_id"])
    _exigir_subarea_habilitada(projeto)
    try:
        repositorios = listar_repositorios_instalacao(int(sessao["installation_id"]))
    except GitHubApiError as exc:
        raise _erro_indisponivel(exc) from exc
    return {"repositories": [{
        "github_repository_id": repo["id"],
        "full_name": repo["full_name"],
        "html_url": repo["html_url"],
        "default_branch": repo.get("default_branch"),
        "private": bool(repo.get("private")),
    } for repo in repositorios]}


@router.post(
    "/projects/{project_id}/repositories",
    response_model=list[ProjectRepositoryResponse],
    status_code=201,
)
async def conectar_repositorios(project_id: str, body: ProjectRepositoryCreate):
    if not integracao_github_habilitada():
        raise HTTPException(status_code=404, detail="Integração com GitHub indisponível.")
    client = get_client()
    _, sessao = _validar_sessao_conexao(client, body.connection_token)
    if sessao["project_id"] != project_id:
        raise HTTPException(status_code=403, detail="Esta conexão pertence a outro projeto.")
    projeto = _obter_projeto(client, project_id)
    _exigir_subarea_habilitada(projeto)

    try:
        autorizados = listar_repositorios_instalacao(int(sessao["installation_id"]))
    except GitHubApiError as exc:
        raise _erro_indisponivel(exc) from exc
    por_id = {int(repo["id"]): repo for repo in autorizados}
    selecionados = list(dict.fromkeys(body.repository_ids))
    if not selecionados or any(repo_id not in por_id for repo_id in selecionados):
        raise HTTPException(status_code=422, detail="Selecione ao menos um repositório autorizado pelo GitHub.")

    salvos: list[dict[str, Any]] = []
    existentes_por_id: dict[int, dict[str, Any] | None] = {}
    # Valida o lote inteiro antes de escrever para não deixar associação parcial.
    for repo_id in selecionados:
        existente = (
            client.table("project_repositories")
            .select("*")
            .eq("github_repository_id", repo_id)
            .execute()
        )
        row = existente.data[0] if existente.data else None
        existentes_por_id[repo_id] = row
        if row and row.get("active") and row["project_id"] != project_id:
            nome_projeto = _obter_projeto(client, row["project_id"]).get("name", "outro projeto")
            raise HTTPException(
                status_code=409,
                detail=f"Este repositório já está conectado ao projeto {nome_projeto}.",
            )

    for repo_id in selecionados:
        repo = por_id[repo_id]
        valores = {
            "project_id": project_id,
            "installation_id": sessao["installation_id"],
            "full_name": repo["full_name"],
            "html_url": repo["html_url"],
            "default_branch": repo.get("default_branch"),
            "active": True,
            "inactive_reason": None,
            "updated_at": _iso(_agora()),
        }
        existente = existentes_por_id[repo_id]
        if existente:
            resposta = (
                client.table("project_repositories").update(valores)
                .eq("id", existente["id"]).execute()
            )
        else:
            resposta = client.table("project_repositories").insert({
                **valores, "github_repository_id": repo_id
            }).execute()
        if resposta.data:
            salvos.append(resposta.data[0])

    client.table("github_connection_sessions").update({
        "status": "consumed", "updated_at": _iso(_agora())
    }).eq("id", sessao["id"]).execute()
    return [_repositorio_publico(row) for row in salvos]


@router.get(
    "/projects/{project_id}/repositories",
    response_model=list[ProjectRepositoryResponse],
)
async def listar_repositorios_projeto(project_id: str):
    if not integracao_github_habilitada():
        raise HTTPException(status_code=404, detail="Integração com GitHub indisponível.")
    client = get_client()
    projeto = _obter_projeto(client, project_id)
    _exigir_subarea_habilitada(projeto)
    resposta = (
        client.table("project_repositories").select("*")
        .eq("project_id", project_id).order("connected_at", desc=False).execute()
    )
    return [_repositorio_publico(row) for row in (resposta.data or [])]


@router.delete("/projects/{project_id}/repositories/{repository_id}", status_code=204)
async def desconectar_repositorio(project_id: str, repository_id: str):
    if not integracao_github_habilitada():
        raise HTTPException(status_code=404, detail="Integração com GitHub indisponível.")
    client = get_client()
    projeto = _obter_projeto(client, project_id)
    _exigir_subarea_habilitada(projeto)
    resposta = (
        client.table("project_repositories").select("id").eq("id", repository_id)
        .eq("project_id", project_id).execute()
    )
    if not resposta.data:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")
    client.table("project_repositories").update({
        "active": False, "inactive_reason": "disconnected", "updated_at": _iso(_agora())
    }).eq("id", repository_id).execute()


def _registrar_delivery(client: Any, delivery_id: str, evento: str) -> tuple[dict[str, Any] | None, bool]:
    existente = client.table("github_webhook_deliveries").select("*").eq("delivery_id", delivery_id).execute()
    if existente.data:
        row = existente.data[0]
        if row.get("status") in {"succeeded", "ignored", "processing"}:
            return row, True
        client.table("github_webhook_deliveries").update({
            "status": "received",
            "attempts": int(row.get("attempts") or 0) + 1,
            "last_error": None,
            "updated_at": _iso(_agora()),
        }).eq("delivery_id", delivery_id).execute()
        return row, False
    client.table("github_webhook_deliveries").insert({
        "delivery_id": delivery_id,
        "event": evento,
        "status": "received",
        "attempts": 1,
    }).execute()
    return None, False


def _atualizar_delivery(client: Any, delivery_id: str, status: str, erro: str | None = None) -> None:
    client.table("github_webhook_deliveries").update({
        "status": status,
        "last_error": erro[:500] if erro else None,
        "updated_at": _iso(_agora()),
    }).eq("delivery_id", delivery_id).execute()


def _tratar_evento_instalacao(client: Any, evento: str, payload: dict[str, Any]) -> None:
    installation_id = (payload.get("installation") or {}).get("id")
    if not installation_id:
        return
    acao = payload.get("action")
    if evento == "installation" and acao in {"deleted", "suspend"}:
        client.table("project_repositories").update({
            "active": False, "inactive_reason": "revoked", "updated_at": _iso(_agora())
        }).eq("installation_id", installation_id).execute()
        return
    if evento == "installation_repositories":
        for repo in payload.get("repositories_removed") or []:
            client.table("project_repositories").update({
                "active": False, "inactive_reason": "revoked", "updated_at": _iso(_agora())
            }).eq("github_repository_id", repo["id"]).eq("installation_id", installation_id).execute()
        for repo in payload.get("repositories_added") or []:
            vinculos = (
                client.table("project_repositories").select("id, inactive_reason")
                .eq("github_repository_id", repo["id"])
                .eq("installation_id", installation_id).execute()
            )
            for vinculo in vinculos.data or []:
                reativar = vinculo.get("inactive_reason") != "disconnected"
                client.table("project_repositories").update({
                    "active": reativar,
                    "inactive_reason": None if reativar else "disconnected",
                    "full_name": repo["full_name"],
                    "html_url": repo.get("html_url") or f"https://github.com/{repo['full_name']}",
                    "updated_at": _iso(_agora()),
                }).eq("id", vinculo["id"]).execute()
        return
    if evento == "installation" and acao == "unsuspend":
        autorizados = listar_repositorios_instalacao(int(installation_id))
        ids = {repo["id"]: repo for repo in autorizados}
        vinculados = (
            client.table("project_repositories").select("id, github_repository_id, inactive_reason")
            .eq("installation_id", installation_id).execute()
        )
        for vinculo in vinculados.data or []:
            repo = ids.get(vinculo["github_repository_id"])
            reativar = bool(repo) and vinculo.get("inactive_reason") != "disconnected"
            client.table("project_repositories").update({
                "active": reativar,
                "inactive_reason": None if reativar else vinculo.get("inactive_reason") or "revoked",
                **({"full_name": repo["full_name"], "html_url": repo["html_url"]} if repo else {}),
                "updated_at": _iso(_agora()),
            }).eq("id", vinculo["id"]).execute()


def _tratar_repositorio_renomeado(client: Any, payload: dict[str, Any]) -> None:
    if payload.get("action") != "renamed":
        return
    repo = payload.get("repository") or {}
    if not repo.get("id") or not repo.get("full_name"):
        return
    client.table("project_repositories").update({
        "full_name": repo["full_name"],
        "html_url": repo.get("html_url") or f"https://github.com/{repo['full_name']}",
        "updated_at": _iso(_agora()),
    }).eq("github_repository_id", repo["id"]).execute()


async def _processar_push(client: Any, payload: dict[str, Any]) -> tuple[int, list[str]]:
    ref = str(payload.get("ref") or "")
    if payload.get("deleted") or not ref.startswith("refs/heads/"):
        return 0, []
    github_repo_id = (payload.get("repository") or {}).get("id")
    vinculo_resp = (
        client.table("project_repositories").select("*")
        .eq("github_repository_id", github_repo_id).eq("active", True).execute()
    )
    if not vinculo_resp.data:
        return 0, []
    vinculo = vinculo_resp.data[0]
    projeto = _obter_projeto(client, vinculo["project_id"])
    if not subarea_github_habilitada(projeto.get("subarea", "")):
        return 0, []

    repo_payload = payload.get("repository") or {}
    if repo_payload.get("full_name") and repo_payload.get("full_name") != vinculo.get("full_name"):
        client.table("project_repositories").update({
            "full_name": repo_payload["full_name"],
            "html_url": repo_payload.get("html_url") or vinculo["html_url"],
            "updated_at": _iso(_agora()),
        }).eq("id", vinculo["id"]).execute()
        vinculo["full_name"] = repo_payload["full_name"]
        vinculo["html_url"] = repo_payload.get("html_url") or vinculo["html_url"]

    commits = payload.get("commits") or []
    if int(payload.get("size") or len(commits)) > len(commits):
        commits = comparar_commits(
            int(vinculo["installation_id"]), vinculo["full_name"],
            str(payload.get("before")), str(payload.get("after")),
        )

    processados = 0
    erros: list[str] = []
    branch = ref.removeprefix("refs/heads/")
    for item in commits:
        sha = str(item.get("id") or item.get("sha") or "")
        if not sha or commit_ja_ingerido(client, vinculo["id"], sha):
            continue
        try:
            detalhe, diff_stat, diff = buscar_commit(
                int(vinculo["installation_id"]), vinculo["full_name"], sha
            )
            commit = detalhe.get("commit") or {}
            autor_commit = commit.get("author") or {}
            committer_commit = commit.get("committer") or {}
            autor_usuario = detalhe.get("author") or {}
            committer_usuario = detalhe.get("committer") or {}
            resultado = await extrair_e_salvar_commit(client, DadosCommit(
                projeto_id=vinculo["project_id"],
                sha=sha,
                mensagem=commit.get("message") or item.get("message") or "",
                autor=autor_commit.get("name") or (item.get("author") or {}).get("name") or "Autor não identificado",
                autor_login=autor_usuario.get("login"),
                data=autor_commit.get("date") or (item.get("timestamp") or ""),
                committer=committer_commit.get("name"),
                committer_login=committer_usuario.get("login"),
                pusher=(payload.get("pusher") or {}).get("name"),
                sender=(payload.get("sender") or {}).get("login"),
                branch=branch,
                diff_stat=diff_stat,
                diff=diff,
                repositorio_id=vinculo["id"],
                repositorio_nome=vinculo["full_name"],
                url=detalhe.get("html_url") or f"{vinculo['html_url']}/commit/{sha}",
            ))
            if resultado["status"] == "ok":
                processados += 1
                try:
                    criar_status_commit(
                        int(vinculo["installation_id"]), vinculo["full_name"], sha,
                        "success", "Commit incorporado ao contexto do projeto",
                    )
                except GitHubApiError:
                    # A ingestão persistida nunca é revertida por falha cosmética de status.
                    pass
        except Exception as exc:
            erros.append(f"{sha[:7]}: {type(exc).__name__}")
    return processados, erros


@public_router.post("/webhooks/github")
async def webhook_github(request: Request):
    if not integracao_github_habilitada():
        raise HTTPException(status_code=404, detail="Integração com GitHub indisponível.")
    corpo = await request.body()
    try:
        assinatura_valida = validar_assinatura_webhook(
            corpo, request.headers.get("X-Hub-Signature-256")
        )
    except GitHubConfigurationError as exc:
        raise _erro_indisponivel(exc) from exc
    if not assinatura_valida:
        raise HTTPException(status_code=401, detail="Assinatura do webhook inválida.")

    delivery_id = request.headers.get("X-GitHub-Delivery")
    evento = request.headers.get("X-GitHub-Event", "")
    if not delivery_id:
        raise HTTPException(status_code=400, detail="X-GitHub-Delivery ausente.")

    client = get_client()
    anterior, duplicada = _registrar_delivery(client, delivery_id, evento)
    if duplicada:
        return {"status": anterior.get("status"), "duplicate": True}
    try:
        payload = json.loads(corpo)
    except json.JSONDecodeError as exc:
        _atualizar_delivery(client, delivery_id, "failed", "JSON inválido")
        raise HTTPException(status_code=400, detail="Payload inválido.") from exc

    try:
        _atualizar_delivery(client, delivery_id, "processing")
        if evento == "push":
            processados, erros = await _processar_push(client, payload)
            if erros:
                _atualizar_delivery(client, delivery_id, "failed", "; ".join(erros))
                return {"status": "failed", "processed": processados, "errors": len(erros)}
            if processados == 0:
                _atualizar_delivery(client, delivery_id, "ignored")
                return {"status": "ignored", "processed": 0}
            _atualizar_delivery(client, delivery_id, "succeeded")
            return {"status": "succeeded", "processed": processados}
        if evento in {"installation", "installation_repositories"}:
            _tratar_evento_instalacao(client, evento, payload)
            _atualizar_delivery(client, delivery_id, "succeeded")
            return {"status": "succeeded"}
        if evento == "repository":
            _tratar_repositorio_renomeado(client, payload)
            _atualizar_delivery(client, delivery_id, "succeeded")
            return {"status": "succeeded"}
        _atualizar_delivery(client, delivery_id, "ignored")
        return {"status": "ignored"}
    except Exception as exc:
        _atualizar_delivery(client, delivery_id, "failed", type(exc).__name__)
        # 500 permite redelivery; detalhes remotos não são expostos.
        raise HTTPException(status_code=500, detail="Falha temporária ao processar webhook.") from exc
