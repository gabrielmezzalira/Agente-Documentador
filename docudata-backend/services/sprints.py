"""Helpers compartilhados pra entidade Sprint."""
from typing import Optional


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


def get_current_sprint_id(client, project_id: str) -> Optional[str]:
    """Resolve o id (uuid) da sprint atual do projeto — mesma lógica de
    GET /projects/{id}/current-sprint (routers/commit_ingest.py), mas devolve
    o id em vez do número. Usado pelo Motor de Score (Phase 18) pra rotear
    eventos tardios (services/pontuacao.py)."""
    sprints_resp = client.table("sprints").select("id, numero").eq("project_id", project_id).execute()
    sprints_rows = sprints_resp.data or []
    if not sprints_rows:
        return None
    numero_para_id = {row["numero"]: row["id"] for row in sprints_rows}

    plannings = (
        client.table("ingestions")
        .select("sprint_number, created_at")
        .eq("project_id", project_id)
        .eq("tipo_documentacao", "planning")
        .order("created_at", desc=True)
        .execute()
    )
    for row in (plannings.data or []):
        if row["sprint_number"] in numero_para_id:
            return numero_para_id[row["sprint_number"]]

    maior_numero = max(numero_para_id)
    return numero_para_id[maior_numero]
