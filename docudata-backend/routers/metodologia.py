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
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from models.schemas import MetodologiaResponse, MetodologiaItem
from services.auth import get_current_pessoa
from services.doc_pdf import markdown_para_pdf

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


def _ler(doc: dict) -> str:
    try:
        return (_DOCS_DIR / doc["arquivo"]).read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail=f"Arquivo ausente: {doc['arquivo']}")


def _acessivel(slug: str, pessoa: dict) -> dict:
    doc = _DOCUMENTOS.get(slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if doc["restrito"] and pessoa["cargo"] == "operacional":
        raise HTTPException(status_code=403, detail="Acesso restrito a Gerente e Líder")
    return doc


@lru_cache(maxsize=16)
def _pdf_em_cache(arquivo: str, titulo: str, modificado_em: float) -> bytes:
    # A data de modificação entra na chave: editar o .md invalida o PDF guardado.
    return markdown_para_pdf(titulo, (_DOCS_DIR / arquivo).read_text(encoding="utf-8"))


def _pdf(doc: dict) -> bytes:
    _ler(doc)  # 500 legível se o arquivo sumiu, em vez de erro do cache
    return _pdf_em_cache(doc["arquivo"], doc["titulo"], (_DOCS_DIR / doc["arquivo"]).stat().st_mtime)


def _nome_pdf(doc: dict) -> str:
    return doc["arquivo"].removesuffix(".md") + ".pdf"


# Rotas de PDF são `def` (não `async`): gerar o PDF é CPU e não pode travar o loop.
@router.get("/export")
def exportar_documentos(pessoa: dict = Depends(get_current_pessoa)):
    """Um .zip com o PDF de todos os documentos que a pessoa pode abrir. Usa o
    mesmo filtro da listagem, então o restrito nunca sai no pacote do operacional.
    Declarada antes de `/{slug}` para não ser capturada como slug."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in _visiveis(pessoa).values():
            zf.writestr(_nome_pdf(doc), _pdf(doc))
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="documentos-docudata.zip"'},
    )


@router.get("/{slug}/pdf")
def baixar_pdf(slug: str, pessoa: dict = Depends(get_current_pessoa)):
    doc = _acessivel(slug, pessoa)
    return Response(
        content=_pdf(doc),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_nome_pdf(doc)}"'},
    )


@router.get("/{slug}", response_model=MetodologiaResponse)
async def get_metodologia(slug: str, pessoa: dict = Depends(get_current_pessoa)):
    doc = _acessivel(slug, pessoa)
    return {"titulo": doc["titulo"], "conteudo": _ler(doc), "restrito": doc["restrito"]}
