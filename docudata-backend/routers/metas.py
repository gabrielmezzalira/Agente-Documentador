"""Meta de funcionalidades por sprint (Rodada B1). Só líder/owner."""
from fastapi import APIRouter, Depends

from models.schemas import MetaEvento, MetaResponse, MetaUpdate
from services.auth import require_role
from services.metas import sprint_ou_404, eventos_detalhados, ler_meta, substituir_meta
from services.supabase_client import get_client

router = APIRouter(prefix="/sprints", tags=["metas"])


def _resposta(sprint_id: str, ids: set[str]) -> MetaResponse:
    return MetaResponse(sprint_id=sprint_id, funcionalidade_ids=sorted(ids))


@router.get("/{sprint_id}/meta", response_model=MetaResponse)
def get_meta(sprint_id: str, _=Depends(require_role("lider"))):
    client = get_client()
    sprint_ou_404(client, sprint_id)
    return _resposta(sprint_id, ler_meta(client, sprint_id))


@router.put("/{sprint_id}/meta", response_model=MetaResponse)
def put_meta(sprint_id: str, body: MetaUpdate, pessoa: dict = Depends(require_role("lider"))):
    return _resposta(sprint_id, substituir_meta(get_client(), sprint_id, body.funcionalidade_ids, pessoa["id"]))


@router.get("/{sprint_id}/meta/eventos", response_model=list[MetaEvento])
def get_eventos(sprint_id: str, _=Depends(require_role("lider"))):
    return eventos_detalhados(get_client(), sprint_id)
