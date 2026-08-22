import os
import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


class ImportState(TypedDict):
    texto_contrato: str
    projeto_id: str
    gemini_api_key: str
    proposta: Optional[list]
    valido: bool
    tentativas: int
    erro: Optional[str]


_IMPORT_SYSTEM_PROMPT = (
    "Você é um especialista em engenharia de requisitos. "
    "Analise o texto do contrato ou documento de escopo fornecido e extraia as funcionalidades do sistema. "
    "Para cada funcionalidade identificada, gere critérios de aceite no formato EARS: "
    "'Quando [evento/condição], o sistema deve [resposta/comportamento]'. "
    "Retorne um JSON com a chave 'funcionalidades' contendo uma lista de objetos, onde cada objeto tem: "
    "'id_funcional' (string curta como F01, F02, ...), "
    "'titulo' (string descritiva), "
    "'descricao' (string opcional com mais contexto), "
    "'criterios_aceite' (lista de strings no formato EARS), "
    "'prioridade' (uma de: must, should, could, wont — padrão: should)."
)

_HARDENED_SUFFIX = "\n\nRetorne APENAS JSON válido, sem texto antes ou depois, sem markdown, sem backticks."


async def gerar_proposta(state: ImportState) -> dict:
    tentativas = state["tentativas"]
    suffix = _HARDENED_SUFFIX if tentativas > 0 else ""
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            max_tokens=4096,
            google_api_key=state["gemini_api_key"],
        )
        messages = [
            SystemMessage(_IMPORT_SYSTEM_PROMPT),
            HumanMessage(f"Texto do contrato:\n\n{state['texto_contrato']}{suffix}"),
        ]
        response = await llm.ainvoke(messages)

        raw = response.content
        if isinstance(raw, list):
            raw = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw)

        parsed = json.loads(raw.strip())
        funcionalidades = parsed.get("funcionalidades", [])
        if not funcionalidades:
            return {
                "valido": False,
                "tentativas": tentativas + 1,
                "erro": "Lista vazia ou JSON sem chave 'funcionalidades'",
            }
        return {"proposta": funcionalidades, "valido": True}
    except Exception as exc:
        return {"valido": False, "tentativas": tentativas + 1, "erro": str(exc)}


def _roteador(state: ImportState) -> str:
    if state["valido"]:
        return END
    if state["tentativas"] < 2:
        return "gerar_proposta"
    return END


_builder = StateGraph(ImportState)
_builder.add_node("gerar_proposta", gerar_proposta)
_builder.add_edge(START, "gerar_proposta")
_builder.add_conditional_edges("gerar_proposta", _roteador)
import_graph = _builder.compile()
