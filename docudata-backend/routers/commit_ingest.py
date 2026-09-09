"""Compatibilidade com o agente legado de ingestão de commits."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from core.rate_limit import GEMINI_RATE_LIMIT, limiter
from services.commit_extraction import DadosCommit, extrair_e_salvar_commit
from services.sprints import get_current_sprint_number
from services.supabase_client import get_client


router = APIRouter(tags=["commit-ingest"])


class CommitPayload(BaseModel):
    project_id: str
    sprint_number: int
    commit_hash: str
    commit_message: str
    author: str
    author_email: Optional[str] = None
    author_github_login: Optional[str] = None
    date: str
    branch: Optional[str] = None
    diff_stat: Optional[str] = None
    diff: Optional[str] = None


@router.get("/projects/{project_id}/current-sprint")
async def get_current_sprint(project_id: str):
    """Retorna a sprint atual sem fazer uma chamada HTTP interna."""
    client = get_client()
    projeto = client.table("projects").select("id").eq("id", project_id).execute()
    if not projeto.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "sprint_number": get_current_sprint_number(client, project_id),
        "started_at": None,
    }


@router.post("/ingest/commit", status_code=201)
@limiter.limit(GEMINI_RATE_LIMIT)
async def ingest_commit(request: Request, response: Response, payload: CommitPayload):
    """Mantém o hook atual enquanto projetos Dev migram gradualmente ao GitHub App."""
    client = get_client()
    return await extrair_e_salvar_commit(client, DadosCommit(
        projeto_id=payload.project_id,
        sprint_numero=payload.sprint_number,
        sha=payload.commit_hash,
        mensagem=payload.commit_message,
        autor=payload.author,
        autor_email=payload.author_email,
        autor_login=payload.author_github_login,
        data=payload.date,
        branch=payload.branch,
        diff_stat=payload.diff_stat,
        diff=payload.diff,
    ))
