"""Recálculo do aprendizado do classificador de nível (spec A2 §4). Puro: sem banco, sem numpy."""
from __future__ import annotations

from services.classificador_regua import (
    FATOR_ALERTA,
    IDX,
    K_ENCOLHIMENTO,
    MARGEM_OPINIAO_OPERACIONAL,
    NIVEL_DO_IDX,
    SINAIS,
    TETO_OPINIAO_GERENTE,
)

MIN_EXEMPLOS_PESOS = 12


def pesos_iniciais() -> dict[str, float]:
    return {s: 0.25 for s in SINAIS}


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores)


def _encolher(soma: float, n: int, alvo: float) -> float:
    return (soma + K_ENCOLHIMENTO * alvo) / (n + K_ENCOLHIMENTO)


def _mais_proximo(tn: float, medias: dict[int, float]) -> int:
    # Empate: degrau menor.
    return min(medias, key=lambda d: (abs(medias[d] - tn), d))


def _peso_opiniao(acertos: int, n: int) -> float:
    return acertos / (n + K_ENCOLHIMENTO)


def nnls(xs: list[list[float]], ys: list[float], iteracoes: int = 2000) -> list[float]:
    """Mínimos quadrados não negativos por gradiente projetado."""
    if not xs:
        return []
    p = len(xs[0])
    lr = 1.0 / (sum(v * v for linha in xs for v in linha) + 1.0)
    w = [0.0] * p
    for _ in range(iteracoes):
        residuos = [sum(linha[j] * w[j] for j in range(p)) - y for linha, y in zip(xs, ys)]
        for j in range(p):
            grad = sum(linha[j] * r for linha, r in zip(xs, residuos))
            w[j] = max(0.0, w[j] - lr * grad)
    return w


def recalcular(exemplos: list[dict]) -> dict:
    ordenados = sorted(exemplos, key=lambda e: e["concluida_em"])
    medias: dict[int, list[float]] = {}
    vistos: set[int] = set()
    ritmo_obs: dict[str, list[float]] = {}
    # Opiniões do operacional já vistas (exemplos anteriores): pessoa -> [acertos, n].
    op_hist: dict[str, list[int]] = {}
    rotulos: dict[str, dict] = {}
    reais: list[tuple[dict, int, int]] = []  # (exemplo, degrau real, degrau pelo tempo)

    for e in ordenados:
        pessoa = e.get("operacional_id")
        razoes = ritmo_obs.get(pessoa, []) if pessoa else []
        ritmo = _encolher(sum(razoes), len(razoes), 1.0) if razoes else 1.0
        tempo = e.get("tempo_limpo_s")
        if tempo is None or tempo <= 0:
            # Sem tempo utilizável: só rotula (nível sugerido); não alimenta nenhum parâmetro.
            nivel = e["nivel_sugerido"]
            rotulos[e["task_id"]] = {
                "ritmo_usado": ritmo,
                "tempo_normalizado_s": 0.0,
                "nivel_pelo_tempo": nivel,
                "nivel_real": nivel,
                "alerta": False,
            }
            continue
        tn = tempo / ritmo
        m = {d: _media(v) for d, v in medias.items() if v}
        sug = IDX[e["nivel_sugerido"]]
        atual = _mais_proximo(tn, m) if sug in m else sug
        pelo_tempo = atual

        real = atual
        op = e.get("opiniao_operacional")
        if op is not None and pessoa and m:
            op_d = IDX[op]
            acertos, n_op = op_hist.get(pessoa, [0, 0])
            if op_d != atual and _peso_opiniao(acertos, n_op) > 0 and atual in m:
                viz = atual + (1 if op_d > atual else -1)
                if viz in m:
                    fronteira = (m[atual] + m[viz]) / 2
                    if abs(tn - fronteira) <= MARGEM_OPINIAO_OPERACIONAL * abs(m[viz] - m[atual]):
                        real = viz

        alerta = real in m and tn > FATOR_ALERTA * m[real]
        rotulos[e["task_id"]] = {
            "ritmo_usado": ritmo,
            "tempo_normalizado_s": tn,
            "nivel_pelo_tempo": NIVEL_DO_IDX[pelo_tempo],
            "nivel_real": NIVEL_DO_IDX[real],
            "alerta": alerta,
        }
        reais.append((e, real, pelo_tempo))
        vistos.add(real)

        if op is not None and pessoa and not e.get("excluida"):
            h = op_hist.setdefault(pessoa, [0, 0])
            h[1] += 1
            h[0] += int(IDX[op] == pelo_tempo)  # acerto contra o tempo, nunca contra o próprio ajuste

        if not e.get("excluida"):
            medias.setdefault(real, []).append(tn)
            if pessoa:
                m_pos = _media(medias[real])
                ritmo_obs.setdefault(pessoa, []).append(e["tempo_limpo_s"] / m_pos)

    parametros: dict[tuple[str, str], tuple[float, int]] = {}
    for d in sorted(vistos):
        v = medias.get(d, [])
        parametros[("media_nivel", str(NIVEL_DO_IDX[d]))] = (_media(v) if v else 0.0, len(v))

    for pessoa, razoes in ritmo_obs.items():
        parametros[("ritmo_pessoa", pessoa)] = (_encolher(sum(razoes), len(razoes), 1.0), len(razoes))

    nao_excluidos = [(e, d, pt) for e, d, pt in reais if not e.get("excluida")]

    vies: dict[str, list[int]] = {}
    for e, d, _ in nao_excluidos:
        if e.get("gerente_id"):
            vies.setdefault(e["gerente_id"], []).append(d - IDX[e["nivel_sugerido"]])
    for g, difs in vies.items():
        parametros[("vies_gerente", g)] = (sum(difs) / (len(difs) + K_ENCOLHIMENTO), len(difs))

    ger: dict[str, list[int]] = {}
    for e, _, pt in nao_excluidos:
        og = e.get("opiniao_gerente")
        if og is not None and e.get("gerente_id"):
            h = ger.setdefault(e["gerente_id"], [0, 0])
            h[1] += 1
            h[0] += int(IDX[og] == pt)
    for g, (acertos, n) in ger.items():
        parametros[("peso_opiniao_gerente", g)] = (min(TETO_OPINIAO_GERENTE, _peso_opiniao(acertos, n)), n)

    ops: dict[str, list[int]] = {}
    for e, _, pt in nao_excluidos:
        op = e.get("opiniao_operacional")
        if op is not None and e.get("operacional_id"):
            h = ops.setdefault(e["operacional_id"], [0, 0])
            h[1] += 1
            h[0] += int(IDX[op] == pt)
    for p, (acertos, n) in ops.items():
        parametros[("peso_opiniao_operacional", p)] = (_peso_opiniao(acertos, n), n)

    com_sinais = [(e["sinais"], d) for e, d, _ in nao_excluidos if e.get("sinais")]
    if len(com_sinais) < MIN_EXEMPLOS_PESOS:
        pesos = pesos_iniciais()
    else:
        w = nnls([[float(s.get(k, 0)) for k in SINAIS] for s, _ in com_sinais], [float(d) for _, d in com_sinais])
        pesos = dict(zip(SINAIS, w))
    for s in SINAIS:
        parametros[("peso_sinal", s)] = (pesos[s], len(com_sinais))

    return {"rotulos": rotulos, "parametros": parametros}


def metricas_acuracia(pares: list[tuple[int, int]]) -> dict:
    n = len(pares)
    matriz: dict[int, dict[int, int]] = {}
    for sug, real in pares:
        linha = matriz.setdefault(sug, {})
        linha[real] = linha.get(real, 0) + 1
    por_nivel: dict[int, dict] = {}
    for nivel in NIVEL_DO_IDX:
        sugeridos = sum(1 for s, _ in pares if s == nivel)
        reais = sum(1 for _, r in pares if r == nivel)
        acertos = matriz.get(nivel, {}).get(nivel, 0)
        por_nivel[nivel] = {
            "precisao": acertos / sugeridos if sugeridos else None,
            "cobertura": acertos / reais if reais else None,
        }
    difs = [abs(IDX[s] - IDX[r]) for s, r in pares]
    return {
        "n": n,
        "exata": sum(1 for d in difs if d == 0) / n if n else 0.0,
        "mais_menos_um": sum(1 for d in difs if d <= 1) / n if n else 0.0,
        "erro_medio_degraus": sum(difs) / n if n else 0.0,
        "matriz": matriz,
        "por_nivel": por_nivel,
    }
