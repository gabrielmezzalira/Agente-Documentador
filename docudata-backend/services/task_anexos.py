"""Imagens anexadas a uma task pelo gerente, para o operacional ver.

Ficam no Supabase Storage (bucket privado, criado na primeira vez), em
`{project_id}/{task_id}/{arquivo}`. Não há tabela: o nome do arquivo guarda o
identificador e um resumo do nome original, e a listagem vem do próprio storage.
O download passa pelo backend, que confere o acesso ao projeto.
"""
import io
import logging
import re
import unicodedata
from uuid import uuid4

logger = logging.getLogger(__name__)

BUCKET = "task-anexos"
MAX_BYTES = 4 * 1024 * 1024  # abaixo dos 4,5 MB que o proxy do Vercel aceita no corpo da requisição
MAX_POR_TASK = 12

# formato detectado pelo Pillow -> (mime, extensão). SVG fica de fora de propósito (pode carregar script).
FORMATOS = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
    "GIF": ("image/gif", "gif"),
}
MIME_POR_EXTENSAO = {ext: mime for mime, ext in FORMATOS.values()}
NOME_VALIDO = re.compile(r"^[a-z0-9][a-z0-9-]{0,90}\.(png|jpg|webp|gif)$")

_bucket_garantido = False


class AnexoInvalido(ValueError):
    """Arquivo recusado. `mensagem` é um texto fixo, escrito aqui, e pode ir direto ao gerente."""

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


def nome_valido(nome: str) -> bool:
    return bool(NOME_VALIDO.match(nome or ""))


def mime_do_nome(nome: str) -> str:
    return MIME_POR_EXTENSAO[nome.rsplit(".", 1)[1]]


def validar_imagem(dados: bytes) -> tuple[str, str]:
    """(mime, extensão) a partir do conteúdo, não do tipo que o navegador declarou."""
    if not dados:
        raise AnexoInvalido("O arquivo está vazio.")
    if len(dados) > MAX_BYTES:
        raise AnexoInvalido(f"A imagem passa de {MAX_BYTES // (1024 * 1024)} MB.")
    from PIL import Image

    try:
        with Image.open(io.BytesIO(dados)) as img:
            img.verify()
            formato = img.format
    except Exception:
        raise AnexoInvalido("O arquivo não é uma imagem válida.")
    if formato not in FORMATOS:
        raise AnexoInvalido("Use uma imagem PNG, JPG, WEBP ou GIF.")
    return FORMATOS[formato]


def _resumo_do_nome(original: str | None) -> str:
    base = (original or "imagem").rsplit(".", 1)[0]
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:40]
    return base or "imagem"


def novo_nome(original: str | None, extensao: str) -> str:
    return f"{uuid4().hex[:12]}-{_resumo_do_nome(original)}.{extensao}"


def _pasta(project_id: str, task_id: str) -> str:
    return f"{project_id}/{task_id}"


def garantir_bucket(client) -> None:
    global _bucket_garantido
    if _bucket_garantido:
        return
    try:
        if BUCKET not in {b.name for b in client.storage.list_buckets()}:
            client.storage.create_bucket(
                BUCKET,
                options={"public": False, "file_size_limit": MAX_BYTES,
                         "allowed_mime_types": [m for m, _ in FORMATOS.values()]},
            )
    except Exception as exc:
        # duas instâncias subindo juntas: quem perdeu a corrida recebe "já existe"
        if "exist" not in str(exc).lower():
            raise
    _bucket_garantido = True


def listar(client, project_id: str, task_id: str) -> list[dict]:
    garantir_bucket(client)
    itens = client.storage.from_(BUCKET).list(_pasta(project_id, task_id)) or []
    saida = []
    for it in itens:
        nome = it.get("name") or ""
        if not nome_valido(nome):
            continue
        meta = it.get("metadata") or {}
        saida.append({"nome": nome, "tamanho": meta.get("size"), "criado_em": it.get("created_at")})
    return sorted(saida, key=lambda a: (a["criado_em"] or "", a["nome"]))


def salvar(client, project_id: str, task_id: str, dados: bytes, original: str | None) -> dict:
    mime, extensao = validar_imagem(dados)
    if len(listar(client, project_id, task_id)) >= MAX_POR_TASK:
        raise AnexoInvalido(f"Cada task aceita até {MAX_POR_TASK} imagens.")
    nome = novo_nome(original, extensao)
    client.storage.from_(BUCKET).upload(
        f"{_pasta(project_id, task_id)}/{nome}", dados, {"content-type": mime, "cache-control": "3600"},
    )
    return {"nome": nome, "tamanho": len(dados), "criado_em": None}


def baixar(client, project_id: str, task_id: str, nome: str) -> bytes:
    garantir_bucket(client)
    return client.storage.from_(BUCKET).download(f"{_pasta(project_id, task_id)}/{nome}")


def remover(client, project_id: str, task_id: str, nome: str) -> None:
    client.storage.from_(BUCKET).remove([f"{_pasta(project_id, task_id)}/{nome}"])


def remover_todos(client, project_id: str, task_id: str) -> None:
    """Best-effort ao excluir a task: sobra arquivo solto, nunca erro para o usuário."""
    try:
        nomes = [a["nome"] for a in listar(client, project_id, task_id)]
        if nomes:
            client.storage.from_(BUCKET).remove([f"{_pasta(project_id, task_id)}/{n}" for n in nomes])
    except Exception as exc:
        logger.warning("anexos_remocao_falhou task=%s exc=%s", task_id, type(exc).__name__)
