"""
Log de auditoria genérico (RBAC-05) — pronto para as Phases 17/18
reutilizarem quando as rotas de avaliação do gerente e score existirem.
Nesta phase, só GET /performance chama isso.
"""
from datetime import datetime, timezone

from services.supabase_client import get_client


def registrar_auditoria(pessoa: dict, rota: str, acao: str) -> None:
    client = get_client()
    client.table("audit_log").insert({
        "pessoa_id": pessoa["id"],
        "pessoa_email": pessoa["email"],
        "rota": rota,
        "acao": acao,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
