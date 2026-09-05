"""Router do Motor de Score (Phase 18): SPI do operacional e baseline de
evolução. Acesso restrito a cargo=lider (RBAC Phase 16,
.planning/intel/decisions.md #4) — nenhum payload de score/SPI é exposto a
Gerente ou Operacional."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    BaselineEvolucaoCreate,
    BaselineEvolucaoResponse,
    SpiOperacionalResponse,
)
from services.auth import require_role
from services.pontuacao import calcular_spi_operacional
from services.supabase_client import get_client

router = APIRouter(tags=["pontuacao"])


@router.get(
    "/operacionais/{operacional_id}/spi",
    response_model=SpiOperacionalResponse,
    dependencies=[Depends(require_role("lider"))],
)
async def get_spi_operacional(operacional_id: str):
    client = get_client()
    return calcular_spi_operacional(client, operacional_id)


@router.post(
    "/baseline-evolucao",
    response_model=BaselineEvolucaoResponse,
    status_code=201,
    dependencies=[Depends(require_role("lider"))],
)
async def criar_baseline_evolucao(data: BaselineEvolucaoCreate):
    client = get_client()
    op_check = client.table("operacionais").select("id").eq("id", data.operacional_id).execute()
    if not op_check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    spi = calcular_spi_operacional(client, data.operacional_id)
    payload = {
        "operacional_id": data.operacional_id,
        "ciclo": data.ciclo,
        "data_snapshot": datetime.now(timezone.utc).isoformat(),
        "nota_inicial": spi["spi"],
        "observacoes": data.observacoes,
    }
    resp = client.table("baseline_evolucao").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar baseline")
    return resp.data[0]
