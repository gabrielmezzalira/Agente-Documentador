"""Rotas de LEITURA para o Painel do Projeto CITi (docs/painel-api.md).

Protegidas por chave de serviço dedicada (`X-Painel-Key`, ver `core.security.require_painel_key`),
no `main.py`. Só `GET`, sem efeito colateral. O painel consulta por `project_id` do DocuData.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from services.painel_leitura import (
    concluidas_em,
    contar_commits,
    escolher_sprint,
    mapear_atas,
    mapear_documentos,
    mapear_escopo,
    mapear_indicadores,
    mapear_kanban,
    mapear_pessoas,
)
from services.previsto_sprint import previsto_da_sprint
from services.supabase_client import get_client
from services.supabase_paginacao import ler_tudo

router = APIRouter(prefix="/integracoes/painel/v1", tags=["painel-leitura"])

_RECIFE = timezone(timedelta(hours=-3))


def _projeto_ou_404(client, project_id: str) -> dict:
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    linhas = (
        client.table("projects")
        .select("id, name, data_inicio, data_fim_contratada, tolerancia_desvio_pontos")
        .eq("id", project_id)
        .execute()
        .data
        or []
    )
    if not linhas:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return linhas[0]


def _sprints(client, project_id: str) -> list[dict]:
    return (
        client.table("sprints").select("*").eq("project_id", project_id).order("numero", desc=True).execute().data or []
    )


def _sprint_ou_404(client, project_id: str, numero: int | None) -> dict:
    sprint = escolher_sprint(_sprints(client, project_id), numero)
    if sprint is None:
        raise HTTPException(status_code=404, detail="Sprint não encontrada")
    return sprint


def _tasks(client, project_id: str) -> list[dict]:
    return ler_tudo(
        lambda: client.table("tasks")
        .select("id, titulo, pontos, coluna_kanban, extra, sprint_id, operacional_id, checklist, "
                "bloqueado_manual, bloqueio_tipo, bloqueado_em")
        .eq("project_id", project_id)
        .order("id")
    )


@router.get("/projetos/{project_id}/kanban")
def kanban(project_id: str, sprint: int | None = Query(default=None, ge=1)):
    """Cartões da sprint (a pedida ou a atual)."""
    client = get_client()
    _projeto_ou_404(client, project_id)
    alvo = _sprint_ou_404(client, project_id, sprint)
    tasks = [t for t in _tasks(client, project_id) if t.get("sprint_id") == alvo["id"]]
    ids = [t["id"] for t in tasks]
    transicoes = (
        ler_tudo(lambda: client.table("task_transicoes").select("task_id, para, timestamp").in_("task_id", ids).order("id"))
        if ids
        else []
    )
    operacionais = client.table("operacionais").select("id, nome").eq("project_id", project_id).execute().data or []
    nomes = {str(o["id"]): o["nome"] for o in operacionais}
    return mapear_kanban(tasks, nomes, concluidas_em(transicoes))


@router.get("/projetos/{project_id}/indicadores")
def indicadores(project_id: str, sprint: int | None = Query(default=None, ge=1)):
    """Indicadores da sprint (a pedida ou a atual): SPI, desvio de pontos, escopo, saúde."""
    client = get_client()
    projeto = _projeto_ou_404(client, project_id)
    alvo = _sprint_ou_404(client, project_id, sprint)
    todas = _tasks(client, project_id)
    da_sprint = [t for t in todas if t.get("sprint_id") == alvo["id"]]
    previsto = previsto_da_sprint(client, alvo["id"])["previsto"]
    hoje = datetime.now(_RECIFE).date()
    return mapear_indicadores(projeto, alvo, da_sprint, todas, previsto, hoje)


@router.get("/projetos/{project_id}/escopo")
def escopo(project_id: str):
    """Matriz de escopo (funcionalidades)."""
    client = get_client()
    _projeto_ou_404(client, project_id)
    funcionalidades = ler_tudo(
        lambda: client.table("funcionalidades").select("*").eq("project_id", project_id).order("id_funcional")
    )
    return mapear_escopo(funcionalidades, _sprints(client, project_id))


def _docs_gerados(client, project_id: str) -> list[dict]:
    return ler_tudo(
        lambda: client.table("generated_docs")
        .select("id, doc_type, sprint_number, content, created_at")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
    )


@router.get("/projetos/{project_id}/atas")
def atas(project_id: str):
    """Atas de reunião geradas (markdown)."""
    client = get_client()
    _projeto_ou_404(client, project_id)
    return mapear_atas(_docs_gerados(client, project_id))


@router.get("/projetos/{project_id}/documentos")
def documentos(project_id: str):
    """Documentos gerados pelo DocuData (sem as atas). Sem link: o conteúdo não sai por aqui."""
    client = get_client()
    _projeto_ou_404(client, project_id)
    return mapear_documentos(_docs_gerados(client, project_id))


@router.get("/projetos/{project_id}/pessoas")
def pessoas(project_id: str):
    """Time operacional do projeto (nome e papel; sem e-mail)."""
    client = get_client()
    _projeto_ou_404(client, project_id)
    linhas = (
        client.table("operacionais").select("id, nome, papel, ativo").eq("project_id", project_id).execute().data or []
    )
    return mapear_pessoas(linhas)


@router.get("/projetos/{project_id}/commits")
def commits(
    project_id: str,
    desde: datetime = Query(...),
    ate: datetime = Query(...),
):
    """Quantidade de commits analisados pelo DocuData entre `desde` e `ate` (ISO 8601)."""
    if ate < desde:
        raise HTTPException(status_code=422, detail="`ate` não pode ser antes de `desde`")
    client = get_client()
    _projeto_ou_404(client, project_id)
    # Sem fuso informado, assume UTC.
    inicio = desde if desde.tzinfo else desde.replace(tzinfo=timezone.utc)
    fim = ate if ate.tzinfo else ate.replace(tzinfo=timezone.utc)
    linhas = ler_tudo(
        lambda: client.table("commit_qualidade").select("id, criado_em").eq("projeto_id", project_id).order("id")
    )
    return {"count": contar_commits(linhas, inicio, fim)}
