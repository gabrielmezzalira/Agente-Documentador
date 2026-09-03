from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskReordenarItem,
    TaskTransicaoResponse,
    TaskSugestaoResponse,
    TaskSugestaoResolve,
)
from services.supabase_client import get_client
from services.wip_check import check_wip
from services.task_events import on_task_transition
from services.spi_health import auto_update_sprint_health

router = APIRouter(prefix="/tasks", tags=["tasks"])

_CAMPOS_TRANSICAO = {"coluna_kanban", "operacional_id", "sprint_id", "bloqueado"}


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
    }).execute()
    return resp.data[0]["id"] if resp.data else None


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


@router.post("", response_model=TaskResponse, status_code=201)
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
            .select("id")
            .eq("id", data.sprint_id)
            .eq("project_id", data.project_id)
            .execute()
        )
        if not sp_check.data:
            raise HTTPException(status_code=422, detail="sprint_id não pertence a este projeto")

    payload: dict = {
        "project_id": data.project_id,
        "titulo": data.titulo,
        "pontos": data.pontos,
        "coluna_kanban": data.coluna_kanban,
        "ordem": data.ordem,
        "checklist": data.checklist or [],
    }
    for field in ("funcionalidade_id", "sprint_id", "operacional_id", "descricao"):
        val = getattr(data, field, None)
        if val is not None:
            payload[field] = val

    # ALERT-01: task já criada direto em em_andamento também ancora o relógio de
    # travamento automático — sem isso o job diário nunca teria referência para ela.
    if payload.get("coluna_kanban") == "em_andamento":
        payload["entrou_em_andamento_em"] = datetime.now(timezone.utc).isoformat()

    resp = client.table("tasks").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return resp.data[0]


@router.get("", response_model=list[TaskResponse])
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
async def resolve_task_sugestao(sugestao_id: str, data: TaskSugestaoResolve):
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
        await patch_task(task_id, TaskUpdate(coluna_kanban="concluida", autor="sugestao_ia"))

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
async def patch_task(task_id: str, data: TaskUpdate):
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
    houve_entrada_em_andamento = False
    houve_saida_de_em_andamento = False
    for campo in ("coluna_kanban", "operacional_id", "sprint_id"):
        novo_valor = getattr(data, campo, None)
        if novo_valor is None or str(novo_valor) == str(task.get(campo) or ""):
            continue
        transicao_id = _registrar_task_transicao(client, task_id, task, campo, novo_valor, data.autor, data.motivo, agora)
        # TRANS-03: reabertura é estritamente a saída concluida -> em_andamento.
        # Nenhuma outra saída de concluida (ex.: concluida -> planejado) conta.
        if campo == "coluna_kanban" and task.get("coluna_kanban") == "concluida" and novo_valor == "em_andamento":
            _registrar_reabertura(client, task_id, transicao_id, task.get("operacional_id"), data.motivo, agora)
            houve_reabertura = True
        # ALERT-01/ALERT-02: relógio de travamento automático — entrou_em_andamento_em
        # ancora em toda entrada confirmada em em_andamento (de qualquer coluna,
        # inclusive reabertura); reseta ao sair de em_andamento para qualquer coluna.
        if campo == "coluna_kanban":
            if novo_valor == "em_andamento":
                houve_entrada_em_andamento = True
            elif task.get("coluna_kanban") == "em_andamento":
                houve_saida_de_em_andamento = True

    if data.bloqueado is not None and data.bloqueado != task.get("bloqueado", False):
        _registrar_task_transicao(client, task_id, task, "bloqueado", data.bloqueado, data.autor, data.motivo, agora)

    updates: dict = {"updated_at": agora.isoformat()}
    # ALERT-01/ALERT-02: set/reset do relógio + reset dos campos de travado_* —
    # mutuamente exclusivo (uma única transição de coluna só pode ser entrada OU
    # saída de em_andamento, nunca as duas).
    if houve_entrada_em_andamento:
        updates["entrou_em_andamento_em"] = agora.isoformat()
        updates["travado_automatico"] = False
        updates["travado_override"] = False
        updates["travado_override_por"] = None
        updates["travado_override_em"] = None
    elif houve_saida_de_em_andamento:
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

    result = client.table("tasks").update(updates).eq("id", task_id).execute()

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

    return result.data[0]


@router.post("/{task_id}/mover", response_model=TaskResponse)
async def mover_task(task_id: str, coluna_destino: str, autor: Optional[str] = None, motivo: Optional[str] = None):
    """Endpoint semântico para drag-and-drop entre colunas."""
    if coluna_destino not in {"planejado", "em_andamento", "concluida"}:
        raise HTTPException(status_code=422, detail="coluna_destino inválida")
    return await patch_task(task_id, TaskUpdate(coluna_kanban=coluna_destino, autor=autor, motivo=motivo))


@router.patch("/reordenar/batch", status_code=200)
async def reordenar_tasks(itens: list[TaskReordenarItem]):
    """Atualiza a ordem de múltiplas tasks de uma vez (drag-and-drop na mesma coluna)."""
    client = get_client()
    for item in itens:
        client.table("tasks").update({"ordem": item.ordem}).eq("id", item.id).execute()
    return {"updated": len(itens)}


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str):
    client = get_client()
    check = client.table("tasks").select("id").eq("id", task_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Task not found")
    client.table("tasks").delete().eq("id", task_id).execute()
