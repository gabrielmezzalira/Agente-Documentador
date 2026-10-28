"""Acompanhamento dos projetos por gerente (Rodada B1). Só líder/owner."""
from fastapi import APIRouter, Depends, Query

from models.schemas import AcompanhamentoResponse
from services.acompanhamento import montar_acompanhamento
from services.auth import require_role
from services.supabase_client import get_client

router = APIRouter(prefix="/acompanhamento", tags=["acompanhamento"])


@router.get("", response_model=AcompanhamentoResponse)
def get_acompanhamento(subarea: str = Query("dados", pattern="^(dados|dev)$"), gerente_email: str | None = Query(None),
                       _=Depends(require_role("lider"))):
    return montar_acompanhamento(get_client(), subarea, gerente_email=gerente_email or None)
