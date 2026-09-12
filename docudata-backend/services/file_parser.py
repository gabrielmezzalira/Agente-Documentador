import base64
import io
import logging
import os
import warnings

_LOG = logging.getLogger("docudata.file_parser")

# Dimensão máxima de qualquer lado da imagem antes de enviar ao Gemini.
# 1024px preserva legibilidade de texto em kanban/whiteboard.
# Acima disso, cada 256px extra custa +258 tokens sem ganho real de extração.
_MAX_IMAGE_DIM = 1024

# Formatos que a interface declara aceitar. MPO entra porque é o container que
# o Pillow reporta para parte das fotos de celular — o arquivo continua sendo
# um JPEG válido e sempre foi aceito.
_FORMATOS_ACEITOS = {"PNG", "JPEG", "JPG", "MPO", "WEBP"}


class ArquivoInvalido(ValueError):
    """Arquivo corrompido, truncado ou em formato não suportado."""


class ArquivoExcedeLimite(ValueError):
    """Imagem acima do teto de pixels aceito para processamento."""


class ProcessamentoDemorouDemais(RuntimeError):
    """Poppler não terminou de rasterizar o PDF dentro do tempo configurado."""


def _inteiro_positivo(nome: str, padrao: str) -> int:
    try:
        valor = int(os.environ.get(nome, padrao))
    except ValueError as exc:
        raise RuntimeError(f"{nome} deve ser um inteiro positivo") from exc
    if valor < 1:
        raise RuntimeError(f"{nome} deve ser um inteiro positivo")
    return valor


def max_image_pixels() -> int:
    """Teto de pixels (largura × altura) aceito antes de qualquer conversão.

    40 MP cobre com folga print de monitor 8K e digitalização A4 em 600 DPI;
    acima disso o custo de memória do decode é maior que qualquer ganho de
    extração e vira vetor de decompression bomb.
    """
    return _inteiro_positivo("MAX_IMAGE_PIXELS", "40000000")


def poppler_timeout_seconds() -> int:
    """Tempo máximo do Poppler ao rasterizar a primeira página de um PDF."""
    return _inteiro_positivo("PDF_POPPLER_TIMEOUT_SECONDS", "30")


def parse_docx(file_bytes: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def parse_pdf(file_bytes: bytes) -> dict:
    """Returns {"text": str, "is_scanned": bool, "b64": Optional[str]}."""
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
    except ArquivoInvalido:
        raise
    except Exception as exc:
        raise ArquivoInvalido("PDF inválido ou corrompido") from exc

    all_text = "\n".join(pages_text)

    if len(all_text.strip()) == 0:
        b64 = _pdf_page_to_base64(file_bytes)
        return {"text": "", "is_scanned": True, "b64": b64}

    return {"text": all_text, "is_scanned": False, "b64": None}


def _pdf_page_to_base64(file_bytes: bytes) -> str:
    from pdf2image import convert_from_bytes
    from pdf2image.exceptions import PDFPopplerTimeoutError

    # 100 DPI: A4 fica ~827×1170px → 20 tiles → 5.160 tokens
    # vs 200 DPI padrão: ~1654×2339px → 72 tiles → 18.576 tokens
    timeout = poppler_timeout_seconds()
    try:
        images = convert_from_bytes(
            file_bytes,
            first_page=1,
            last_page=1,
            dpi=100,
            timeout=timeout,
        )
    except PDFPopplerTimeoutError as exc:
        # Sem timeout o processo do Poppler podia ficar preso segurando o
        # worker do uvicorn até o cliente desistir.
        _LOG.warning("poppler_timeout segundos=%s", timeout)
        raise ProcessamentoDemorouDemais(
            "O PDF demorou demais para ser processado"
        ) from exc
    except Exception as exc:
        _LOG.warning("poppler_falhou exc=%s", type(exc).__name__)
        raise ArquivoInvalido("Não foi possível converter o PDF em imagem") from exc

    if not images:
        return ""
    return _pil_to_base64(_resize_pil(images[0]))


def parse_image(file_bytes: bytes) -> str:
    """Valida, redimensiona para _MAX_IMAGE_DIM e devolve PNG em base64."""
    from PIL import Image

    limite_pixels = max_image_pixels()

    with warnings.catch_warnings():
        # DecompressionBombWarning é só aviso por padrão: o processamento
        # seguia normalmente com a imagem gigante já decodificada.
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            # verify() detecta arquivo truncado/corrompido sem decodificar tudo,
            # mas invalida o objeto — daí a segunda abertura para converter.
            with Image.open(io.BytesIO(file_bytes)) as sonda:
                formato = (sonda.format or "").upper()
                largura, altura = sonda.size
                sonda.verify()
            _validar_formato(formato)
            _validar_pixels(largura, altura, limite_pixels)

            with Image.open(io.BytesIO(file_bytes)) as img:
                img.load()
                return _pil_to_base64(_resize_pil(img))
        except (ArquivoInvalido, ArquivoExcedeLimite):
            raise
        except Image.DecompressionBombWarning as exc:
            raise ArquivoExcedeLimite(_MENSAGEM_PIXELS) from exc
        except Image.DecompressionBombError as exc:
            raise ArquivoExcedeLimite(_MENSAGEM_PIXELS) from exc
        except Exception as exc:
            _LOG.warning("imagem_invalida exc=%s", type(exc).__name__)
            raise ArquivoInvalido("Imagem inválida ou corrompida") from exc


_MENSAGEM_PIXELS = "Imagem grande demais para processamento"


def _validar_formato(formato: str) -> None:
    if formato not in _FORMATOS_ACEITOS:
        raise ArquivoInvalido(
            "Formato de imagem não suportado. Use PNG, JPEG ou WEBP."
        )


def _validar_pixels(largura: int, altura: int, limite: int) -> None:
    if largura * altura > limite:
        _LOG.warning("imagem_acima_do_teto pixels=%s limite=%s", largura * altura, limite)
        raise ArquivoExcedeLimite(_MENSAGEM_PIXELS)


def _resize_pil(img):
    from PIL import Image

    w, h = img.size
    _validar_pixels(w, h, max_image_pixels())

    # Converte para RGB antes de redimensionar (evita erros com RGBA/P em JPEG)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    if max(w, h) <= _MAX_IMAGE_DIM:
        return img

    scale = _MAX_IMAGE_DIM / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    _LOG.info(
        "redimensionando_imagem de=%sx%s para=%sx%s tiles=%s->%s",
        w, h, new_w, new_h, _tiles(w, h), _tiles(new_w, new_h),
    )
    return img.resize((new_w, new_h), Image.LANCZOS)


def _pil_to_base64(img) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _tiles(w: int, h: int) -> int:
    import math
    return math.ceil(w / 256) * math.ceil(h / 256)
