"""Router do Motor de Score: SPI do operacional, evolução e baseline.

Acesso: o ranking e o score final continuam exclusivos do Líder
(routers/performance.py). SPI travado e Evolução por operacional foram abertos
ao Gerente em 2026-09-07 (decisão do Líder) para sustentar a conversa de
feedback — Operacional segue sem acesso a nenhum payload de score."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    BaselineEvolucaoCreate,
    BaselineEvolucaoResponse,
    SpiEvolucaoOperacionalResponse,
    SpiOperacionalResponse,
)
from services.auth import require_not_operacional, require_role
from services.pontuacao import calcular_spi_operacional, listar_spi_evolucao_do_projeto
from services.supabase_client import get_client

router = APIRouter(tags=["pontuacao"])


@router.get(
    "/operacionais/{operacional_id}/spi",
    response_model=SpiOperacionalResponse,
    dependencies=[Depends(require_not_operacional)],
)
async def get_spi_operacional(operacional_id: str):
    client = get_client()
    return calcular_spi_operacional(client, operacional_id)


@router.get(
    "/projects/{projeto_id}/spi-evolucao",
    response_model=list[SpiEvolucaoOperacionalResponse],
    dependencies=[Depends(require_not_operacional)],
)
async def get_spi_evolucao_do_projeto(projeto_id: str):
    """SPI travado e Evolução de cada operacional do projeto — a leitura que o
    gerente usa na conversa de feedback. Não expõe score final nem ranking."""
    client = get_client()
    projeto = client.table("projects").select("id").eq("id", projeto_id).execute()
    if not projeto.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return listar_spi_evolucao_do_projeto(client, projeto_id)


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
