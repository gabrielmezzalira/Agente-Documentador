import os
import json
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
    ingestion_id: Optional[str]
    # Validation fields — set by router before invoke
    tipo_esperado: Optional[str]
    force: Optional[bool]
    projeto_nome: Optional[str]
    cliente: Optional[str]
    projeto_descricao: Optional[str]
    # Validation outputs — written by validar_tipo node
    tipo_detectado: Optional[str]
    mensagem_validacao: Optional[str]
    valido_tipo: Optional[bool]


_COST_PER_INPUT_TOKEN = 0.30 / 1_000_000   # USD — Gemini 3.5 Flash-Lite
_COST_PER_OUTPUT_TOKEN = 2.50 / 1_000_000  # USD — Gemini 3.5 Flash-Lite


def _make_structured_llm(api_key: str):
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        max_tokens=2048,
        google_api_key=api_key,
    )
    return llm.with_structured_output(ConteudoEstruturado, method="json_schema", include_raw=True)

_SYSTEM_PROMPT = (
    "Voce e um assistente especializado em extrair conhecimento estruturado de qualquer artefato "
    "de projeto de dados do CITi: documentos de sprint, atas de reuniao, transcricoes, prints de "
    "backlog, tasks, codigo-fonte, scripts, arquivos de configuracao, ou qualquer outro material "
    "relacionado ao projeto. "
    "Para prints de kanban, backlog ou lista de tarefas: extraia cada tarefa no campo 'tarefas' "
    "no formato 'nome da tarefa — Responsavel: [nome se visivel] — Prazo: [prazo se visivel] — DoD: [criterio se visivel]'. "
    "Extraia riscos/bloqueios visiveis no campo 'problemas' no formato 'risco — Consequencia: [consequencia se visivel]'. "
    "Se algum campo nao estiver visivel, omita essa parte (nao invente). "
    "Para codigo-fonte: extraia o que o codigo faz (resumo), funcionalidades implementadas "
    "(tarefas), decisoes de arquitetura ou padroes usados (decisoes), TODOs ou problemas "
    "identificados nos comentarios (problemas), e proximos passos visiveis no codigo. "
    "Extraia apenas informacoes explicitamente presentes no conteudo. "
    "Nao infira ou invente informacoes ausentes."
)
_HARDENED_SUFFIX = "\n\nRetorne APENAS JSON valido, sem texto antes ou depois, sem markdown, sem backticks."

_VALIDATION_SYSTEM_PROMPT = (
    "Voce e um classificador de documentos para um sistema de gestao de projetos de dados do CITi. "
    "Seu trabalho e identificar o tipo de documento enviado por gerentes de projeto de dados. "
    "O projeto se chama '{projeto_nome}', o cliente e '{cliente}' e a descricao do projeto e: '{projeto_descricao}'. "
    "\n\n"
    "Classifique o documento em uma das seguintes 8 categorias:\n"
    "- planning: backlog da sprint, lista de tarefas, registro de riscos, definicao de escopo para proxima sprint\n"
    "- daily: atualizacao de standup (feito / fazendo / impedimentos), nota breve de status\n"
    "- review: review da sprint, relatorio de entrega, satisfacao do cliente, tabela planejado vs entregue\n"
    "- retrospectiva: retrospectiva, o que funcionou / nao funcionou, acoes de melhoria\n"
    "- ata_reuniao: ata de reuniao, transcricao de reuniao, agenda com notas\n"
    "- commit: diff de git, mudanca de codigo, mensagem de commit com alteracoes tecnicas\n"
    "- upload_livre: qualquer outro documento relacionado ao projeto que nao se encaixa nas categorias acima\n"
    "- nao_relacionado: material claramente nao relacionado a gestao de projetos: aula academica, documento pessoal, conteudo aleatorio\n"
    "\n"
    "Retorne um JSON com os campos:\n"
    "- tipo_detectado: string (uma das 8 categorias acima)\n"
    "- nao_bloquear: boolean (true quando ha incerteza sobre a classificacao)\n"
    "- explicacao: string (uma frase em portugues explicando a classificacao)\n"
    "\n"
    "IMPORTANTE: Em caso de duvida ou conteudo ambiguo, retorne nao_bloquear: true — "
    "nunca bloqueie quando nao tiver alta confianca de que o conteudo e incompativel. "
    "Retorne APENAS o JSON, sem texto antes ou depois, sem markdown, sem backticks."
)

_CATEGORY_LABELS = {
    "planning": "Planning",
    "daily": "Daily",
    "review": "Review",
    "retrospectiva": "Retrospectiva",
    "ata_reuniao": "Ata de Reuniao",
    "commit": "Commit",
    "upload_livre": "Upload Livre",
    "nao_relacionado": "Conteudo Nao Relacionado",
}


async def validar_tipo(state: ExtractionState) -> dict:
    tipo_esperado = state.get("tipo_esperado") or "upload_livre"
    force = state.get("force") or False
    projeto_nome = state.get("projeto_nome") or ""
    cliente = state.get("cliente") or ""
    projeto_descricao = state.get("projeto_descricao") or ""
    gemini_api_key = state.get("gemini_api_key") or ""
    arquivo_nome = state.get("arquivo_nome") or ""
    arquivo_bytes = state.get("arquivo_bytes") or b""
    mime_type = state.get("mime_type") or ""

    # Build a short preview from arquivo_bytes (preprocessar_arquivo has not run yet)
    try:
        preview = arquivo_bytes[:3000].decode("utf-8", errors="replace")
    except Exception:
        preview = f"[binary content — mime: {mime_type}]"

    if force:
        return {
            "tipo_detectado": "",
            "mensagem_validacao": "Override forcado pelo gerente",
            "valido_tipo": True,
        }

    tipo_detectado = "upload_livre"
    nao_bloquear = True
    explicacao = ""

    try:
        system_prompt = _VALIDATION_SYSTEM_PROMPT.format(
            projeto_nome=projeto_nome,
            cliente=cliente,
            projeto_descricao=projeto_descricao,
        )
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            max_tokens=256,
            google_api_key=gemini_api_key,
        )
        human_content = (
            f"Arquivo: {arquivo_nome}\n"
            f"Tipo MIME: {mime_type}\n\n"
            f"Conteudo (primeiros 3000 caracteres):\n{preview}"
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content),
        ]
        print(f"[validar_tipo] Classificando '{arquivo_nome}' | tipo_esperado={tipo_esperado}")
        response = await llm.ainvoke(messages)
        response_text = response.content.strip()
        # Strip markdown fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()
        parsed = json.loads(response_text)
        tipo_detectado = parsed.get("tipo_detectado", "upload_livre")
        nao_bloquear = parsed.get("nao_bloquear", True)
        explicacao = parsed.get("explicacao", "")
    except Exception as exc:
        # Safe fallback: never block on parse or API error
        print(f"[validar_tipo] Error during classification — defaulting to nao_bloquear=True: {exc}")
        nao_bloquear = True

    # Apply blocking logic
    if nao_bloquear:
        return {
            "tipo_detectado": tipo_detectado,
            "mensagem_validacao": explicacao,
            "valido_tipo": True,
        }

    if tipo_esperado == "upload_livre":
        # Upload livre: only block nao_relacionado
        if tipo_detectado == "nao_relacionado":
            msg = (
                f"Conteudo parece ser {explicacao} — "
                "o sistema aceita documentos de projeto (atas, plannings, reviews, etc.)."
            )
            return {
                "tipo_detectado": tipo_detectado,
                "mensagem_validacao": msg,
                "valido_tipo": False,
            }
        return {
            "tipo_detectado": tipo_detectado,
            "mensagem_validacao": explicacao,
            "valido_tipo": True,
        }

    # Specific type expected
    if tipo_detectado == tipo_esperado or tipo_detectado == "upload_livre":
        return {
            "tipo_detectado": tipo_detectado,
            "mensagem_validacao": explicacao,
            "valido_tipo": True,
        }

    # Mismatch detected
    label_detectado = _CATEGORY_LABELS.get(tipo_detectado, tipo_detectado)
    label_esperado = _CATEGORY_LABELS.get(tipo_esperado, tipo_esperado)

    if tipo_detectado == "nao_relacionado":
        msg = (
            f"Conteudo parece ser {explicacao} — "
            "o sistema aceita documentos de projeto (atas, plannings, reviews, etc.)."
        )
    else:
        msg = (
            f"Esse arquivo parece ser uma {label_detectado}, nao um(a) {label_esperado}. "
            f"Para ingerir como {label_detectado}, use o botao {label_detectado} da sprint."
        )

    return {
        "tipo_detectado": tipo_detectado,
        "mensagem_validacao": msg,
        "valido_tipo": False,
    }


def _roteador_validacao(state: ExtractionState):
    if state.get("valido_tipo", True):
        return "detectar_tipo"
    return END


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
        parsed: Optional[ConteudoEstruturado] = raw_result.get("parsed")
        raw_msg = raw_result["raw"]

        if parsed is None:
            pe = raw_result.get("parsing_error")
            print(f"[extrair_conteudo] Structured output parsing failed: {pe}")
            return {"valido": False, "tentativas": tentativas + 1, "erro": f"Structured output parsing failed: {pe}"}

        usage = getattr(raw_msg, "usage_metadata", None) or {}
        in_tok = usage.get("input_tokens", 0) or 0
        out_tok = usage.get("output_tokens", 0) or 0


        content = parsed.model_dump()

        # Completeness guardrail — rejeita extrações completamente vazias
        all_lists = ["tarefas", "decisoes", "problemas", "proximos_passos", "tecnologias"]
        has_any_content = (
            (content.get("resumo") or "").strip()
            or (content.get("contexto_cliente") or "").strip()
            or any(len(content.get(f) or []) > 0 for f in all_lists)
        )
        if not has_any_content:
            return {
                "valido": False,
                "tentativas": tentativas + 1,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "erro": "Completeness check failed: all extracted fields are empty",
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
        # Enrich extracted_content with validation metadata for traceability
        content_to_save = dict(state["conteudo_estruturado"])
        content_to_save["_meta_tipo_detectado"] = state.get("tipo_detectado") or ""
        if state.get("force"):
            content_to_save["_meta_force_override"] = True
        response = (
            client.table("ingestions")
            .insert({
                "project_id": state["projeto_id"],
                "sprint_number": state["sprint_numero"],
                "file_name": state["arquivo_nome"],
                "file_type": state["tipo"],
                "extracted_content": content_to_save,
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
    return {"ingestion_id": response.data[0].get("id")}


def _roteador(state: ExtractionState):
    if state["valido"]:
        return "salvar"
    if state["tentativas"] < 2:
        return "extrair_conteudo"
    return END


_builder = StateGraph(ExtractionState)
_builder.add_node("validar_tipo", validar_tipo)
_builder.add_node("detectar_tipo", detectar_tipo)
_builder.add_node("preprocessar_arquivo", preprocessar_arquivo)
_builder.add_node("extrair_conteudo", extrair_conteudo)
_builder.add_node("salvar", salvar)

_builder.add_edge(START, "validar_tipo")
_builder.add_conditional_edges("validar_tipo", _roteador_validacao, {"detectar_tipo": "detectar_tipo", END: END})
_builder.add_edge("detectar_tipo", "preprocessar_arquivo")
_builder.add_edge("preprocessar_arquivo", "extrair_conteudo")
_builder.add_conditional_edges("extrair_conteudo", _roteador)
_builder.add_edge("salvar", END)

extraction_graph = _builder.compile()
