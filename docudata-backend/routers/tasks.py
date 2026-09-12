import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import (
    RedistribuirPontosRequest,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskReordenarItem,
    TaskTransicaoResponse,
    TaskSugestaoResponse,
    TaskSugestaoResolve,
)
from services.auth import get_current_pessoa, require_not_operacional, require_project_access
from services.email_service import email_task_atribuida, email_task_concluida, send_email
from services.supabase_client import get_client
from services.wip_check import check_wip
from services.task_events import on_task_transition
from services.spi_health import auto_update_sprint_health
from services.pontuacao import rotear_evento_pos_fechamento

_LOG = logging.getLogger("docudata.tasks")

router = APIRouter(prefix="/tasks", tags=["tasks"])

_CAMPOS_TRANSICAO = {"coluna_kanban", "operacional_id", "sprint_id", "bloqueado"}

# Operacional só executa: move a task no kanban e marca checklist. Pontos,
# sprint, responsável, título/descrição e bloqueio são decisão de gerente/líder.
_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL = {
    "titulo", "descricao", "pontos", "funcionalidade_id", "sprint_id",
    "operacional_id", "ordem", "extra", "bloqueado", "motivo_bloqueio",
    "bloqueado_manual", "bloqueado_por", "bloqueado_resolvido_por",
}


def _registrar_task_transicao(
    client,
    task_id: str,
    task_atual: dict,
    campo: str,
    novo_valor,
    autor: Optional[str],
    motivo: Optional[str],
    agora: datetime,
) -> Optional[str]:
    anterior = (
        client.table("task_transicoes")
        .select("timestamp")
        .eq("task_id", task_id)
        .eq("campo", campo)
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    if anterior.data:
        ts_anterior = datetime.fromisoformat(anterior.data[0]["timestamp"]).replace(tzinfo=timezone.utc)
    else:
        ts_anterior = datetime.fromisoformat(task_atual["created_at"]).replace(tzinfo=timezone.utc)

    duracao = int((agora - ts_anterior).total_seconds())
    resp = client.table("task_transicoes").insert({
        "task_id": task_id,
        "campo": campo,
        "de": str(task_atual.get(campo)) if task_atual.get(campo) is not None else None,
        "para": str(novo_valor) if novo_valor is not None else None,
        "autor": autor,
        "timestamp": agora.isoformat(),
        "motivo": motivo,
        "duracao_fase_anterior_segundos": duracao,
        "operacional_id": task_atual.get("operacional_id"),
    }).execute()
    return resp.data[0]["id"] if resp.data else None


def _avisar_operacional_atribuicao(client, task: dict) -> None:
    """Best-effort: notifica por e-mail o operacional designado para a task.
    A atribuição vale mesmo que o e-mail falhe — o nome já aparece no card do Kanban."""
    try:
        operacional_id = task.get("operacional_id")
        if not operacional_id:
            return
        op = client.table("operacionais").select("nome, email").eq("id", operacional_id).execute().data
        if not op or not op[0].get("email"):
            return
        operacional_nome = op[0]["nome"]
        operacional_email = op[0]["email"]

        proj = client.table("projects").select("name").eq("id", task["project_id"]).execute().data
        projeto_nome = proj[0]["name"] if proj else "projeto"

        sprint_numero = None
        sprint_id = task.get("sprint_id")
        if sprint_id:
            sp = client.table("sprints").select("numero").eq("id", sprint_id).execute().data
            sprint_numero = sp[0]["numero"] if sp else None

        subject, html = email_task_atribuida(projeto_nome, operacional_nome, task["titulo"], sprint_numero)
        send_email(operacional_email, subject, html)
    except Exception as exc:
        _LOG.warning("notificacao_atribuicao_falhou exc=%s", type(exc).__name__)


def _avisar_gerente_task_concluida(client, task: dict) -> None:
    """Best-effort: avisa gerente/líder quando um operacional marca uma task
    como concluída. A conclusão vale mesmo que o e-mail falhe."""
    try:
        proj = client.table("projects").select("name").eq("id", task["project_id"]).execute().data
        projeto_nome = proj[0]["name"] if proj else "projeto"

        operacional_nome = "Alguém"
        op_id = task.get("operacional_id")
        if op_id:
            op = client.table("operacionais").select("nome").eq("id", op_id).execute().data
            if op:
                operacional_nome = op[0]["nome"]

        sprint_numero = None
        sprint_id = task.get("sprint_id")
        if sprint_id:
            sp = client.table("sprints").select("numero").eq("id", sprint_id).execute().data
            sprint_numero = sp[0]["numero"] if sp else None

        gerentes = (
            client.table("pessoa").select("email").in_("cargo", ["gerente", "lider"]).execute().data or []
        )
        if not gerentes:
            return

        subject, html = email_task_concluida(projeto_nome, operacional_nome, task["titulo"], sprint_numero)
        for g in gerentes:
            send_email(g["email"], subject, html)
    except Exception as exc:
        print(f"[tasks] Aviso: falha ao notificar gerente sobre conclusão ({exc}) — task salva mesmo assim")


def _registrar_reabertura(
    client,
    task_id: str,
    transicao_id: Optional[str],
    operacional_id: Optional[str],
    motivo: Optional[str],
    agora: datetime,
) -> None:
    """TRANS-03: concluida -> em_andamento é a única transição que conta como reabertura."""
    client.table("task_reaberturas").insert({
        "task_id": task_id,
        "transicao_id": transicao_id,
        "operacional_id": operacional_id,
        "motivo": motivo,
        "timestamp": agora.isoformat(),
    }).execute()


def _pontos_usados_na_sprint(client, sprint_id: str, ignorar_task_id: str | None = None) -> int:
    """Soma dos pontos das tasks da sprint que consomem orçamento. Tasks extras
    ficam de fora: elas são trabalho concedido além do planejado."""
    query = client.table("tasks").select("id, pontos, extra").eq("sprint_id", sprint_id)
    if ignorar_task_id is not None:
        query = query.neq("id", ignorar_task_id)
    rows = query.execute().data or []
    return sum(t["pontos"] for t in rows if not t.get("extra"))


@router.post("/redistribuir-pontos", dependencies=[Depends(require_not_operacional)])
async def redistribuir_pontos(data: RedistribuirPontosRequest):
    """Encolhe proporcionalmente os pontos das tasks já existentes na sprint para
    abrir espaço para `pontos_novos`, em vez de simplesmente recusar a task nova.

    Cada task fica com no mínimo 1 ponto (a tabela não aceita 0), então sprints
    muito cheias podem não conseguir abrir o espaço pedido — nesse caso o pedido
    é recusado com o quanto daria para liberar."""
    client = get_client()

    sprint = (
        client.table("sprints")
        .select("id, pontos_orcamento")
        .eq("id", data.sprint_id)
        .execute()
    )
    if not sprint.data:
        raise HTTPException(status_code=404, detail="Sprint not found")
    orcamento = sprint.data[0].get("pontos_orcamento")
    if orcamento is None:
        raise HTTPException(status_code=409, detail="Esta sprint não tem orçamento de pontos definido.")

    tasks = (
        client.table("tasks")
        .select("id, titulo, pontos, extra")
        .eq("sprint_id", data.sprint_id)
        .execute()
        .data or []
    )
    elegiveis = [t for t in tasks if not t.get("extra")]
    if not elegiveis:
        raise HTTPException(status_code=409, detail="Não há tasks para redistribuir nesta sprint.")

    alvo = orcamento - data.pontos_novos
    if alvo < len(elegiveis):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Não dá para abrir {data.pontos_novos} pontos: as {len(elegiveis)} tasks da sprint "
                f"precisam de pelo menos 1 ponto cada, então o máximo liberável é "
                f"{orcamento - len(elegiveis)}."
            ),
        )

    total_atual = sum(t["pontos"] for t in elegiveis)
    novos: list[dict] = []
    for t in elegiveis:
        proporcional = max(1, round(t["pontos"] * alvo / total_atual))
        novos.append({**t, "novo": proporcional})

    # Arredondamento pode estourar ou sobrar; ajusta na task maior até bater.
    def soma():
        return sum(n["novo"] for n in novos)

    while soma() > alvo:
        maior = max((n for n in novos if n["novo"] > 1), key=lambda n: n["novo"], default=None)
        if maior is None:
            break
        maior["novo"] -= 1
    while soma() < alvo:
        maior = max(novos, key=lambda n: n["novo"])
        maior["novo"] += 1

    for n in novos:
        if n["novo"] != n["pontos"]:
            client.table("tasks").update({"pontos": n["novo"]}).eq("id", n["id"]).execute()

    return {
        "sprint_id": data.sprint_id,
        "pontos_orcamento": orcamento,
        "pontos_liberados": data.pontos_novos,
        "ajustes": [
            {"task_id": n["id"], "titulo": n["titulo"], "de": n["pontos"], "para": n["novo"]}
            for n in novos
        ],
    }


@router.post("", response_model=TaskResponse, status_code=201, dependencies=[Depends(require_not_operacional)])
async def create_task(data: TaskCreate):
    client = get_client()

    check = client.table("projects").select("id").eq("id", data.project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.operacional_id:
        op_check = (
            client.table("operacionais")
            .select("id")
            .eq("id", data.operacional_id)
            .eq("project_id", data.project_id)
            .execute()
        )
        if not op_check.data:
            raise HTTPException(status_code=422, detail="operacional_id não pertence a este projeto")

    if data.funcionalidade_id:
        fn_check = (
            client.table("funcionalidades")
            .select("id")
            .eq("id", data.funcionalidade_id)
            .eq("project_id", data.project_id)
            .execute()
        )
        if not fn_check.data:
            raise HTTPException(status_code=422, detail="funcionalidade_id não pertence a este projeto")

    if data.sprint_id:
        sp_check = (
            client.table("sprints")
            .select("id, pontos_orcamento, iniciada")
            .eq("id", data.sprint_id)
            .eq("project_id", data.project_id)
            .execute()
        )
        if not sp_check.data:
            raise HTTPException(status_code=422, detail="sprint_id não pertence a este projeto")
        orcamento = sp_check.data[0].get("pontos_orcamento")
        # Task extra é trabalho concedido além do planejado: por definição ela não
        # cabe no orçamento, então não é validada contra ele nem entra na soma.
        if orcamento is not None and not data.extra:
            usados = _pontos_usados_na_sprint(client, data.sprint_id)
            if usados + data.pontos > orcamento:
                mensagem = f"Orçamento da sprint excedido: restam {orcamento - usados} pontos."
                raise HTTPException(
                    status_code=409,
                    detail=mensagem,
                )

    payload: dict = {
        "project_id": data.project_id,
        "titulo": data.titulo,
        "pontos": data.pontos,
        "coluna_kanban": data.coluna_kanban,
        "ordem": data.ordem,
        "checklist": data.checklist or [],
        "extra": data.extra,
    }
    for field in ("funcionalidade_id", "sprint_id", "operacional_id", "descricao"):
        val = getattr(data, field, None)
        if val is not None:
            payload[field] = val

    # ALERT-01/ALERT-04: o relógio de travamento automático conta desde que a
    # task esteja ativa (planejado ou em_andamento) E a sprint dela já tenha
    # começado (sprints.iniciada) — task de sprint futura não deve contar tempo
    # parado antes da hora (evita alerta em massa quando a sprint finalmente
    # inicia; nesse momento iniciar_sprint_e_ancorar_tasks ancora essas tasks).
    if payload.get("coluna_kanban") != "concluida" and data.sprint_id:
        sprint_iniciada = bool(sp_check.data[0].get("iniciada")) if sp_check.data else False
        if sprint_iniciada:
            payload["entrou_em_andamento_em"] = datetime.now(timezone.utc).isoformat()

    resp = client.table("tasks").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create task")

    if payload.get("operacional_id"):
        _avisar_operacional_atribuicao(client, resp.data[0])

    return resp.data[0]


@router.get("", response_model=list[TaskResponse], dependencies=[Depends(require_project_access)])
async def list_tasks(
    project_id: str = Query(...),
    sprint_id: Optional[str] = Query(default=None),
    operacional_id: Optional[str] = Query(default=None),
    coluna: Optional[str] = Query(default=None),
    funcionalidade_id: Optional[str] = Query(default=None),
):
    client = get_client()
    query = (
        client.table("tasks")
        .select("*")
        .eq("project_id", project_id)
        .order("coluna_kanban", desc=False)
        .order("ordem", desc=False)
    )
    if sprint_id is not None:
        query = query.eq("sprint_id", sprint_id)
    if operacional_id is not None:
        query = query.eq("operacional_id", operacional_id)
    if coluna is not None:
        query = query.eq("coluna_kanban", coluna)
    if funcionalidade_id is not None:
        query = query.eq("funcionalidade_id", funcionalidade_id)

    return query.execute().data or []


# ── Sugestões — rotas fixas antes de /{task_id} para evitar captura pelo path param ──

@router.get("/sugestoes", response_model=list[TaskSugestaoResponse])
async def list_task_sugestoes(project_id: str = Query(...)):
    client = get_client()
    resp = (
        client.table("task_sugestoes")
        .select("*, tasks(titulo, project_id, coluna_kanban)")
        .is_("aceita", "null")
        .execute()
    )
    rows = resp.data or []
    result = []
    for row in rows:
        task_info = row.get("tasks") or {}
        if task_info.get("project_id") != project_id:
            continue
        result.append(TaskSugestaoResponse(
            id=row["id"],
            task_id=row["task_id"],
            task_titulo=task_info.get("titulo", ""),
            acao=row["acao"],
            motivo=row.get("motivo"),
            origem_ingestion_id=row.get("origem_ingestion_id"),
            aceita=row.get("aceita"),
            criado_em=row["criado_em"],
            task_coluna_atual=task_info.get("coluna_kanban"),
        ))
    return result


@router.patch("/sugestoes/{sugestao_id}", response_model=TaskSugestaoResponse)
async def resolve_task_sugestao(sugestao_id: str, data: TaskSugestaoResolve, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    resp = (
        client.table("task_sugestoes")
        .select("*, tasks(titulo, project_id, coluna_kanban)")
        .eq("id", sugestao_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Sugestão não encontrada")
    row = resp.data[0]

    if data.aceita and row["acao"] == "mover_para_concluida":
        task_id = row["task_id"]
        # Delega ao mesmo caminho gated usado por PATCH /tasks/{id} e POST /tasks/{id}/mover
        # (DoR/DoD/WIP + gravação em task_transicoes). Se patch_task levantar HTTPException
        # (ex.: DoD com checklist incompleto), a exceção propaga e a sugestão continua não
        # resolvida — o update de "aceita" abaixo nunca acontece.
        await patch_task(task_id, TaskUpdate(coluna_kanban="concluida", autor="sugestao_ia"), pessoa=pessoa)

    updated = (
        client.table("task_sugestoes")
        .update({"aceita": data.aceita})
        .eq("id", sugestao_id)
        .select("*, tasks(titulo, project_id, coluna_kanban)")
        .execute()
    )
    row = updated.data[0]
    task_info = row.get("tasks") or {}
    return TaskSugestaoResponse(
        id=row["id"],
        task_id=row["task_id"],
        task_titulo=task_info.get("titulo", ""),
        acao=row["acao"],
        motivo=row.get("motivo"),
        origem_ingestion_id=row.get("origem_ingestion_id"),
        aceita=row.get("aceita"),
        criado_em=row["criado_em"],
        task_coluna_atual=task_info.get("coluna_kanban"),
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    client = get_client()
    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return resp.data[0]


@router.get("/{task_id}/transicoes", response_model=list[TaskTransicaoResponse])
async def list_task_transicoes(task_id: str):
    client = get_client()
    resp = (
        client.table("task_transicoes")
        .select("*")
        .eq("task_id", task_id)
        .order("timestamp", desc=False)
        .execute()
    )
    return resp.data or []


@router.patch("/{task_id}", response_model=TaskResponse)
async def patch_task(task_id: str, data: TaskUpdate, pessoa: dict = Depends(get_current_pessoa)):
    if pessoa["cargo"] == "operacional":
        pedidos = set(data.model_dump(exclude_unset=True))
        negados = pedidos & _CAMPOS_BLOQUEADOS_PARA_OPERACIONAL
        if negados:
            raise HTTPException(
                status_code=403,
                detail=f"Operacional não pode alterar: {', '.join(sorted(negados))}",
            )

    client = get_client()

    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = resp.data[0]
    project_id = task["project_id"]

    if data.operacional_id is not None:
        op_check = (
            client.table("operacionais")
            .select("id")
            .eq("id", data.operacional_id)
            .eq("project_id", project_id)
            .execute()
        )
        if not op_check.data:
            raise HTTPException(status_code=422, detail="operacional_id não pertence a este projeto")

    if data.sprint_id is not None:
        sp_check = (
            client.table("sprints")
            .select("id")
            .eq("id", data.sprint_id)
            .eq("project_id", project_id)
            .execute()
        )
        if not sp_check.data:
            raise HTTPException(status_code=422, detail="sprint_id não pertence a este projeto")

    if data.pontos is not None or data.sprint_id is not None:
        sprint_id_efetivo = data.sprint_id if data.sprint_id is not None else task.get("sprint_id")
        pontos_efetivo = data.pontos if data.pontos is not None else task["pontos"]
        if sprint_id_efetivo:
            sp_orc = client.table("sprints").select("pontos_orcamento").eq("id", sprint_id_efetivo).execute()
            orcamento = sp_orc.data[0].get("pontos_orcamento") if sp_orc.data else None
            extra_efetivo = data.extra if data.extra is not None else task.get("extra", False)
            if orcamento is not None and not extra_efetivo:
                usados = _pontos_usados_na_sprint(client, sprint_id_efetivo, ignorar_task_id=task_id)
                if usados + pontos_efetivo > orcamento:
                    mensagem = f"Orçamento da sprint excedido: restam {orcamento - usados} pontos."
                    raise HTTPException(
                        status_code=409,
                        detail=mensagem,
                    )

    # WIP check — rejeita antes de qualquer escrita se o limite for ultrapassado
    coluna_nova = data.coluna_kanban
    coluna_atual = task.get("coluna_kanban")
    if coluna_nova is not None and coluna_nova != coluna_atual:
        # DoR: task sem sprint não pode ir para em_andamento
        sprint_efetivo = data.sprint_id if data.sprint_id is not None else task.get("sprint_id")
        if coluna_nova == "em_andamento" and not sprint_efetivo:
            raise HTTPException(
                status_code=409,
                detail="DoR: associe a task a uma sprint antes de movê-la para Em Andamento.",
            )
        # DoD: checklist deve estar completo (ou vazio) antes de ir para Concluída.
        # MET-07 (ganchos daily/commit/retrospectiva -> sinais de saúde) é explicitamente
        # NÃO implementado nesta task — deferido, não silenciosamente descartado.
        if coluna_nova == "concluida":
            checklist_efetivo = data.checklist if data.checklist is not None else task.get("checklist", [])
            pendentes = [item for item in (checklist_efetivo or []) if not item.get("done")]
            if pendentes:
                raise HTTPException(
                    status_code=409,
                    detail=f"DoD: {len(pendentes)} item(ns) do checklist ainda não concluído(s).",
                )
        op_efetivo = data.operacional_id if data.operacional_id is not None else task.get("operacional_id")
        ok, motivo = check_wip(client, project_id, op_efetivo, coluna_nova)
        if not ok:
            raise HTTPException(status_code=409, detail=motivo)

    # TRANS-05: desmarcar bloqueado_manual exige informar quem resolveu — gate roda
    # independentemente de mudança de coluna, antes de qualquer escrita.
    if (
        data.bloqueado_manual is not None
        and data.bloqueado_manual != task.get("bloqueado_manual", False)
        and data.bloqueado_manual is False
        and data.bloqueado_resolvido_por not in ("operacional", "gerente")
    ):
        raise HTTPException(
            status_code=422,
            detail="Informe quem resolveu o bloqueio (operacional ou gerente) antes de desmarcar.",
        )

    agora = datetime.now(timezone.utc)

    # Registra transições para campos monitorados
    houve_reabertura = False
    houve_bloqueio_resolvido = False
    houve_atribuicao_operacional = False
    for campo in ("coluna_kanban", "operacional_id", "sprint_id"):
        novo_valor = getattr(data, campo, None)
        if novo_valor is None or str(novo_valor) == str(task.get(campo) or ""):
            continue
        if campo == "operacional_id":
            houve_atribuicao_operacional = True
        transicao_id = _registrar_task_transicao(client, task_id, task, campo, novo_valor, data.autor, data.motivo, agora)
        # TRANS-03: reabertura é estritamente a saída concluida -> em_andamento.
        # Nenhuma outra saída de concluida (ex.: concluida -> planejado) conta.
        if campo == "coluna_kanban" and task.get("coluna_kanban") == "concluida" and novo_valor == "em_andamento":
            _registrar_reabertura(client, task_id, transicao_id, task.get("operacional_id"), data.motivo, agora)
            houve_reabertura = True

    if data.bloqueado is not None and data.bloqueado != task.get("bloqueado", False):
        _registrar_task_transicao(client, task_id, task, "bloqueado", data.bloqueado, data.autor, data.motivo, agora)

    updates: dict = {"updated_at": agora.isoformat()}
    # ALERT-01/ALERT-04: o relógio de travamento automático conta desde que a
    # task esteja ativa (planejado OU em_andamento) E a sprint dela já tenha
    # começado — não só a partir de em_andamento, porque um operacional pode
    # estar trabalhando numa task sem nunca arrastar o card. Reavalia sempre
    # que coluna ou sprint mudam: cobre reabertura (concluida -> qualquer
    # coluna ativa), troca de sprint (pode ganhar ou perder a âncora conforme a
    # sprint nova já tenha começado) e entrada em concluída (relógio para).
    if coluna_nova is not None or data.sprint_id is not None:
        coluna_efetiva = coluna_nova if coluna_nova is not None else coluna_atual
        sprint_efetivo_id = data.sprint_id if data.sprint_id is not None else task.get("sprint_id")
        anchor_atual = task.get("entrou_em_andamento_em")

        if coluna_efetiva == "concluida" or not sprint_efetivo_id:
            sprint_iniciada = False
        else:
            sp_iniciada_resp = client.table("sprints").select("iniciada").eq("id", sprint_efetivo_id).execute()
            sprint_iniciada = bool(sp_iniciada_resp.data and sp_iniciada_resp.data[0].get("iniciada"))

        if sprint_iniciada and anchor_atual is None:
            updates["entrou_em_andamento_em"] = agora.isoformat()
            updates["travado_automatico"] = False
            updates["travado_override"] = False
            updates["travado_override_por"] = None
            updates["travado_override_em"] = None
        elif not sprint_iniciada and anchor_atual is not None:
            updates["entrou_em_andamento_em"] = None
            updates["travado_automatico"] = False
            updates["travado_override"] = False
            updates["travado_override_por"] = None
            updates["travado_override_em"] = None
    for field in (
        "titulo", "descricao", "pontos", "funcionalidade_id", "sprint_id",
        "operacional_id", "coluna_kanban", "bloqueado", "motivo_bloqueio",
        "checklist", "ordem",
    ):
        val = getattr(data, field, None)
        if val is not None:
            updates[field] = val
    # bloqueado pode ser False, precisa checar explicitamente
    if data.bloqueado is not None:
        updates["bloqueado"] = data.bloqueado
    if data.extra is not None:
        updates["extra"] = data.extra
    if houve_reabertura:
        updates["contador_reaberturas"] = (task.get("contador_reaberturas") or 0) + 1

    # TRANS-04/TRANS-05: bloqueado_manual (gate 422 acima já garantiu que, ao
    # desmarcar, bloqueado_resolvido_por veio válido)
    if data.bloqueado_manual is not None and data.bloqueado_manual != task.get("bloqueado_manual", False):
        updates["bloqueado_manual"] = data.bloqueado_manual
        if data.bloqueado_manual is True:
            updates["bloqueado_em"] = agora.isoformat()
            updates["bloqueado_por"] = data.bloqueado_por
        else:
            updates["bloqueado_resolvido_por"] = data.bloqueado_resolvido_por
            updates["bloqueado_resolvido_em"] = agora.isoformat()
            houve_bloqueio_resolvido = True

    result = client.table("tasks").update(updates).eq("id", task_id).execute()

    if houve_atribuicao_operacional:
        _avisar_operacional_atribuicao(client, result.data[0])

    try:
        if houve_reabertura:
            rotear_evento_pos_fechamento(client, task, "qualidade_reaberturas")
        if houve_bloqueio_resolvido:
            rotear_evento_pos_fechamento(client, task, "autonomia_bloqueios_totais")
            if data.bloqueado_resolvido_por == "operacional":
                rotear_evento_pos_fechamento(client, task, "autonomia_bloqueios_resolvidos_proprio")
    except Exception:
        pass  # best-effort

    # Dispara evento de transição de coluna para logging e detecção de funcionalidade completa
    if coluna_nova is not None and coluna_nova != coluna_atual:
        on_task_transition(client, task, "coluna_kanban", coluna_atual, coluna_nova)
        if coluna_nova == "concluida":
            sprint_id_atual = task.get("sprint_id")
            if sprint_id_atual:
                try:
                    auto_update_sprint_health(client, sprint_id_atual)
                except Exception:
                    pass  # best-effort
            if pessoa["cargo"] == "operacional":
                _avisar_gerente_task_concluida(client, result.data[0])

    return result.data[0]


@router.post("/{task_id}/mover", response_model=TaskResponse)
async def mover_task(
    task_id: str,
    coluna_destino: str,
    autor: Optional[str] = None,
    motivo: Optional[str] = None,
    pessoa: dict = Depends(get_current_pessoa),
):
    """Endpoint semântico para drag-and-drop entre colunas."""
    if coluna_destino not in {"planejado", "em_andamento", "concluida"}:
        raise HTTPException(status_code=422, detail="coluna_destino inválida")
    return await patch_task(task_id, TaskUpdate(coluna_kanban=coluna_destino, autor=autor, motivo=motivo), pessoa=pessoa)


@router.post("/{task_id}/travado/override", response_model=TaskResponse)
async def override_travamento(task_id: str, autor: Optional[str] = None):
    """
    ALERT-03: suprime o alerta de travamento automático e reinicia o relógio
    (revisão 2026-09-12) — não é mais imunidade permanente. Muita task trava
    por motivo alheio ao operacional (ex: falta de retorno do cliente); nesses
    casos o gerente precisa de um novo prazo do zero, não de uma isenção
    eterna que nunca mais avisa se a task continuar parada.

    travado_automatico volta a False (o badge some porque a condição de
    exibição no frontend é travado_automatico && !travado_override) e
    entrou_em_andamento_em é reancorado em agora, então o job diário volta a
    avaliar essa task normalmente a partir daqui — se ficar parada além do
    novo prazo, trava de novo. travado_override/_por/_em continuam gravados
    como histórico de que houve uma supressão.

    Desde a revisão de 2026-09-07 o override também dispensa a penalidade de
    Entrega: os eventos de travamento ainda não contabilizados desta task são
    marcados como dispensados e o fechamento da sprint passa a ignorá-los. É a
    válvula de escape para travamento que não é culpa do operacional.
    """
    client = get_client()

    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = resp.data[0]

    if task.get("coluna_kanban") == "concluida" or not task.get("entrou_em_andamento_em"):
        raise HTTPException(
            status_code=409,
            detail="Task não tem relógio de travamento rodando — não há alerta para suprimir.",
        )

    agora = datetime.now(timezone.utc)
    updates = {
        "travado_override": True,
        "travado_override_por": autor,
        "travado_override_em": agora.isoformat(),
        "travado_automatico": False,
        "entrou_em_andamento_em": agora.isoformat(),
    }
    result = client.table("tasks").update(updates).eq("id", task_id).execute()

    try:
        (
            client.table("task_travamentos")
            .update({"dispensado": True})
            .eq("task_id", task_id)
            .eq("dispensado", False)
            .execute()
        )
    except Exception:
        pass  # best-effort — o override do alerta não pode falhar por causa disso

    return result.data[0]


@router.patch("/reordenar/batch", status_code=200)
async def reordenar_tasks(itens: list[TaskReordenarItem]):
    """Atualiza a ordem de múltiplas tasks de uma vez (drag-and-drop na mesma coluna)."""
    client = get_client()
    for item in itens:
        client.table("tasks").update({"ordem": item.ordem}).eq("id", item.id).execute()
    return {"updated": len(itens)}


@router.delete("/{task_id}", status_code=204, dependencies=[Depends(require_not_operacional)])
async def delete_task(task_id: str):
    client = get_client()
    check = client.table("tasks").select("id, sprint_id").eq("id", task_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Task not found")

    sprint_id = check.data[0].get("sprint_id")
    if sprint_id:
        sprint = client.table("sprints").select("avaliacao_completa_em").eq("id", sprint_id).execute()
        if sprint.data and sprint.data[0].get("avaliacao_completa_em"):
            raise HTTPException(
                status_code=409,
                detail="A pontuação desta sprint já foi travada (Avaliação Semanal confirmada); exclusão de task bloqueada.",
            )

    client.table("tasks").delete().eq("id", task_id).execute()
