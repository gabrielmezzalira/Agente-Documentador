"""Aprovação de funcionalidade pelo gerente (spec A1 §3).

"Concluída e aprovada" = status 'concluida' e aprovada_em preenchido. O status
não ganha valor novo para não quebrar quem já lê status. Toda mudança de
aprovação vira linha em transicoes_status com campo 'aprovacao'."""
import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from services.supabase_paginacao import ler_tudo

logger = logging.getLogger(__name__)


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


def _ids_com_tasks(client, ids: list[str], lote: int = 50) -> set[str]:
    """Funcionalidades com ao menos uma task não extra (as que ditam o status), em lote."""
    achadas: set[str] = set()
    for i in range(0, len(ids), lote):
        parte = ids[i:i + lote]
        rows = ler_tudo(
            lambda: client.table("tasks").select("id, funcionalidade_id").in_("funcionalidade_id", parte).eq("extra", False).order("id")
        )
        achadas |= {r["funcionalidade_id"] for r in rows}
    return achadas


def nomes_dos_aprovadores(client, funcs: list[dict]) -> list[dict]:
    ids = sorted({f["aprovada_por"] for f in funcs if f.get("aprovada_por")})
    nomes: dict[str, str] = {}
    if ids:
        rows = client.table("pessoa").select("id, nome").in_("id", ids).execute().data or []
        nomes = {r["id"]: r["nome"] for r in rows}
    return [{**f, "aprovada_por_nome": nomes.get(f.get("aprovada_por"))} for f in funcs]


def _metas_abertas(client, ids: list[str], lote: int = 100) -> dict[str, list[int]]:
    """Números das sprints ainda não fechadas cuja meta contém cada funcionalidade, em lote."""
    por_func: dict[str, set[str]] = {}
    for i in range(0, len(ids), lote):
        parte = ids[i:i + lote]
        rows = ler_tudo(
            lambda: client.table("sprint_meta_funcionalidades").select("sprint_id, funcionalidade_id")
            .in_("funcionalidade_id", parte).order("sprint_id").order("funcionalidade_id")
        )
        for r in rows:
            por_func.setdefault(r["funcionalidade_id"], set()).add(r["sprint_id"])
    sprint_ids = sorted({s for ss in por_func.values() for s in ss})
    abertas: dict[str, int] = {}
    for i in range(0, len(sprint_ids), lote):
        parte = sprint_ids[i:i + lote]
        rows = ler_tudo(
            lambda: client.table("sprints").select("id, numero, avaliacao_completa_em").in_("id", parte).order("id")
        )
        abertas.update({r["id"]: r["numero"] for r in rows if not r.get("avaliacao_completa_em")})
    return {f: sorted(abertas[s] for s in ss if s in abertas) for f, ss in por_func.items()}


def com_tem_tasks(client, funcs: list[dict]) -> list[dict]:
    ids = [f["id"] for f in funcs]
    com_tasks = _ids_com_tasks(client, ids)
    try:
        metas = _metas_abertas(client, ids)
    except Exception:
        # Enriquecimento opcional: sem a tabela de metas (migração pendente) ou com erro de leitura, o CRUD segue.
        logger.exception("Falha ao ler as metas das funcionalidades")
        metas = {}
    return [{**f, "tem_tasks": f["id"] in com_tasks, "meta_sprints": metas.get(f["id"], [])} for f in funcs]


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
    return com_tem_tasks(client, nomes_dos_aprovadores(client, resp.data))[0]


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
    return com_tem_tasks(client, nomes_dos_aprovadores(client, resp.data))[0]


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
