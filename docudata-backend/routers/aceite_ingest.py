"""Router para ingestão de resultados da suíte de verificação de aceite.

POST /ingest/aceite  — recebe resultado dos 5 gates do CI (GitHub Actions) e
                       atualiza execucoes_aceite com gates e concluido_em.

GET  /execucoes_aceite/{project_id} — lista execuções de aceite do projeto.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from models.schemas import ExecucaoAceitePayload, ExecucaoAceiteResponse
from services.supabase_client import get_client

router = APIRouter(tags=["aceite-ingest"])


@router.post("/ingest/aceite", status_code=200)
async def ingest_aceite(payload: ExecucaoAceitePayload):
    """Recebe resultado dos gates do CI e atualiza execucoes_aceite.

    Lógica de upsert por (funcionalidade_id, commit_sha):
    - Se encontrado: UPDATE gates + concluido_em
    - Se não encontrado: INSERT novo registro com gates e concluido_em
    """
    client = get_client()
    agora = datetime.now(timezone.utc).isoformat()

    # Buscar execução existente pelo par (funcionalidade_id, commit_sha)
    existing = (
        client.table("execucoes_aceite")
        .select("id")
        .eq("funcionalidade_id", payload.funcionalidade_id)
        .eq("commit_sha", payload.commit_sha)
        .execute()
    )

    if existing.data:
        # Atualizar registro existente
        exec_id = existing.data[0]["id"]
        client.table("execucoes_aceite").update({
            "gates": payload.gates,
            "concluido_em": agora,
        }).eq("id", exec_id).execute()
    else:
        # Buscar project_id via funcionalidade_id para inserir novo registro
        func_resp = (
            client.table("funcionalidades")
            .select("project_id")
            .eq("id", payload.funcionalidade_id)
            .execute()
        )
        if not func_resp.data:
            raise HTTPException(
                status_code=404,
                detail=f"Funcionalidade {payload.funcionalidade_id} not found",
            )
        project_id = func_resp.data[0]["project_id"]

        client.table("execucoes_aceite").insert({
            "funcionalidade_id": payload.funcionalidade_id,
            "project_id": project_id,
            "commit_sha": payload.commit_sha,
            "gates": payload.gates,
            "concluido_em": agora,
        }).execute()

    return {"status": "ok", "funcionalidade_id": payload.funcionalidade_id}


@router.get("/execucoes_aceite/{project_id}", response_model=list[ExecucaoAceiteResponse])
async def list_execucoes_aceite(project_id: str):
    """Lista todas as execuções de aceite de um projeto, ordenadas pela mais recente."""
    client = get_client()
    response = (
        client.table("execucoes_aceite")
        .select("*")
        .eq("project_id", project_id)
        .order("disparado_em", desc=True)
        .execute()
    )
    return response.data or []
