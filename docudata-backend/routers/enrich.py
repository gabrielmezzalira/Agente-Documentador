"""Endpoint de enriquecimento: analisa matéria-prima bruta (texto ou arquivo) via Gemini
e retorna campos estruturados prontos para o gerente revisar antes de gerar o documento.

Não salva nada no banco — é uma etapa de pré-visualização/validação.
"""
from typing import Optional

from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from services.supabase_client import get_client

router = APIRouter(prefix="/enrich", tags=["enrich"])


# ── Schemas de retorno por tipo de doc ────────────────────────────────────────

class BacklogItem(BaseModel):
    item: str = ""
    responsavel: str = ""
    prazo: str = ""
    criterio: str = ""


class DependenciaItem(BaseModel):
    item: str = ""
    prazo: str = ""
    consequencia: str = ""
    confianca: str = ""


class RiscoItem(BaseModel):
    risco: str = ""
    consequencia: str = ""


class CarryOverItem(BaseModel):
    item: str = ""
    causa_raiz: str = ""


class PlanningEnrichment(BaseModel):
    descricao: str = Field(default="", description="Objetivo da sprint em 1-2 frases")
    itens_backlog: list[BacklogItem] = Field(default_factory=list)
    horas_disponiveis: Optional[int] = None
    horas_estimadas: Optional[int] = None
    periodo_inicio: Optional[str] = Field(default=None, description="DD/MM/AAAA ou YYYY-MM-DD")
    periodo_fim: Optional[str] = Field(default=None, description="DD/MM/AAAA ou YYYY-MM-DD")
    dependencias_items: list[DependenciaItem] = Field(default_factory=list)
    riscos_items: list[RiscoItem] = Field(default_factory=list)
    carry_over_items: list[CarryOverItem] = Field(default_factory=list)


class DailyEnrichment(BaseModel):
    data: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    feito: str = ""
    proximo: str = ""
    impedimentos: Optional[str] = None


class ReviewEnrichment(BaseModel):
    observacoes: Optional[str] = None
    percepcao_cliente: Optional[str] = None
    sinal_satisfacao: Optional[str] = Field(
        default=None,
        description=(
            "Escolha exatamente uma das opções abaixo conforme o tom do cliente, ou null se não for possível inferir: "
            "'Elogio espontâneo', 'Neutro / sem sinal', "
            "'Reclamação pontual, resolvida na própria Review', "
            "'Reclamação não resolvida ao final da Review', "
            "'Reclamação recorrente sobre o mesmo tema (2ª vez)', "
            "'Cliente solicitou reunião de escalonamento'"
        ),
    )
    pedidos_fora_escopo: Optional[str] = None


class RetrospectivaEnrichment(BaseModel):
    observacoes: Optional[str] = None
    pedido_fora_escopo_status: Optional[str] = None


_SCHEMA_MAP = {
    "planning": PlanningEnrichment,
    "daily": DailyEnrichment,
    "review": ReviewEnrichment,
    "retrospectiva": RetrospectivaEnrichment,
}

_PROMPTS = {
    "planning": (
        "Você é um assistente de documentação do CITi. Analise a matéria-prima abaixo "
        "(pode ser pauta de sprint, transcrição de reunião de planning, lista de tarefas, "
        "documento do Planner, ou qualquer insumo de planejamento) e extraia os dados "
        "estruturados do Planning.\n\n"
        "Extraia apenas o que está explicitamente presente no texto — nunca invente. "
        "Deixe campos vazios (string vazia ou lista vazia) quando a informação não estiver presente.\n\n"
        "Campos a extrair:\n"
        "- descricao: objetivo geral da sprint em 1-2 frases\n"
        "- itens_backlog: cada tarefa/atividade com responsável, prazo e critério de aceite se visíveis\n"
        "- horas_disponiveis: capacidade do squad em horas (inteiro), null se não mencionado\n"
        "- horas_estimadas: estimativa de horas necessárias, null se não mencionada\n"
        "- periodo_inicio: data de início da sprint (formato DD/MM/AAAA ou YYYY-MM-DD), null se não mencionada\n"
        "- periodo_fim: data de fim da sprint (formato DD/MM/AAAA ou YYYY-MM-DD), null se não mencionada\n"
        "- dependencias_items: dependências externas que o squad precisa de terceiros\n"
        "- riscos_items: riscos identificados para a sprint\n"
        "- carry_over_items: itens não entregues de sprints anteriores mencionados"
    ),
    "daily": (
        "Você é um assistente de documentação do CITi. Analise a matéria-prima abaixo "
        "(pode ser mensagem de status, transcrição de daily, atualização no WhatsApp/chat, etc.) "
        "e extraia os campos da Daily.\n\n"
        "Deixe campos vazios ou null quando a informação não estiver presente.\n\n"
        "Campos a extrair:\n"
        "- data: data da daily em formato YYYY-MM-DD, null se não identificada\n"
        "- feito: o que foi feito desde a última daily\n"
        "- proximo: o que será feito até a próxima daily\n"
        "- impedimentos: impedimentos ou riscos mencionados, null se nenhum"
    ),
    "review": (
        "Você é um assistente de documentação do CITi. Analise a matéria-prima abaixo "
        "(pode ser transcrição da reunião de review, relato do gerente, feedback do cliente, "
        "anotações pós-sprint, etc.) e extraia os campos da Review de Sprint.\n\n"
        "Campos a extrair:\n"
        "- observacoes: resumo geral da sprint do ponto de vista do gerente\n"
        "- percepcao_cliente: como o cliente reagiu ou avaliou a entrega, null se não mencionado\n"
        "- sinal_satisfacao: classifique o sinal do cliente escolhendo EXATAMENTE uma das opções: "
        "'Elogio espontâneo' (cliente elogiou proativamente), "
        "'Neutro / sem sinal' (sem elogio nem reclamação), "
        "'Reclamação pontual, resolvida na própria Review' (problema levantado e resolvido na reunião), "
        "'Reclamação não resolvida ao final da Review' (problema aberto ao fim da reunião), "
        "'Reclamação recorrente sobre o mesmo tema (2ª vez)' (mesmo problema já reportado antes), "
        "'Cliente solicitou reunião de escalonamento' (cliente pediu escalada). "
        "null se não for possível inferir com segurança\n"
        "- pedidos_fora_escopo: pedidos do cliente fora do escopo combinado, null se nenhum"
    ),
    "retrospectiva": (
        "Você é um assistente de documentação do CITi. Analise a matéria-prima abaixo "
        "(pode ser anotações de retrospectiva, relato pós-sprint, transcrição da retro, etc.) "
        "e extraia os campos da Retrospectiva.\n\n"
        "Campos a extrair:\n"
        "- observacoes: reflexão geral sobre o que aconteceu na sprint\n"
        "- pedido_fora_escopo_status: status dos pedidos fora do escopo recebidos "
        "(ex: 'aceito para próxima sprint', 'recusado', 'postergado'), null se não houver"
    ),
}


def _get_api_key(projeto_id: str) -> str:
    client = get_client()
    resp = client.table("projects").select("gemini_api_key").eq("id", projeto_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    key = resp.data[0].get("gemini_api_key") or ""
    if not key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto não tem uma chave de API do Gemini configurada.",
        )
    return key


async def _prepare_content(
    texto: Optional[str],
    arquivo: Optional[UploadFile],
) -> tuple[str, bool, Optional[str], Optional[str]]:
    """Retorna (content_text, is_vision, image_b64, image_mime)."""
    content_text = ""
    is_vision = False
    image_b64 = None
    image_mime = None

    if arquivo is not None:
        file_bytes = await arquivo.read()
        mime = arquivo.content_type or ""

        if mime == "application/pdf":
            from services.file_parser import parse_pdf
            result = parse_pdf(file_bytes)
            if result["is_scanned"]:
                is_vision = True
                image_b64 = result["b64"]
                image_mime = "image/png"
            else:
                content_text = result["text"][:30_000]
        elif mime in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
            from services.file_parser import parse_image
            image_b64 = parse_image(file_bytes)
            image_mime = mime
            is_vision = True
        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from services.file_parser import parse_docx
            content_text = parse_docx(file_bytes)[:30_000]
        else:
            from services.file_parser import parse_txt
            content_text = parse_txt(file_bytes)[:30_000]

    if texto:
        content_text = (content_text + "\n\n" + texto).strip() if content_text else texto[:30_000]

    return content_text, is_vision, image_b64, image_mime


@router.post("")
async def enrich(
    projeto_id: str = Form(...),
    doc_type: str = Form(...),
    texto: Optional[str] = Form(None),
    arquivo: Optional[UploadFile] = File(None),
):
    """Analisa matéria-prima bruta e retorna campos pré-preenchidos para validação manual.

    Não salva nada no banco — resposta serve apenas para pré-popular o modal antes da geração.
    """
    if doc_type not in _SCHEMA_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"doc_type inválido: {doc_type!r}. Use: {list(_SCHEMA_MAP)}",
        )

    api_key = _get_api_key(projeto_id)
    content_text, is_vision, image_b64, image_mime = await _prepare_content(texto, arquivo)

    if not content_text and not is_vision:
        raise HTTPException(status_code=422, detail="Forneça texto ou arquivo para análise.")

    schema_model = _SCHEMA_MAP[doc_type]
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0,
        google_api_key=api_key,
    ).with_structured_output(schema_model, method="json_schema", include_raw=True)

    if is_vision:
        messages = [
            SystemMessage(content=_PROMPTS[doc_type]),
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}},
                {"type": "text", "text": "Analise esta imagem e extraia as informações estruturadas conforme solicitado."},
            ]),
        ]
    else:
        messages = [
            SystemMessage(content=_PROMPTS[doc_type]),
            HumanMessage(content=content_text),
        ]

    try:
        raw_result = await llm.ainvoke(messages)
        parsed = raw_result.get("parsed")
        if parsed is None:
            pe = raw_result.get("parsing_error")
            print(f"[enrich] Structured output parsing failed for doc_type={doc_type}: {pe}")
            raise HTTPException(
                status_code=502,
                detail="Falha ao estruturar resposta da IA. Tente reformular o texto ou use um arquivo diferente.",
            )
        return parsed.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro na análise: {exc}")
