"""Meta de funcionalidades por sprint (Rodada B1). Só líder/owner."""
from fastapi import APIRouter, Depends

from models.schemas import MetaEvento, MetaResponse, MetaUpdate
from services.auth import require_role
from services.metas import eventos_da_meta, ler_meta, substituir_meta
from services.supabase_client import get_client

router = APIRouter(prefix="/sprints", tags=["metas"])


def _resposta(sprint_id: str, ids: set[str]) -> MetaResponse:
    return MetaResponse(sprint_id=sprint_id, funcionalidade_ids=sorted(ids))


@router.get("/{sprint_id}/meta", response_model=MetaResponse)
def get_meta(sprint_id: str, _=Depends(require_role("lider"))):
    return _resposta(sprint_id, ler_meta(get_client(), sprint_id))


@router.put("/{sprint_id}/meta", response_model=MetaResponse)
def put_meta(sprint_id: str, body: MetaUpdate, pessoa: dict = Depends(require_role("lider"))):
    return _resposta(sprint_id, substituir_meta(get_client(), sprint_id, body.funcionalidade_ids, pessoa["id"]))


@router.get("/{sprint_id}/meta/eventos", response_model=list[MetaEvento])
def get_eventos(sprint_id: str, _=Depends(require_role("lider"))):
    client = get_client()
    eventos = eventos_da_meta(client, [sprint_id])
    fids = list({e["funcionalidade_id"] for e in eventos})
    pids = list({e["pessoa_id"] for e in eventos if e.get("pessoa_id")})
    titulos = {f["id"]: f["titulo"] for f in (client.table("funcionalidades").select("id, titulo").in_("id", fids).execute().data or [])} if fids else {}
    nomes = {p["id"]: p["nome"] for p in (client.table("pessoa").select("id, nome").in_("id", pids).execute().data or [])} if pids else {}
    return [MetaEvento(funcionalidade_id=e["funcionalidade_id"], titulo=titulos.get(e["funcionalidade_id"]), acao=e["acao"],
                       pessoa_nome=nomes.get(e.get("pessoa_id")), criado_em=str(e["criado_em"])) for e in eventos]
