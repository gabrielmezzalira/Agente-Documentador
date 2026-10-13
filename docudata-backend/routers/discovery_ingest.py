"""Entrada de reuniões de Discovery vinda do Agente Diagnóstico (Spec 12 §2). Serviço a serviço."""
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from core.rate_limit import GEMINI_RATE_LIMIT, limiter
from models.discovery import ReuniaoIngestRequest, ReuniaoIngestResponse
from services import discovery_store as store
from services.discovery_analise import analisar_em_segundo_plano
from services.discovery_redacao import TRANSCRICAO_MAX_BYTES, redigir_estrutura, redigir_segredos
from services.supabase_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery-ingest"])


def _resposta_duplicada(existente: dict, project_id: str) -> ReuniaoIngestResponse:
    # fonte_session_id é único no banco: a mesma sessão em outro projeto é conflito, não reenvio.
    if existente.get("project_id") != project_id:
        raise HTTPException(status_code=409, detail="Sessão já registrada em outro projeto")
    return ReuniaoIngestResponse(id=existente["id"], analise_status=existente["analise_status"], duplicada=True)


@router.post("/reunioes", response_model=ReuniaoIngestResponse, status_code=202)
@limiter.limit(GEMINI_RATE_LIMIT)
async def receber_reuniao(
    request: Request, response: Response, data: ReuniaoIngestRequest, background: BackgroundTasks,
):
    """Guarda a reunião (e a transcrição, à parte) e dispara a análise em segundo plano."""
    # Limite de tamanho primeiro: barato e antes de qualquer consulta ou regex.
    if data.transcricao and len(data.transcricao.encode("utf-8")) > TRANSCRICAO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Transcrição acima do limite de 2 MB")

    client = get_client()
    # O projeto é carregado no servidor; a subárea nunca vem do corpo.
    if store.buscar_projeto(client, data.docudata_project_id) is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    existente = store.buscar_reuniao_por_fonte(client, data.fonte_session_id)
    if existente:  # reenvio: idempotente, sem nova análise nem nova cobrança do Gemini
        response.status_code = 200
        return _resposta_duplicada(existente, data.docudata_project_id)

    transcricao, redigida = None, False
    if data.transcricao:
        transcricao, redigida = redigir_segredos(data.transcricao)

    try:
        reuniao = store.inserir_reuniao(
            client, project_id=data.docudata_project_id, tipo=data.tipo,
            ocorrida_em=data.ocorrida_em.isoformat() if data.ocorrida_em else None,
            fonte_session_id=data.fonte_session_id,
            conteudo_estruturado=redigir_estrutura(data.conteudo_estruturado),
        )
    except Exception:
        # Reenvio concorrente: o UNIQUE de fonte_session_id barrou o segundo INSERT.
        existente = store.buscar_reuniao_por_fonte(client, data.fonte_session_id)
        if not existente:
            logger.error("Falha ao gravar reunião de Discovery")
            raise HTTPException(status_code=500, detail="Erro interno ao registrar a reunião")
        response.status_code = 200
        return _resposta_duplicada(existente, data.docudata_project_id)

    if transcricao:
        store.inserir_transcricao(client, reuniao_id=reuniao["id"], conteudo=transcricao, redigida=redigida)
    background.add_task(analisar_em_segundo_plano, reuniao["id"])
    return ReuniaoIngestResponse(id=reuniao["id"], analise_status="pendente")
