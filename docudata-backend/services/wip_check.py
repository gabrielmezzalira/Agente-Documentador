from typing import Optional


def check_wip(
    client,
    project_id: str,
    operacional_id: Optional[str],
    coluna_destino: str,
) -> tuple[bool, Optional[str]]:
    """
    Verifica limites WIP antes de mover uma task para coluna_destino.
    Só age quando coluna_destino == 'em_andamento'.
    Retorna (ok, motivo) — se ok=False, motivo descreve o limite atingido.
    """
    if coluna_destino != "em_andamento":
        return True, None

    project = client.table("projects").select("wip_config").eq("id", project_id).execute()
    if not project.data:
        return True, None

    wip = project.data[0].get("wip_config") or {}

    limite_coluna: Optional[int] = wip.get("por_coluna_em_andamento")
    if limite_coluna is not None:
        atual = len(
            client.table("tasks")
            .select("id")
            .eq("project_id", project_id)
            .eq("coluna_kanban", "em_andamento")
            .execute()
            .data
        )
        if atual >= limite_coluna:
            return False, f"Limite WIP da coluna em_andamento atingido ({atual}/{limite_coluna})"

    limite_pessoa: Optional[int] = wip.get("por_pessoa")
    if limite_pessoa is not None and operacional_id:
        atual = len(
            client.table("tasks")
            .select("id")
            .eq("project_id", project_id)
            .eq("operacional_id", operacional_id)
            .eq("coluna_kanban", "em_andamento")
            .execute()
            .data
        )
        if atual >= limite_pessoa:
            return False, f"Limite WIP por pessoa atingido ({atual}/{limite_pessoa})"

    return True, None
