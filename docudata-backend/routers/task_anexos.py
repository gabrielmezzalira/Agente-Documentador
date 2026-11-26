"""Imagens anexadas às tasks. O gerente anexa e remove; quem tem acesso ao projeto vê."""
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from core.observability import falha_externa
from services import task_anexos as anexos
from services.acesso import exigir_acesso_por
from services.auth import get_current_pessoa, require_not_operacional
from services.supabase_client import get_client

router = APIRouter(prefix="/tasks", tags=["task-anexos"])


def _com_url(task_id: str, item: dict) -> dict:
    return {**item, "url": f"/tasks/{task_id}/anexos/{item['nome']}"}


def _nome_ou_404(nome: str) -> str:
    if not anexos.nome_valido(nome):
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return nome


@router.get("/{task_id}/anexos")
async def listar_anexos(task_id: str, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    project_id = exigir_acesso_por(client, pessoa, "task", task_id)
    try:
        return [_com_url(task_id, a) for a in anexos.listar(client, project_id, task_id)]
    except Exception as exc:
        raise falha_externa("supabase.storage.listar", exc, "Não foi possível listar as imagens", status_code=503)


@router.post("/{task_id}/anexos", status_code=201)
async def anexar_imagem(task_id: str, arquivo: UploadFile = File(...), pessoa: dict = Depends(require_not_operacional)):
    client = get_client()
    project_id = exigir_acesso_por(client, pessoa, "task", task_id)
    # lê um byte a mais que o limite: arquivo maior é recusado sem carregar tudo na memória
    dados = await arquivo.read(anexos.MAX_BYTES + 1)
    try:
        item = anexos.salvar(client, project_id, task_id, dados, arquivo.filename)
    except anexos.AnexoInvalido as exc:
        raise HTTPException(status_code=422, detail=exc.mensagem)
    except Exception as exc:
        raise falha_externa("supabase.storage.upload", exc, "Não foi possível salvar a imagem", status_code=503)
    return _com_url(task_id, item)


@router.get("/{task_id}/anexos/{nome}")
async def baixar_imagem(task_id: str, nome: str, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    project_id = exigir_acesso_por(client, pessoa, "task", task_id)
    _nome_ou_404(nome)
    try:
        dados = anexos.baixar(client, project_id, task_id, nome)
    except Exception:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return Response(
        content=dados,
        media_type=anexos.mime_do_nome(nome),
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.delete("/{task_id}/anexos/{nome}", status_code=204)
async def remover_imagem(task_id: str, nome: str, pessoa: dict = Depends(require_not_operacional)):
    client = get_client()
    project_id = exigir_acesso_por(client, pessoa, "task", task_id)
    _nome_ou_404(nome)
    try:
        anexos.remover(client, project_id, task_id, nome)
    except Exception as exc:
        raise falha_externa("supabase.storage.remover", exc, "Não foi possível remover a imagem", status_code=503)
