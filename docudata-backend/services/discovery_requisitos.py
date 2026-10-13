"""Regras puras dos requisitos de Discovery (Spec 12 §4): transições, cargos, código e duplicata.

Sem I/O: o acesso ao banco mora em `discovery_store.py`; a autorização por projeto, na rota.
"""
import re
import unicodedata
from difflib import SequenceMatcher

from services.auth import nivel


class RegraRequisitoErro(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# (de, para) -> cargo mínimo e se o motivo é obrigatório
_TRANSICOES: dict[tuple[str, str], tuple[str, bool]] = {
    ("proposto", "em_revisao"): ("operacional", False),
    ("em_revisao", "validado"): ("gerente", False),
    ("proposto", "rejeitado"): ("gerente", True),
    ("em_revisao", "rejeitado"): ("gerente", True),
    ("validado", "rejeitado"): ("gerente", True),
    ("rejeitado", "proposto"): ("gerente", True),
}


def validar_transicao(de: str, para: str, cargo: str, motivo: str | None) -> None:
    if de == para:
        raise RegraRequisitoErro(409, "O requisito já está nesse status")
    regra = _TRANSICOES.get((de, para))
    if regra is None:
        raise RegraRequisitoErro(409, f"Transição não permitida: {de} -> {para}")
    cargo_minimo, exige_motivo = regra
    if nivel(cargo) < nivel(cargo_minimo):
        raise RegraRequisitoErro(403, f"Acesso restrito a {cargo_minimo}")
    if exige_motivo and not (motivo and motivo.strip()):
        raise RegraRequisitoErro(422, "Informe o motivo")


def pode_editar(status: str, cargo: str) -> bool:
    """Operacional edita só antes de validar; gerente+ edita sempre."""
    if nivel(cargo) >= nivel("gerente"):
        return True
    return status in ("proposto", "em_revisao")


_CODIGO = re.compile(r"^RQ-(\d+)$")


def proximo_codigo(existentes: list[str]) -> str:
    numeros = [int(m.group(1)) for c in existentes if (m := _CODIGO.match(c))]
    return f"RQ-{(max(numeros) + 1 if numeros else 1):03d}"


def normalizar_titulo(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    so_palavras = re.sub(r"[^a-z0-9]+", " ", sem_acento.lower())
    return so_palavras.strip()


def achar_duplicata(titulo: str, existentes: list[dict], limiar: float = 0.82) -> dict | None:
    """O existente mais parecido, se passar do limiar; senão None. Nunca funde: só sinaliza."""
    alvo = normalizar_titulo(titulo)
    melhor, melhor_nota = None, 0.0
    for item in existentes:
        nota = SequenceMatcher(None, alvo, normalizar_titulo(item["titulo"])).ratio()
        if nota > melhor_nota:
            melhor, melhor_nota = item, nota
    return melhor if melhor_nota >= limiar else None
