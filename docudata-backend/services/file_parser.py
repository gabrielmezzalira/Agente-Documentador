import base64
import io

# Dimensão máxima de qualquer lado da imagem antes de enviar ao Gemini.
# 1024px preserva legibilidade de texto em kanban/whiteboard.
# Acima disso, cada 256px extra custa +258 tokens sem ganho real de extração.
_MAX_IMAGE_DIM = 1024


def parse_docx(file_bytes: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def parse_pdf(file_bytes: bytes) -> dict:
    """Returns {"text": str, "is_scanned": bool, "b64": Optional[str]}."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages_text = [page.extract_text() or "" for page in pdf.pages]

    all_text = "\n".join(pages_text)

    if len(all_text.strip()) < 100:
        b64 = _pdf_page_to_base64(file_bytes)
        return {"text": "", "is_scanned": True, "b64": b64}

    return {"text": all_text, "is_scanned": False, "b64": None}


def _pdf_page_to_base64(file_bytes: bytes) -> str:
    from pdf2image import convert_from_bytes

    # 100 DPI: A4 fica ~827×1170px → 20 tiles → 5.160 tokens
    # vs 200 DPI padrão: ~1654×2339px → 72 tiles → 18.576 tokens
    images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=100)
    if not images:
        return ""
    return _pil_to_base64(_resize_pil(images[0]))


def parse_image(file_bytes: bytes) -> str:
    """Resize to _MAX_IMAGE_DIM on longest side, normalize to PNG, return base64."""
    from PIL import Image

    img = Image.open(io.BytesIO(file_bytes))
    return _pil_to_base64(_resize_pil(img))


def _resize_pil(img):
    from PIL import Image

    # Converte para RGB antes de redimensionar (evita erros com RGBA/P em JPEG)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) <= _MAX_IMAGE_DIM:
        return img

    scale = _MAX_IMAGE_DIM / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    print(f"[file_parser] Resizing image {w}×{h} → {new_w}×{new_h} ({_tiles(w,h)} → {_tiles(new_w,new_h)} tiles)")
    return img.resize((new_w, new_h), Image.LANCZOS)


def _pil_to_base64(img) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _tiles(w: int, h: int) -> int:
    import math
    return math.ceil(w / 256) * math.ceil(h / 256)
