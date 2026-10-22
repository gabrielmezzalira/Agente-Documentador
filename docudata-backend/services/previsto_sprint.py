"""Previsto da sprint (spec A1 §4): foto das tasks no início + tasks que
surgiram depois que ela começou. Task extra nunca entra — é trabalho concedido
além do planejado."""


def marcas_ao_entrar_na_sprint(sprint_iniciada: bool, extra: bool) -> dict:
    """Marcas de uma task que acaba de entrar numa sprint (criada nela ou
    movida para ela). A foto do início pertence à sprint de origem, então
    prevista_no_inicio sempre zera; se a sprint destino ainda não começou, a
    foto será tirada quando ela começar."""
    return {"prevista_no_inicio": False, "surgiu_na_sprint": bool(sprint_iniciada and not extra)}


def marcar_foto_do_inicio(client, sprint_id: str) -> None:
    (
        client.table("tasks")
        .update({"prevista_no_inicio": True})
        .eq("sprint_id", sprint_id)
        .eq("extra", False)
        .execute()
    )


def previsto_da_sprint(client, sprint_id: str) -> dict:
    tasks = (
        client.table("tasks")
        .select("pontos, extra, prevista_no_inicio, surgiu_na_sprint")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    planejado = sum(t["pontos"] for t in tasks if not t.get("extra") and t.get("prevista_no_inicio"))
    surgiu = sum(
        t["pontos"] for t in tasks
        if not t.get("extra") and t.get("surgiu_na_sprint") and not t.get("prevista_no_inicio")
    )
    return {"previsto": planejado + surgiu, "planejado_no_inicio": planejado, "surgiu_na_sprint": surgiu}
