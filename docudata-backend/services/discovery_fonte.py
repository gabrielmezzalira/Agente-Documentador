"""Fonte de texto de uma reunião e sua divisão em janelas de análise (Spec 12 §3). Funções puras."""
import json

from graphs.requisitos_graph import FONTE_MAX_CHARS

MAX_JANELAS = 4
_FRACAO_MINIMA_JANELA = 0.5  # só corta em quebra de linha se ela estiver na segunda metade da janela


def texto_da_reuniao(reuniao: dict, transcricao: str | None) -> str:
    """Conteúdo estruturado ANTES da transcrição (o estruturado fica na primeira janela)."""
    estruturado = json.dumps(reuniao.get("conteudo_estruturado") or {}, ensure_ascii=False)
    return f"{estruturado}\n\n{transcricao}" if transcricao else estruturado


def fonte_da_reuniao(reuniao: dict, transcricao: str | None) -> str:
    """Primeira janela da fonte (compatibilidade)."""
    return texto_da_reuniao(reuniao, transcricao)[:FONTE_MAX_CHARS]


def janelas_da_fonte(reuniao: dict, transcricao: str | None) -> tuple[list[str], bool]:
    """(janelas, truncada): até MAX_JANELAS janelas sequenciais de até FONTE_MAX_CHARS, cortadas em
    fronteira de linha quando possível. `truncada` é True se sobrou texto sem analisar."""
    texto = texto_da_reuniao(reuniao, transcricao)
    janelas, inicio = [], 0
    while inicio < len(texto) and len(janelas) < MAX_JANELAS:
        fim = min(inicio + FONTE_MAX_CHARS, len(texto))
        if fim < len(texto):
            quebra = texto.rfind("\n", inicio, fim)
            if quebra > inicio + FONTE_MAX_CHARS * _FRACAO_MINIMA_JANELA:
                fim = quebra + 1
        janelas.append(texto[inicio:fim])
        inicio = fim
    return janelas, inicio < len(texto)
