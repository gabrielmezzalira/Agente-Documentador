"""Helpers compartilhados pra entidade Sprint."""


def ensure_sprint_row(client, project_id: str, numero: int) -> None:
    """Cria sprint no banco se ainda não existir. Idempotente.

    Usado por /ingest e /sprint-docs/* para garantir que toda ingestão tem uma
    sprint row correspondente (importante pro GET /projects/{id}/sprints listar
    todas sprints com atividade, mesmo as não criadas explicitamente pelo
    botão "+ Nova sprint").
    """
    existing = (
        client.table("sprints")
        .select("id")
        .eq("project_id", project_id)
        .eq("numero", numero)
        .execute()
    )
    if existing.data:
        return
    try:
        client.table("sprints").insert({"project_id": project_id, "numero": numero}).execute()
    except Exception:
        # Race condition (UNIQUE violation) ou outro erro — outra request criou primeiro
        pass


def get_current_sprint_number(client, project_id: str) -> int:
    """Resolve a sprint vigente sem depender de uma chamada HTTP interna."""
    sprints_resp = (
        client.table("sprints").select("numero").eq("project_id", project_id).execute()
    )
    numeros = {row["numero"] for row in (sprints_resp.data or [])}
    if not numeros:
        return 1

    plannings = (
        client.table("ingestions")
        .select("sprint_number, created_at")
        .eq("project_id", project_id)
        .eq("tipo_documentacao", "planning")
        .order("created_at", desc=True)
        .execute()
    )
    for row in plannings.data or []:
        if row["sprint_number"] in numeros:
            return row["sprint_number"]
    return max(numeros)
