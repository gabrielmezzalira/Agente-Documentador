"""Documentos de metodologia interna servidos pelo app.

O conteúdo é markdown versionado em `docudata-backend/docs/` — fonte única, sem
cópia no bundle do frontend e sem arquivo estático servido fora do gate de RBAC.
O router inteiro roda atrás de `require_not_operacional` (registrado em main.py):
a metodologia de performance é camada oculta, restrita a Líder e Gerente.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.schemas import MetodologiaResponse

router = APIRouter(prefix="/metodologia", tags=["metodologia"])

_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

_DOCUMENTOS = {
    "performance": ("Sistema de Acompanhamento de Performance", "metodologia-performance.md"),
}


@router.get("/{slug}", response_model=MetodologiaResponse)
async def get_metodologia(slug: str):
    doc = _DOCUMENTOS.get(slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    titulo, nome_arquivo = doc
    caminho = _DOCS_DIR / nome_arquivo
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail=f"Arquivo de metodologia ausente: {nome_arquivo}")

    return {"titulo": titulo, "conteudo": conteudo}
