"""Converte os documentos internos (markdown de `docs/`) em PDF.

Só cobre o subconjunto de markdown que esses documentos usam: títulos até ####,
parágrafos, listas (com aninhamento por indentação), tabelas, citações, linha
horizontal e ênfase inline. Usa só as fontes padrão do PDF (Helvetica), que não
exigem arquivo de fonte no deploy; por isso os poucos símbolos fora do Windows-1252
são trocados por texto antes de renderizar.
"""
import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_VERDE = colors.HexColor("#16a34a")
_TEXTO = colors.HexColor("#1f2933")
_SUAVE = colors.HexColor("#6b7280")
_LINHA = colors.HexColor("#e5e7eb")
_FUNDO = colors.HexColor("#f3f4f6")

_SUBSTITUICOES = {"✅": "Sim", "❌": "Não", "−": "-", "≥": ">=", "≤": "<=", "→": "->"}

_LARGURA_UTIL = A4[0] - 4 * cm


def _estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    corpo = ParagraphStyle("corpo", parent=base, fontName="Helvetica", fontSize=10, leading=14.5,
                           textColor=_TEXTO, spaceAfter=6, alignment=TA_LEFT)
    return {
        "corpo": corpo,
        "h1": ParagraphStyle("h1", parent=corpo, fontName="Helvetica-Bold", fontSize=22, leading=27, spaceAfter=10, keepWithNext=1),
        "h2": ParagraphStyle("h2", parent=corpo, fontName="Helvetica-Bold", fontSize=15, leading=19,
                             spaceBefore=16, spaceAfter=8, textColor=colors.black, keepWithNext=1),
        "h3": ParagraphStyle("h3", parent=corpo, fontName="Helvetica-Bold", fontSize=12, leading=16,
                             spaceBefore=10, spaceAfter=5, textColor=colors.black, keepWithNext=1),
        "h4": ParagraphStyle("h4", parent=corpo, fontName="Helvetica-Bold", fontSize=10.5, leading=14,
                             spaceBefore=8, spaceAfter=4, keepWithNext=1),
        "item": ParagraphStyle("item", parent=corpo, spaceAfter=3),
        "citacao": ParagraphStyle("citacao", parent=corpo, textColor=colors.HexColor("#14532d"), spaceAfter=0),
        "celula": ParagraphStyle("celula", parent=corpo, fontSize=8.5, leading=11, spaceAfter=0),
        "cabecalho": ParagraphStyle("cabecalho", parent=corpo, fontName="Helvetica-Bold", fontSize=8.5,
                                    leading=11, spaceAfter=0, textColor=colors.black),
    }


def _inline(texto: str) -> str:
    """Markdown inline -> marcação de Paragraph do reportlab."""
    for simbolo, troca in _SUBSTITUICOES.items():
        texto = texto.replace(simbolo, troca)
    texto = escape(texto)
    texto = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", texto)
    # Âncora interna não tem para onde ir no PDF; link externo vira link clicável.
    texto = re.sub(r"\[([^\]]+)\]\(#[^)]*\)", r"\1", texto)
    texto = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#16a34a">\1</link>', texto)
    return texto


def _celulas(linha: str) -> list[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def _tabela(linhas: list[str], estilos: dict) -> Table:
    linhas = [l for l in linhas if not re.fullmatch(r"\|?[\s:|-]+\|?", l.strip())]
    dados = [_celulas(l) for l in linhas]
    ncol = max(len(r) for r in dados)
    dados = [r + [""] * (ncol - len(r)) for r in dados]

    # Largura proporcional ao texto mais longo de cada coluna, com piso para a
    # coluna estreita não quebrar letra a letra.
    pesos = [max(min(len(r[i]), 60) for r in dados) + 4 for i in range(ncol)]
    larguras = [_LARGURA_UTIL * p / sum(pesos) for p in pesos]

    corpo = [
        [Paragraph(_inline(c), estilos["cabecalho" if i == 0 else "celula"]) for c in r]
        for i, r in enumerate(dados)
    ]
    tabela = Table(corpo, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _FUNDO),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, _LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabela


def _citacao(partes: list[str], estilos: dict) -> Table:
    """`partes` são as linhas da citação já sem o `>`; linha vazia separa parágrafos."""
    paragrafos, atual = [], []
    for p in partes + [""]:
        if p:
            atual.append(p)
        elif atual:
            paragrafos.append(_inline(" ".join(atual)))
            atual = []
    texto = "<br/><br/>".join(paragrafos)
    caixa = Table([[Paragraph(texto, estilos["citacao"])]], colWidths=[_LARGURA_UTIL], hAlign="LEFT")
    caixa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, _VERDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return caixa


_ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def _flowables(conteudo: str, estilos: dict) -> list:
    saida: list = []
    paragrafo: list[str] = []
    linhas = conteudo.splitlines()
    i = 0

    def fechar_paragrafo():
        if paragrafo:
            saida.append(Paragraph(_inline(" ".join(paragrafo)), estilos["corpo"]))
            paragrafo.clear()

    while i < len(linhas):
        linha = linhas[i]
        limpa = linha.strip()

        if not limpa:
            fechar_paragrafo()
            i += 1
            continue

        titulo = re.match(r"^(#{1,4})\s+(.*)$", limpa)
        if titulo:
            fechar_paragrafo()
            nivel = len(titulo.group(1))
            saida.append(Paragraph(_inline(titulo.group(2)), estilos[f"h{nivel}"]))
            if nivel == 2:
                fio = HRFlowable(width="100%", thickness=0.6, color=_VERDE, spaceBefore=0, spaceAfter=8)
                fio.keepWithNext = 1  # título + fio não ficam sozinhos no pé da página
                saida.append(fio)
            i += 1
            continue

        if re.fullmatch(r"-{3,}|\*{3,}", limpa):
            fechar_paragrafo()
            saida.append(HRFlowable(width="100%", thickness=0.5, color=_LINHA, spaceBefore=6, spaceAfter=10))
            i += 1
            continue

        if limpa.startswith("|"):
            fechar_paragrafo()
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            saida.append(_tabela(bloco, estilos))
            saida.append(Spacer(1, 8))
            continue

        if limpa.startswith(">"):
            fechar_paragrafo()
            partes: list[str] = []
            while i < len(linhas) and linhas[i].strip().startswith(">"):
                partes.append(re.sub(r"^>\s?", "", linhas[i].strip()))
                i += 1
            saida.append(_citacao(partes, estilos))
            saida.append(Spacer(1, 8))
            continue

        item = _ITEM.match(linha)
        if item:
            fechar_paragrafo()
            nivel = len(item.group(1).expandtabs(2)) // 2
            marcador = "•" if item.group(2) in "-*" else item.group(2)
            texto = [item.group(3)]
            i += 1
            # Linhas seguintes indentadas que não abrem outro item continuam este.
            while i < len(linhas) and linhas[i].strip() and linhas[i].startswith(" ") \
                    and not _ITEM.match(linhas[i]):
                texto.append(linhas[i].strip())
                i += 1
            recuo = 14 + nivel * 14
            estilo = ParagraphStyle(f"item{nivel}", parent=estilos["item"], leftIndent=recuo, bulletIndent=recuo - 11)
            saida.append(Paragraph(_inline(" ".join(texto)), estilo, bulletText=marcador))
            continue

        paragrafo.append(limpa)
        i += 1

    fechar_paragrafo()
    return saida


def markdown_para_pdf(titulo: str, conteudo: str) -> bytes:
    estilos = _estilos()
    buffer = io.BytesIO()

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_SUAVE)
        canvas.drawString(2 * cm, 1.2 * cm, f"DocuData · {titulo}"[:110])
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=titulo, author="DocuData · CITi",
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    doc.build(_flowables(conteudo, estilos), onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()
