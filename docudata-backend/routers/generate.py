from fastapi import APIRouter, HTTPException

from graphs.generation_graph import generation_graph, GenerationState
from models.schemas import GenerateRequest, GenerateResponse
from services.supabase_client import get_client

router = APIRouter(tags=["generate"])

_VALID_DOC_TYPES = {"sprint_status", "sprint_retro", "decisoes", "completo", "ata_reuniao", "onboarding"}
_SPRINT_REQUIRED = {"sprint_status", "sprint_retro"}
_INGESTION_REQUIRED = {"ata_reuniao"}


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    if req.tipo_doc not in _VALID_DOC_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tipo_doc. Accepted: {', '.join(sorted(_VALID_DOC_TYPES))}",
        )
    if req.tipo_doc in _SPRINT_REQUIRED and req.sprint_numero is None:
        raise HTTPException(
            status_code=422,
            detail=f"sprint_numero is required for tipo_doc='{req.tipo_doc}'",
        )
    if req.tipo_doc in _INGESTION_REQUIRED and not req.ingestion_id:
        raise HTTPException(
            status_code=422,
            detail=f"ingestion_id is required for tipo_doc='{req.tipo_doc}'",
        )

    client = get_client()
    project_resp = client.table("projects").select("*").eq("id", req.projeto_id).execute()
    if not project_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project = project_resp.data[0]

    api_key = project.get("gemini_api_key") or ""
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto não tem uma chave de API do Gemini configurada. Configure-a no dashboard antes de gerar documentos.",
        )

    state: GenerationState = {
        "projeto_id": req.projeto_id,
        "projeto_nome": project["name"],
        "cliente": project["client"],
        "tipo_doc": req.tipo_doc,
        "sprint_numero": req.sprint_numero,
        "ingestion_id": req.ingestion_id,
        "observacoes": req.observacoes,
        "gemini_api_key": api_key,
        "ingestions": [],
        "contexto": "",
        "documento": "",
        "input_tokens": 0,
        "output_tokens": 0,
    }

    await generation_graph.ainvoke(state)

    doc_resp = (
        client.table("generated_docs")
        .select("*")
        .eq("project_id", req.projeto_id)
        .eq("doc_type", req.tipo_doc)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not doc_resp.data:
        raise HTTPException(status_code=502, detail="Document generation failed")

    return doc_resp.data[0]


@router.get("/docs/{projeto_id}", response_model=list[GenerateResponse])
async def list_docs(projeto_id: str):
    client = get_client()
    response = (
        client.table("generated_docs")
        .select("*")
        .eq("project_id", projeto_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@router.delete("/docs/{doc_id}", status_code=204)
async def delete_doc(doc_id: str):
    """Delete a single generated document by UUID."""
    client = get_client()
    response = client.table("generated_docs").select("id").eq("id", doc_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Document not found")
    client.table("generated_docs").delete().eq("id", doc_id).execute()
