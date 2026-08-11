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


class ItemEntregue(BaseModel):
    item: str = ""
    entregue: str = ""        # "S" ou "N"
    motivo_nao: str = ""      # causa raiz nº se não entregue
    causa_raiz_num: str = ""  # número da causa raiz (1-7)


class PedidoForaEscopoItem(BaseModel):
    data: str = ""
    descricao: str = ""
    status: str = ""          # "Insistência" ou "Sugestão pontual"


class ItemProximaSprint(BaseModel):
    item: str = ""
    causa_raiz_num: str = ""  # número da causa raiz (1-7)


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
    # Campos Template 2 CITi
    squad: Optional[str] = None
    periodo_inicio: Optional[str] = Field(default=None, description="DD/MM/AAAA ou YYYY-MM-DD")
    periodo_fim: Optional[str] = Field(default=None, description="DD/MM/AAAA ou YYYY-MM-DD")
    subarea: Optional[str] = Field(default=None, description="'desenvolvimento', 'dados' ou 'produto'")
    itens_planejados_entregues: list[ItemEntregue] = Field(default_factory=list)
    percentual_itens_prontos: Optional[str] = Field(default=None, description="Ex: '8 de 10 = 80%'")
    pedidos_fora_escopo_itens: list[PedidoForaEscopoItem] = Field(default_factory=list)
    itens_proxima_sprint: list[ItemProximaSprint] = Field(default_factory=list)


class CausaRaizImpacto(BaseModel):
    causa_raiz_num: str = ""   # número da causa raiz (1-7) e nome da categoria
    impacto: str = ""          # "Baixo", "Médio" ou "Alto"


class AcaoMelhoria(BaseModel):
    acao: str = ""
    responsavel: str = ""
    prazo: str = ""


class RetrospectivaEnrichment(BaseModel):
    observacoes: Optional[str] = None
    pedido_fora_escopo_status: Optional[str] = None
    # Campos Template 3 CITi
    squad: Optional[str] = None
    periodo_inicio: Optional[str] = Field(default=None, description="DD/MM/AAAA ou YYYY-MM-DD")
    periodo_fim: Optional[str] = Field(default=None, description="DD/MM/AAAA ou YYYY-MM-DD")
    subarea: Optional[str] = Field(default=None, description="'desenvolvimento', 'dados' ou 'produto'")
    o_que_funcionou: list[str] = Field(default_factory=list, description="Mínimo 1 item específico")
    o_que_nao_funcionou: list[str] = Field(default_factory=list, description="Mínimo 1 item específico")
    causa_raiz_impacto: list[CausaRaizImpacto] = Field(default_factory=list)
    acoes_melhoria: list[AcaoMelhoria] = Field(default_factory=list, description="Máximo 2 ações")
    houve_pedido_fora_escopo: Optional[str] = Field(default=None, description="'sim' ou 'nao'")
    status_pedido_fora_escopo: Optional[str] = None


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
        "anotações pós-sprint, etc.) e extraia os campos da Review de Sprint seguindo o Template 2 CITi.\n\n"
        "Extraia apenas o que está explicitamente presente — nunca invente. Deixe null ou lista vazia quando a informação não estiver presente.\n\n"
        "Campos a extrair:\n"
        "- observacoes: resumo geral da sprint do ponto de vista do gerente\n"
        "- percepcao_cliente: frase literal ou paráfrase objetiva do que o cliente disse/comunicou (NÃO interprete — transcreva), null se não mencionado\n"
        "- sinal_satisfacao: classifique o sinal escolhendo EXATAMENTE uma das opções: "
        "'Elogio espontâneo', 'Neutro / sem sinal', "
        "'Reclamação pontual, resolvida na própria Review', "
        "'Reclamação não resolvida ao final da Review', "
        "'Reclamação recorrente sobre o mesmo tema (2ª vez)', "
        "'Cliente solicitou reunião de escalonamento'. null se não for possível inferir\n"
        "- pedidos_fora_escopo: pedidos do cliente fora do escopo (texto livre), null se nenhum\n"
        "- squad: membros do time e seus papéis mencionados no texto, null se não identificado\n"
        "- periodo_inicio: data de início da sprint (DD/MM/AAAA ou YYYY-MM-DD), null se não mencionada\n"
        "- periodo_fim: data de fim da sprint (DD/MM/AAAA ou YYYY-MM-DD), null se não mencionada\n"
        "- subarea: 'desenvolvimento', 'dados' ou 'produto' se mencionado, null caso contrário\n"
        "- itens_planejados_entregues: lista de itens planejados com status de entrega. Para cada item: "
        "item (nome da tarefa), entregue ('S' ou 'N'), motivo_nao (motivo se não entregue), "
        "causa_raiz_num (número 1-7 da causa raiz se não entregue). Lista vazia se não identificado\n"
        "- percentual_itens_prontos: percentual de itens entregues (ex: '8 de 10 = 80%'), null se não calculável\n"
        "- pedidos_fora_escopo_itens: lista de pedidos fora do escopo com data, descricao e status "
        "('Insistência' ou 'Sugestão pontual'). Lista vazia se não houver pedidos\n"
        "- itens_proxima_sprint: itens não entregues que passam para a próxima sprint. Para cada item: "
        "item (nome) e causa_raiz_num (número 1-7). Lista vazia se não identificado\n\n"
        "Categorias de causa raiz: 1=Especificação incompleta no Planning, 2=Dependência do cliente atrasada, "
        "3=Pedido de escopo novo, 4=Estimativa equivocada, 5=Bloqueio técnico, "
        "6=Ausência/rotatividade de membro, 7=Outro"
    ),
    "retrospectiva": (
        "Você é um assistente de documentação do CITi. Analise a matéria-prima abaixo "
        "(pode ser anotações de retrospectiva, relato pós-sprint, transcrição da retro, etc.) "
        "e extraia os campos da Retrospectiva seguindo o Template 3 CITi.\n\n"
        "Extraia apenas o que está explicitamente presente — nunca invente. Deixe null ou lista vazia quando a informação não estiver presente.\n\n"
        "Campos a extrair:\n"
        "- observacoes: reflexão geral sobre o que aconteceu na sprint\n"
        "- squad: membros do time e seus papéis mencionados, null se não identificado\n"
        "- periodo_inicio: data de início (DD/MM/AAAA ou YYYY-MM-DD), null se não mencionada\n"
        "- periodo_fim: data de fim (DD/MM/AAAA ou YYYY-MM-DD), null se não mencionada\n"
        "- subarea: 'desenvolvimento', 'dados' ou 'produto' se mencionado, null caso contrário\n"
        "- o_que_funcionou: lista de itens específicos que funcionaram bem (processo, entrega, decisão acertada). "
        "Mínimo 1 se identificável. Lista vazia se não houver\n"
        "- o_que_nao_funcionou: lista de itens que não funcionaram (bloqueio, estimativa errada, problema de processo). "
        "Mínimo 1 se identificável. Lista vazia se não houver\n"
        "- causa_raiz_impacto: para cada problema de 'o_que_nao_funcionou', a causa raiz e impacto. "
        "Para cada item: causa_raiz_num (número 1-7 e nome da categoria) e impacto ('Baixo', 'Médio' ou 'Alto')\n"
        "- acoes_melhoria: máximo 2 ações concretas para próxima sprint. Para cada uma: acao, responsavel, prazo\n"
        "- houve_pedido_fora_escopo: 'sim' ou 'nao' se identificável, null caso contrário\n"
        "- status_pedido_fora_escopo: se houve pedido, descreva o status do registro "
        "(ex: 'lista informal', 'CR formalizado', 'aceito para Sprint X', 'recusado'), null se não houver\n"
        "- pedido_fora_escopo_status: igual ao status_pedido_fora_escopo (campo backward-compat)\n\n"
        "Categorias de causa raiz: 1=Especificação incompleta no Planning, 2=Dependência do cliente atrasada, "
        "3=Pedido de escopo novo, 4=Estimativa equivocada, 5=Bloqueio técnico, "
        "6=Ausência/rotatividade de membro, 7=Outro"
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
        model="gemini-flash-latest",
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
