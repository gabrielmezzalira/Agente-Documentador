"""Router para ingestão de commits GitHub.

POST /ingest/commit  — recebe metadados + diff de um commit e extrai
                       conhecimento estruturado via Gemini.
GET  /projects/{project_id}/current-sprint — retorna a sprint atual do
                       projeto baseada na última ingestion de tipo 'planning'.
"""
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import ConteudoEstruturado, AvaliacaoQualidadeCommit
from services.supabase_client import get_client
from services.sprints import ensure_sprint_row

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

_COMMIT_QUALIDADE_PROMPT = (
    "Voce avalia a qualidade tecnica de uma entrega de codigo a partir do commit e do diff "
    "fornecidos. Pontue de 0 a 10 olhando: complexidade da tarefa resolvida no contexto do "
    "commit, qualidade da documentacao e das mensagens de commit, e aderencia a boas praticas "
    "esperadas (nomes claros, tratamento de erro, testes quando cabivel). "
    "Nunca liste pendencia pra corrigir — devolva so a nota e uma frase curta explicando o "
    "porque, no mesmo espirito de um placar."
)

_TASK_TAG_RE = re.compile(r"\[task:([0-9a-fA-F-]{36})\]")


@router.post("/ingest/commit", status_code=201)
async def ingest_commit(payload: CommitPayload):
    """Recebe metadados de um commit GitHub e registra como ingestion no DocuData."""
    client = get_client()

    # Verifica que projeto existe e busca api_key
    project_resp = client.table("projects").select("gemini_api_key, arquetipo").eq("id", payload.project_id).execute()
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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini extraction failed: {exc}")

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
            })
            .execute()
        )
        if not response.data:
            raise RuntimeError("Insert returned no data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Supabase insert failed: {exc}")

    ingestion_id = response.data[0].get("id")
    print(f"[ingest_commit] commit={payload.commit_hash[:7]} sprint={payload.sprint_number} id={ingestion_id}")

    arquetipo = project_resp.data[0].get("arquetipo") or "padrao"
    if arquetipo == "padrao":
        try:
            task_id = None
            match_task = _TASK_TAG_RE.search(payload.commit_message)
            if match_task:
                task_id = match_task.group(1)

            operacional_id = None
            if payload.author_github_login:
                op_resp = (
                    client.table("operacionais")
                    .select("id")
                    .eq("project_id", payload.project_id)
                    .eq("github_login", payload.author_github_login)
                    .execute()
                )
                if op_resp.data:
                    operacional_id = op_resp.data[0]["id"]
            if operacional_id is None and payload.author_email:
                op_resp = (
                    client.table("operacionais")
                    .select("id")
                    .eq("project_id", payload.project_id)
                    .eq("email", payload.author_email)
                    .execute()
                )
                if op_resp.data:
                    operacional_id = op_resp.data[0]["id"]

            qualidade_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_tokens=512, google_api_key=api_key)
            qualidade_structured = qualidade_llm.with_structured_output(AvaliacaoQualidadeCommit)
            avaliacao: AvaliacaoQualidadeCommit = await qualidade_structured.ainvoke([
                SystemMessage(content=_COMMIT_QUALIDADE_PROMPT),
                HumanMessage(content=user_content),
            ])
            client.table("commit_qualidade").insert({
                "commit_hash": payload.commit_hash,
                "task_id": task_id,
                "operacional_id": operacional_id,
                "projeto_id": payload.project_id,
                "nota": avaliacao.nota,
                "evidencia": avaliacao.evidencia,
            }).execute()
        except Exception as exc:
            print(f"[ingest_commit] Aviso: avaliacao de qualidade de commit falhou ({exc}) — continuando")

    return {
        "status": "ok",
        "ingestion_id": ingestion_id,
        "sprint_number": payload.sprint_number,
    }
