"""Foto de perfil das pessoas (aparece ao lado do nome em squads, avaliações, performance...).

Fica no Supabase Storage (bucket privado, criado na primeira vez), um arquivo por pessoa em
`{chave}.webp`. A chave vem do nome (sem acento, minúsculo, hífens): o mesmo nome em projetos
diferentes usa a mesma foto, sem precisar de coluna nem migração. A foto é recortada em quadrado
e reduzida, então o arquivo é sempre pequeno e no mesmo formato.
"""
import io
import re
import unicodedata

from services.task_anexos import MAX_BYTES, validar_imagem

BUCKET = "fotos-perfil"
LADO = 256
LADO_COMPLETA = 1024
CHAVE_VALIDA = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")

_bucket_garantido = False


def chave_do_nome(nome: str | None) -> str:
    base = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:80]


def chave_valida(chave: str) -> bool:
    return bool(CHAVE_VALIDA.match(chave or ""))


def preparar(dados: bytes) -> bytes:
    """Valida o arquivo, recorta em quadrado e devolve WEBP de LADO x LADO."""
    validar_imagem(dados)
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(dados)) as img:
        img.seek(0)  # GIF animado: primeiro quadro
        img = ImageOps.exif_transpose(img).convert("RGBA")
        img = ImageOps.fit(img, (LADO, LADO), Image.LANCZOS)
        saida = io.BytesIO()
        img.save(saida, "WEBP", quality=85)
    return saida.getvalue()


def preparar_completa(dados: bytes) -> bytes:
    """Versão para ampliar ao clicar na foto: sem recorte, só reduzida (maior lado = LADO_COMPLETA)."""
    validar_imagem(dados)
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(dados)) as img:
        img.seek(0)
        img = ImageOps.exif_transpose(img).convert("RGBA")
        img.thumbnail((LADO_COMPLETA, LADO_COMPLETA), Image.LANCZOS)
        saida = io.BytesIO()
        img.save(saida, "WEBP", quality=88)
    return saida.getvalue()


def garantir_bucket(client) -> None:
    global _bucket_garantido
    if _bucket_garantido:
        return
    try:
        if BUCKET not in {b.name for b in client.storage.list_buckets()}:
            client.storage.create_bucket(
                BUCKET, options={"public": False, "file_size_limit": MAX_BYTES, "allowed_mime_types": ["image/webp"]},
            )
    except Exception as exc:
        if "exist" not in str(exc).lower():
            raise
    _bucket_garantido = True


def versoes(client) -> dict[str, str]:
    """{chave: marca de atualização}; a marca muda quando a foto é trocada e invalida o cache do navegador."""
    garantir_bucket(client)
    itens = client.storage.from_(BUCKET).list("", {"limit": 1000}) or []
    saida = {}
    for it in itens:
        nome = it.get("name") or ""
        if nome.endswith(".webp") and chave_valida(nome[:-5]):
            saida[nome[:-5]] = it.get("updated_at") or it.get("created_at") or "1"
    return saida


def salvar(client, chave: str, dados: bytes) -> None:
    garantir_bucket(client)
    opcoes = {"content-type": "image/webp", "upsert": "true", "cache-control": "3600"}
    miniatura = preparar(dados)
    completa = preparar_completa(dados)
    # A completa vai numa subpasta para não aparecer como "pessoa" em versoes().
    client.storage.from_(BUCKET).upload(f"completa/{chave}.webp", completa, opcoes)
    client.storage.from_(BUCKET).upload(f"{chave}.webp", miniatura, opcoes)


def baixar(client, chave: str, completa: bool = False) -> bytes:
    garantir_bucket(client)
    if completa:
        try:
            return client.storage.from_(BUCKET).download(f"completa/{chave}.webp")
        except Exception:
            pass  # foto antiga, anterior à versão ampliável: cai na miniatura
    return client.storage.from_(BUCKET).download(f"{chave}.webp")


def remover(client, chave: str) -> None:
    client.storage.from_(BUCKET).remove([f"{chave}.webp", f"completa/{chave}.webp"])
