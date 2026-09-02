from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.supabase_client import get_client

router = APIRouter(prefix="/metricas", tags=["metricas"])


@router.get("/{project_id}/spi")
async def get_spi(project_id: str):
    """SPI por sprint: pontos_previstos, pontos_realizados, spi."""
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    sprints = (
        client.table("sprints")
        .select("id, numero, pontos_previstos")
        .eq("project_id", project_id)
        .order("numero")
        .execute()
        .data or []
    )

    result = []
    for s in sprints:
        tasks_resp = (
            client.table("tasks")
            .select("pontos, coluna_kanban")
            .eq("sprint_id", s["id"])
            .execute()
        )
        tasks = tasks_resp.data or []
        pontos_realizados = sum(t["pontos"] for t in tasks if t["coluna_kanban"] == "concluida")
        pontos_previstos = s.get("pontos_previstos")
        spi = None
        if pontos_previstos and pontos_previstos > 0:
            spi = round(pontos_realizados / pontos_previstos, 3)
        result.append({
            "sprint_numero": s["numero"],
            "pontos_previstos": pontos_previstos,
            "pontos_realizados": pontos_realizados,
            "spi": spi,
        })
    return result


@router.get("/{project_id}/throughput")
async def get_throughput(project_id: str):
    """Tasks concluídas e pontos realizados por sprint."""
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    sprints = (
        client.table("sprints")
        .select("id, numero")
        .eq("project_id", project_id)
        .order("numero")
        .execute()
        .data or []
    )

    result = []
    for s in sprints:
        tasks_resp = (
            client.table("tasks")
            .select("pontos, coluna_kanban")
            .eq("sprint_id", s["id"])
            .execute()
        )
        tasks = tasks_resp.data or []
        concluidas = [t for t in tasks if t["coluna_kanban"] == "concluida"]
        result.append({
            "sprint_numero": s["numero"],
            "tasks_total": len(tasks),
            "tasks_concluidas": len(concluidas),
            "pontos_concluidos": sum(t["pontos"] for t in concluidas),
        })
    return result


@router.get("/{project_id}/cycle-time")
async def get_cycle_time(
    project_id: str,
    sprint_numero: Optional[int] = Query(default=None),
):
    """
    Cycle-time por task: tempo (em horas) entre entrada em em_andamento e saída para concluida.
    Usa task_transicoes com campo=coluna_kanban e duracao_fase_anterior_segundos da transição → concluida.
    """
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks_query = (
        client.table("tasks")
        .select("id, titulo, sprint_id, operacional_id, coluna_kanban")
        .eq("project_id", project_id)
        .eq("coluna_kanban", "concluida")
    )

    if sprint_numero is not None:
        sprint_resp = (
            client.table("sprints")
            .select("id")
            .eq("project_id", project_id)
            .eq("numero", sprint_numero)
            .execute()
        )
        if sprint_resp.data:
            tasks_query = tasks_query.eq("sprint_id", sprint_resp.data[0]["id"])

    tasks = tasks_query.execute().data or []

    operacionais_map: dict = {}
    sprints_map: dict = {}

    result = []
    for task in tasks:
        # duracao da fase em_andamento antes de ir para concluida
        trans = (
            client.table("task_transicoes")
            .select("duracao_fase_anterior_segundos, timestamp")
            .eq("task_id", task["id"])
            .eq("campo", "coluna_kanban")
            .eq("para", "concluida")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not trans.data:
            continue
        duracao_s = trans.data[0].get("duracao_fase_anterior_segundos")
        if not duracao_s:
            continue

        # Sprint numero
        sprint_id = task.get("sprint_id")
        sprint_num = None
        if sprint_id:
            if sprint_id not in sprints_map:
                sr = client.table("sprints").select("numero").eq("id", sprint_id).execute()
                sprints_map[sprint_id] = sr.data[0]["numero"] if sr.data else None
            sprint_num = sprints_map[sprint_id]

        # Operacional nome
        op_id = task.get("operacional_id")
        op_nome = None
        if op_id:
            if op_id not in operacionais_map:
                or_ = client.table("operacionais").select("nome").eq("id", op_id).execute()
                operacionais_map[op_id] = or_.data[0]["nome"] if or_.data else None
            op_nome = operacionais_map[op_id]

        result.append({
            "task_titulo": task["titulo"],
            "sprint_numero": sprint_num,
            "cycle_time_horas": round(duracao_s / 3600, 1),
            "operacional_nome": op_nome,
        })

    result.sort(key=lambda x: (x["sprint_numero"] or 0, x["cycle_time_horas"]))
    return result


@router.get("/{project_id}/cfd")
async def get_cfd(project_id: str):
    """
    Flow snapshot por sprint: total de tasks em cada coluna.
    Retorna dados para gráfico de área empilhado.
    """
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    sprints = (
        client.table("sprints")
        .select("id, numero")
        .eq("project_id", project_id)
        .order("numero")
        .execute()
        .data or []
    )

    result = []
    for s in sprints:
        tasks = (
            client.table("tasks")
            .select("coluna_kanban")
            .eq("sprint_id", s["id"])
            .execute()
            .data or []
        )
        planejado = sum(1 for t in tasks if t["coluna_kanban"] == "planejado")
        em_andamento = sum(1 for t in tasks if t["coluna_kanban"] == "em_andamento")
        concluida = sum(1 for t in tasks if t["coluna_kanban"] == "concluida")
        if tasks:
            result.append({
                "sprint_numero": s["numero"],
                "planejado": planejado,
                "em_andamento": em_andamento,
                "concluida": concluida,
            })
    return result
