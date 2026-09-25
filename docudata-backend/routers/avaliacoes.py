from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    AvaliacaoEdicaoItem,
    AvaliacaoGerenteCreate,
    AvaliacaoGerenteEdicao,
    AvaliacaoGerenteResponse,
    AvaliacaoHistoricoItem,
    ConfirmarAvaliacaoResponse,
    ElegivelResponse,
    PendenciaAvaliacaoResponse,
)
from services.auth import get_current_pessoa, require_not_operacional, require_role
from services.elegibilidade import listar_vinculados_no_projeto
from services.pontuacao import calcular_e_travar_pontuacao, sincronizar_snapshot_gerente
from services.sprints import iniciar_sprint_e_ancorar_tasks
from services.supabase_client import get_client

router = APIRouter(prefix="/avaliacoes", tags=["avaliacoes"])

_EDITAVEL_HORAS = 48


def _operacionais_elegiveis(client, sprint_id: str) -> list[dict]:
    """Elegível = vinculado ao projeto (Entrega 2), não mais "tem task na
    sprint" — corrige o bug de PULL onde quem não puxava nada nunca aparecia
    como pendente nem era avaliado. Ver
    docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
    sprint_resp = client.table("sprints").select("project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        return []
    project_id = sprint_resp.data[0]["project_id"]
    momento = datetime.now(timezone.utc).isoformat()
    return listar_vinculados_no_projeto(client, project_id, momento)


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


_CAMPOS_RESPOSTA = ("resposta_1", "resposta_2", "resposta_3", "resposta_4", "resposta_5", "resposta_6", "resposta_7")


def _por_id(client, tabela: str, colunas: str, ids) -> dict[str, dict]:
    ids = list({i for i in ids if i})
    if not ids:
        return {}
    rows = client.table(tabela).select(colunas).in_("id", ids).execute().data or []
    return {r["id"]: r for r in rows}


def _montar_historico(client, avaliacoes: list[dict]) -> list[dict]:
    """Enriquece avaliações com nomes (projeto, sprint, operacional, avaliador)
    e resumo de edições, em lote — uma query por tabela, não por linha."""
    if not avaliacoes:
        return []
    sprints = _por_id(client, "sprints", "id, numero, project_id", [a["sprint_id"] for a in avaliacoes])
    projetos = _por_id(client, "projects", "id, name, modo_trabalho", [s["project_id"] for s in sprints.values()])
    operacionais = _por_id(client, "operacionais", "id, nome", [a["operacional_id"] for a in avaliacoes])
    edicoes = (
        client.table("avaliacoes_gerente_edicoes")
        .select("avaliacao_id, editor_id, criado_em")
        .in_("avaliacao_id", [a["id"] for a in avaliacoes])
        .execute()
        .data or []
    )
    pessoas = _por_id(
        client, "pessoa", "id, nome",
        [a["gerente_id"] for a in avaliacoes] + [e["editor_id"] for e in edicoes],
    )

    total: dict[str, int] = {}
    ultima: dict[str, dict] = {}
    for e in edicoes:
        aid = e["avaliacao_id"]
        total[aid] = total.get(aid, 0) + 1
        if aid not in ultima or str(e["criado_em"]) > str(ultima[aid]["criado_em"]):
            ultima[aid] = e

    itens = []
    for a in avaliacoes:
        sprint = sprints.get(a["sprint_id"], {})
        projeto = projetos.get(sprint.get("project_id"), {})
        ult = ultima.get(a["id"])
        itens.append({
            "id": a["id"],
            "operacional_id": a["operacional_id"],
            "operacional_nome": operacionais.get(a["operacional_id"], {}).get("nome", "—"),
            "sprint_id": a["sprint_id"],
            "sprint_numero": sprint.get("numero"),
            "projeto_id": sprint.get("project_id"),
            "projeto_nome": projeto.get("name", "—"),
            "modo_trabalho": projeto.get("modo_trabalho") or "ATRIBUICAO",
            "avaliador_nome": pessoas.get(a["gerente_id"], {}).get("nome", "—"),
            **{c: a.get(c) for c in _CAMPOS_RESPOSTA},
            "criado_em": a["criado_em"],
            "total_edicoes": total.get(a["id"], 0),
            "ultima_edicao_em": ult["criado_em"] if ult else None,
            "ultima_edicao_por": pessoas.get(ult["editor_id"], {}).get("nome", "—") if ult else None,
        })
    itens.sort(key=lambda i: (i["projeto_nome"], -(i["sprint_numero"] or 0), i["operacional_nome"]))
    return itens


@router.get("/historico", response_model=list[AvaliacaoHistoricoItem])
async def historico_avaliacoes(project_id: Optional[str] = None, sprint_id: Optional[str] = None):
    """Todas as avaliações (gerente/líder/owner veem tudo — decisão da spec
    2026-09-25), filtráveis por projeto ou sprint."""
    client = get_client()
    q = client.table("avaliacoes_gerente").select("*")
    if sprint_id:
        q = q.eq("sprint_id", sprint_id)
    elif project_id:
        sprint_ids = [
            s["id"] for s in client.table("sprints").select("id").eq("project_id", project_id).execute().data or []
        ]
        if not sprint_ids:
            return []
        q = q.in_("sprint_id", sprint_ids)
    return _montar_historico(client, q.execute().data or [])


@router.patch("/{avaliacao_id}", response_model=AvaliacaoHistoricoItem)
async def editar_avaliacao(
    avaliacao_id: str,
    data: AvaliacaoGerenteEdicao,
    pessoa: dict = Depends(get_current_pessoa),
):
    """Correção de nota dada errado, sem prazo (a janela de 48h vale só pro
    questionário). Mantém o avaliador original e grava o log com motivo."""
    client = get_client()
    encontrada = client.table("avaliacoes_gerente").select("*").eq("id", avaliacao_id).execute().data
    if not encontrada:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    atual = encontrada[0]

    novas = {
        "resposta_1": data.resposta_1,
        "resposta_2": data.resposta_2,
        "resposta_3": data.resposta_3,
        "resposta_4": data.resposta_4,
        "resposta_5": data.resposta_5,
        "resposta_7": data.resposta_7,
    }
    if all(atual.get(k) == v for k, v in novas.items()):
        raise HTTPException(status_code=422, detail="Nenhuma nota alterada.")

    antes = {c: atual.get(c) for c in _CAMPOS_RESPOSTA}
    atualizada = client.table("avaliacoes_gerente").update(novas).eq("id", avaliacao_id).execute().data
    if not atualizada:
        raise HTTPException(status_code=500, detail="Falha ao salvar avaliação")
    atualizada = atualizada[0]

    client.table("avaliacoes_gerente_edicoes").insert({
        "avaliacao_id": avaliacao_id,
        "editor_id": pessoa["id"],
        "antes": antes,
        "depois": {**antes, **novas},
        "motivo": data.motivo,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }).execute()

    sincronizar_snapshot_gerente(client, atualizada)
    return _montar_historico(client, [atualizada])[0]


@router.get("/{avaliacao_id}/edicoes", response_model=list[AvaliacaoEdicaoItem])
async def listar_edicoes(avaliacao_id: str):
    client = get_client()
    rows = (
        client.table("avaliacoes_gerente_edicoes")
        .select("*")
        .eq("avaliacao_id", avaliacao_id)
        .order("criado_em", desc=True)
        .execute()
        .data or []
    )
    pessoas = _por_id(client, "pessoa", "id, nome", [r["editor_id"] for r in rows])
    return [
        {
            "id": r["id"],
            "editor_nome": pessoas.get(r["editor_id"], {}).get("nome", "—"),
            "antes": r["antes"],
            "depois": r["depois"],
            "motivo": r["motivo"],
            "criado_em": r["criado_em"],
        }
        for r in rows
    ]


@router.get("/{sprint_id}/pendencias", response_model=list[PendenciaAvaliacaoResponse])
async def listar_pendencias(sprint_id: str):
    client = get_client()
    operacionais = _operacionais_elegiveis(client, sprint_id)
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


@router.get("/{sprint_id}/elegiveis", response_model=list[ElegivelResponse], dependencies=[Depends(require_not_operacional)])
async def listar_elegiveis(sprint_id: str):
    """RF-C7 (Entrega 2): todo operacional vinculado ao projeto no momento da
    consulta, com contagem de tasks na sprint (0 é válido) e se já tem
    avaliação registrada — audita quem entra no denominador da Avaliação
    Semanal mesmo sem ter puxado nenhuma task."""
    client = get_client()
    sprint_resp = client.table("sprints").select("project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        raise HTTPException(status_code=404, detail="Sprint not found")

    operacionais = _operacionais_elegiveis(client, sprint_id)

    task_rows = client.table("tasks").select("operacional_id").eq("sprint_id", sprint_id).execute().data or []
    tasks_por_operacional: dict[str, int] = {}
    for t in task_rows:
        op = t.get("operacional_id")
        if op:
            tasks_por_operacional[op] = tasks_por_operacional.get(op, 0) + 1

    aval_rows = client.table("avaliacoes_gerente").select("operacional_id").eq("sprint_id", sprint_id).execute().data or []
    avaliados_ids = {a["operacional_id"] for a in aval_rows}

    return [
        {
            "operacional_id": op["id"],
            "nome": op["nome"],
            "tasks_na_sprint": tasks_por_operacional.get(op["id"], 0),
            "avaliado": op["id"] in avaliados_ids,
        }
        for op in operacionais
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

    pontuacoes = calcular_e_travar_pontuacao(client, sprint_id)

    agora_iso = datetime.now(timezone.utc).isoformat()
    resp = client.table("sprints").update({"avaliacao_completa_em": agora_iso}).eq("id", sprint_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Sprint not found")

    # ALERT-04: confirmar a avaliação da última sprint ativa também conta como
    # "início" da próxima, pra destravar o relógio de travamento automático das
    # tasks que já estavam planejadas nela — sem depender do gerente lembrar de
    # clicar em "Iniciar próxima sprint" também. Best-effort: a avaliação já foi
    # travada acima e não pode falhar por causa disso.
    try:
        sprint_atual = resp.data[0]
        proxima = (
            client.table("sprints")
            .select("id, iniciada")
            .eq("project_id", sprint_atual["project_id"])
            .eq("numero", sprint_atual["numero"] + 1)
            .execute()
            .data
        )
        if proxima and not proxima[0]["iniciada"]:
            iniciar_sprint_e_ancorar_tasks(client, proxima[0]["id"])
    except Exception:
        pass  # best-effort

    return {
        "sprint_id": sprint_id,
        "avaliacao_completa_em": resp.data[0]["avaliacao_completa_em"],
        "pontuacao_travada_count": len(pontuacoes),
    }


@router.delete("/{sprint_id}/confirmar", response_model=ConfirmarAvaliacaoResponse, dependencies=[Depends(require_role("lider"))])
async def reabrir_avaliacao_semanal(sprint_id: str):
    """Desfaz o fechamento de uma sprint: apaga a pontuação travada e limpa a
    marca de conclusão, para que o gerente corrija o Kanban e confirme de novo.

    Restrito ao Líder porque mexe em dado que já entrou no ranking. As avaliações
    do questionário NÃO são apagadas: o gerente não precisa responder tudo de
    novo, e a janela de 48h de edição continua valendo como antes.

    O marco de tempo que evita dupla contagem (services/pontuacao.py) é derivado
    do fechamento mais recente do projeto, então apagar estas linhas devolve o
    marco ao estado anterior automaticamente."""
    client = get_client()

    sprint = client.table("sprints").select("id, avaliacao_completa_em").eq("id", sprint_id).execute()
    if not sprint.data:
        raise HTTPException(status_code=404, detail="Sprint not found")
    if not sprint.data[0].get("avaliacao_completa_em"):
        raise HTTPException(status_code=409, detail="Esta sprint não está fechada.")

    apagadas = (
        client.table("pontuacao_operacional_sprint").delete().eq("sprint_id", sprint_id).execute().data or []
    )
    # Eventos que tinham sido redirecionados para cá voltam a ficar pendentes de
    # um fechamento; sem isso eles seriam contados no próximo fechamento também.
    client.table("eventos_pontuacao_tardios").delete().eq("sprint_id_alvo", sprint_id).execute()

    resp = client.table("sprints").update({"avaliacao_completa_em": None}).eq("id", sprint_id).execute()
    return {
        "sprint_id": sprint_id,
        "avaliacao_completa_em": resp.data[0]["avaliacao_completa_em"],
        "pontuacao_travada_count": len(apagadas),
    }
