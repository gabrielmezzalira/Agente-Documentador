from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    AvaliacaoGerenteCreate,
    AvaliacaoGerenteResponse,
    ConfirmarAvaliacaoResponse,
    PendenciaAvaliacaoResponse,
)
from services.auth import get_current_pessoa
from services.supabase_client import get_client

router = APIRouter(prefix="/avaliacoes", tags=["avaliacoes"])

_EDITAVEL_HORAS = 48


def _operacionais_com_task_na_sprint(client, sprint_id: str) -> list[dict]:
    task_rows = (
        client.table("tasks").select("operacional_id").eq("sprint_id", sprint_id).execute().data or []
    )
    operacional_ids = {t["operacional_id"] for t in task_rows if t.get("operacional_id")}
    if not operacional_ids:
        return []
    return (
        client.table("operacionais")
        .select("id, nome, email, project_id")
        .in_("id", list(operacional_ids))
        .execute()
        .data or []
    )


def _buscar_ultima_avaliacao_outro_projeto(client, operacional: dict) -> Optional[dict]:
    if not operacional.get("email"):
        return None
    outras_linhas = (
        client.table("operacionais")
        .select("id, project_id")
        .eq("email", operacional["email"])
        .neq("project_id", operacional["project_id"])
        .execute()
        .data or []
    )
    if not outras_linhas:
        return None
    outros_ids = [o["id"] for o in outras_linhas]
    projeto_por_operacional = {o["id"]: o["project_id"] for o in outras_linhas}

    avals = (
        client.table("avaliacoes_gerente")
        .select("*")
        .in_("operacional_id", outros_ids)
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
        .data or []
    )
    if not avals:
        return None
    aval = avals[0]
    project_id = projeto_por_operacional[aval["operacional_id"]]
    proj_resp = client.table("projects").select("name").eq("id", project_id).execute().data
    project_name = proj_resp[0]["name"] if proj_resp else "—"
    return {
        "avaliacao_id": aval["id"],
        "project_name": project_name,
        "criado_em": aval["criado_em"],
        "resposta_1": aval["resposta_1"],
        "resposta_2": aval["resposta_2"],
        "resposta_3": aval["resposta_3"],
        "resposta_4": aval["resposta_4"],
        "resposta_5": aval["resposta_5"],
        "resposta_6": aval["resposta_6"],
        "resposta_7": aval["resposta_7"],
    }


@router.get("/{sprint_id}/pendencias", response_model=list[PendenciaAvaliacaoResponse])
async def listar_pendencias(sprint_id: str):
    client = get_client()
    operacionais = _operacionais_com_task_na_sprint(client, sprint_id)
    if not operacionais:
        return []

    ja_avaliados = (
        client.table("avaliacoes_gerente").select("operacional_id").eq("sprint_id", sprint_id).execute().data or []
    )
    avaliados_ids = {a["operacional_id"] for a in ja_avaliados}
    pendentes = [op for op in operacionais if op["id"] not in avaliados_ids]

    return [
        {
            "operacional_id": op["id"],
            "nome": op["nome"],
            "ultima_avaliacao_outro_projeto": _buscar_ultima_avaliacao_outro_projeto(client, op),
        }
        for op in pendentes
    ]


@router.post("", response_model=AvaliacaoGerenteResponse, status_code=201)
async def criar_ou_atualizar_avaliacao(data: AvaliacaoGerenteCreate, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    agora = datetime.now(timezone.utc)

    existing = (
        client.table("avaliacoes_gerente")
        .select("*")
        .eq("operacional_id", data.operacional_id)
        .eq("sprint_id", data.sprint_id)
        .execute()
        .data
    )

    payload = {
        "operacional_id": data.operacional_id,
        "sprint_id": data.sprint_id,
        "gerente_id": pessoa["id"],
        "resposta_1": data.resposta_1,
        "resposta_2": data.resposta_2,
        "resposta_3": data.resposta_3,
        "resposta_4": data.resposta_4,
        "resposta_5": data.resposta_5,
        "resposta_6": data.resposta_6,
        "resposta_7": data.resposta_7,
    }
    if data.reaproveitada_de:
        payload["reaproveitada_de"] = data.reaproveitada_de

    if existing:
        row = existing[0]
        editavel_ate_raw = row["editavel_ate"]
        if isinstance(editavel_ate_raw, str):
            editavel_ate = datetime.fromisoformat(editavel_ate_raw.replace("Z", "+00:00"))
        else:
            editavel_ate = editavel_ate_raw
        if agora > editavel_ate:
            raise HTTPException(status_code=409, detail="Janela de edição de 48h já encerrada para esta avaliação")
        resp = client.table("avaliacoes_gerente").update(payload).eq("id", row["id"]).execute()
    else:
        payload["criado_em"] = agora.isoformat()
        payload["editavel_ate"] = (agora + timedelta(hours=_EDITAVEL_HORAS)).isoformat()
        resp = client.table("avaliacoes_gerente").insert(payload).execute()

    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar avaliação")
    return resp.data[0]


@router.post("/{sprint_id}/confirmar", response_model=ConfirmarAvaliacaoResponse)
async def confirmar_avaliacao_semanal(sprint_id: str):
    client = get_client()
    pendencias = await listar_pendencias(sprint_id)
    if pendencias:
        nomes = ", ".join(p["nome"] for p in pendencias)
        raise HTTPException(status_code=409, detail=f"Ainda há avaliações pendentes: {nomes}")

    agora_iso = datetime.now(timezone.utc).isoformat()
    resp = client.table("sprints").update({"avaliacao_completa_em": agora_iso}).eq("id", sprint_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return {"sprint_id": sprint_id, "avaliacao_completa_em": resp.data[0]["avaliacao_completa_em"]}
