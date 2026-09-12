"""Helpers compartilhados pra entidade Sprint."""
from datetime import datetime, timezone
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


def compute_planejado_vs_entregue(client, project_id: str, numero: int) -> list[dict]:
    """Monta a tabela 'planejado vs. entregue' da Review a partir do kanban real
    da sprint — 1 linha por task, 'entregue' = task concluída ao final da sprint.

    motivo_nao/causa_raiz_num ficam sempre vazios (dependem de julgamento humano,
    o gerente completa manualmente); recalculado do zero a cada chamada.
    """
    sprint_resp = (
        client.table("sprints")
        .select("id")
        .eq("project_id", project_id)
        .eq("numero", numero)
        .limit(1)
        .execute()
    )
    if not sprint_resp.data:
        return []
    sprint_id = sprint_resp.data[0]["id"]

    tasks_resp = (
        client.table("tasks")
        .select("titulo, coluna_kanban")
        .eq("sprint_id", sprint_id)
        .order("coluna_kanban")
        .order("ordem")
        .execute()
    )
    tasks = tasks_resp.data or []
    return [
        {
            "item": t["titulo"],
            "entregue": "S" if t["coluna_kanban"] == "concluida" else "N",
            "motivo_nao": "",
            "causa_raiz_num": "",
        }
        for t in tasks
    ]


def iniciar_sprint_e_ancorar_tasks(client, sprint_id: str) -> None:
    """Marca a sprint como iniciada e ancora o relógio de travamento automático
    (ALERT-01) das tasks que já estavam nela (planejado ou em_andamento) e ainda
    não tinham relógio rodando.

    Sem isso, uma task criada em Planejado para uma sprint futura ficaria sem
    âncora até alguém movê-la manualmente pra Em Andamento — o que é exatamente
    o cenário que motivou o relógio passar a contar desde Planejado: um
    operacional pode estar trabalhando nela sem nunca arrastar o card. O relógio
    só é ancorado a partir de AGORA (não retroativo à criação da task), porque
    antes da sprint iniciar o tempo parado não deveria contar.

    Chamado tanto pelo botão "Iniciar próxima sprint" quanto, implicitamente,
    pela confirmação da Avaliação Semanal da sprint anterior (routers/avaliacoes.py)."""
    client.table("sprints").update({
        "iniciada": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", sprint_id).execute()

    agora_iso = datetime.now(timezone.utc).isoformat()
    pendentes = (
        client.table("tasks")
        .select("id")
        .eq("sprint_id", sprint_id)
        .neq("coluna_kanban", "concluida")
        .is_("entrou_em_andamento_em", "null")
        .execute()
        .data or []
    )
    for t in pendentes:
        client.table("tasks").update({"entrou_em_andamento_em": agora_iso}).eq("id", t["id"]).execute()
