"""Redação de segredos e limites do conteúdo de Discovery (Spec 12 §2 e §6; AGENTS.md §5.3).

Roda ANTES de gravar e ANTES de qualquer texto ir ao modelo. Puro: sem I/O.
"""
import re
from typing import Any

TRANSCRICAO_MAX_BYTES = 2 * 1024 * 1024
TRECHO_MAX_CHARS = 600

_REDIGIDO = "[REDIGIDO]"

_PADROES: list[tuple[re.Pattern[str], str]] = [
    # Corpo limitado (anti-ReDoS); BEGIN sem END redige até o fim do texto (mais seguro).
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.{0,8000}?-----END [A-Z ]*PRIVATE KEY-----|.*)", re.S),
     _REDIGIDO),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), _REDIGIDO),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), _REDIGIDO),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"), _REDIGIDO),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), _REDIGIDO),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/\-]{8,}=*"), "Bearer " + _REDIGIDO),
    (re.compile(r"(?<=://)([^\s:/@]+):[^\s@/]+@"), r"\1:" + _REDIGIDO + "@"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), _REDIGIDO),
    (re.compile(r"\bxox[abpr]-[A-Za-z0-9\-]{10,}"), _REDIGIDO),
    # Aceita nomes compostos (access_token, AWS_SECRET_ACCESS_KEY, client_secret...).
    (re.compile(r"(?i)(?<!\w)(\w*(?:senha|password|passwd|pwd|token|secret|api[_\- ]?key)\w*)\s*[:=]\s*\S+"),
     r"\1: " + _REDIGIDO),
]


def redigir_segredos(texto: str) -> tuple[str, bool]:
    """Devolve o texto sem segredos conhecidos e se algo foi redigido."""
    redigiu = False
    for padrao, troca in _PADROES:
        texto, n = padrao.subn(troca, texto)
        redigiu = redigiu or n > 0
    return texto, redigiu


def redigir_estrutura(valor: Any) -> Any:
    """Aplica `redigir_segredos` em todas as strings de dict/list (o resto passa igual).

    Não muta a entrada. Chaves de dict, tuplas e sets não são redigidos.
    """
    if isinstance(valor, str):
        return redigir_segredos(valor)[0]
    if isinstance(valor, dict):
        return {k: redigir_estrutura(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [redigir_estrutura(v) for v in valor]
    return valor


def limitar_trecho(trecho: str, max_chars: int = TRECHO_MAX_CHARS) -> str:
    """Corta em max_chars e acrescenta "…" (o resultado pode ter max_chars+1)."""
    return trecho if len(trecho) <= max_chars else trecho[:max_chars] + "…"
