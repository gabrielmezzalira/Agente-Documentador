import statistics

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.supabase_client import get_client

router = APIRouter(prefix="/metricas", tags=["metricas"])


def _percentiles(cycle_times_horas: list[float]) -> dict:
    """p50/p85 (em horas) via statistics.quantiles; lida com 0/1 pontos de dados."""
    if len(cycle_times_horas) < 2:
        return {
            "p50_horas": cycle_times_horas[0] if cycle_times_horas else None,
            "p85_horas": cycle_times_horas[0] if cycle_times_horas else None,
        }
    q = statistics.quantiles(cycle_times_horas, n=100, method="inclusive")
    return {"p50_horas": round(q[49], 1), "p85_horas": round(q[84], 1)}


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


@router.get("/{project_id}/performance-operacional")
async def get_performance_operacional(project_id: str):
    """
    Performance por operacional (MET-01 + MET-06): pontos_atribuidos, pontos_realizados,
    tasks_concluidas e um SPI interino (estimado) por operacional.

    O "spi" aqui é um proxy interino recomputado ao vivo a partir da soma de todos os
    pontos já atribuídos ao operacional (qualquer coluna) — NÃO é um baseline travado.
    O baseline formal por operacional é responsabilidade da Phase 18 / SCORE-03.
    """
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    operacionais = (
        client.table("operacionais")
        .select("id, nome")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    tasks = (
        client.table("tasks")
        .select("operacional_id, pontos, coluna_kanban")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )

    by_op: dict = {}
    for t in tasks:
        op_id = t.get("operacional_id")
        if not op_id:
            continue
        bucket = by_op.setdefault(op_id, {"pontos_atribuidos": 0, "pontos_realizados": 0, "tasks_concluidas": 0})
        bucket["pontos_atribuidos"] += t["pontos"]
        if t["coluna_kanban"] == "concluida":
            bucket["pontos_realizados"] += t["pontos"]
            bucket["tasks_concluidas"] += 1

    result = []
    for op in operacionais:
        b = by_op.get(op["id"], {"pontos_atribuidos": 0, "pontos_realizados": 0, "tasks_concluidas": 0})
        spi = round(b["pontos_realizados"] / b["pontos_atribuidos"], 3) if b["pontos_atribuidos"] > 0 else None
        result.append({
            "operacional_id": op["id"],
            "operacional_nome": op["nome"],
            **b,
            "spi": spi,
        })
    return result


@router.get("/{project_id}/cycle-time/stats")
async def get_cycle_time_stats(project_id: str):
    """
    Estatísticas agregadas de cycle-time (MET-02): p50_horas e p85_horas via
    statistics.quantiles. Endpoint aditivo — não altera o contrato de /cycle-time.
    """
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = (
        client.table("tasks")
        .select("id, sprint_id, operacional_id, coluna_kanban")
        .eq("project_id", project_id)
        .eq("coluna_kanban", "concluida")
        .execute()
        .data or []
    )

    cycle_times_horas: list[float] = []
    for task in tasks:
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
        cycle_times_horas.append(round(duracao_s / 3600, 1))

    return _percentiles(cycle_times_horas)
