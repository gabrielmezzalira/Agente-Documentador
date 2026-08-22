from datetime import datetime, timezone, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from models.schemas import (
    FuncionalidadeCreate,
    FuncionalidadeUpdate,
    FuncionalidadeResponse,
    TransicaoStatusResponse,
    ImportPropostaResponse,
    ImportConfirmarRequest,
    FuncionalidadeProposta,
)
from services.supabase_client import get_client

router = APIRouter(prefix="/funcionalidades", tags=["funcionalidades"])


class ImportarRequest(BaseModel):
    project_id: str
    texto_contrato: str


@router.post("/importar", response_model=ImportPropostaResponse)
async def importar_funcionalidades(data: ImportarRequest):
    """Propõe funcionalidades a partir do texto do contrato via IA. Não salva nada."""
    import os
    from graphs.import_graph import import_graph

    texto = data.texto_contrato[:50000]
    if len(texto.strip()) < 20:
        raise HTTPException(status_code=422, detail="Texto do contrato muito curto para análise")

    client = get_client()
    proj = client.table("projects").select("gemini_api_key").eq("id", data.project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")
    api_key = (proj.data[0].get("gemini_api_key") or "").strip()
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="Nenhuma API key Gemini configurada para este projeto")

    state = await import_graph.ainvoke({
        "texto_contrato": texto,
        "projeto_id": data.project_id,
        "gemini_api_key": api_key,
        "proposta": None,
        "valido": False,
        "tentativas": 0,
        "erro": None,
    })

    if not state.get("valido") or not state.get("proposta"):
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível extrair funcionalidades do contrato: {state.get('erro', 'resposta inválida')}",
        )

    propostas = []
    for item in state["proposta"]:
        try:
            propostas.append(FuncionalidadeProposta(**item))
        except Exception:
            pass

    if not propostas:
        raise HTTPException(status_code=502, detail="Gemini retornou lista sem itens válidos")

    return ImportPropostaResponse(propostas=propostas)


@router.post("/importar/confirmar", response_model=list[FuncionalidadeResponse], status_code=201)
async def confirmar_importacao(data: ImportConfirmarRequest):
    """Cria as funcionalidades confirmadas e descarta as rejeitadas."""
    client = get_client()
    proj_check = client.table("projects").select("id").eq("id", data.project_id).execute()
    if not proj_check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    confirmadas = [item.proposta for item in data.itens if item.confirmed]
    if not confirmadas:
        return []

    criadas = []
    for prop in confirmadas:
        payload = {
            "project_id": data.project_id,
            "id_funcional": prop.id_funcional,
            "titulo": prop.titulo,
            "criterios_aceite": prop.criterios_aceite,
            "prioridade": prop.prioridade,
        }
        if prop.descricao:
            payload["descricao"] = prop.descricao
        resp = client.table("funcionalidades").insert(payload).execute()
        if resp.data:
            criadas.append(resp.data[0])

    return criadas


@router.post("", response_model=FuncionalidadeResponse, status_code=201)
async def create_funcionalidade(data: FuncionalidadeCreate):
    client = get_client()
    payload = {
        "project_id": data.project_id,
        "id_funcional": data.id_funcional,
        "titulo": data.titulo,
        "criterios_aceite": data.criterios_aceite,
        "prioridade": data.prioridade,
    }
    if data.descricao is not None:
        payload["descricao"] = data.descricao
    if data.responsavel is not None:
        payload["responsavel"] = data.responsavel
    if data.sprint_alvo is not None:
        payload["sprint_alvo"] = data.sprint_alvo
    response = client.table("funcionalidades").insert(payload).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create funcionalidade")
    return response.data[0]


@router.get("", response_model=list[FuncionalidadeResponse])
async def list_funcionalidades(project_id: str = Query(...)):
    client = get_client()
    response = (
        client.table("funcionalidades")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=False)
        .execute()
    )
    return response.data or []


@router.get("/{funcionalidade_id}/transicoes", response_model=list[TransicaoStatusResponse])
async def list_transicoes(funcionalidade_id: str):
    client = get_client()
    response = (
        client.table("transicoes_status")
        .select("*")
        .eq("funcionalidade_id", funcionalidade_id)
        .order("timestamp", desc=False)
        .execute()
    )
    return response.data or []


@router.get("/{funcionalidade_id}", response_model=FuncionalidadeResponse)
async def get_funcionalidade(funcionalidade_id: str):
    client = get_client()
    response = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    return response.data[0]


@router.patch("/{funcionalidade_id}", response_model=FuncionalidadeResponse)
async def patch_funcionalidade(funcionalidade_id: str, data: FuncionalidadeUpdate):
    client = get_client()

    # Fetch current row
    resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    func = resp.data[0]

    agora = datetime.now(timezone.utc)

    # Record transitions for status fields that changed
    for campo in ("status", "status_cliente"):
        novo_valor = getattr(data, campo, None)
        if novo_valor is None or novo_valor == func.get(campo):
            continue
        anterior = (
            client.table("transicoes_status")
            .select("timestamp")
            .eq("funcionalidade_id", funcionalidade_id)
            .eq("campo", campo)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if anterior.data:
            ts_anterior = datetime.fromisoformat(anterior.data[0]["timestamp"]).replace(tzinfo=timezone.utc)
        else:
            ts_anterior = datetime.fromisoformat(func["created_at"]).replace(tzinfo=timezone.utc)
        duracao = int((agora - ts_anterior).total_seconds())
        client.table("transicoes_status").insert({
            "funcionalidade_id": funcionalidade_id,
            "campo": campo,
            "de": func[campo],
            "para": novo_valor,
            "autor": data.autor,
            "timestamp": agora.isoformat(),
            "motivo": data.motivo,
            "duracao_fase_anterior_segundos": duracao,
        }).execute()

    # Build update payload
    updates: dict = {}
    for field in ("titulo", "descricao", "criterios_aceite", "prioridade", "responsavel", "sprint_alvo"):
        val = getattr(data, field, None)
        if val is not None:
            updates[field] = val

    for campo in ("status", "status_cliente"):
        novo_valor = getattr(data, campo, None)
        if novo_valor is not None and novo_valor != func.get(campo):
            updates[campo] = novo_valor

    # Auto-set data_aprovacao_cliente when status_cliente becomes aprovado
    if updates.get("status_cliente") == "aprovado":
        if data.data_aprovacao_cliente is None:
            updates["data_aprovacao_cliente"] = date.today().isoformat()
        else:
            updates["data_aprovacao_cliente"] = data.data_aprovacao_cliente.isoformat()
    elif data.data_aprovacao_cliente is not None:
        updates["data_aprovacao_cliente"] = data.data_aprovacao_cliente.isoformat()

    if not updates:
        return func

    result = client.table("funcionalidades").update(updates).eq("id", funcionalidade_id).execute()
    return result.data[0]


@router.delete("/{funcionalidade_id}", status_code=204)
async def delete_funcionalidade(funcionalidade_id: str):
    client = get_client()
    check = client.table("funcionalidades").select("id").eq("id", funcionalidade_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    client.table("funcionalidades").delete().eq("id", funcionalidade_id).execute()
