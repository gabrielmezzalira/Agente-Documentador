"""Propostas de melhoria (PTA).

O candidato (operacional) propõe uma melhoria para o cliente; o PM aprova,
recusa com motivo ou deixa para depois. A aprovada vira uma task extra marcada
como "inovação" e rende bônus de pontuação no fechamento da sprint em que foi
aprovada (services/pontuacao.py, services/performance.py::_bonus_extra).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

import services.classificador_ciclo as ciclo
from models.schemas import PropostaMelhoriaCreate, PropostaMelhoriaDecisao, PropostaMelhoriaResponse
from routers.tasks import _resolver_operacional_id_da_pessoa
from services.auth import get_current_pessoa, require_not_operacional, require_project_access
from services.classificador_regua import texto_da_task
from services.previsto_sprint import marcas_ao_entrar_na_sprint
from services.sprints import get_current_sprint_id
from services.supabase_client import get_client

_LOG = logging.getLogger("docudata.propostas")

router = APIRouter(tags=["propostas"])

_DETAIL_NAO_PTA = "Propostas de melhoria só existem em projetos PTA."
_ABERTAS = ("pendente", "adiada")


def _projeto_pta(client, project_id: str) -> dict:
    resp = client.table("projects").select("id, subarea, modo_trabalho").eq("id", project_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    if resp.data[0].get("subarea") != "pta":
        raise HTTPException(status_code=422, detail=_DETAIL_NAO_PTA)
    return resp.data[0]


@router.post("/projects/{project_id}/propostas", response_model=PropostaMelhoriaResponse, status_code=201)
async def criar_proposta(project_id: str, data: PropostaMelhoriaCreate, pessoa: dict = Depends(get_current_pessoa)):
    if pessoa["cargo"] != "operacional":
        raise HTTPException(status_code=403, detail="Só o candidato propõe melhorias.")
    client = get_client()
    _projeto_pta(client, project_id)
    operacional_id = _resolver_operacional_id_da_pessoa(client, project_id, pessoa["email"])
    if not operacional_id:
        raise HTTPException(status_code=403, detail="Você não está vinculado a este projeto.")

    resp = client.table("propostas_melhoria").insert({
        "project_id": project_id,
        "operacional_id": operacional_id,
        "titulo": data.titulo,
        "valor_cliente": data.valor_cliente,
        "esforco": data.esforco,
    }).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao registrar a proposta")
    return resp.data[0]


@router.get("/projects/{project_id}/propostas", response_model=list[PropostaMelhoriaResponse])
async def listar_propostas(project_id: str, pessoa: dict = Depends(require_project_access)):
    client = get_client()
    _projeto_pta(client, project_id)
    query = client.table("propostas_melhoria").select("*").eq("project_id", project_id)
    if pessoa["cargo"] == "operacional":
        meu_id = _resolver_operacional_id_da_pessoa(client, project_id, pessoa["email"])
        if not meu_id:
            raise HTTPException(status_code=403, detail="Você não está vinculado a este projeto.")
        query = query.eq("operacional_id", meu_id)
    rows = query.order("criado_em", desc=True).execute().data or []

    nomes = {
        o["id"]: o["nome"]
        for o in (
            client.table("operacionais").select("id, nome").eq("project_id", project_id).execute().data or []
        )
    }
    # Abertas (pendentes e adiadas) primeiro; dentro de cada grupo, a ordem por criado_em desc já vem da query.
    rows = sorted(rows, key=lambda r: r["status"] not in _ABERTAS)
    return [{**r, "operacional_nome": nomes.get(r["operacional_id"])} for r in rows]


@router.post("/propostas/{proposta_id}/decisao", response_model=PropostaMelhoriaResponse)
async def decidir_proposta(
    proposta_id: str, data: PropostaMelhoriaDecisao, pessoa: dict = Depends(require_not_operacional)
):
    client = get_client()
    resp = client.table("propostas_melhoria").select("*").eq("id", proposta_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Proposta not found")
    proposta = resp.data[0]
    await require_project_access(proposta["project_id"], pessoa)
    projeto = _projeto_pta(client, proposta["project_id"])

    if proposta["status"] not in _ABERTAS:
        raise HTTPException(status_code=409, detail="Esta proposta já foi decidida.")

    agora = datetime.now(timezone.utc).isoformat()
    updates: dict = {"decidido_por": pessoa["id"], "decidido_em": agora}
    if data.acao == "recusar":
        updates.update({"status": "recusada", "motivo": data.motivo})
    elif data.acao == "adiar":
        updates.update({"status": "adiada", "motivo": data.motivo})
    else:
        task_id, sprint_id = _aprovar(client, proposta, projeto, pessoa)
        updates.update({"status": "aprovada", "task_id": task_id, "sprint_id": sprint_id})

    atualizada = client.table("propostas_melhoria").update(updates).eq("id", proposta_id).execute().data
    return atualizada[0] if atualizada else {**proposta, **updates}


def _aprovar(client, proposta: dict, projeto: dict, pessoa: dict) -> tuple[str, str | None]:
    """Cria a task de inovação e a classificação manual. Devolve (task_id, sprint_id)."""
    project_id = proposta["project_id"]
    sprint_id = get_current_sprint_id(client, project_id)
    sprint_iniciada = False
    if sprint_id:
        sp = client.table("sprints").select("id, iniciada").eq("id", sprint_id).execute().data
        sprint_iniciada = bool(sp and sp[0].get("iniciada"))

    descricao = "Valor para o cliente: " + proposta["valor_cliente"]
    payload: dict = {
        "project_id": project_id,
        "titulo": proposta["titulo"],
        "descricao": descricao,
        "pontos": proposta["esforco"],
        "coluna_kanban": "planejado",
        "ordem": 0,
        "checklist": [],
        "extra": True,
        "inovacao": True,
        "requer_aprovacao": False,
    }
    if projeto.get("modo_trabalho") != "PULL":
        payload["operacional_id"] = proposta["operacional_id"]
    if sprint_id:
        payload["sprint_id"] = sprint_id
        payload.update(marcas_ao_entrar_na_sprint(sprint_iniciada, True))
        if sprint_iniciada:
            payload["entrou_em_andamento_em"] = datetime.now(timezone.utc).isoformat()

    criada = client.table("tasks").insert(payload).execute().data
    if not criada:
        raise HTTPException(status_code=500, detail="Failed to create task")
    task_id = criada[0]["id"]
    try:
        ciclo.gravar_classificacao(
            client, task_id, ciclo.resultado_manual(proposta["esforco"]), tipo="criacao",
            criado_por=pessoa["id"], texto=texto_da_task(proposta["titulo"], descricao, []),
        )
        if sprint_iniciada:
            ciclo.travar_nivel(client, [task_id])
    except Exception:
        _LOG.error("falha ao classificar a task da proposta %s", proposta["id"], exc_info=True)
        client.table("tasks").delete().eq("id", task_id).execute()
        raise HTTPException(
            status_code=503,
            detail="Nível do gerente indisponível: aplique a migração v12.",
        )
    return task_id, sprint_id
