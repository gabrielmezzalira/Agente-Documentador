"""Router para ingestão de commits GitHub.

POST /ingest/commit  — recebe metadados + diff de um commit e extrai
                       conhecimento estruturado via Gemini.
GET  /projects/{project_id}/current-sprint — retorna a sprint atual do
                       projeto baseada na última ingestion de tipo 'planning'.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import ConteudoEstruturado
from services.supabase_client import get_client
from services.sprints import ensure_sprint_row

router = APIRouter(tags=["commit-ingest"])

_COST_PER_INPUT_TOKEN = 0.30 / 1_000_000   # USD — Gemini 3.5 Flash-Lite
_COST_PER_OUTPUT_TOKEN = 2.50 / 1_000_000  # USD — Gemini 3.5 Flash-Lite


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

    # Sprints que ainda existem para este projeto
    sprints_resp = (
        client.table("sprints")
        .select("numero")
        .eq("project_id", project_id)
        .execute()
    )
    existing_sprint_numbers = {row["numero"] for row in (sprints_resp.data or [])}

    if not existing_sprint_numbers:
        return {"sprint_number": 1, "started_at": None}

    # Última planning em uma sprint que ainda existe
    plannings = (
        client.table("ingestions")
        .select("sprint_number, created_at")
        .eq("project_id", project_id)
        .eq("tipo_documentacao", "planning")
        .order("created_at", desc=True)
        .execute()
    )
    for row in (plannings.data or []):
        if row["sprint_number"] in existing_sprint_numbers:
            return {"sprint_number": row["sprint_number"], "started_at": row["created_at"]}

    # Fallback: maior sprint existente
    return {"sprint_number": max(existing_sprint_numbers), "started_at": None}


# ─────────────────────────────────────────────
# POST /ingest/commit
# ─────────────────────────────────────────────

_COMMIT_SYSTEM_PROMPT = (
    "Voce e um assistente especializado em extrair conhecimento estruturado de commits de codigo "
    "de projetos de dados do CITi. A partir dos metadados e do diff fornecidos, extraia: "
    "resumo do que foi feito, tarefas implementadas, decisoes tecnicas tomadas, problemas ou "
    "bugs corrigidos, contexto do cliente (se mencionado), proximos passos visiveis no diff, "
    "e tecnologias utilizadas. "
    "Extraia apenas informacoes explicitamente presentes no conteudo. "
    "Nao infira ou invente informacoes ausentes. "
    "Para o campo tecnologias_removidas: inclua SOMENTE tecnologias que foram explicitamente "
    "deletadas neste commit — por exemplo, pacote removido de requirements.txt ou package.json, "
    "diretorio inteiro excluido, ou imports completamente removidos de todos os arquivos do projeto. "
    "Nao inclua tecnologia apenas por nao ser mencionada no commit. "
    "Se nao houver remocao explicita e completa, deixe tecnologias_removidas como lista vazia."
)


@router.post("/ingest/commit", status_code=201)
async def ingest_commit(payload: CommitPayload):
    """Recebe metadados de um commit GitHub e registra como ingestion no DocuData."""
    client = get_client()

    # Verifica que projeto existe e busca api_key
    project_resp = client.table("projects").select("gemini_api_key").eq("id", payload.project_id).execute()
    if not project_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    api_key = project_resp.data[0].get("gemini_api_key") or ""
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto nao tem uma chave de API do Gemini configurada. Configure-a no dashboard antes de enviar commits.",
        )

    ensure_sprint_row(client, payload.project_id, payload.sprint_number)

    # Monta prompt com metadados do commit + diff
    user_content = (
        f"Commit: {payload.commit_hash}\n"
        f"Mensagem: {payload.commit_message}\n"
        f"Autor: {payload.author}\n"
        f"Data: {payload.date}\n"
    )
    if payload.diff_stat:
        user_content += f"\nEstatisticas do diff:\n{payload.diff_stat}\n"
    user_content += f"\nDiff das mudancas (arquivos modificados):\n{payload.diff or 'nao informado'}\n"

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        max_tokens=2048,
        google_api_key=api_key,
    )
    structured_llm = llm.with_structured_output(ConteudoEstruturado, method="json_schema", include_raw=True)

    messages = [
        SystemMessage(content=_COMMIT_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    try:
        raw_result = await structured_llm.ainvoke(messages)
        parsed: ConteudoEstruturado = raw_result["parsed"]
        raw_msg = raw_result["raw"]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini extraction failed: {exc}")

    usage = getattr(raw_msg, "usage_metadata", None) or {}
    in_tok = usage.get("input_tokens", 0) or 0
    out_tok = usage.get("output_tokens", 0) or 0
    cost = in_tok * _COST_PER_INPUT_TOKEN + out_tok * _COST_PER_OUTPUT_TOKEN

    content = parsed.model_dump()
    content["_meta_autor"] = payload.author
    content["_meta_data_commit"] = payload.date
    content["_meta_commit_msg"] = payload.commit_message
    if payload.branch:
        content["_meta_branch"] = payload.branch

    # Salva ingestion com tipo_documentacao='commit'
    try:
        response = (
            client.table("ingestions")
            .insert({
                "project_id": payload.project_id,
                "sprint_number": payload.sprint_number,
                "file_name": f"commit:{payload.commit_hash[:7]}",
                "file_type": "commit",
                "tipo_documentacao": "commit",
                "extracted_content": content,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "cost_usd": round(cost, 8),
            })
            .execute()
        )
        if not response.data:
            raise RuntimeError("Insert returned no data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Supabase insert failed: {exc}")

    ingestion_id = response.data[0].get("id")
    print(
        f"[ingest_commit] commit={payload.commit_hash[:7]} "
        f"sprint={payload.sprint_number} "
        f"tokens in={in_tok} out={out_tok} cost=${cost:.6f} "
        f"id={ingestion_id}"
    )

    return {
        "status": "ok",
        "ingestion_id": ingestion_id,
        "sprint_number": payload.sprint_number,
    }
