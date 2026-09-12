"""Pedido de task extra.

Nasceu de um feedback real: operacional termina o que tinha e não tem
proximidade (ou jeito) de pedir mais trabalho, então fica parado. O botão troca
uma conversa social por uma ação de um clique, e o gerente recebe por e-mail.

A task concedida é marcada como extra: ela não consome o orçamento de pontos da
sprint e, se concluída antes do fechamento, vira bônus no score em vez de entrar
em Entrega (services/performance.py::_bonus_extra).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    SolicitacaoTaskCreate,
    SolicitacaoTaskResponse,
    SolicitacaoTaskResolve,
)
from services.auth import get_current_pessoa, require_not_operacional
from services.email_service import email_solicitacao_task, send_email
from services.sprints import get_current_sprint_id
from services.supabase_client import get_client

_LOG = logging.getLogger("docudata.solicitacoes")

router = APIRouter(prefix="/solicitacoes-task", tags=["solicitacoes-task"])


@router.post("", response_model=SolicitacaoTaskResponse, status_code=201)
async def criar_solicitacao(data: SolicitacaoTaskCreate, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()

    op_resp = (
        client.table("operacionais")
        .select("id, nome, project_id")
        .eq("id", data.operacional_id)
        .execute()
    )
    if not op_resp.data:
        raise HTTPException(status_code=404, detail="Operacional not found")
    operacional = op_resp.data[0]
    project_id = operacional["project_id"]

    # Só faz sentido pedir mais trabalho quando não sobrou nada em aberto.
    abertas = (
        client.table("tasks")
        .select("id")
        .eq("operacional_id", data.operacional_id)
        .neq("coluna_kanban", "concluida")
        .execute()
        .data or []
    )
    if abertas:
        raise HTTPException(
            status_code=409,
            detail=f"Você ainda tem {len(abertas)} task(s) em aberto. Conclua antes de pedir mais.",
        )

    pendente = (
        client.table("solicitacoes_task")
        .select("*")
        .eq("operacional_id", data.operacional_id)
        .eq("status", "pendente")
        .execute()
        .data or []
    )
    if pendente:
        return pendente[0]

    sprint_id = get_current_sprint_id(client, project_id)
    payload = {
        "project_id": project_id,
        "sprint_id": sprint_id,
        "operacional_id": data.operacional_id,
    }
    if data.sugestao is not None:
        payload["sugestao"] = data.sugestao.strip() or None

    resp = client.table("solicitacoes_task").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao registrar o pedido")

    _avisar_gerente(client, project_id, operacional["nome"], sprint_id, payload.get("sugestao"))
    return resp.data[0]


def _avisar_gerente(
    client, project_id: str, operacional_nome: str, sprint_id: str | None, sugestao: str | None = None
) -> None:
    """Best-effort: o pedido vale mesmo que o e-mail falhe, porque ele também
    aparece no Kanban do gerente."""
    try:
        proj = client.table("projects").select("name").eq("id", project_id).execute().data
        projeto_nome = proj[0]["name"] if proj else "projeto"

        sprint_numero = None
        if sprint_id:
            sp = client.table("sprints").select("numero").eq("id", sprint_id).execute().data
            sprint_numero = sp[0]["numero"] if sp else None

        gerentes = (
            client.table("pessoa").select("email").in_("cargo", ["gerente", "lider"]).execute().data or []
        )
        if not gerentes:
            return

        subject, html = email_solicitacao_task(projeto_nome, operacional_nome, sprint_numero, sugestao)
        for g in gerentes:
            send_email(g["email"], subject, html)
    except Exception as exc:
        _LOG.warning("notificacao_solicitacao_falhou exc=%s", type(exc).__name__)


@router.get("/projects/{project_id}", response_model=list[SolicitacaoTaskResponse])
async def listar_solicitacoes(project_id: str, status: str = "pendente"):
    client = get_client()
    rows = (
        client.table("solicitacoes_task")
        .select("*")
        .eq("project_id", project_id)
        .eq("status", status)
        .order("criado_em", desc=True)
        .execute()
        .data or []
    )
    if not rows:
        return []

    nomes = {
        o["id"]: o["nome"]
        for o in (
            client.table("operacionais")
            .select("id, nome")
            .in_("id", list({r["operacional_id"] for r in rows}))
            .execute()
            .data or []
        )
    }
    return [{**r, "operacional_nome": nomes.get(r["operacional_id"], "—")} for r in rows]


@router.patch(
    "/{solicitacao_id}",
    response_model=SolicitacaoTaskResponse,
    dependencies=[Depends(require_not_operacional)],
)
async def resolver_solicitacao(solicitacao_id: str, data: SolicitacaoTaskResolve):
    client = get_client()
    check = client.table("solicitacoes_task").select("id").eq("id", solicitacao_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Solicitação not found")

    resp = (
        client.table("solicitacoes_task")
        .update({
            "status": data.status,
            "respondido_em": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", solicitacao_id)
        .execute()
    )
    return resp.data[0]
