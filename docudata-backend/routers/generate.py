from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, File, HTTPException, UploadFile

from graphs.generation_graph import generation_graph, GenerationState
from models.schemas import GenerateRequest, GenerateResponse, ManualDocCreate
from services.supabase_client import get_client

router = APIRouter(tags=["generate"])

_VALID_DOC_TYPES = {
    "repasse_semanal", "retrospectiva", "log_decisoes", "documentacao_final",
    "ata_reuniao", "onboarding",
    "planning", "daily", "review",
}
_SPRINT_REQUIRED = {"repasse_semanal", "retrospectiva", "review"}
_INGESTION_REQUIRED = {"ata_reuniao", "planning", "daily"}


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
        "data_atual": datetime.now().strftime("%d/%m/%Y"),
        "ingestions": [],
        "contexto": "",
        "documento": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "erro_contexto": None,
    }

    result = await generation_graph.ainvoke(state)
    if result.get("erro_contexto"):
        raise HTTPException(status_code=422, detail=result["erro_contexto"])

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


@router.post("/docs/manual", response_model=GenerateResponse, status_code=201)
async def create_manual_doc(req: ManualDocCreate):
    """Cria um documento manualmente (markdown digitado pelo gerente), sem chamar o LLM.

    Útil quando o gerente quer registrar um doc final que foi escrito fora do sistema,
    ou quando quer editar/regenerar um doc com texto próprio.
    """
    if not req.content.strip():
        raise HTTPException(status_code=422, detail="content não pode estar vazio")
    client = get_client()
    check = client.table("projects").select("id").eq("id", req.projeto_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    response = (
        client.table("generated_docs")
        .insert({
            "project_id": req.projeto_id,
            "doc_type": req.doc_type,
            "sprint_number": req.sprint_numero,
            "content": req.content,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0,
        })
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create manual doc")
    return response.data[0]


@router.post("/docs/manual/upload", response_model=GenerateResponse, status_code=201)
async def create_manual_doc_from_pdf(
    projeto_id: str = Form(...),
    doc_type: str = Form(...),
    sprint_numero: Optional[int] = Form(None),
    arquivo: UploadFile = File(...),
):
    """Cria doc manual a partir de PDF — extrai texto via pdfplumber, sem chamar LLM.

    PDFs escaneados (sem camada de texto) são rejeitados; nesse caso o gerente deveria
    usar o upload livre, que tem fallback para vision.
    """
    if arquivo.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="Arquivo deve ser PDF")

    client = get_client()
    check = client.table("projects").select("id").eq("id", projeto_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    pdf_bytes = await arquivo.read()
    from services.file_parser import parse_pdf
    parsed = parse_pdf(pdf_bytes)
    if parsed["is_scanned"]:
        raise HTTPException(
            status_code=422,
            detail="PDF parece escaneado (sem camada de texto). Use o upload livre para PDFs escaneados.",
        )
    text = parsed["text"].strip()
    if not text:
        raise HTTPException(status_code=422, detail="PDF não contém texto extraível")

    response = (
        client.table("generated_docs")
        .insert({
            "project_id": projeto_id,
            "doc_type": doc_type,
            "sprint_number": sprint_numero,
            "content": text,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0,
        })
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create manual doc")
    return response.data[0]


@router.delete("/docs/{doc_id}", status_code=204)
async def delete_doc(doc_id: str):
    """Delete a single generated document by UUID."""
    client = get_client()
    response = client.table("generated_docs").select("id").eq("id", doc_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Document not found")
    client.table("generated_docs").delete().eq("id", doc_id).execute()
