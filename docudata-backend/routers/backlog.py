"""Backlog pessoal (gerente, líder e owner): quadro de coisas a fazer que só a própria pessoa enxerga.

Além do cargo, toda consulta filtra pelo id de quem está logado — outro Owner
(se existir) não vê nem altera a lista alheia.
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.observability import falha_externa
from services.auth import require_not_operacional
from services.supabase_client import get_client

router = APIRouter(prefix="/backlog", tags=["backlog"])

Prioridade = Literal["alta", "media", "baixa"]
Status = Literal["planejado", "andamento", "concluido"]


class BacklogCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    notas: Optional[str] = Field(default=None, max_length=5000)
    prioridade: Prioridade = "media"
    status: Status = "planejado"


class BacklogUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=200)
    notas: Optional[str] = Field(default=None, max_length=5000)
    prioridade: Optional[Prioridade] = None
    status: Optional[Status] = None


def _com_status(linha: dict) -> dict:
    """Linhas anteriores à migração v19 não têm status: deriva de `feito`."""
    linha = dict(linha)
    linha["status"] = linha.get("status") or ("concluido" if linha.get("feito") else "planejado")
    return linha


def _erro(exc: Exception, acao: str):
    texto = str(exc)
    if "backlog_pessoal" in texto and any(m in texto for m in ("PGRST205", "42P01", "does not exist")):
        return HTTPException(status_code=503, detail="Backlog indisponível: aplique a migração v18.")
    if "status" in texto and any(m in texto for m in ("PGRST204", "42703", "does not exist", "schema cache")):
        return HTTPException(status_code=503, detail="Backlog indisponível: aplique a migração v19.")
    return falha_externa("supabase.backlog", exc, f"Não foi possível {acao}", status_code=500)


def _campos_de_status(status: str) -> dict:
    """`feito` e `concluido_em` acompanham o status, para o dado antigo e o novo não divergirem."""
    concluido = status == "concluido"
    return {
        "status": status, "feito": concluido,
        "concluido_em": datetime.now(timezone.utc).isoformat() if concluido else None,
    }


@router.get("")
async def listar(pessoa: dict = Depends(require_not_operacional)):
    try:
        linhas = (
            get_client().table("backlog_pessoal").select("*").eq("pessoa_id", pessoa["id"])
            .order("criado_em", desc=True).execute().data or []
        )
    except Exception as exc:
        raise _erro(exc, "carregar o backlog")
    return [_com_status(l) for l in linhas]


@router.post("", status_code=201)
async def criar(data: BacklogCreate, pessoa: dict = Depends(require_not_operacional)):
    titulo = data.titulo.strip()
    if not titulo:
        raise HTTPException(status_code=422, detail="Dê um título ao item")
    try:
        resp = get_client().table("backlog_pessoal").insert({
            "pessoa_id": pessoa["id"], "titulo": titulo, "notas": (data.notas or "").strip() or None,
            "prioridade": data.prioridade, **_campos_de_status(data.status),
        }).execute()
    except Exception as exc:
        raise _erro(exc, "criar o item")
    return _com_status(resp.data[0])


@router.patch("/{item_id}")
async def atualizar(item_id: str, data: BacklogUpdate, pessoa: dict = Depends(require_not_operacional)):
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
    if data.status is not None:
        campos.update(_campos_de_status(data.status))
    try:
        atual = client.table("backlog_pessoal").select("*").eq("id", item_id).eq("pessoa_id", pessoa["id"]).execute().data
        if not atual:
            raise HTTPException(status_code=404, detail="Item não encontrado")
        if not campos:
            return _com_status(atual[0])
        # Já estava concluído e continua: mantém a data original da conclusão.
        if campos.get("status") == "concluido" and _com_status(atual[0])["status"] == "concluido":
            campos["concluido_em"] = atual[0].get("concluido_em") or campos["concluido_em"]
        resp = client.table("backlog_pessoal").update(campos).eq("id", item_id).eq("pessoa_id", pessoa["id"]).execute()
    except HTTPException:
        raise
    except Exception as exc:
        raise _erro(exc, "atualizar o item")
    return _com_status(resp.data[0])


@router.delete("/{item_id}", status_code=204)
async def apagar(item_id: str, pessoa: dict = Depends(require_not_operacional)):
    try:
        get_client().table("backlog_pessoal").delete().eq("id", item_id).eq("pessoa_id", pessoa["id"]).execute()
    except Exception as exc:
        raise _erro(exc, "apagar o item")
