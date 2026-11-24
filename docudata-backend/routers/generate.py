from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from core.rate_limit import GEMINI_RATE_LIMIT, limiter
from graphs.generation_graph import generation_graph, GenerationState
from models.schemas import GenerateRequest, GenerateResponse, ManualDocCreate
from services.acesso import SEM_ACESSO, exigir_acesso, exigir_acesso_por
from services.auth import get_current_pessoa
from services.file_parser import mime_efetivo
from services.supabase_client import get_client
from services.gemini_key import get_gemini_api_key

router = APIRouter(tags=["generate"])

_VALID_DOC_TYPES = {
    "repasse_semanal", "retrospectiva", "log_decisoes", "documentacao_final",
    "ata_reuniao", "onboarding",
    "planning", "daily", "review",
}
_SPRINT_REQUIRED = {"repasse_semanal", "retrospectiva", "review"}
_INGESTION_REQUIRED = {"ata_reuniao", "planning", "daily"}


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit(GEMINI_RATE_LIMIT)
async def generate(
    request: Request, response: Response, req: GenerateRequest,
    pessoa: dict = Depends(get_current_pessoa),
):
    acesso_client = get_client()
    exigir_acesso(acesso_client, pessoa, req.projeto_id)
    if req.ingestion_id:
        projeto_da_ingestao = exigir_acesso_por(acesso_client, pessoa, "ingestion", req.ingestion_id)
        if projeto_da_ingestao != req.projeto_id:
            raise HTTPException(status_code=403, detail=SEM_ACESSO)
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
    project_resp = client.table("projects").select("id, name, client").eq("id", req.projeto_id).execute()
    if not project_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project = project_resp.data[0]

    api_key = get_gemini_api_key()

    state: GenerationState = {
        "projeto_id": req.projeto_id,
        "projeto_nome": project["name"],
        "cliente": project["client"],
        "tipo_doc": req.tipo_doc,
        "sprint_numero": req.sprint_numero,
        "ingestion_id": req.ingestion_id,
        "observacoes": req.observacoes,
        "api_key": api_key,
        "data_atual": datetime.now().strftime("%d/%m/%Y"),
        "ingestions": [],
        "contexto": "",
        "documento": "",
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
async def list_docs(projeto_id: str, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    exigir_acesso(client, pessoa, projeto_id)
    response = (
        client.table("generated_docs")
        .select("*")
        .eq("project_id", projeto_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@router.post("/docs/manual", response_model=GenerateResponse, status_code=201)
async def create_manual_doc(req: ManualDocCreate, pessoa: dict = Depends(get_current_pessoa)):
    """Cria um documento manualmente (markdown digitado pelo gerente), sem chamar o LLM.

    Útil quando o gerente quer registrar um doc final que foi escrito fora do sistema,
    ou quando quer editar/regenerar um doc com texto próprio.
    """
    client = get_client()
    exigir_acesso(client, pessoa, req.projeto_id)
    if not req.content.strip():
        raise HTTPException(status_code=422, detail="content não pode estar vazio")
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
    pessoa: dict = Depends(get_current_pessoa),
):
    """Cria doc manual a partir de PDF — extrai texto via pdfplumber, sem chamar LLM.

    PDFs escaneados (sem camada de texto) são rejeitados; nesse caso o gerente deveria
    usar o upload livre, que tem fallback para vision.
    """
    client = get_client()
    exigir_acesso(client, pessoa, projeto_id)
    mime_arquivo = mime_efetivo(arquivo.filename, arquivo.content_type)
    eh_markdown = mime_arquivo == "text/markdown"
    if mime_arquivo != "application/pdf" and not eh_markdown:
        raise HTTPException(status_code=422, detail="Arquivo deve ser PDF ou Markdown")

    check = client.table("projects").select("id").eq("id", projeto_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    pdf_bytes = await arquivo.read()
    if eh_markdown:
        text = pdf_bytes.decode("utf-8", errors="replace").strip()
        if not text:
            raise HTTPException(status_code=422, detail="Arquivo Markdown vazio")
    else:
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
        })
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create manual doc")
    return response.data[0]


@router.delete("/docs/{doc_id}", status_code=204)
async def delete_doc(doc_id: str, pessoa: dict = Depends(get_current_pessoa)):
    """Delete a single generated document by UUID."""
    client = get_client()
    exigir_acesso_por(client, pessoa, "doc", doc_id)
    client.table("generated_docs").delete().eq("id", doc_id).execute()


class UpdateDocSprint(BaseModel):
    sprint_number: Optional[int] = None
    content: Optional[str] = None


@router.patch("/docs/{doc_id}", response_model=GenerateResponse)
async def update_doc_sprint(doc_id: str, body: UpdateDocSprint, pessoa: dict = Depends(get_current_pessoa)):
    """Move um documento gerado para outra sprint e/ou edita seu conteúdo markdown.

    Só atualiza os campos que vieram no corpo da requisição — `sprint_number`
    explicitamente `null` limpa a sprint (comportamento de mover já existente);
    `content` omitido não mexe no conteúdo.
    """
    updates = body.model_dump(exclude_unset=True)
    if "content" in updates and not (updates["content"] or "").strip():
        raise HTTPException(status_code=422, detail="content não pode estar vazio")
    if not updates:
        raise HTTPException(status_code=422, detail="Nenhum campo para atualizar")

    client = get_client()
    exigir_acesso_por(client, pessoa, "doc", doc_id)
    result = (
        client.table("generated_docs")
        .update(updates)
        .eq("id", doc_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update document")
    return result.data[0]
