"""Rotas autenticadas do Discovery (Spec 12 §4): requisitos, revisão, validação e promoção.

Cargo checado no backend; `project_id` derivado do recurso (nunca do corpo). A transcrição
inteira só sai por `GET /reunioes/{id}/transcricao`, para gerente+."""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response

from core.rate_limit import GEMINI_RATE_LIMIT, limiter

from models.discovery import (
    RequisitoDetalheResponse, RequisitoPatch, RequisitoResponse, ReuniaoResponse, StatusRequisito,
)
from services import discovery_store as store
from services.auth import require_project_access, require_role
from services.discovery_analise import analisar_em_segundo_plano, reconsolidar_em_segundo_plano
from services.discovery_contexto import compilar_contexto
from services.discovery_promocao import promover_requisito
from services.discovery_requisitos import RegraRequisitoErro, pode_editar, validar_transicao
from services.supabase_client import get_client

router = APIRouter(prefix="/discovery", tags=["discovery"])
_ACESSO = [Depends(require_project_access)]
_CAMPOS_EDITAVEIS = ("titulo", "descricao", "criterios_aceite", "prioridade_sugerida")


def _regra(exc: RegraRequisitoErro) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.detail)


def _com_contagem(client, requisitos: list[dict]) -> list[dict]:
    contagem = store.contar_evidencias(client, [r["id"] for r in requisitos])
    return [{**r, "n_evidencias": contagem.get(r["id"], 0)} for r in requisitos]


async def _acesso_ou_404(project_id: str, pessoa: dict, detalhe: str) -> None:
    """Sem acesso ao projeto do objeto responde 404, igual a inexistente (não revela que existe)."""
    try:
        await require_project_access(project_id, pessoa)
    except HTTPException as exc:
        if exc.status_code == 403:
            raise HTTPException(status_code=404, detail=detalhe) from exc
        raise


async def _requisito_com_acesso(client, requisito_id: str, pessoa: dict) -> dict:
    req = store.buscar_requisito(client, requisito_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requisito não encontrado")
    await _acesso_ou_404(req["project_id"], pessoa, "Requisito não encontrado")
    return req


async def _reuniao_com_acesso(client, reuniao_id: str, pessoa: dict) -> dict:
    reuniao = store.buscar_reuniao(client, reuniao_id)
    if reuniao is None:
        raise HTTPException(status_code=404, detail="Reunião não encontrada")
    await _acesso_ou_404(reuniao["project_id"], pessoa, "Reunião não encontrada")
    return reuniao


@router.get("/projetos/{project_id}/requisitos", response_model=list[RequisitoResponse], dependencies=_ACESSO)
async def listar_requisitos(project_id: str, status: StatusRequisito | None = Query(default=None)):
    client = get_client()
    return _com_contagem(client, store.listar_requisitos(client, project_id, status))


@router.get("/projetos/{project_id}/reunioes", response_model=list[ReuniaoResponse], dependencies=_ACESSO)
async def listar_reunioes(project_id: str):
    return store.listar_reunioes(get_client(), project_id)  # response_model descarta conteúdo e transcrição


@router.get("/projetos/{project_id}/contexto", dependencies=_ACESSO)
async def contexto(project_id: str):
    return compilar_contexto(get_client(), project_id)


@router.get("/requisitos/{requisito_id}", response_model=RequisitoDetalheResponse)
async def detalhe_requisito(requisito_id: str, pessoa: dict = Depends(require_role("operacional"))):
    client = get_client()
    req = await _requisito_com_acesso(client, requisito_id, pessoa)
    return {
        **_com_contagem(client, [req])[0],
        "evidencias": store.listar_evidencias(client, requisito_id),
        "transicoes": store.listar_transicoes(client, requisito_id),
    }


@router.patch("/requisitos/{requisito_id}", response_model=RequisitoResponse)
async def alterar_requisito(requisito_id: str, dados: RequisitoPatch, pessoa: dict = Depends(require_role("operacional"))):
    client = get_client()
    req = await _requisito_com_acesso(client, requisito_id, pessoa)
    autor, cargo = pessoa["email"], pessoa["cargo"]
    campos: dict = {}
    transicoes: list[tuple[str, str, str, str | None]] = []

    edicoes = dados.model_dump(exclude_none=True, include=set(_CAMPOS_EDITAVEIS))
    if edicoes:
        if not pode_editar(req["status"], cargo):
            raise HTTPException(status_code=403, detail="Requisito validado só o gerente edita")
        campos.update(edicoes)
        transicoes.append(("edicao", "", ",".join(sorted(edicoes)), dados.motivo))

    if dados.status is not None:
        try:
            validar_transicao(req["status"], dados.status, cargo, dados.motivo)
        except RegraRequisitoErro as exc:
            raise _regra(exc) from exc
        campos["status"] = dados.status
        if dados.status == "em_revisao":
            campos["revisado_por"] = autor
        elif dados.status == "validado":
            campos["validado_por"] = autor
        else:
            campos["motivo_decisao"] = dados.motivo
        transicoes.append(("status", req["status"], dados.status, dados.motivo))

    if req["status"] in ("proposto", "em_revisao"):
        # Condicional ao status na hora da escrita: se a análise/outro revisor mudou antes, não sobrescreve.
        atualizado = store.atualizar_requisito_se_editavel(client, requisito_id, campos)
        if atualizado is None:
            raise HTTPException(status_code=409, detail="O requisito mudou enquanto você editava; recarregue")
    else:
        atualizado = store.atualizar_requisito(client, requisito_id, campos)
    for campo, de, para, motivo in transicoes:
        store.inserir_transicao(client, requisito_id=requisito_id, campo=campo, de=de, para=para, autor=autor, motivo=motivo)
    return _com_contagem(client, [atualizado])[0]


@router.post("/requisitos/{requisito_id}/promover")
async def promover(requisito_id: str, pessoa: dict = Depends(require_role("gerente"))):
    client = get_client()
    await _requisito_com_acesso(client, requisito_id, pessoa)
    try:
        return promover_requisito(client, requisito_id, pessoa["email"])
    except RegraRequisitoErro as exc:
        raise _regra(exc) from exc


@router.post("/projetos/{project_id}/reconsolidar", status_code=202)
@limiter.limit(GEMINI_RATE_LIMIT)
async def reconsolidar(
    request: Request, response: Response, project_id: str, background: BackgroundTasks,
    pessoa: dict = Depends(require_role("gerente")),
):
    await require_project_access(project_id, pessoa)
    if store.buscar_projeto(get_client(), project_id) is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    background.add_task(reconsolidar_em_segundo_plano, project_id)
    return {"status": "agendada"}


@router.post("/reunioes/{reuniao_id}/analisar", status_code=202)
@limiter.limit(GEMINI_RATE_LIMIT)
async def reanalisar(
    request: Request, response: Response, reuniao_id: str, background: BackgroundTasks,
    pessoa: dict = Depends(require_role("gerente")),
):
    client = get_client()
    await _reuniao_com_acesso(client, reuniao_id, pessoa)
    # Ação explícita: volta a `pendente` mesmo com reserva velha; uma análise em andamento não é
    # derrubada (a reserva dentro de analisar_reuniao impede a execução dupla).
    store.reiniciar_analise(client, reuniao_id, agora=datetime.now(timezone.utc))
    background.add_task(analisar_em_segundo_plano, reuniao_id)
    return {"status": "agendada"}


@router.get("/reunioes/{reuniao_id}/transcricao")
async def transcricao(reuniao_id: str, response: Response, pessoa: dict = Depends(require_role("gerente"))):
    response.headers["Cache-Control"] = "no-store"  # texto integral nunca em cache de navegador/proxy
    client = get_client()
    await _reuniao_com_acesso(client, reuniao_id, pessoa)
    t = store.buscar_transcricao(client, reuniao_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")
    expira = t.get("expira_em")
    if expira and datetime.fromisoformat(str(expira).replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Transcrição expirada")
    return {"conteudo": t["conteudo"], "redigida": bool(t.get("redigida"))}
