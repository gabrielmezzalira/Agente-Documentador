"""Meta de funcionalidades por sprint (Rodada B1, entrega 2)."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from services.supabase_paginacao import ler_tudo

LOTE = 100


def _dt(v) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def diferenca_meta(atual: set[str], nova: set[str]) -> tuple[set[str], set[str]]:
    return nova - atual, atual - nova


def meta_em(eventos: list[dict], ate: datetime) -> set[str]:
    meta: set[str] = set()
    for e in sorted(eventos, key=lambda e: _dt(e["criado_em"])):
        if _dt(e["criado_em"]) > ate:
            break
        if e["acao"] == "incluiu":
            meta.add(e["funcionalidade_id"])
        else:
            meta.discard(e["funcionalidade_id"])
    return meta


def meta_original(eventos: list[dict], inicio: datetime | None) -> set[str]:
    if not eventos:
        return set()
    if inicio is not None:
        antes = meta_em(eventos, inicio)
        if antes:
            return antes
    primeiro = min(_dt(e["criado_em"]) for e in eventos)
    fim_do_dia = datetime(primeiro.year, primeiro.month, primeiro.day, tzinfo=timezone.utc) + timedelta(days=1) - timedelta(microseconds=1)
    return meta_em(eventos, fim_do_dia)


def resultado_meta(meta: set[str], entregues: set[str]) -> dict:
    if not meta:
        return {"total": 0, "entregues": 0, "batida": None}
    n = len(meta & entregues)
    return {"total": len(meta), "entregues": n, "batida": n == len(meta)}


def funcionalidade_entregue(func: dict, fechada_em: str | None) -> bool:
    if func.get("status") != "concluida" or not func.get("aprovada_em"):
        return False
    return fechada_em is None or _dt(func["aprovada_em"]) <= _dt(fechada_em)


def _lotes(ids: list[str]):
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), LOTE):
        yield ids[i:i + LOTE]


def metas_das_sprints(client, sprint_ids: list[str]) -> dict[str, set[str]]:
    saida: dict[str, set[str]] = {s: set() for s in sprint_ids}
    for lote in _lotes(sprint_ids):
        linhas = ler_tudo(lambda lote=lote: client.table("sprint_meta_funcionalidades")
                          .select("sprint_id, funcionalidade_id").in_("sprint_id", lote)
                          .order("sprint_id").order("funcionalidade_id"))
        for l in linhas:
            saida[l["sprint_id"]].add(l["funcionalidade_id"])
    return saida


def ler_meta(client, sprint_id: str) -> set[str]:
    return metas_das_sprints(client, [sprint_id])[sprint_id]


def eventos_da_meta(client, sprint_ids: list[str]) -> list[dict]:
    saida: list[dict] = []
    for lote in _lotes(sprint_ids):
        saida += ler_tudo(lambda lote=lote: client.table("sprint_meta_eventos")
                          .select("id, sprint_id, funcionalidade_id, acao, pessoa_id, criado_em")
                          .in_("sprint_id", lote).order("criado_em").order("id"))
    return saida


def substituir_meta(client, sprint_id: str, funcionalidade_ids: list[str], pessoa_id) -> set[str]:
    sprint = (client.table("sprints").select("id, project_id, avaliacao_completa_em")
              .eq("id", sprint_id).execute().data or [])
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint não encontrada")
    sprint = sprint[0]
    if sprint.get("avaliacao_completa_em"):
        raise HTTPException(status_code=409, detail="A sprint já foi fechada; a meta não pode mais mudar.")

    novos = list(dict.fromkeys(funcionalidade_ids))
    encontradas: dict[str, dict] = {}
    for lote in _lotes(novos):
        for f in (client.table("funcionalidades")
                  .select("id, project_id, id_funcional, status, aprovada_em").in_("id", lote).execute().data or []):
            encontradas[f["id"]] = f
    for fid in novos:
        f = encontradas.get(fid)
        if f is None or f.get("project_id") != sprint["project_id"] or funcionalidade_entregue(f, None):
            rotulo = (f or {}).get("id_funcional") or fid
            raise HTTPException(status_code=422, detail=f"Funcionalidade inválida para a meta: {rotulo}")

    incluir, retirar = diferenca_meta(ler_meta(client, sprint_id), set(novos))
    for fid in novos:
        if fid in incluir:
            client.table("sprint_meta_funcionalidades").insert(
                {"sprint_id": sprint_id, "funcionalidade_id": fid, "incluida_por": pessoa_id}).execute()
    for fid in retirar:
        client.table("sprint_meta_funcionalidades").delete().eq("sprint_id", sprint_id).eq("funcionalidade_id", fid).execute()
    eventos = ([{"sprint_id": sprint_id, "funcionalidade_id": f, "acao": "incluiu", "pessoa_id": pessoa_id} for f in sorted(incluir)]
               + [{"sprint_id": sprint_id, "funcionalidade_id": f, "acao": "retirou", "pessoa_id": pessoa_id} for f in sorted(retirar)])
    if eventos:
        client.table("sprint_meta_eventos").insert(eventos).execute()
    return ler_meta(client, sprint_id)
