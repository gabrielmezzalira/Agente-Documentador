from difflib import SequenceMatcher
from typing import Optional


def on_task_transition(
    client,
    task: dict,
    campo: str,
    de: Optional[str],
    para: Optional[str],
) -> bool:
    """
    Registra uma transição de task como ingestion do tipo task_event
    e detecta se a funcionalidade associada ficou 100% concluída.

    Retorna True se a funcionalidade tornou-se 100% concluída nesta transição.
    Só loga se a task tiver sprint_id (para vincular ao número da sprint).
    """
    _log_ingestion(client, task, campo, de, para)
    return _detectar_funcionalidade_completa(client, task, campo, para)


def _log_ingestion(client, task: dict, campo: str, de, para) -> None:
    sprint_id = task.get("sprint_id")
    if not sprint_id:
        return

    sprint = client.table("sprints").select("numero").eq("id", sprint_id).execute()
    if not sprint.data:
        return

    sprint_numero = sprint.data[0]["numero"]
    client.table("ingestions").insert({
        "project_id": task["project_id"],
        "sprint_number": sprint_numero,
        "file_name": f"task_event:{task['id']}",
        "file_type": "task_event",
        "extracted_content": {
            "resumo": f"Task '{task['titulo']}': {campo} {de} → {para}",
            "tarefas": [task["titulo"]],
            "decisoes": [],
            "problemas": [],
            "contexto_cliente": "",
            "proximos_passos": [],
            "tecnologias": [],
            "tecnologias_removidas": [],
        },
    }).execute()


def on_review_ingested(
    client,
    ingestion_id: str,
    project_id: str,
    sprint_numero: int,
    tarefas_from_review: list[str],
) -> int:
    """
    Após ingerir um review, faz fuzzy match das tarefas mencionadas no review
    contra as tasks ativas da sprint e cria sugestões em task_sugestoes.
    Retorna o número de sugestões criadas.
    """
    if not tarefas_from_review:
        return 0

    sprint_resp = (
        client.table("sprints")
        .select("id")
        .eq("project_id", project_id)
        .eq("numero", sprint_numero)
        .execute()
    )
    if not sprint_resp.data:
        return 0
    sprint_id = sprint_resp.data[0]["id"]

    tasks_resp = (
        client.table("tasks")
        .select("id, titulo, coluna_kanban")
        .eq("project_id", project_id)
        .eq("sprint_id", sprint_id)
        .neq("coluna_kanban", "concluida")
        .execute()
    )
    tasks = tasks_resp.data or []
    if not tasks:
        return 0

    created = 0
    for tarefa_texto in tarefas_from_review:
        t_norm = tarefa_texto.lower().strip()
        for task in tasks:
            task_norm = task["titulo"].lower().strip()
            ratio = SequenceMatcher(None, t_norm, task_norm).ratio()
            match = ratio >= 0.6 or t_norm in task_norm or task_norm in t_norm
            if not match:
                continue
            existing = (
                client.table("task_sugestoes")
                .select("id")
                .eq("task_id", task["id"])
                .eq("acao", "mover_para_concluida")
                .is_("aceita", "null")
                .execute()
            )
            if existing.data:
                continue
            client.table("task_sugestoes").insert({
                "task_id": task["id"],
                "acao": "mover_para_concluida",
                "motivo": f"Mencionada como concluída no review da Sprint {sprint_numero}: \"{tarefa_texto}\"",
                "origem_ingestion_id": ingestion_id,
            }).execute()
            created += 1

    return created


def _detectar_funcionalidade_completa(client, task: dict, campo: str, para) -> bool:
    if campo != "coluna_kanban" or para != "concluida":
        return False

    funcionalidade_id = task.get("funcionalidade_id")
    if not funcionalidade_id:
        return False

    todas = (
        client.table("tasks")
        .select("coluna_kanban")
        .eq("funcionalidade_id", funcionalidade_id)
        .execute()
        .data
    )
    return bool(todas) and all(t["coluna_kanban"] == "concluida" for t in todas)
