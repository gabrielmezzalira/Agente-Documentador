from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from models.schemas import BoletimCreate, BoletimResponse
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
