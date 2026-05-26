import os
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import ConteudoEstruturado
from services.supabase_client import get_client


class ExtractionState(TypedDict):
    arquivo_bytes: bytes
    arquivo_nome: str
    mime_type: str
    sprint_numero: int
    projeto_id: str
    gemini_api_key: str
    tipo: str
    texto_preprocessado: str
    conteudo_estruturado: Optional[dict]
    valido: bool
    tentativas: int
    erro: Optional[str]
    input_tokens: int
    output_tokens: int


_COST_PER_INPUT_TOKEN = 0.15 / 1_000_000   # USD — Gemini 2.5 Flash
_COST_PER_OUTPUT_TOKEN = 0.60 / 1_000_000  # USD — Gemini 2.5 Flash


def _make_structured_llm(api_key: str):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=2048,
        google_api_key=api_key,
    )
    return llm.with_structured_output(ConteudoEstruturado, method="json_schema", include_raw=True)

_SYSTEM_PROMPT = (
    "Voce e um assistente especializado em extrair conhecimento estruturado de qualquer artefato "
    "de projeto de dados do CITi: documentos de sprint, atas de reuniao, transcricoes, prints de "
    "backlog, tasks, codigo-fonte, scripts, arquivos de configuracao, ou qualquer outro material "
    "relacionado ao projeto. "
    "Para codigo-fonte: extraia o que o codigo faz (resumo), funcionalidades implementadas "
    "(tarefas), decisoes de arquitetura ou padroes usados (decisoes), TODOs ou problemas "
    "identificados nos comentarios (problemas), e proximos passos visiveis no codigo. "
    "Extraia apenas informacoes explicitamente presentes no conteudo. "
    "Nao infira ou invente informacoes ausentes."
)
_HARDENED_SUFFIX = "\n\nRetorne APENAS JSON valido, sem texto antes ou depois, sem markdown, sem backticks."


def detectar_tipo(state: ExtractionState) -> dict:
    mime = state["mime_type"]
    if (
        mime.startswith("text/")
        or mime == "application/json"
        or mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        tipo = "texto"
    elif mime == "application/pdf":
        tipo = "pdf"
    elif mime in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        tipo = "imagem"
    else:
        tipo = "desconhecido"
    return {"tipo": tipo}


def preprocessar_arquivo(state: ExtractionState) -> dict:
    tipo = state["tipo"]
    arquivo_bytes = state["arquivo_bytes"]
    arquivo_nome = state["arquivo_nome"]

    if tipo == "texto":
        if state["mime_type"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            from services.file_parser import parse_docx
            texto = parse_docx(arquivo_bytes)
        else:
            from services.file_parser import parse_txt
            texto = parse_txt(arquivo_bytes)
        texto = _normalize_text(texto)
        original_len = len(texto)
        texto = texto[:50_000]
        if len(texto) < original_len:
            print(
                f"[preprocessar_arquivo] Truncated '{arquivo_nome}': "
                f"{original_len} -> 50000 chars"
            )
        return {"texto_preprocessado": texto}

    if tipo == "pdf":
        from services.file_parser import parse_pdf
        result = parse_pdf(arquivo_bytes)
        if result["is_scanned"]:
            print(f"[preprocessar_arquivo] Scanned PDF '{arquivo_nome}' — switching to vision")
            return {"texto_preprocessado": f"base64_image:image/png:{result['b64']}"}
        texto = result["text"][:50_000]
        return {"texto_preprocessado": texto}

    if tipo == "imagem":
        from services.file_parser import parse_image
        b64 = parse_image(arquivo_bytes)
        return {"texto_preprocessado": f"base64_image:image/png:{b64}"}

    # Unknown type — signal failure; completeness guardrail will terminate via _roteador
    return {"texto_preprocessado": "", "tentativas": 2, "erro": f"Unsupported file type: {tipo}"}


import re as _re

def _normalize_text(text: str) -> str:
    # Remove trailing whitespace por linha e colapsa 3+ linhas em branco para 2
    lines = [line.rstrip() for line in text.split("\n")]
    return _re.sub(r"\n{3,}", "\n\n", "\n".join(lines))

_EXTRACT_PROMPT = "Extraia as informacoes do seguinte documento de projeto de dados:\n\n"


def _build_human_message(texto_preprocessado: str, suffix: str) -> HumanMessage:
    if texto_preprocessado.startswith("base64_image:"):
        # Format: base64_image:<mime>:<b64data>
        _, image_mime, b64data = texto_preprocessado.split(":", 2)
        return HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime};base64,{b64data}"},
            },
            {
                "type": "text",
                "text": _EXTRACT_PROMPT.rstrip() + suffix,
            },
        ])
    return HumanMessage(content=f"{_EXTRACT_PROMPT}{texto_preprocessado}{suffix}")


async def extrair_conteudo(state: ExtractionState) -> dict:
    tentativas = state["tentativas"]
    suffix = _HARDENED_SUFFIX if tentativas > 0 else ""
    texto = state["texto_preprocessado"]
    is_vision = texto.startswith("base64_image:")
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        _build_human_message(texto, suffix),
    ]
    print(
        f"[extrair_conteudo] Tentativa {tentativas + 1} | "
        f"arquivo: {state['arquivo_nome']} | "
        f"{'[vision]' if is_vision else f'preview: {texto[:200]!r}'}"
    )
    try:
        structured_llm = _make_structured_llm(state["gemini_api_key"])
        raw_result = await structured_llm.ainvoke(messages)
        parsed: ConteudoEstruturado = raw_result["parsed"]
        raw_msg = raw_result["raw"]

        usage = getattr(raw_msg, "usage_metadata", None) or {}
        in_tok = usage.get("input_tokens", 0) or 0
        out_tok = usage.get("output_tokens", 0) or 0

        content = parsed.model_dump()

        # Completeness guardrail — block empty/null extractions before saving
        # tecnologias is optional (not all docs mention a stack), so excluded from the null check
        fields = ["resumo", "tarefas", "decisoes", "problemas", "contexto_cliente", "proximos_passos"]
        all_lists = ["tarefas", "decisoes", "problemas", "proximos_passos", "tecnologias"]
        has_any_content = (
            content.get("resumo", "").strip()
            or content.get("contexto_cliente", "").strip()
            or any(len(content.get(f) or []) > 0 for f in all_lists)
        )
        if any(content.get(f) is None for f in fields) or not has_any_content:
            return {
                "valido": False,
                "tentativas": tentativas + 1,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "erro": "Completeness check failed: required fields are empty or null",
            }

        return {
            "conteudo_estruturado": content,
            "valido": True,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }
    except Exception as exc:
        return {"valido": False, "tentativas": tentativas + 1, "erro": str(exc)}


async def salvar(state: ExtractionState) -> dict:
    client = get_client()
    in_tok = state.get("input_tokens", 0) or 0
    out_tok = state.get("output_tokens", 0) or 0
    cost = in_tok * _COST_PER_INPUT_TOKEN + out_tok * _COST_PER_OUTPUT_TOKEN
    print(f"[salvar] tokens in={in_tok} out={out_tok} cost=${cost:.6f}")
    try:
        response = (
            client.table("ingestions")
            .insert({
                "project_id": state["projeto_id"],
                "sprint_number": state["sprint_numero"],
                "file_name": state["arquivo_nome"],
                "file_type": state["tipo"],
                "extracted_content": state["conteudo_estruturado"],
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "cost_usd": round(cost, 8),
            })
            .execute()
        )
        if not response.data:
            raise RuntimeError("Insert returned no data — row may not have been written")
    except Exception as exc:
        return {"erro": f"Supabase insert failed: {exc}", "valido": False}
    return {}


def _roteador(state: ExtractionState):
    if state["valido"]:
        return "salvar"
    if state["tentativas"] < 2:
        return "extrair_conteudo"
    return END


_builder = StateGraph(ExtractionState)
_builder.add_node("detectar_tipo", detectar_tipo)
_builder.add_node("preprocessar_arquivo", preprocessar_arquivo)
_builder.add_node("extrair_conteudo", extrair_conteudo)
_builder.add_node("salvar", salvar)

_builder.add_edge(START, "detectar_tipo")
_builder.add_edge("detectar_tipo", "preprocessar_arquivo")
_builder.add_edge("preprocessar_arquivo", "extrair_conteudo")
_builder.add_conditional_edges("extrair_conteudo", _roteador)
_builder.add_edge("salvar", END)

extraction_graph = _builder.compile()
