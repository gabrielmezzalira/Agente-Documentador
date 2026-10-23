# docudata-backend/services/classificador_regua.py
"""Régua v1 do classificador do nível da task (spec A2 §1).

Os critérios e sinais mudam só por revisão versionada deste arquivo (rito
mensal). Cada classificação guarda VERSAO_REGUA."""
import re
import unicodedata

from services.regua import NIVEIS

VERSAO_REGUA = "v1"

K_ENCOLHIMENTO = 10
TETO_OPINIAO_GERENTE = 0.15
FATOR_ALERTA = 3.0
MARGEM_OPINIAO_OPERACIONAL = 0.25
K_PARECIDAS = 8
TIMEOUT_CLASSIFICACAO_S = 20
NIVEL_PROVISORIO_PADRAO = 2

IDX: dict[int, int] = {n: i for i, n in enumerate(NIVEIS)}
NIVEL_DO_IDX: tuple[int, ...] = tuple(NIVEIS)

CRITERIOS_NIVEL: dict[int, str] = {
    1: "Mudança pontual em uma parte do sistema, caminho já conhecido, sem incerteza.",
    2: "Mexe em mais de uma parte seguindo um padrão que já existe, com pouca incerteza.",
    3: "Várias partes integradas ou regra de negócio não trivial, com alguma incerteza técnica.",
    5: "Incerteza alta: exige investigação, decisão de arquitetura ou tecnologia nova para o time.",
}

SINAIS: tuple[str, ...] = ("partes", "novidade", "incerteza", "dependencia", "tamanho", "risco")

DESCRICAO_SINAIS: dict[str, dict[int, str]] = {
    "partes": {0: "uma parte do sistema", 1: "duas partes", 2: "três ou mais partes"},
    "novidade": {0: "repete um padrão que o projeto já tem", 1: "adapta um padrão existente", 2: "o projeto nunca fez"},
    "incerteza": {0: "o que fazer está claro", 1: "há pontos a decidir", 2: "precisa investigar antes"},
    "dependencia": {0: "nenhuma dependência", 1: "depende de outra parte interna", 2: "depende de terceiro ou do cliente"},
    "tamanho": {0: "1 a 2 itens ou entregáveis", 1: "3 a 5 itens", 2: "6 ou mais itens"},
    "risco": {0: "nada sensível", 1: "regra de negócio importante", 2: "dados de produção, migração, segurança ou pagamento"},
}

_EVIDENCIA_MIN_CHARS = 8

_PADROES_INSTRUCAO = [
    r"\bignore\b.*\binstru", r"\bclassifique\b", r"\bclassifica(r)?\b.*\bcomo\b.*\bn[ií]vel\b",
    r"\bvoc[eê] (é|e) um\b", r"\bresponda\b.*\bn[ií]vel\b", r"\bdesconsidere\b", r"\bprompt\b",
]


def _normalizar(texto: str) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", sem_acento.lower())).strip()


def para_nivel(degrau: float) -> int:
    i = int(max(0, min(3, round(degrau + 1e-9))))
    return NIVEL_DO_IDX[i]


def texto_da_task(titulo: str, descricao: str | None, checklist: list[dict] | None) -> str:
    partes = [titulo.strip()]
    if descricao and descricao.strip():
        partes.append(descricao.strip())
    itens = [str(i.get("texto", "")).strip() for i in (checklist or []) if str(i.get("texto", "")).strip()]
    if itens:
        partes.append("\n".join(f"- {t}" for t in itens))
    return "\n\n".join(partes)


def texto_suficiente(descricao: str | None, checklist: list[dict] | None) -> bool:
    if descricao and descricao.strip():
        return True
    itens = [i for i in (checklist or []) if str(i.get("texto", "")).strip()]
    return len(itens) >= 2


def evidencia_valida(trecho: str, texto: str) -> bool:
    alvo = _normalizar(trecho or "")
    return len(alvo) >= _EVIDENCIA_MIN_CHARS and f" {alvo} " in f" {_normalizar(texto)} "


def parece_instrucao(texto: str) -> bool:
    t = texto.lower()
    return any(re.search(p, t) for p in _PADROES_INSTRUCAO)
