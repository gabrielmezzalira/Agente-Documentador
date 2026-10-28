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


def sprint_ou_404(client, sprint_id: str) -> dict:
    sprint = (client.table("sprints").select("id, project_id, avaliacao_completa_em")
              .eq("id", sprint_id).execute().data or [])
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint não encontrada")
    return sprint[0]


def substituir_meta(client, sprint_id: str, funcionalidade_ids: list[str], pessoa_id) -> set[str]:
    sprint = sprint_ou_404(client, sprint_id)
    if sprint.get("avaliacao_completa_em"):
        raise HTTPException(status_code=409, detail="A sprint já foi fechada; a meta não pode mais mudar.")

    novos = list(dict.fromkeys(funcionalidade_ids))
    incluir, retirar = diferenca_meta(ler_meta(client, sprint_id), set(novos))
    a_incluir = [f for f in novos if f in incluir]

    encontradas: dict[str, dict] = {}
    for lote in _lotes(a_incluir):
        for f in (client.table("funcionalidades")
                  .select("id, project_id, id_funcional, status, aprovada_em").in_("id", lote).execute().data or []):
            encontradas[f["id"]] = f
    for fid in a_incluir:
        f = encontradas.get(fid)
        if f is None or f.get("project_id") != sprint["project_id"] or funcionalidade_entregue(f, None):
            rotulo = (f or {}).get("id_funcional") or fid
            raise HTTPException(status_code=422, detail=f"Funcionalidade inválida para a meta: {rotulo}")

    eventos = ([{"sprint_id": sprint_id, "funcionalidade_id": f, "acao": "incluiu", "pessoa_id": pessoa_id} for f in a_incluir]
               + [{"sprint_id": sprint_id, "funcionalidade_id": f, "acao": "retirou", "pessoa_id": pessoa_id} for f in sorted(retirar)])
    try:
        # Eventos primeiro: se a escrita da meta falhar, a nova tentativa cura (meta_em é baseado em conjunto).
        if eventos:
            client.table("sprint_meta_eventos").insert(eventos).execute()
        if a_incluir:
            client.table("sprint_meta_funcionalidades").upsert(
                [{"sprint_id": sprint_id, "funcionalidade_id": f, "incluida_por": pessoa_id} for f in a_incluir],
                on_conflict="sprint_id,funcionalidade_id").execute()
        for lote in _lotes(sorted(retirar)):
            client.table("sprint_meta_funcionalidades").delete().eq("sprint_id", sprint_id).in_("funcionalidade_id", lote).execute()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=409, detail="A meta foi alterada ao mesmo tempo; recarregue e tente de novo.")
    return ler_meta(client, sprint_id)


def eventos_detalhados(client, sprint_id: str) -> list[dict]:
    sprint_ou_404(client, sprint_id)
    eventos = eventos_da_meta(client, [sprint_id])
    titulos: dict[str, str] = {}
    for lote in _lotes([e["funcionalidade_id"] for e in eventos]):
        for f in client.table("funcionalidades").select("id, titulo").in_("id", lote).execute().data or []:
            titulos[f["id"]] = f["titulo"]
    nomes: dict[str, str] = {}
    for lote in _lotes([e["pessoa_id"] for e in eventos if e.get("pessoa_id")]):
        for p in client.table("pessoa").select("id, nome").in_("id", lote).execute().data or []:
            nomes[p["id"]] = p["nome"]
    return [{"funcionalidade_id": e["funcionalidade_id"], "titulo": titulos.get(e["funcionalidade_id"]), "acao": e["acao"],
             "pessoa_nome": nomes.get(e.get("pessoa_id")), "criado_em": str(e["criado_em"])} for e in eventos]
