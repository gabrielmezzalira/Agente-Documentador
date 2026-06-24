from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from graphs.extraction_graph import extraction_graph, ExtractionState
from models.schemas import IngestResponse
from services.supabase_client import get_client
from services.sprints import ensure_sprint_row

_ACCEPTED_BINARY_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
    "application/json",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}


def _is_accepted(mime: str) -> bool:
    # Qualquer text/* cobre .txt, .py, .js, .ts, .sql, .md, .yaml, .csv, etc.
    return mime.startswith("text/") or mime in _ACCEPTED_BINARY_MIME_TYPES


router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    arquivo: UploadFile = File(...),
    sprint_numero: int = Form(...),
    projeto_id: str = Form(...),
):
    if not _is_accepted(arquivo.content_type):
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported file type. "
                "Accepted: .txt, .docx, .pdf, .png, .jpg, .jpeg, .webp, "
                ".py, .js, .ts, .sql, .md, .yaml, .json, and other text files"
            ),
        )

    db = get_client()
    project_resp = db.table("projects").select("gemini_api_key").eq("id", projeto_id).execute()
    if not project_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    api_key = project_resp.data[0].get("gemini_api_key") or ""
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto não tem uma chave de API do Gemini configurada. Configure-a no dashboard antes de enviar arquivos.",
        )

    ensure_sprint_row(db, projeto_id, sprint_numero)

    file_bytes = await arquivo.read()
    state: ExtractionState = {
        "arquivo_bytes": file_bytes,
        "arquivo_nome": arquivo.filename,
        "mime_type": arquivo.content_type,
        "sprint_numero": sprint_numero,
        "projeto_id": projeto_id,
        "gemini_api_key": api_key,
        "tipo": "",
        "texto_preprocessado": "",
        "conteudo_estruturado": None,
        "valido": False,
        "tentativas": 0,
        "erro": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "ingestion_id": None,
    }
    result = await extraction_graph.ainvoke(state)

    if not result.get("valido"):
        raise HTTPException(
            status_code=502,
            detail=result.get("erro") or "Extraction failed",
        )

    return IngestResponse(
        status="ok",
        sprint=sprint_numero,
        tentativas=result.get("tentativas", 0),
    )
