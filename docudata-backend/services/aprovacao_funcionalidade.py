"""Aprovação de funcionalidade pelo gerente (spec A1 §3).

"Concluída e aprovada" = status 'concluida' e aprovada_em preenchido. O status
não ganha valor novo para não quebrar quem já lê status. Toda mudança de
aprovação vira linha em transicoes_status com campo 'aprovacao'."""
from datetime import datetime, timezone

from fastapi import HTTPException


def _buscar(client, funcionalidade_id: str) -> dict:
    resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    return resp.data[0]


def _registrar(client, func: dict, de: str, para: str, autor: str | None, motivo: str | None, agora: datetime) -> None:
    anterior = (
        client.table("transicoes_status")
        .select("timestamp")
        .eq("funcionalidade_id", func["id"])
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    base = anterior.data[0]["timestamp"] if anterior.data else func.get("created_at")
    duracao = None
    if base:
        inicio = datetime.fromisoformat(str(base).replace("Z", "+00:00"))
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        duracao = int((agora - inicio).total_seconds())
    client.table("transicoes_status").insert({
        "funcionalidade_id": func["id"],
        "campo": "aprovacao",
        "de": de,
        "para": para,
        "autor": autor,
        "timestamp": agora.isoformat(),
        "motivo": motivo,
        "duracao_fase_anterior_segundos": duracao,
    }).execute()


def nomes_dos_aprovadores(client, funcs: list[dict]) -> list[dict]:
    ids = sorted({f["aprovada_por"] for f in funcs if f.get("aprovada_por")})
    nomes: dict[str, str] = {}
    if ids:
        rows = client.table("pessoa").select("id, nome").in_("id", ids).execute().data or []
        nomes = {r["id"]: r["nome"] for r in rows}
    return [{**f, "aprovada_por_nome": nomes.get(f.get("aprovada_por"))} for f in funcs]


def aprovar(client, funcionalidade_id: str, pessoa_id: str) -> dict:
    func = _buscar(client, funcionalidade_id)
    if func.get("status") != "concluida":
        raise HTTPException(status_code=409, detail="Só dá para aprovar uma funcionalidade concluída.")
    if func.get("aprovada_em"):
        raise HTTPException(status_code=409, detail="Funcionalidade já está aprovada.")
    abertas = (
        client.table("tasks")
        .select("id")
        .eq("funcionalidade_id", funcionalidade_id)
        .neq("coluna_kanban", "concluida")
        .limit(1)
        .execute()
    )
    if abertas.data:
        raise HTTPException(status_code=409, detail="Há tasks desta funcionalidade ainda não concluídas.")
    agora = datetime.now(timezone.utc)
    _registrar(client, func, "pendente", "aprovada", pessoa_id, None, agora)
    resp = client.table("funcionalidades").update({
        "aprovada_em": agora.isoformat(),
        "aprovada_por": pessoa_id,
    }).eq("id", funcionalidade_id).execute()
    return nomes_dos_aprovadores(client, resp.data)[0]


def desfazer_aprovacao(client, funcionalidade_id: str, autor: str | None) -> dict:
    func = _buscar(client, funcionalidade_id)
    if not func.get("aprovada_em"):
        raise HTTPException(status_code=409, detail="Funcionalidade não está aprovada.")
    agora = datetime.now(timezone.utc)
    _registrar(client, func, "aprovada", "pendente", autor, "desfeita pelo gerente", agora)
    resp = client.table("funcionalidades").update({
        "aprovada_em": None,
        "aprovada_por": None,
    }).eq("id", funcionalidade_id).execute()
    return nomes_dos_aprovadores(client, resp.data)[0]


def revogar_se_aprovada(client, funcionalidade_id: str | None, motivo: str) -> bool:
    """Funcionalidade aprovada que deixa de estar pronta (task reaberta, task
    nova, status mudado à mão) perde a aprovação. Devolve True se revogou."""
    if not funcionalidade_id:
        return False
    resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not resp.data or not resp.data[0].get("aprovada_em"):
        return False
    func = resp.data[0]
    _registrar(client, func, "aprovada", "pendente", None, motivo, datetime.now(timezone.utc))
    client.table("funcionalidades").update({"aprovada_em": None, "aprovada_por": None}).eq("id", funcionalidade_id).execute()
    return True
