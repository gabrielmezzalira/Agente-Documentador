"""Documentos internos servidos pelo app.

O conteúdo é markdown versionado em `docudata-backend/docs/` — fonte única, sem
cópia no bundle do frontend e sem arquivo estático servido fora do gate de RBAC.

Nem todo documento tem a mesma audiência, então o gate é por documento e não pelo
router inteiro: o guia do sistema e a versão pública da metodologia são para
todos, e a metodologia completa (pesos, fórmulas, notas cruas) é camada oculta,
restrita a Gerente para cima.
"""
import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from models.schemas import MetodologiaResponse, MetodologiaItem
from services.auth import get_current_pessoa

router = APIRouter(prefix="/metodologia", tags=["metodologia"])

_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

_DOCUMENTOS: dict[str, dict] = {
    "biblia": {
        "titulo": "Bíblia do DocuData",
        "resumo": "Tudo o que existe no sistema, em detalhe: tasks, classificador, planning, métricas e documentação.",
        "arquivo": "biblia-do-docudata.md",
        "restrito": True,
    },
    "guia": {
        "titulo": "Guia do DocuData",
        "resumo": "Como o sistema funciona, tela por tela.",
        "arquivo": "guia-do-sistema.md",
        "restrito": False,
    },
    "acompanhamento": {
        "titulo": "Como sua contribuição é acompanhada",
        "resumo": "Para operacionais: o que conta, o que não conta e como funciona o reconhecimento.",
        "arquivo": "acompanhamento-publico.md",
        "restrito": False,
    },
    "performance": {
        "titulo": "Sistema de Acompanhamento de Performance",
        "resumo": "Metodologia completa: pesos, fórmulas e manual do gerente.",
        "arquivo": "metodologia-performance.md",
        "restrito": True,
    },
}


def _visiveis(pessoa: dict) -> dict[str, dict]:
    ehOperacional = pessoa["cargo"] == "operacional"
    return {slug: doc for slug, doc in _DOCUMENTOS.items() if not (doc["restrito"] and ehOperacional)}


@router.get("", response_model=list[MetodologiaItem])
async def listar_documentos(pessoa: dict = Depends(get_current_pessoa)):
    """Só lista o que a pessoa pode abrir, para não anunciar a existência de um
    documento restrito a quem não vai conseguir ler."""
    return [
        {"slug": slug, "titulo": doc["titulo"], "resumo": doc["resumo"]}
        for slug, doc in _visiveis(pessoa).items()
    ]


@router.get("/export")
async def exportar_documentos(pessoa: dict = Depends(get_current_pessoa)):
    """Um .zip com o markdown de todos os documentos que a pessoa pode abrir. Usa o
    mesmo filtro da listagem, então o restrito nunca sai no pacote do operacional.
    Declarada antes de `/{slug}` para não ser capturada como slug."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in _visiveis(pessoa).values():
            try:
                conteudo = (_DOCS_DIR / doc["arquivo"]).read_text(encoding="utf-8")
            except OSError:
                raise HTTPException(status_code=500, detail=f"Arquivo ausente: {doc['arquivo']}")
            zf.writestr(doc["arquivo"], conteudo)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="documentos-docudata.zip"'},
    )


@router.get("/{slug}", response_model=MetodologiaResponse)
async def get_metodologia(slug: str, pessoa: dict = Depends(get_current_pessoa)):
    doc = _DOCUMENTOS.get(slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if doc["restrito"] and pessoa["cargo"] == "operacional":
        raise HTTPException(status_code=403, detail="Acesso restrito a Gerente e Líder")

    caminho = _DOCS_DIR / doc["arquivo"]
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail=f"Arquivo ausente: {doc['arquivo']}")

    return {"titulo": doc["titulo"], "conteudo": conteudo, "restrito": doc["restrito"]}
