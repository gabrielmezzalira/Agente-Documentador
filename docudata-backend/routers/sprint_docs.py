"""Endpoints híbridos para Planning / Daily / Review.

Cada endpoint recebe campos estruturados (do modal) + PDF opcional, monta um
`extracted_content` consolidado, cria UM registro em `ingestions` (com
`tipo_documentacao` setado), dispara o `generation_graph` no novo `tipo_doc`
correspondente e retorna ingestion_id + doc_id.

Decisão arquitetural: a ingestão recebida pelo modal **NÃO** passa por extração
LLM quando só vêm os campos estruturados (já estão estruturados — chamar Gemini
seria desperdício e fonte de alucinação). Se houver PDF anexo, ele passa pelo
`extraction_graph` separadamente e os campos extraídos são mesclados.
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, File, UploadFile, HTTPException

from graphs.extraction_graph import extraction_graph, ExtractionState
from graphs.generation_graph import generation_graph, GenerationState
from models.schemas import SprintDocResponse
from services.supabase_client import get_client
from services.sprints import ensure_sprint_row

router = APIRouter(prefix="/sprint-docs", tags=["sprint-docs"])

_PDF_MIME = "application/pdf"
_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
_ACCEPTED_ANEXO_MIMES = {_PDF_MIME} | _IMAGE_MIMES


async def _extract_anexo_to_content(
    project_id: str,
    sprint_numero: int,
    api_key: str,
    anexo: UploadFile,
) -> dict:
    """Roda o extraction_graph no anexo (PDF ou imagem) e devolve o `extracted_content`.

    Para planning, o anexo pode ser um print de kanban (PNG/JPG) com tarefas do backlog —
    a vision do Gemini identifica e extrai os itens automaticamente.

    Cuidado: o graph atual cria um registro em `ingestions` ao final. Para evitar
    duplicação, deletamos esse registro intermediário e retornamos apenas o conteúdo.
    """
    if anexo.content_type not in _ACCEPTED_ANEXO_MIMES:
        raise HTTPException(
            status_code=422,
            detail=f"Anexo deve ser PDF ou imagem (PNG/JPG/WEBP). Recebido: {anexo.content_type}",
        )

    file_bytes = await anexo.read()
    state: ExtractionState = {
        "arquivo_bytes": file_bytes,
        "arquivo_nome": anexo.filename or "anexo.pdf",
        "mime_type": anexo.content_type,
        "sprint_numero": sprint_numero,
        "projeto_id": project_id,
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
            detail=f"Extração do PDF anexo falhou: {result.get('erro') or 'erro desconhecido'}",
        )

    # Remove o registro intermediário criado pelo graph — vamos inserir um único
    # registro consolidado com tipo_documentacao setado.
    intermediate_id = result.get("ingestion_id")
    if intermediate_id:
        client = get_client()
        client.table("ingestions").delete().eq("id", intermediate_id).execute()

    return result.get("conteudo_estruturado") or {}


def _merge_content(base: dict, extra: dict) -> dict:
    """Mescla content do PDF dentro do content base do form.

    - Strings: concatena com separador.
    - Listas: une preservando ordem (form primeiro, anexo depois) sem duplicar.
    """
    if not extra:
        return base
    merged = dict(base)

    for key in ("resumo", "contexto_cliente"):
        anexo_val = (extra.get(key) or "").strip()
        if anexo_val and anexo_val not in merged.get(key, ""):
            existing = merged.get(key, "").strip()
            merged[key] = (existing + ("\n\n" if existing else "") + anexo_val)

    for key in ("tarefas", "decisoes", "problemas", "proximos_passos", "tecnologias"):
        base_list = merged.get(key) or []
        extra_list = extra.get(key) or []
        seen = {item.lower() for item in base_list if isinstance(item, str)}
        for item in extra_list:
            if isinstance(item, str) and item.lower() not in seen:
                base_list.append(item)
                seen.add(item.lower())
        merged[key] = base_list

    return merged


def _project_or_404(project_id: str) -> tuple[dict, str]:
    """Carrega projeto e retorna (project_dict, api_key). Levanta 404/422 se inválido."""
    client = get_client()
    resp = client.table("projects").select("*").eq("id", project_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project = resp.data[0]
    api_key = project.get("gemini_api_key") or ""
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto não tem uma chave de API do Gemini configurada.",
        )
    return project, api_key


async def _run_generation(
    project: dict,
    tipo_doc: str,
    sprint_numero: int,
    ingestion_id: Optional[str],
    api_key: str,
) -> dict:
    """Dispara o generation_graph e devolve o registro de generated_docs salvo."""
    state: GenerationState = {
        "projeto_id": project["id"],
        "projeto_nome": project["name"],
        "cliente": project["client"],
        "tipo_doc": tipo_doc,
        "sprint_numero": sprint_numero,
        "ingestion_id": ingestion_id,
        "observacoes": None,
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

    client = get_client()
    doc_resp = (
        client.table("generated_docs")
        .select("*")
        .eq("project_id", project["id"])
        .eq("doc_type", tipo_doc)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not doc_resp.data:
        raise HTTPException(status_code=502, detail="Document generation failed")
    return doc_resp.data[0]


def _insert_ingestion(
    project_id: str,
    sprint_numero: int,
    file_name: str,
    tipo_documentacao: str,
    extracted_content: dict,
) -> dict:
    client = get_client()
    response = (
        client.table("ingestions")
        .insert({
            "project_id": project_id,
            "sprint_number": sprint_numero,
            "file_name": file_name,
            "file_type": "texto",
            "tipo_documentacao": tipo_documentacao,
            "extracted_content": extracted_content,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0,
        })
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to insert ingestion")
    return response.data[0]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/planning", response_model=SprintDocResponse, status_code=201)
async def submit_planning(
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    descricao: str = Form(...),
    itens_backlog: str = Form("[]"),  # JSON array de strings
    anexo: Optional[UploadFile] = File(None),
):
    """Submete o Planning de uma sprint. Cria ingestion + dispara geração do doc."""
    project, api_key = _project_or_404(projeto_id)
    try:
        backlog = json.loads(itens_backlog)
        if not isinstance(backlog, list):
            raise ValueError("itens_backlog deve ser JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"itens_backlog inválido: {exc}")

    ensure_sprint_row(get_client(), projeto_id, sprint_numero)

    base_content = {
        "resumo": descricao,
        "tarefas": [str(item) for item in backlog],
        "decisoes": [],
        "problemas": [],
        "contexto_cliente": "",
        "proximos_passos": [str(item) for item in backlog],
        "tecnologias": [],
    }

    if anexo is not None:
        extra = await _extract_anexo_to_content(projeto_id, sprint_numero, api_key, anexo)
        base_content = _merge_content(base_content, extra)

    ingestion = _insert_ingestion(
        project_id=projeto_id,
        sprint_numero=sprint_numero,
        file_name=f"planning-sprint-{sprint_numero}",
        tipo_documentacao="planning",
        extracted_content=base_content,
    )

    doc = await _run_generation(
        project=project,
        tipo_doc="planning",
        sprint_numero=sprint_numero,
        ingestion_id=ingestion["id"],
        api_key=api_key,
    )

    return SprintDocResponse(
        ingestion_id=ingestion["id"],
        doc_id=doc["id"],
        doc_type="planning",
        sprint_number=sprint_numero,
        content=doc["content"],
        created_at=doc["created_at"],
    )


@router.post("/daily", response_model=SprintDocResponse, status_code=201)
async def submit_daily(
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    data: str = Form(...),                     # ISO date (YYYY-MM-DD)
    feito: str = Form(...),
    proximo: str = Form(...),
    impedimentos: Optional[str] = Form(None),
    anexo: Optional[UploadFile] = File(None),
):
    """Submete uma Daily. Cria ingestion + dispara geração do doc."""
    project, api_key = _project_or_404(projeto_id)
    ensure_sprint_row(get_client(), projeto_id, sprint_numero)

    impedimentos_clean = (impedimentos or "").strip()

    resumo = (
        f"Daily {data} — "
        f"Feito: {feito.strip()} | "
        f"Próximo: {proximo.strip()}"
    )
    if impedimentos_clean:
        resumo += f" | Impedimentos: {impedimentos_clean}"

    base_content = {
        "resumo": resumo,
        "tarefas": [feito.strip()] if feito.strip() else [],
        "decisoes": [],
        "problemas": [impedimentos_clean] if impedimentos_clean else [],
        "contexto_cliente": "",
        "proximos_passos": [proximo.strip()] if proximo.strip() else [],
        "tecnologias": [],
        "campos_daily": {
            "data": data,
            "feito": feito,
            "proximo": proximo,
            "impedimentos": impedimentos_clean,
        },
    }

    if anexo is not None:
        extra = await _extract_anexo_to_content(projeto_id, sprint_numero, api_key, anexo)
        base_content = _merge_content(base_content, extra)

    ingestion = _insert_ingestion(
        project_id=projeto_id,
        sprint_numero=sprint_numero,
        file_name=f"daily-{data}",
        tipo_documentacao="daily",
        extracted_content=base_content,
    )

    doc = await _run_generation(
        project=project,
        tipo_doc="daily",
        sprint_numero=sprint_numero,
        ingestion_id=ingestion["id"],
        api_key=api_key,
    )

    return SprintDocResponse(
        ingestion_id=ingestion["id"],
        doc_id=doc["id"],
        doc_type="daily",
        sprint_number=sprint_numero,
        content=doc["content"],
        created_at=doc["created_at"],
    )


@router.post("/ata", response_model=SprintDocResponse, status_code=201)
async def submit_ata_with_upload(
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    anexo: UploadFile = File(...),
):
    """Gera Ata de Reunião a partir de uma transcrição em PDF (upload + extração + geração em uma chamada).

    Diferente de planning/daily/review (que recebem campos estruturados), a ata depende
    SEMPRE de uma transcrição — o PDF é obrigatório. A ingestão resultante fica com
    tipo_documentacao=NULL (é um insumo livre, não conta como mínimo obrigatório).
    """
    project, api_key = _project_or_404(projeto_id)
    ensure_sprint_row(get_client(), projeto_id, sprint_numero)

    if anexo.content_type != _PDF_MIME:
        raise HTTPException(
            status_code=422,
            detail=f"Transcrição da ata deve ser PDF. Recebido: {anexo.content_type}",
        )

    # Roda extraction_graph — ele já cria a ingestion intermediária
    file_bytes = await anexo.read()
    state: ExtractionState = {
        "arquivo_bytes": file_bytes,
        "arquivo_nome": anexo.filename or "transcricao.pdf",
        "mime_type": anexo.content_type,
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
            detail=f"Extração da transcrição falhou: {result.get('erro') or 'erro desconhecido'}",
        )

    ingestion_id = result.get("ingestion_id")
    if not ingestion_id:
        raise HTTPException(status_code=500, detail="Ingestão da transcrição não retornou ID")

    doc = await _run_generation(
        project=project,
        tipo_doc="ata_reuniao",
        sprint_numero=sprint_numero,
        ingestion_id=ingestion_id,
        api_key=api_key,
    )
    return SprintDocResponse(
        ingestion_id=ingestion_id,
        doc_id=doc["id"],
        doc_type="ata_reuniao",
        sprint_number=sprint_numero,
        content=doc["content"],
        created_at=doc["created_at"],
    )


@router.post("/review", response_model=SprintDocResponse, status_code=201)
async def submit_review(
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    observacoes: Optional[str] = Form(None),
    anexo: Optional[UploadFile] = File(None),
):
    """Submete a Review de uma sprint. Cria ingestion + dispara geração do doc.

    A review se baseia no planning + dailys + ingestões livres da sprint para
    computar o delta (planejado vs realizado). Observações do gerente são
    anexadas como contexto adicional.
    """
    project, api_key = _project_or_404(projeto_id)
    ensure_sprint_row(get_client(), projeto_id, sprint_numero)

    observacoes_clean = (observacoes or "").strip()

    base_content = {
        "resumo": observacoes_clean or f"Review da Sprint {sprint_numero}",
        "tarefas": [],
        "decisoes": [],
        "problemas": [],
        "contexto_cliente": "",
        "proximos_passos": [],
        "tecnologias": [],
    }

    if anexo is not None:
        extra = await _extract_anexo_to_content(projeto_id, sprint_numero, api_key, anexo)
        base_content = _merge_content(base_content, extra)

    ingestion = _insert_ingestion(
        project_id=projeto_id,
        sprint_numero=sprint_numero,
        file_name=f"review-sprint-{sprint_numero}",
        tipo_documentacao="review",
        extracted_content=base_content,
    )

    # Para review, o generation_graph busca TODAS ingestões da sprint (não só esta)
    # para computar o delta — ingestion_id não é usado nesse caminho
    doc = await _run_generation(
        project=project,
        tipo_doc="review",
        sprint_numero=sprint_numero,
        ingestion_id=None,
        api_key=api_key,
    )

    return SprintDocResponse(
        ingestion_id=ingestion["id"],
        doc_id=doc["id"],
        doc_type="review",
        sprint_number=sprint_numero,
        content=doc["content"],
        created_at=doc["created_at"],
    )
