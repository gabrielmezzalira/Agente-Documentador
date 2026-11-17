"""Frente da task (software, mobile, dados, ia): identificada pela IA em segundo plano."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from services.classificador_regua import texto_da_task
from services.gemini_key import get_gemini_api_key
from services.supabase_client import get_client

_LOG = logging.getLogger("docudata.frente")

FRENTES = ("software", "mobile", "dados", "ia")

_PROMPT_SISTEMA = (
    "Você identifica a frente de trabalho de uma task de projeto do CITi. Escolha exatamente uma:\n"
    "- software: sistema web, API, backend, frontend web, infra e devops.\n"
    "- mobile: app iOS/Android, React Native, Flutter, publicação em loja.\n"
    "- dados: ETL, pipeline, modelagem, dashboard/BI, SQL, análise.\n"
    "- ia: LLM, agentes, machine learning, visão computacional, NLP, prompts.\n"
    'Responda somente no schema {"frente": "<uma das quatro>"}.'
)


class _SaidaFrente(BaseModel):
    frente: str


async def classificar_frente(
    api_key: str,
    *,
    titulo: str,
    descricao: str | None,
    checklist: list[dict] | None,
    projeto_nome: str | None,
    subarea: str | None,
) -> str | None:
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_tokens=64, google_api_key=api_key)
    structured = llm.with_structured_output(_SaidaFrente, method="json_schema")
    mensagem = (
        f"Projeto: {projeto_nome or 'não informado'}\nSubárea: {subarea or 'não informada'}\n\n"
        f"Task:\n{texto_da_task(titulo, descricao, checklist)[:6000]}"
    )
    saida = await structured.ainvoke([SystemMessage(content=_PROMPT_SISTEMA), HumanMessage(content=mensagem)])
    valor = (getattr(saida, "frente", None) or "").strip().lower()
    return valor if valor in FRENTES else None


async def atualizar_frente_da_task(task_id: str) -> None:
    """Agendada em BackgroundTasks: nunca levanta, nunca sobrescreve a escolha do gerente."""
    try:
        client = get_client()
        rows = client.table("tasks").select("*").eq("id", task_id).execute().data
        if not rows:
            return
        task = rows[0]
        if task.get("frente_definida_por") == "gerente":
            return
        proj = client.table("projects").select("name, subarea").eq("id", task["project_id"]).execute().data
        projeto = proj[0] if proj else {}
        frente = await classificar_frente(
            get_gemini_api_key(),
            titulo=task.get("titulo") or "",
            descricao=task.get("descricao"),
            checklist=task.get("checklist"),
            projeto_nome=projeto.get("name"),
            subarea=projeto.get("subarea"),
        )
        if frente is None:
            return
        # A IA leva segundos: o filtro impede de sobrescrever uma frente que o gerente
        # gravou nesse meio tempo. `.neq` sozinho não casa NULL no PostgREST, daí o `or_`.
        (
            client.table("tasks")
            .update({"frente": frente, "frente_definida_por": "ia"})
            .eq("id", task_id)
            .or_("frente_definida_por.is.null,frente_definida_por.neq.gerente")
            .execute()
        )
    except Exception:
        _LOG.warning("falha ao classificar a frente da task %s", task_id, exc_info=True)
