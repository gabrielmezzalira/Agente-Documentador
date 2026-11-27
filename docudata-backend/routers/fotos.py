"""Foto de perfil das pessoas. Qualquer pessoa logada vê; gerente/líder troca a de qualquer um e cada um troca a própria."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from core.observability import falha_externa
from services import fotos_perfil as fotos
from services.auth import get_current_pessoa
from services.supabase_client import get_client
from services.task_anexos import MAX_BYTES, AnexoInvalido

router = APIRouter(prefix="/fotos", tags=["fotos"])


def _exigir_permissao(client, pessoa: dict, chave: str) -> None:
    if pessoa["cargo"] != "operacional":
        return
    linha = client.table("pessoa").select("nome").eq("id", pessoa["id"]).execute().data
    if not linha or fotos.chave_do_nome(linha[0]["nome"]) != chave:
        raise HTTPException(status_code=403, detail="Você só pode trocar a sua própria foto")


@router.get("")
async def listar_fotos(pessoa: dict = Depends(get_current_pessoa)):
    try:
        return fotos.versoes(get_client())
    except Exception as exc:
        raise falha_externa("supabase.storage.fotos", exc, "Não foi possível carregar as fotos", status_code=503)


@router.get("/{chave}")
async def baixar_foto(chave: str, tam: str = "", pessoa: dict = Depends(get_current_pessoa)):
    if not fotos.chave_valida(chave):
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    try:
        dados = fotos.baixar(get_client(), chave, completa=tam == "completa")
    except Exception:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return Response(
        content=dados,
        media_type="image/webp",
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff", "Content-Disposition": "inline"},
    )


@router.put("")
async def trocar_foto(
    nome: str = Form(...), arquivo: UploadFile = File(...), pessoa: dict = Depends(get_current_pessoa),
):
    chave = fotos.chave_do_nome(nome)
    if not fotos.chave_valida(chave):
        raise HTTPException(status_code=422, detail="Nome inválido")
    client = get_client()
    _exigir_permissao(client, pessoa, chave)
    dados = await arquivo.read(MAX_BYTES + 1)
    try:
        fotos.salvar(client, chave, dados)
    except AnexoInvalido as exc:
        raise HTTPException(status_code=422, detail=exc.mensagem)
    except Exception as exc:
        raise falha_externa("supabase.storage.fotos", exc, "Não foi possível salvar a foto", status_code=503)
    return {"chave": chave}


@router.delete("/{chave}", status_code=204)
async def remover_foto(chave: str, pessoa: dict = Depends(get_current_pessoa)):
    if not fotos.chave_valida(chave):
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    client = get_client()
    _exigir_permissao(client, pessoa, chave)
    try:
        fotos.remover(client, chave)
    except Exception as exc:
        raise falha_externa("supabase.storage.fotos", exc, "Não foi possível remover a foto", status_code=503)
