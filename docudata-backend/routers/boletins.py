from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from models.schemas import BoletimCreate, BoletimPatch, BoletimResponse
from services.supabase_client import get_client

router = APIRouter(prefix="/boletins", tags=["boletins"])

# ---------------------------------------------------------------------------
# Constante do sistema — prompt para geração do boletim de aceite
# ---------------------------------------------------------------------------

_BOLETIM_SYSTEM_PROMPT = (
    "Você é um assistente especializado em comunicação com clientes de projetos de dados do CITi. "
    "Sua tarefa é gerar um Boletim de Aceite em markdown, em português, de forma clara e acessível "
    "para um cliente não técnico. O boletim deve conter: "
    "1. Título — nome do projeto e identificação do lote de funcionalidades "
    "2. Funcionalidades para Aceite — para cada funcionalidade: nome e critérios de aceite em "
    "linguagem de negócio (sem jargão técnico) "
    "3. Instruções para Aceite — como o cliente deve registrar o retorno (aprovado ou ajuste pedido). "
    "Reescreva os critérios de aceite em linguagem acessível ao cliente — sem termos técnicos como "
    '"endpoint", "payload", "UUID". '
    "Retorne APENAS o markdown, sem texto antes ou depois, sem blocos de código, sem backticks."
)


# ---------------------------------------------------------------------------
# Status transition table — sequência enforced (RESEARCH Pitfall 2)
# Transições válidas: rascunho→enviado, enviado→aprovado, enviado→ajuste
# ---------------------------------------------------------------------------

TRANSICOES_VALIDAS: dict[str, set[str]] = {
    "rascunho": {"enviado"},
    "enviado": {"aprovado", "ajuste"},
}


# ---------------------------------------------------------------------------
# Auxiliar — registra transição de status_cliente em transicoes_status
# e atualiza funcionalidades.status_cliente (replicado de funcionalidades.py:280-307)
# ---------------------------------------------------------------------------


def _registrar_transicao_status_cliente(
    client,
    func_id: str,
    status_anterior: str,
    novo_status: str,
    agora: datetime,
) -> None:
    """Registra transição de status_cliente em transicoes_status e atualiza a funcionalidade.

    Replica o padrão de funcionalidades.py:280-307 para atualização em batch
    (RESEARCH Pattern 2, Pitfall 4). Calcula duracao_fase_anterior_segundos para
    que o Bloco B do Painel possa detectar funcionalidades "aguardando cliente".
    """
    # Buscar última transição de status_cliente para calcular duração da fase anterior
    anterior = (
        client.table("transicoes_status")
        .select("timestamp")
        .eq("funcionalidade_id", func_id)
        .eq("campo", "status_cliente")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    if anterior.data:
        ts_anterior = datetime.fromisoformat(anterior.data[0]["timestamp"]).replace(
            tzinfo=timezone.utc
        )
    else:
        # Sem transição anterior: usar created_at da funcionalidade como referência
        func_resp = (
            client.table("funcionalidades")
            .select("created_at")
            .eq("id", func_id)
            .execute()
        )
        if func_resp.data:
            ts_anterior = datetime.fromisoformat(
                func_resp.data[0]["created_at"]
            ).replace(tzinfo=timezone.utc)
        else:
            ts_anterior = agora

    duracao = int((agora - ts_anterior).total_seconds())

    # Inserir registro de transição em transicoes_status
    client.table("transicoes_status").insert(
        {
            "funcionalidade_id": func_id,
            "campo": "status_cliente",
            "de": status_anterior,
            "para": novo_status,
            "autor": None,
            "timestamp": agora.isoformat(),
            "motivo": None,
            "duracao_fase_anterior_segundos": duracao,
        }
    ).execute()

    # Atualizar funcionalidades.status_cliente
    client.table("funcionalidades").update({"status_cliente": novo_status}).eq(
        "id", func_id
    ).execute()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201, response_model=BoletimResponse)
async def criar_boletim(body: BoletimCreate):
    """Gera um boletim de aceite via Gemini e persiste em boletins_aceite.

    Segurança (T-12-01): verifica que todos os funcionalidade_ids pertencem
    ao project_id informado antes de chamar o Gemini.
    Segurança (T-12-02): gemini_api_key nunca incluída no response.
    """
    client = get_client()

    # Buscar projeto (404 se não existe)
    proj_resp = (
        client.table("projects")
        .select("id, name, client, gemini_api_key")
        .eq("id", body.project_id)
        .execute()
    )
    if not proj_resp.data:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    projeto = proj_resp.data[0]

    # Verificar gemini_api_key (422 se ausente/vazia)
    api_key = (projeto.get("gemini_api_key") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto não tem uma chave de API do Gemini configurada.",
        )

    # Verificar ownership das funcionalidades (T-12-01 — anti-spoofing)
    if not body.funcionalidade_ids:
        raise HTTPException(
            status_code=422,
            detail="É necessário informar ao menos uma funcionalidade.",
        )

    ownership_resp = (
        client.table("funcionalidades")
        .select("id")
        .eq("project_id", body.project_id)
        .in_("id", body.funcionalidade_ids)
        .execute()
    )
    found_ids = {row["id"] for row in (ownership_resp.data or [])}
    if len(found_ids) != len(body.funcionalidade_ids):
        raise HTTPException(
            status_code=422,
            detail="Algumas funcionalidades não pertencem a este projeto",
        )

    # Buscar funcionalidades com critérios de aceite
    funcs_resp = (
        client.table("funcionalidades")
        .select("id, titulo, criterios_aceite")
        .in_("id", body.funcionalidade_ids)
        .execute()
    )
    funcionalidades = funcs_resp.data or []

    # Montar contexto textual para o Gemini
    linhas: list[str] = [
        f"Projeto: {projeto.get('name', '')}",
        f"Cliente: {projeto.get('client', '')}",
        "",
        "Funcionalidades para aceite:",
        "",
    ]
    for func in funcionalidades:
        linhas.append(f"## {func.get('titulo', func['id'])}")
        criterios: list[str] = func.get("criterios_aceite") or []
        if criterios:
            linhas.append("Critérios de aceite:")
            for criterio in criterios:
                linhas.append(f"- {criterio}")
        else:
            linhas.append("Critérios de aceite: (nenhum registrado)")
        linhas.append("")

    contexto = "\n".join(linhas)

    # Chamar Gemini (T-12-04: try/except → 502 em vez de travar)
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        max_tokens=2048,
        google_api_key=api_key,
    )
    try:
        result = await llm.ainvoke(
            [
                SystemMessage(content=_BOLETIM_SYSTEM_PROMPT),
                HumanMessage(content=contexto),
            ]
        )
        markdown: str = result.content  # type: ignore[assignment]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini failed: {exc}")

    # Inserir em boletins_aceite
    agora = datetime.now(timezone.utc).isoformat()
    insert_resp = (
        client.table("boletins_aceite")
        .insert(
            {
                "project_id": body.project_id,
                "sprint_numero": body.sprint_numero,
                "funcionalidade_ids": [str(fid) for fid in body.funcionalidade_ids],
                "status": "rascunho",
                "conteudo": markdown,
                "criado_em": agora,
            }
        )
        .execute()
    )
    if not insert_resp.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar o boletim")

    row = insert_resp.data[0]
    return BoletimResponse(
        id=row["id"],
        project_id=row["project_id"],
        sprint_numero=row.get("sprint_numero"),
        funcionalidade_ids=row.get("funcionalidade_ids") or [],
        status=row["status"],
        retorno_tipo=row.get("retorno_tipo"),
        conteudo=row["conteudo"],
        criado_em=row["criado_em"],
        enviado_em=row.get("enviado_em"),
        retorno_em=row.get("retorno_em"),
    )


@router.get("/{project_id}", response_model=list[BoletimResponse])
async def listar_boletins(project_id: str):
    """Lista todos os boletins de aceite de um projeto, mais recentes primeiro."""
    client = get_client()

    resp = (
        client.table("boletins_aceite")
        .select("*")
        .eq("project_id", project_id)
        .order("criado_em", desc=True)
        .execute()
    )
    rows = resp.data or []
    return [
        BoletimResponse(
            id=r["id"],
            project_id=r["project_id"],
            sprint_numero=r.get("sprint_numero"),
            funcionalidade_ids=r.get("funcionalidade_ids") or [],
            status=r["status"],
            retorno_tipo=r.get("retorno_tipo"),
            conteudo=r["conteudo"],
            criado_em=r["criado_em"],
            enviado_em=r.get("enviado_em"),
            retorno_em=r.get("retorno_em"),
        )
        for r in rows
    ]


@router.patch("/{id}", response_model=BoletimResponse)
async def atualizar_status_boletim(id: str, body: BoletimPatch):
    """Atualiza o status de um boletim de aceite com validação de sequência.

    Segurança (T-12-05): Transições válidas enforced via TRANSICOES_VALIDAS.
    Segurança (T-12-06): retorno_tipo obrigatório quando status=ajuste.
    Segurança (T-12-08): funcionalidades já verificadas no POST /boletins — ids são confiáveis.
    """
    client = get_client()

    # Buscar boletim (404 se não existe)
    boletim_resp = (
        client.table("boletins_aceite").select("*").eq("id", id).execute()
    )
    if not boletim_resp.data:
        raise HTTPException(status_code=404, detail="Boletim não encontrado")
    boletim = boletim_resp.data[0]

    status_atual = boletim["status"]
    novo_status = body.status

    # Validar sequência de status (T-12-05, RESEARCH Pitfall 2)
    if novo_status not in TRANSICOES_VALIDAS.get(status_atual, set()):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transição inválida: {status_atual} → {novo_status}. "
                "Transições válidas: rascunho→enviado, enviado→aprovado, enviado→ajuste"
            ),
        )

    # Validar retorno_tipo obrigatório para status=ajuste (T-12-06, D-06, RESEARCH Pitfall 3)
    if novo_status == "ajuste" and body.retorno_tipo not in ("bug", "mudanca_escopo"):
        raise HTTPException(
            status_code=422,
            detail="retorno_tipo é obrigatório quando status = ajuste (valores aceitos: bug, mudanca_escopo)",
        )

    # Derivar novo status_cliente para as funcionalidades do lote (D-05)
    # enviado → status_cliente = "enviado"
    # aprovado → status_cliente = "aprovado"
    # ajuste → status_cliente = "ajuste_pedido"
    _STATUS_CLIENTE_MAP: dict[str, str] = {
        "enviado": "enviado",
        "aprovado": "aprovado",
        "ajuste": "ajuste_pedido",
    }
    novo_status_cliente = _STATUS_CLIENTE_MAP[novo_status]

    agora = datetime.now(timezone.utc)

    # Atualizar status_cliente de cada funcionalidade do lote com TransicaoStatus (RESEARCH Pattern 2, Pitfall 4)
    funcionalidade_ids: list[str] = boletim.get("funcionalidade_ids") or []
    for func_id in funcionalidade_ids:
        # Buscar status_cliente atual da funcionalidade
        func_resp = (
            client.table("funcionalidades")
            .select("status_cliente")
            .eq("id", func_id)
            .execute()
        )
        if not func_resp.data:
            continue
        status_anterior = func_resp.data[0].get("status_cliente") or "nao_enviado"

        # Registrar transição e atualizar funcionalidade
        _registrar_transicao_status_cliente(
            client, func_id, status_anterior, novo_status_cliente, agora
        )

    # Montar campos de update do boletim
    campos_update: dict = {"status": novo_status}
    if novo_status == "enviado":
        campos_update["enviado_em"] = agora.isoformat()
    elif novo_status in ("aprovado", "ajuste"):
        campos_update["retorno_em"] = agora.isoformat()
        campos_update["retorno_tipo"] = body.retorno_tipo

    # Executar update do boletim
    update_resp = (
        client.table("boletins_aceite")
        .update(campos_update)
        .eq("id", id)
        .execute()
    )
    if not update_resp.data:
        raise HTTPException(status_code=500, detail="Falha ao atualizar o boletim")

    row = update_resp.data[0]
    return BoletimResponse(
        id=row["id"],
        project_id=row["project_id"],
        sprint_numero=row.get("sprint_numero"),
        funcionalidade_ids=row.get("funcionalidade_ids") or [],
        status=row["status"],
        retorno_tipo=row.get("retorno_tipo"),
        conteudo=row["conteudo"],
        criado_em=row["criado_em"],
        enviado_em=row.get("enviado_em"),
        retorno_em=row.get("retorno_em"),
    )
