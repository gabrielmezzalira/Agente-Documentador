"""Redação de segredos e limites do conteúdo de Discovery (Spec 12 §2 e §6; AGENTS.md §5.3).

Roda ANTES de gravar e ANTES de qualquer texto ir ao modelo. Puro: sem I/O.
"""
import re
from typing import Any

TRANSCRICAO_MAX_BYTES = 2 * 1024 * 1024
TRECHO_MAX_CHARS = 600

_REDIGIDO = "[REDIGIDO]"

_PADROES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), _REDIGIDO),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), _REDIGIDO),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), _REDIGIDO),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"), _REDIGIDO),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), _REDIGIDO),
    (re.compile(r"(?i)\b(senha|password|passwd|pwd|token|secret|api[_\- ]?key)\b\s*[:=]\s*\S+"),
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
    """Aplica `redigir_segredos` em todas as strings de dict/list (o resto passa igual)."""
    if isinstance(valor, str):
        return redigir_segredos(valor)[0]
    if isinstance(valor, dict):
        return {k: redigir_estrutura(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [redigir_estrutura(v) for v in valor]
    return valor


def limitar_trecho(trecho: str, max_chars: int = TRECHO_MAX_CHARS) -> str:
    return trecho if len(trecho) <= max_chars else trecho[:max_chars] + "…"
