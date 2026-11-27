"""Backlog pessoal do Owner: lista de coisas a fazer que só ele enxerga.

Além do cargo Owner, toda consulta filtra pelo id de quem está logado — outro Owner
(se existir) não vê nem altera a lista alheia.
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.observability import falha_externa
from services.auth import require_role
from services.supabase_client import get_client

router = APIRouter(prefix="/backlog", tags=["backlog"])

Prioridade = Literal["alta", "media", "baixa"]


class BacklogCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    notas: Optional[str] = Field(default=None, max_length=5000)
    prioridade: Prioridade = "media"


class BacklogUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=200)
    notas: Optional[str] = Field(default=None, max_length=5000)
    prioridade: Optional[Prioridade] = None
    feito: Optional[bool] = None


def _erro(exc: Exception, acao: str):
    texto = str(exc)
    if "backlog_pessoal" in texto and any(m in texto for m in ("PGRST205", "42P01", "does not exist")):
        return HTTPException(status_code=503, detail="Backlog indisponível: aplique a migração v18.")
    return falha_externa("supabase.backlog", exc, f"Não foi possível {acao}", status_code=500)


@router.get("")
async def listar(pessoa: dict = Depends(require_role("owner"))):
    try:
        linhas = (
            get_client().table("backlog_pessoal").select("*").eq("pessoa_id", pessoa["id"])
            .order("criado_em", desc=True).execute().data or []
        )
    except Exception as exc:
        raise _erro(exc, "carregar o backlog")
    return linhas


@router.post("", status_code=201)
async def criar(data: BacklogCreate, pessoa: dict = Depends(require_role("owner"))):
    titulo = data.titulo.strip()
    if not titulo:
        raise HTTPException(status_code=422, detail="Dê um título ao item")
    try:
        resp = get_client().table("backlog_pessoal").insert({
            "pessoa_id": pessoa["id"], "titulo": titulo, "notas": (data.notas or "").strip() or None,
            "prioridade": data.prioridade,
        }).execute()
    except Exception as exc:
        raise _erro(exc, "criar o item")
    return resp.data[0]


@router.patch("/{item_id}")
async def atualizar(item_id: str, data: BacklogUpdate, pessoa: dict = Depends(require_role("owner"))):
    client = get_client()
    campos: dict = {}
    if data.titulo is not None:
        if not data.titulo.strip():
            raise HTTPException(status_code=422, detail="O título não pode ficar vazio")
        campos["titulo"] = data.titulo.strip()
    if data.notas is not None:
        campos["notas"] = data.notas.strip() or None
    if data.prioridade is not None:
        campos["prioridade"] = data.prioridade
    if data.feito is not None:
        campos["feito"] = data.feito
        campos["concluido_em"] = datetime.now(timezone.utc).isoformat() if data.feito else None
    try:
        atual = client.table("backlog_pessoal").select("id").eq("id", item_id).eq("pessoa_id", pessoa["id"]).execute().data
        if not atual:
            raise HTTPException(status_code=404, detail="Item não encontrado")
        if not campos:
            return client.table("backlog_pessoal").select("*").eq("id", item_id).execute().data[0]
        resp = client.table("backlog_pessoal").update(campos).eq("id", item_id).eq("pessoa_id", pessoa["id"]).execute()
    except HTTPException:
        raise
    except Exception as exc:
        raise _erro(exc, "atualizar o item")
    return resp.data[0]


@router.delete("/{item_id}", status_code=204)
async def apagar(item_id: str, pessoa: dict = Depends(require_role("owner"))):
    try:
        get_client().table("backlog_pessoal").delete().eq("id", item_id).eq("pessoa_id", pessoa["id"]).execute()
    except Exception as exc:
        raise _erro(exc, "apagar o item")
