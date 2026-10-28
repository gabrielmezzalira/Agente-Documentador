"""Acompanhamento dos projetos por gerente (Rodada B1). Só líder/owner."""
from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import AcompDetalheResponse, AcompanhamentoResponse
from services.acompanhamento import montar_acompanhamento, montar_detalhe
from services.auth import require_role
from services.supabase_client import get_client

router = APIRouter(prefix="/acompanhamento", tags=["acompanhamento"])


@router.get("", response_model=AcompanhamentoResponse)
def get_acompanhamento(subarea: str = Query("dados", pattern="^(dados|dev)$"), gerente_email: str | None = Query(None),
                       _=Depends(require_role("lider"))):
    return montar_acompanhamento(get_client(), subarea, gerente_email=gerente_email or None)


@router.get("/projetos/{projeto_id}", response_model=AcompDetalheResponse)
def get_detalhe_projeto(projeto_id: str, _=Depends(require_role("lider"))):
    detalhe = montar_detalhe(get_client(), projeto_id)
    if detalhe is None:
        raise HTTPException(404, "Projeto não encontrado")
    return detalhe
