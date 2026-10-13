"""Saneamento puro de valores vindos do modelo (não confiável) antes de chegarem ao store."""
import math
from typing import Any

from graphs.requisitos_graph import SPEAKER_MAX_CHARS, TITULO_MAX_CHARS

_CONFIANCA_PADRAO = 0.5


def confianca_segura(valor: Any) -> float:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return _CONFIANCA_PADRAO
    return _CONFIANCA_PADRAO if math.isnan(v) else min(1.0, max(0.0, v))


def speaker_limitado(valor: str | None) -> str | None:
    return valor[:SPEAKER_MAX_CHARS] if valor else None


def candidatos_duplicata(conhecidos: list[dict]) -> list[dict]:
    """Só linhas com título não vazio, com título limitado (o difflib é quadrático)."""
    return [
        {"id": r["id"], "titulo": r["titulo"][:TITULO_MAX_CHARS]}
        for r in conhecidos if isinstance(r.get("titulo"), str) and r["titulo"].strip()
    ]
