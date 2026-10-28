"""Status da funcionalidade derivado das tasks (Rodada B1, entrega 1).

Regra (extras ignoradas): sem tasks → não mexe; todas em planejado →
nao_iniciada; todas concluídas → concluida; senão → em_andamento.
`em_ajuste` é manual e só cede para nao_iniciada/concluida."""
import logging
from datetime import datetime, timezone

from services.aprovacao_funcionalidade import revogar_se_aprovada

logger = logging.getLogger(__name__)


def status_derivado(tasks: list[dict]) -> str | None:
    colunas = [t.get("coluna_kanban") for t in tasks if not t.get("extra")]
    if not colunas:
        return None
    if all(c == "planejado" for c in colunas):
        return "nao_iniciada"
    if all(c == "concluida" for c in colunas):
        return "concluida"
    return "em_andamento"


def _ts(valor: str) -> datetime:
    dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def registrar_transicao_status(client, func: dict, novo: str, autor: str | None, motivo: str | None, agora: datetime) -> None:
    anterior = (
        client.table("transicoes_status")
        .select("timestamp")
        .eq("funcionalidade_id", func["id"])
        .eq("campo", "status")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    base = anterior.data[0]["timestamp"] if anterior.data else func["created_at"]
    duracao = int((agora - _ts(base)).total_seconds())
    client.table("transicoes_status").insert({
        "funcionalidade_id": func["id"],
        "campo": "status",
        "de": func.get("status"),
        "para": novo,
        "autor": autor,
        "timestamp": agora.isoformat(),
        "motivo": motivo,
        "duracao_fase_anterior_segundos": duracao,
    }).execute()


def _tasks_da_funcionalidade(client, funcionalidade_id: str) -> list[dict]:
    return (
        client.table("tasks")
        .select("coluna_kanban, extra")
        .eq("funcionalidade_id", funcionalidade_id)
        .execute()
        .data or []
    )


def funcionalidade_tem_tasks(client, funcionalidade_id: str) -> bool:
    return status_derivado(_tasks_da_funcionalidade(client, funcionalidade_id)) is not None


def sincronizar_status(client, funcionalidade_id: str | None, autor: str | None = "sistema") -> str | None:
    if not funcionalidade_id:
        return None
    try:
        resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
        if not resp.data:
            return None
        func = resp.data[0]
        novo = status_derivado(_tasks_da_funcionalidade(client, funcionalidade_id))
        atual = func.get("status")
        if novo is None or novo == atual:
            return None
        if atual == "em_ajuste" and novo == "em_andamento":
            return None
        agora = datetime.now(timezone.utc)
        registrar_transicao_status(client, func, novo, autor, "derivado das tasks", agora)
        client.table("funcionalidades").update({"status": novo}).eq("id", funcionalidade_id).execute()
        if atual == "concluida":
            revogar_se_aprovada(client, funcionalidade_id, "revogada: status derivado das tasks")
        return novo
    except Exception:
        logger.exception("falha ao sincronizar status da funcionalidade %s", funcionalidade_id)
        return None
