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

from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Request, Response

from core.rate_limit import GEMINI_RATE_LIMIT, limiter
from graphs.extraction_graph import extraction_graph, ExtractionState
from graphs.generation_graph import generation_graph, GenerationState
from models.schemas import SprintDocResponse
from services.supabase_client import get_client
from services.gemini_key import get_gemini_api_key
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
    tipo_esperado: str = "upload_livre",
    force: bool = False,
    project: dict = None,
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

    _project = project or {}
    file_bytes = await anexo.read()
    state: ExtractionState = {
        "arquivo_bytes": file_bytes,
        "arquivo_nome": anexo.filename or "anexo.pdf",
        "mime_type": anexo.content_type,
        "sprint_numero": sprint_numero,
        "projeto_id": project_id,
        "api_key": api_key,
        "tipo": "",
        "texto_preprocessado": "",
        "conteudo_estruturado": None,
        "valido": False,
        "tentativas": 0,
        "erro": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "ingestion_id": None,
        "tipo_esperado": tipo_esperado,
        "force": force,
        "projeto_nome": _project.get("name", ""),
        "cliente": _project.get("client", ""),
        "projeto_descricao": _project.get("description", "") or "",
        "tipo_detectado": "",
        "mensagem_validacao": "",
        "valido_tipo": False,
    }
    result = await extraction_graph.ainvoke(state)
    if result.get("valido_tipo") is False and not result.get("valido"):
        raise HTTPException(
            status_code=422,
            detail={
                "tipo_detectado": result.get("tipo_detectado", ""),
                "tipo_esperado": tipo_esperado,
                "mensagem": result.get("mensagem_validacao", ""),
                "pode_forcar": True,
            },
        )
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


def _project_or_404(project_id: str) -> dict:
    """Carrega somente os campos públicos necessários do projeto."""
    client = get_client()
    resp = client.table("projects").select("id, name, client, description").eq("id", project_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return resp.data[0]


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
        "api_key": api_key,
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
@limiter.limit(GEMINI_RATE_LIMIT)
async def submit_planning(
    request: Request,
    response: Response,
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    descricao: str = Form(...),
    itens_backlog: str = Form("[]"),  # JSON array de {item, prazo?, criterio?}
    squad: Optional[str] = Form(None),
    periodo_inicio: Optional[str] = Form(None),  # formato ISO date YYYY-MM-DD
    periodo_fim: Optional[str] = Form(None),      # formato ISO date YYYY-MM-DD
    horas_disponiveis: Optional[int] = Form(None),  # horas reais disponíveis do squad
    horas_estimadas: Optional[int] = Form(None),    # horas estimadas necessárias
    dependencias_items: str = Form("[]"),   # [{item, prazo?, consequencia?, confianca?}]
    riscos_items: str = Form("[]"),         # [{risco, consequencia?}]
    carry_over_items: str = Form("[]"),     # [{item, causa_raiz?}]
    anexo: Optional[UploadFile] = File(None),
    force: bool = Form(False),
):
    """Submete o Planning de uma sprint. Cria ingestion + dispara geração do doc."""
    project = _project_or_404(projeto_id)
    api_key = get_gemini_api_key()
    try:
        backlog = json.loads(itens_backlog)
        if not isinstance(backlog, list):
            raise ValueError("itens_backlog deve ser JSON array")
        # Normaliza: aceita strings legacy ou objetos {item, responsavel, prazo, criterio}
        backlog_items = []
        for entry in backlog:
            if isinstance(entry, str):
                backlog_items.append({"item": entry, "responsavel": "", "prazo": "", "criterio": ""})
            elif isinstance(entry, dict):
                backlog_items.append({
                    "item": entry.get("item", ""),
                    "responsavel": entry.get("responsavel", "") or "",
                    "prazo": entry.get("prazo", "") or "",
                    "criterio": entry.get("criterio", "") or "",
                })
        dep_items = json.loads(dependencias_items) if isinstance(dependencias_items, str) else []
        risco_items = json.loads(riscos_items) if isinstance(riscos_items, str) else []
        co_items = json.loads(carry_over_items) if isinstance(carry_over_items, str) else []
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Payload inválido: {exc}")

    ensure_sprint_row(get_client(), projeto_id, sprint_numero)

    def _fmt(b: dict) -> str:
        s = b["item"]
        if b.get("responsavel"): s += f" — Responsável: {b['responsavel']}"
        if b.get("prazo"): s += f" — Prazo: {b['prazo']}"
        if b.get("criterio"): s += f" — DoD: {b['criterio']}"
        return s

    tarefas_fmt = [_fmt(b) for b in backlog_items if b["item"]]
    riscos_fmt = [f"{r['risco']} — Consequência: {r.get('consequencia','')}" for r in risco_items if r.get("risco")]

    base_content = {
        "resumo": descricao,
        "tarefas": tarefas_fmt,
        "decisoes": [],
        "problemas": riscos_fmt,
        "contexto_cliente": "",
        "proximos_passos": tarefas_fmt,
        "tecnologias": [],
        "campos_planning": {
            "squad": squad or "",
            "periodo_inicio": periodo_inicio or "",
            "periodo_fim": periodo_fim or "",
            "horas_disponiveis": horas_disponiveis,
            "horas_estimadas": horas_estimadas,
            "backlog_items": backlog_items,
            "dependencias_items": dep_items,
            "riscos_items": risco_items,
            "carry_over_items": co_items,
        },
    }

    if anexo is not None:
        extra = await _extract_anexo_to_content(projeto_id, sprint_numero, api_key, anexo, tipo_esperado="planning", force=force, project=project)
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
@limiter.limit(GEMINI_RATE_LIMIT)
async def submit_daily(
    request: Request,
    response: Response,
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    data: str = Form(...),                     # ISO date (YYYY-MM-DD)
    feito: str = Form(...),
    proximo: str = Form(...),
    impedimentos: Optional[str] = Form(None),
    anexo: Optional[UploadFile] = File(None),
    force: bool = Form(False),
):
    """Submete uma Daily. Cria ingestion + dispara geração do doc."""
    project = _project_or_404(projeto_id)
    api_key = get_gemini_api_key()
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
        extra = await _extract_anexo_to_content(projeto_id, sprint_numero, api_key, anexo, tipo_esperado="daily", force=force, project=project)
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
@limiter.limit(GEMINI_RATE_LIMIT)
async def submit_ata_with_upload(
    request: Request,
    response: Response,
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    anexo: UploadFile = File(...),
    force: bool = Form(False),
):
    """Gera Ata de Reunião a partir de uma transcrição em PDF (upload + extração + geração em uma chamada).

    Diferente de planning/daily/review (que recebem campos estruturados), a ata depende
    SEMPRE de uma transcrição — o PDF é obrigatório. A ingestão resultante fica com
    tipo_documentacao=NULL (é um insumo livre, não conta como mínimo obrigatório).
    """
    project = _project_or_404(projeto_id)
    api_key = get_gemini_api_key()
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
        "api_key": api_key,
        "tipo": "",
        "texto_preprocessado": "",
        "conteudo_estruturado": None,
        "valido": False,
        "tentativas": 0,
        "erro": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "ingestion_id": None,
        "tipo_esperado": "ata_reuniao",
        "force": force,
        "projeto_nome": project.get("name", ""),
        "cliente": project.get("client", ""),
        "projeto_descricao": project.get("description", "") or "",
        "tipo_detectado": "",
        "mensagem_validacao": "",
        "valido_tipo": False,
    }
    result = await extraction_graph.ainvoke(state)
    if result.get("valido_tipo") is False and not result.get("valido"):
        raise HTTPException(
            status_code=422,
            detail={
                "tipo_detectado": result.get("tipo_detectado", ""),
                "tipo_esperado": "ata_reuniao",
                "mensagem": result.get("mensagem_validacao", ""),
                "pode_forcar": True,
            },
        )
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
@limiter.limit(GEMINI_RATE_LIMIT)
async def submit_review(
    request: Request,
    response: Response,
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    observacoes: Optional[str] = Form(None),
    percepcao_cliente: Optional[str] = Form(None),   # frase literal ou paráfrase objetiva do cliente
    sinal_satisfacao: Optional[str] = Form(None),    # categoria de satisfação do cliente
    pedidos_fora_escopo: Optional[str] = Form(None), # texto livre backward-compat
    # Campos Template 2 CITi
    squad: Optional[str] = Form(None),               # membros e papéis do squad
    periodo_inicio: Optional[str] = Form(None),      # ISO date YYYY-MM-DD
    periodo_fim: Optional[str] = Form(None),         # ISO date YYYY-MM-DD
    subarea: Optional[str] = Form(None),             # "desenvolvimento" | "dados" | "produto"
    itens_planejados_entregues: str = Form("[]"),     # [{item, entregue, motivo_nao, causa_raiz_num}]
    percentual_itens_prontos: Optional[str] = Form(None),  # ex: "8 de 10 = 80%"
    pedidos_fora_escopo_itens: str = Form("[]"),     # [{data, descricao, status}]
    itens_proxima_sprint: str = Form("[]"),          # [{item, causa_raiz_num}]
    anexo: Optional[UploadFile] = File(None),
    force: bool = Form(False),
):
    """Submete a Review de uma sprint. Cria ingestion + dispara geração do doc.

    A review se baseia no planning + dailys + ingestões livres da sprint para
    computar o delta (planejado vs realizado). Observações do gerente são
    anexadas como contexto adicional.
    """
    project = _project_or_404(projeto_id)
    api_key = get_gemini_api_key()
    ensure_sprint_row(get_client(), projeto_id, sprint_numero)

    observacoes_clean = (observacoes or "").strip()

    try:
        ipe_parsed = json.loads(itens_planejados_entregues) if isinstance(itens_planejados_entregues, str) else []
        pfe_parsed = json.loads(pedidos_fora_escopo_itens) if isinstance(pedidos_fora_escopo_itens, str) else []
        ips_parsed = json.loads(itens_proxima_sprint) if isinstance(itens_proxima_sprint, str) else []
    except (json.JSONDecodeError, ValueError):
        ipe_parsed, pfe_parsed, ips_parsed = [], [], []

    base_content = {
        "resumo": observacoes_clean or f"Review da Sprint {sprint_numero}",
        "tarefas": [],
        "decisoes": [],
        "problemas": [],
        "contexto_cliente": "",
        "proximos_passos": [],
        "tecnologias": [],
        "campos_review": {
            # Campos de percepção (Template 2 — Percepção do Cliente / Sinal de Satisfação)
            "percepcao_cliente": percepcao_cliente or "",
            "sinal_satisfacao": sinal_satisfacao or "",
            "pedidos_fora_escopo": pedidos_fora_escopo or "",  # texto livre backward-compat
            # Campos de cabeçalho (Template 2)
            "squad": squad or "",
            "periodo_inicio": periodo_inicio or "",
            "periodo_fim": periodo_fim or "",
            "subarea": subarea or "",
            # Tabela Planejado vs Entregue — [{item, entregue, motivo_nao, causa_raiz_num}]
            "itens_planejados_entregues": ipe_parsed,
            # % de Itens com "Pronto" Cumprido Integralmente
            "percentual_itens_prontos": percentual_itens_prontos or "",
            # Tabela Pedidos Fora do Escopo — [{data, descricao, status}]
            "pedidos_fora_escopo_itens": pfe_parsed,
            # Tabela Itens que Passam para a Próxima Sprint — [{item, causa_raiz_num}]
            "itens_proxima_sprint": ips_parsed,
        },
    }

    if anexo is not None:
        try:
            extra = await _extract_anexo_to_content(projeto_id, sprint_numero, api_key, anexo, tipo_esperado="review", force=force, project=project)
            base_content = _merge_content(base_content, extra)
        except HTTPException as exc:
            if exc.status_code == 422:
                raise
            print(f"[submit_review] Anexo extraction failed (non-fatal): {exc.detail}")

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


@router.post("/retrospectiva", response_model=SprintDocResponse, status_code=201)
@limiter.limit(GEMINI_RATE_LIMIT)
async def submit_retrospectiva(
    request: Request,
    response: Response,
    projeto_id: str = Form(...),
    sprint_numero: int = Form(...),
    observacoes: Optional[str] = Form(None),
    pedido_fora_escopo_status: Optional[str] = Form(None),  # backward-compat
    # Campos Template 3 CITi
    squad: Optional[str] = Form(None),              # membros e papéis do squad
    periodo_inicio: Optional[str] = Form(None),     # ISO date YYYY-MM-DD
    periodo_fim: Optional[str] = Form(None),        # ISO date YYYY-MM-DD
    subarea: Optional[str] = Form(None),            # "desenvolvimento" | "dados" | "produto"
    o_que_funcionou: str = Form("[]"),              # list[str] — mínimo 1 item
    o_que_nao_funcionou: str = Form("[]"),          # list[str] — mínimo 1 item
    causa_raiz_impacto: str = Form("[]"),           # [{causa_raiz_num, impacto}]
    acoes_melhoria: str = Form("[]"),               # [{acao, responsavel, prazo}] — máx 2
    houve_pedido_fora_escopo: Optional[str] = Form(None),   # "sim" | "nao"
    status_pedido_fora_escopo: Optional[str] = Form(None),  # lista informal | CR formalizado
    anexo: Optional[UploadFile] = File(None),
    force: bool = Form(False),
):
    """Submete a Retrospectiva de uma sprint. Cria ingestion + dispara geração do doc.

    A retrospectiva consolida o que aconteceu na sprint (planning + dailys + review)
    e captura o status dos pedidos fora de escopo recebidos durante o review.
    """
    project = _project_or_404(projeto_id)
    api_key = get_gemini_api_key()
    ensure_sprint_row(get_client(), projeto_id, sprint_numero)

    try:
        oqf_parsed = json.loads(o_que_funcionou) if isinstance(o_que_funcionou, str) else []
        oqnf_parsed = json.loads(o_que_nao_funcionou) if isinstance(o_que_nao_funcionou, str) else []
        cri_parsed = json.loads(causa_raiz_impacto) if isinstance(causa_raiz_impacto, str) else []
        am_parsed = json.loads(acoes_melhoria) if isinstance(acoes_melhoria, str) else []
    except (json.JSONDecodeError, ValueError):
        oqf_parsed, oqnf_parsed, cri_parsed, am_parsed = [], [], [], []

    base_content = {
        "resumo": observacoes or f"Retrospectiva da Sprint {sprint_numero}",
        "tarefas": [],
        "decisoes": [],
        "problemas": [],
        "contexto_cliente": "",
        "proximos_passos": [],
        "tecnologias": [],
        "campos_retrospectiva": {
            "pedido_fora_escopo_status": pedido_fora_escopo_status or "",  # backward-compat
            # Cabeçalho (Template 3)
            "squad": squad or "",
            "periodo_inicio": periodo_inicio or "",
            "periodo_fim": periodo_fim or "",
            "subarea": subarea or "",
            # O que Funcionou — list[str]
            "o_que_funcionou": oqf_parsed,
            # O que Não Funcionou — list[str]
            "o_que_nao_funcionou": oqnf_parsed,
            # Causa Raiz × Impacto — [{causa_raiz_num, impacto: "Baixo"|"Médio"|"Alto"}]
            "causa_raiz_impacto": cri_parsed,
            # Ações de Melhoria — [{acao, responsavel, prazo}] máx 2
            "acoes_melhoria": am_parsed,
            # Houve Pedido Fora de Escopo? — "sim" | "nao"
            "houve_pedido_fora_escopo": houve_pedido_fora_escopo or "",
            # Status do registro — "lista informal" | "CR formalizado"
            "status_pedido_fora_escopo": status_pedido_fora_escopo or "",
        },
    }

    if anexo is not None:
        try:
            extra = await _extract_anexo_to_content(projeto_id, sprint_numero, api_key, anexo, tipo_esperado="retrospectiva", force=force, project=project)
            base_content = _merge_content(base_content, extra)
        except HTTPException as exc:
            if exc.status_code == 422:
                raise
            print(f"[submit_retrospectiva] Anexo extraction failed (non-fatal): {exc.detail}")

    ingestion = _insert_ingestion(
        project_id=projeto_id,
        sprint_numero=sprint_numero,
        file_name=f"retrospectiva-sprint-{sprint_numero}",
        tipo_documentacao="retrospectiva",
        extracted_content=base_content,
    )

    # Para retrospectiva, o generation_graph busca TODAS as ingestões da sprint
    # para consolidar o que foi planejado vs realizado — ingestion_id não é usado nesse caminho
    doc = await _run_generation(
        project=project,
        tipo_doc="retrospectiva",
        sprint_numero=sprint_numero,
        ingestion_id=None,
        api_key=api_key,
    )

    return SprintDocResponse(
        ingestion_id=ingestion["id"],
        doc_id=doc["id"],
        doc_type="retrospectiva",
        sprint_number=sprint_numero,
        content=doc["content"],
        created_at=doc["created_at"],
    )
