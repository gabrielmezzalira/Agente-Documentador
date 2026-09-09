"""Router para ingestão de commits GitHub.

POST /ingest/commit  — recebe metadados + diff de um commit e extrai
                       conhecimento estruturado via Gemini.
GET  /projects/{project_id}/current-sprint — retorna a sprint atual do
                       projeto baseada na última ingestion de tipo 'planning'.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from core.rate_limit import GEMINI_RATE_LIMIT, limiter
from services.commit_extraction import DadosCommit, extrair_e_salvar_commit
from services.supabase_client import get_client
from services.sprints import get_current_sprint_number

router = APIRouter(tags=["commit-ingest"])

class CommitPayload(BaseModel):
    project_id: str
    sprint_number: int
    commit_hash: str
    commit_message: str
    author: str
    date: str
    branch: Optional[str] = None
    diff_stat: Optional[str] = None
    diff: Optional[str] = None


# ─────────────────────────────────────────────
# GET /projects/{project_id}/current-sprint
# ─────────────────────────────────────────────

@router.get("/projects/{project_id}/current-sprint")
async def get_current_sprint(project_id: str):
    """Retorna a sprint atual do projeto baseada na última ingestion de planning
    cujo sprint_number ainda existe na tabela sprints."""
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"sprint_number": get_current_sprint_number(client, project_id), "started_at": None}


# ─────────────────────────────────────────────
# POST /ingest/commit
# ─────────────────────────────────────────────

@router.post("/ingest/commit", status_code=201)
@limiter.limit(GEMINI_RATE_LIMIT)
async def ingest_commit(request: Request, response: Response, payload: CommitPayload):
    """Recebe metadados de um commit GitHub e registra como ingestion no DocuData."""
    client = get_client()

    # O hook legado continua sem colunas de origem até o fim do piloto Dev.
    return await extrair_e_salvar_commit(client, DadosCommit(
        projeto_id=payload.project_id,
        sprint_numero=payload.sprint_number,
        sha=payload.commit_hash,
        mensagem=payload.commit_message,
        autor=payload.author,
        data=payload.date,
        branch=payload.branch,
        diff_stat=payload.diff_stat,
        diff=payload.diff,
    ))
