"""Router do Motor de Score: SPI do operacional.

Acesso: o ranking e o score final continuam exclusivos do Líder
(routers/performance.py). SPI travado por operacional foi aberto ao Gerente
em 2026-09-07 (decisão do Líder) para sustentar a conversa de feedback —
Operacional segue sem acesso a nenhum payload de score.

O extrato de pontos (GET /operacionais/{id}/extrato) é extra do usuário —
não faz parte do SDD de Modos de Trabalho e de Avaliação — e segue a mesma
regra de acesso: Gerente e Líder, nunca Operacional."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    PontuacaoEventoResponse,
    SpiOperacionalResponse,
    SpiPorOperacionalDoProjetoResponse,
)
from services.acesso import exigir_acesso, exigir_acesso_por, project_id_de
from services.auth import require_not_operacional, require_project_access, require_role
from services.pontuacao import calcular_spi_operacional, listar_extrato_pontos, listar_spi_do_projeto
from services.supabase_client import get_client

router = APIRouter(tags=["pontuacao"])


@router.get(
    "/operacionais/{operacional_id}/spi",
    response_model=SpiOperacionalResponse,
)
async def get_spi_operacional(operacional_id: str, pessoa: dict = Depends(require_not_operacional)):
    client = get_client()
    exigir_acesso_por(client, pessoa, "operacional", operacional_id)
    return calcular_spi_operacional(client, operacional_id)


@router.get(
    "/projects/{projeto_id}/spi",
    response_model=list[SpiPorOperacionalDoProjetoResponse],
)
async def get_spi_do_projeto(projeto_id: str, pessoa: dict = Depends(require_not_operacional)):
    """SPI travado de cada operacional do projeto — a leitura que o gerente
    usa na conversa de feedback. Não expõe score final nem ranking."""
    client = get_client()
    exigir_acesso(client, pessoa, projeto_id)
    projeto = client.table("projects").select("id").eq("id", projeto_id).execute()
    if not projeto.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return listar_spi_do_projeto(client, projeto_id)


@router.get(
    "/operacionais/{operacional_id}/extrato",
    response_model=list[PontuacaoEventoResponse],
)
async def get_extrato_pontos(
    operacional_id: str, sprint_id: Optional[str] = None, pessoa: dict = Depends(require_not_operacional)
):
    """Extrato de todo ponto ganho ou descontado do operacional (extra do
    usuário). Gerente e Líder apenas."""
    client = get_client()
    project_id = exigir_acesso_por(client, pessoa, "operacional", operacional_id)
    if sprint_id and project_id_de(client, "sprint", sprint_id) != project_id:
        raise HTTPException(status_code=403, detail="Esta sprint pertence a outro projeto.")
    return listar_extrato_pontos(client, operacional_id, sprint_id)
