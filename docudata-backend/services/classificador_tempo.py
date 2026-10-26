"""Tempo limpo de uma task concluída (spec A2 §4.1): do primeiro Em Andamento
até a última conclusão, sem a espera em pendente_aprovacao, sem o tempo
parado em concluida antes de uma reabertura e sem bloqueio de cliente."""
from datetime import datetime, timezone

_PAUSAS_DE_COLUNA = {"pendente_aprovacao", "concluida"}


def _ts(valor: str) -> datetime:
    d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _uniao(intervalos: list[tuple[datetime, datetime]]) -> float:
    total, fim_atual, ini_atual = 0.0, None, None
    for ini, fim in sorted(intervalos):
        if fim_atual is None or ini > fim_atual:
            if fim_atual is not None:
                total += (fim_atual - ini_atual).total_seconds()
            ini_atual, fim_atual = ini, fim
        else:
            fim_atual = max(fim_atual, fim)
    if fim_atual is not None:
        total += (fim_atual - ini_atual).total_seconds()
    return total


def tempo_limpo(transicoes: list[dict], task: dict) -> dict | None:
    trans = sorted(transicoes, key=lambda t: _ts(t["timestamp"]))
    colunas = [t for t in trans if t.get("campo") == "coluna_kanban"]
    conclusoes = [t for t in colunas if t.get("para") == "concluida"]
    if not conclusoes:
        return None
    fim = _ts(conclusoes[-1]["timestamp"])

    inicios = [t for t in colunas if t.get("para") == "em_andamento"]
    if inicios:
        inicio = _ts(inicios[0]["timestamp"])
    elif task.get("pull_em"):
        inicio = _ts(task["pull_em"])
    elif task.get("entrou_em_andamento_em"):
        inicio = _ts(task["entrou_em_andamento_em"])
    else:
        return None
    if fim <= inicio:
        return None

    pausas: list[tuple[datetime, datetime]] = []
    for i, t in enumerate(colunas):
        if t.get("para") in _PAUSAS_DE_COLUNA:
            prox = colunas[i + 1] if i + 1 < len(colunas) else None
            ini_p = _ts(t["timestamp"])
            fim_p = _ts(prox["timestamp"]) if prox else fim
            pausas.append((max(ini_p, inicio), min(fim_p, fim)))

    aberto: datetime | None = None
    for t in trans:
        if t.get("campo") != "bloqueado":
            continue
        para = str(t.get("para")).lower()
        if para == "true" and t.get("bloqueio_tipo") == "cliente":
            aberto = _ts(t["timestamp"])
        elif para == "false" and aberto is not None:
            pausas.append((max(aberto, inicio), min(_ts(t["timestamp"]), fim)))
            aberto = None
    if aberto is not None:
        pausas.append((max(aberto, inicio), fim))

    pausas = [(a, b) for a, b in pausas if b > a]
    bruto = (fim - inicio).total_seconds()
    limpo = max(0.0, bruto - _uniao(pausas))
    return {
        "tempo_bruto_s": int(bruto),
        "tempo_limpo_s": int(limpo),
        "reaberta": any(t.get("de") == "concluida" for t in colunas),
        "concluida_em": conclusoes[-1]["timestamp"],
    }
