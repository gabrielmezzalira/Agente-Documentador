"""Router para ingestão de revisões diárias de código.

POST /ingest/revisao  — recebe diff acumulado das últimas 24h de um repo
                        e extrai achados estruturados via Gemini.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import RevisaoEstruturada, Achado
from services.supabase_client import get_client

router = APIRouter(tags=["revisao-ingest"])

_PRIORIDADE: dict[str, int] = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2, "BAIXA": 3}

_REVISAO_SYSTEM_PROMPT = (
    "Você é um revisor técnico sênior especializado em projetos de dados do CITi. "
    "A partir do diff acumulado das últimas 24 horas de um repositório, identifique achados relevantes: "
    "bugs potenciais, vulnerabilidades de segurança, dívida técnica significativa, "
    "remoção acidental de testes, credenciais expostas ou lógica incorreta. "
    "\n\nRegras obrigatórias:\n"
    "1. Toda afirmação técnica DEVE ter referencia no formato arquivo:linha (ex: services/auth.py:42). "
    "   Se não há linha confirmada no diff, não inclua o achado.\n"
    "2. Se não há mudança relevante ou o diff está vazio, retorne achados=[] com relatórios "
    "   informando ausência de problemas.\n"
    "3. Não invente achados. Baseie-se estritamente no diff fornecido.\n"
    "4. Severidade: CRITICA (risco de segurança ou perda de dados), ALTA (bug funcional), "
    "   MEDIA (qualidade/manutenibilidade), BAIXA (estilo/convenção).\n"
    "5. Confiança: ALTA (certeza pela evidência no diff), MEDIA (provavelmente um problema), "
    "   BAIXA (suspeita que requer investigação).\n"
    "6. descricao_gerente: linguagem de negócio, sem arquivo:linha, máximo 2 frases.\n"
    "7. descricao_tecnica: descrição precisa com arquivo:linha e contexto do código.\n"
    "8. Limite de achados: máximo 20, priorizando CRITICA > ALTA > MEDIA > BAIXA.\n"
    "Retorne APENAS JSON válido sem markdown, sem backticks, sem texto adicional."
)


class RevisaoPayload(BaseModel):
    project_id: str
    data_revisao: str  # ISO date "YYYY-MM-DD"
    diff_agregado: str
    commits_analisados: int
    diff_chars_total: int
    lista_commits: list[str] = []


@router.post("/ingest/revisao", status_code=201)
async def ingest_revisao(payload: RevisaoPayload):
    """Recebe diff agregado das últimas 24h e registra revisão diária no DocuData."""
    client = get_client()

    project_resp = client.table("projects").select("gemini_api_key").eq("id", payload.project_id).execute()
    if not project_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    api_key = project_resp.data[0].get("gemini_api_key") or ""
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto nao tem uma chave de API do Gemini configurada. Configure-a no dashboard antes de enviar revisões.",
        )

    commits_str = "\n".join(f"- {msg}" for msg in payload.lista_commits) if payload.lista_commits else "(nenhum)"
    user_content = (
        f"Data da revisão: {payload.data_revisao}\n"
        f"Commits analisados: {payload.commits_analisados}\n"
        f"\nMensagens de commit:\n{commits_str}\n"
        f"\nDiff acumulado das últimas 24h:\n{payload.diff_agregado}\n"
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        max_tokens=4096,
        google_api_key=api_key,
    )
    structured_llm = llm.with_structured_output(RevisaoEstruturada, method="json_schema", include_raw=True)

    try:
        raw_result = await structured_llm.ainvoke([
            SystemMessage(content=_REVISAO_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ])
        parsed: RevisaoEstruturada = raw_result["parsed"]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini revision failed: {exc}")

    achados_sorted = sorted(parsed.achados, key=lambda a: _PRIORIDADE.get(a.severidade, 4))
    achados_capped = achados_sorted[:20]

    try:
        response = (
            client.table("revisoes_diarias")
            .insert({
                "project_id": payload.project_id,
                "data_revisao": payload.data_revisao,
                "achados": [a.model_dump() for a in achados_capped],
                "relatorio_gerente": parsed.relatorio_gerente,
                "relatorio_tecnico": parsed.relatorio_tecnico,
                "commits_analisados": payload.commits_analisados,
                "diff_chars_total": payload.diff_chars_total,
            })
            .execute()
        )
        if not response.data:
            raise RuntimeError("Insert returned no data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Supabase insert failed: {exc}")

    revisao_id = response.data[0].get("id")
    return {
        "status": "ok",
        "revisao_id": revisao_id,
        "achados_count": len(achados_capped),
    }
