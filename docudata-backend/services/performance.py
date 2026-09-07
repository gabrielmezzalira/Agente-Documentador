"""Cálculo de ranking do Motor de Score (Phase 19).

Agrega a sequência pessoal de cada operacional em 3 janelas por contagem de
sprints (nunca calendário), com agregação em duas camadas por dimensão: por
projeto primeiro, depois média simples entre projetos — mesmo método de
services/pontuacao.py::calcular_spi_operacional. Uma pessoa pode ter mais de
uma linha `operacionais` (uma por projeto) — agrupadas aqui por e-mail.
"""

JANELAS = {"sprint": 1, "quinzenal": 2, "mensal": 4}

# Bônus de task extra: cada ponto entregue além do que a pessoa tinha vale 1
# ponto de score, até o teto. O teto é o que impede o bônus de virar a alavanca
# principal do ranking.
BONUS_EXTRA_POR_PONTO = 1.0
BONUS_EXTRA_TETO = 5.0


def listar_pessoas_ativas(client) -> list[dict]:
    """Agrupa operacionais ativos por e-mail — uma pessoa pode ter uma linha
    `operacionais` por projeto. Sem e-mail, cada linha vira sua própria pessoa
    (não dá pra casar identidade cross-projeto sem um identificador comum)."""
    rows = client.table("operacionais").select("id, nome, email, ativo").eq("ativo", True).execute().data or []
    por_chave: dict[str, dict] = {}
    for row in rows:
        chave = row.get("email") or row["id"]
        pessoa = por_chave.setdefault(chave, {"email": chave, "nome": row["nome"], "operacional_ids": []})
        pessoa["operacional_ids"].append(row["id"])
    return list(por_chave.values())


def _sequencia_pessoal(client, operacional_ids: list[str]) -> list[dict]:
    if not operacional_ids:
        return []
    return (
        client.table("pontuacao_operacional_sprint")
        .select("*")
        .in_("operacional_id", operacional_ids)
        .gt("entrega_pontos_alocados", 0)
        .order("sprint_fim", desc=True)
        .execute()
        .data or []
    )


def calcular_ranking_pessoa(client, pessoa: dict, pesos_por_arquetipo: dict[str, dict]) -> dict:
    """Calcula o score das 3 janelas pra uma pessoa. `pesos_por_arquetipo` é
    pré-carregado ({arquetipo: row de pesos_arquetipo}) — evita reconsultar
    a tabela pra cada pessoa do ranking."""
    sequencia = _sequencia_pessoal(client, pessoa["operacional_ids"])
    resultado: dict[str, dict | None] = {}
    for nome_janela, tamanho in JANELAS.items():
        linhas = sequencia[:tamanho]
        if not linhas:
            resultado[nome_janela] = None
            continue
        resultado[nome_janela] = _calcular_janela(client, linhas, tamanho, pesos_por_arquetipo)
    return resultado


def _calcular_janela(client, linhas: list[dict], tamanho_esperado: int, pesos_por_arquetipo: dict) -> dict:
    projeto_ids = list({l["projeto_id"] for l in linhas})
    arquetipos = _arquetipos_dos_projetos(client, projeto_ids)
    arquetipo_usado = _arquetipo_dominante(linhas, arquetipos)
    pesos = pesos_por_arquetipo.get(arquetipo_usado) or pesos_por_arquetipo["padrao"]

    por_projeto: dict[str, list[dict]] = {}
    for linha in linhas:
        por_projeto.setdefault(linha["projeto_id"], []).append(linha)

    sub_scores = {
        "entrega": _media_cross_projeto(por_projeto, _entrega_por_projeto),
        "gerente": _media_cross_projeto(por_projeto, _gerente_por_projeto),
        "evolucao": _media_cross_projeto(por_projeto, _evolucao_por_projeto),
        "autonomia": _media_cross_projeto(
            por_projeto,
            lambda ls: _autonomia_por_projeto(ls, float(pesos.get("peso_pergunta3_autonomia") or 0.5)),
        ),
        "qualidade": _media_cross_projeto(
            por_projeto,
            lambda ls: _qualidade_por_projeto(ls, float(pesos.get("peso_commit_qualidade") or 0.5)),
        ),
    }

    base = _score_final(sub_scores, pesos)
    bonus = _bonus_extra(linhas)
    score_final = None if base is None else round(min(base + bonus, 100.0), 2)

    return {
        **sub_scores,
        "score_final": score_final,
        "bonus_extra": bonus,
        "janela_parcial": len(linhas) < tamanho_esperado,
        "arquetipo_usado": arquetipo_usado,
    }


def _bonus_extra(linhas: list[dict]) -> float:
    """Task extra é a que o operacional pediu depois de fechar tudo que tinha.
    Ela não entra em Entrega (não consumiu orçamento da sprint, e entrar no
    denominador puniria quem pediu mais trabalho): vira um bônus somado ao score
    final, com teto, para que o ranking não vire "quem pediu mais task"."""
    pontos = sum(l.get("bonus_pontos_extra") or 0 for l in linhas)
    return float(min(pontos * BONUS_EXTRA_POR_PONTO, BONUS_EXTRA_TETO))


def _media_cross_projeto(por_projeto: dict[str, list[dict]], calc_por_projeto) -> float | None:
    valores = [v for v in (calc_por_projeto(linhas) for linhas in por_projeto.values()) if v is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 2)


def _entrega_por_projeto(linhas: list[dict]) -> float | None:
    """Entrega desconta os pontos penalizados por travamento automático: uma task
    que ficou parada muito além do tempo esperado não conta como entrega cheia
    (decisão do Líder, 2026-09-07). O gerente pode dispensar o travamento no
    alerta da task, e aí ele não penaliza."""
    concluidos = sum(l["entrega_pontos_concluidos"] for l in linhas)
    penalizados = sum(l.get("entrega_pontos_penalizados") or 0 for l in linhas)
    alocados = sum(l["entrega_pontos_alocados"] for l in linhas)
    if alocados <= 0:
        return None
    efetivos = max(concluidos - penalizados, 0)
    return round(min(efetivos / alocados * 100, 100), 2)


def _gerente_por_projeto(linhas: list[dict]) -> float | None:
    valores = [l["gerente_media"] for l in linhas if l.get("gerente_media") is not None]
    if not valores:
        return None
    return round(min(sum(valores) / len(valores) * 20, 100), 2)


def _evolucao_por_projeto(linhas: list[dict]) -> float | None:
    valores = [l["gerente_pergunta6"] for l in linhas if l.get("gerente_pergunta6") is not None]
    if not valores:
        return None
    return round(min(sum(valores) / len(valores) * 20, 100), 2)


def _autonomia_por_projeto(linhas: list[dict], peso_pergunta3: float) -> float | None:
    """Combina dois sinais: os bloqueios que a pessoa resolveu sozinha e a leitura
    do gerente na pergunta 3 ("destravou sozinha antes de te escalar?").

    O sinal de bloqueio só existe quando alguém marca bloqueio, o que na prática
    é raro. Sem ele, Autonomia era sempre 100 e virava peso morto; por isso a
    pergunta 3 entra como segunda fonte e sustenta a dimensão sozinha quando não
    houve bloqueio nenhum (decisão do Líder, 2026-09-07)."""
    resolvidos = sum(l["autonomia_bloqueios_resolvidos_proprio"] for l in linhas)
    totais = sum(l["autonomia_bloqueios_totais"] for l in linhas)
    bloqueio_score = round(resolvidos / totais * 100, 2) if totais > 0 else None

    notas3 = [l["gerente_pergunta3"] for l in linhas if l.get("gerente_pergunta3") is not None]
    pergunta3_score = round(min(sum(notas3) / len(notas3) * 20, 100), 2) if notas3 else None

    if bloqueio_score is None and pergunta3_score is None:
        return None
    if bloqueio_score is None:
        return pergunta3_score
    if pergunta3_score is None:
        return bloqueio_score
    return round(peso_pergunta3 * pergunta3_score + (1 - peso_pergunta3) * bloqueio_score, 2)


def _qualidade_por_projeto(linhas: list[dict], peso_commit: float) -> float | None:
    """Sem nenhuma task concluída e sem nota de commit, a dimensão fica
    indisponível em vez de 100. Dar 100 a quem não entregou nada era premiar a
    ausência de entrega (decisão do Líder, 2026-09-07)."""
    reaberturas = sum(l["qualidade_reaberturas"] for l in linhas)
    tasks_concluidas = sum(l["qualidade_tasks_concluidas"] for l in linhas)
    retrabalho = None if tasks_concluidas <= 0 else round(max(1 - reaberturas / tasks_concluidas, 0) * 100, 2)

    notas_commit = [l["qualidade_commit_media"] for l in linhas if l.get("qualidade_commit_media") is not None]
    commit_score = min(sum(notas_commit) / len(notas_commit) * 10, 100) if notas_commit else None

    if retrabalho is None and commit_score is None:
        return None
    if commit_score is None:
        return retrabalho
    if retrabalho is None:
        return round(commit_score, 2)
    return round(peso_commit * commit_score + (1 - peso_commit) * retrabalho, 2)


def _arquetipos_dos_projetos(client, projeto_ids: list[str]) -> dict[str, str]:
    rows = client.table("projects").select("id, arquetipo").in_("id", projeto_ids).execute().data or []
    return {r["id"]: r.get("arquetipo") or "padrao" for r in rows}


def _arquetipo_dominante(linhas: list[dict], arquetipos: dict[str, str]) -> str:
    contagem: dict[str, int] = {}
    mais_recente: dict[str, str] = {}
    for linha in linhas:
        pid = linha["projeto_id"]
        contagem[pid] = contagem.get(pid, 0) + 1
        if pid not in mais_recente or linha["sprint_fim"] > mais_recente[pid]:
            mais_recente[pid] = linha["sprint_fim"]
    maior = max(contagem.values())
    empatados = [pid for pid, c in contagem.items() if c == maior]
    vencedor = max(empatados, key=lambda pid: mais_recente[pid])
    return arquetipos.get(vencedor, "padrao")


def _score_final(sub_scores: dict[str, float | None], pesos: dict) -> float | None:
    mapa_peso = {
        "entrega": float(pesos["peso_entrega"]),
        "gerente": float(pesos["peso_gerente"]),
        "qualidade": float(pesos["peso_qualidade"]),
        "autonomia": float(pesos["peso_autonomia"]),
        "evolucao": float(pesos["peso_evolucao"]),
    }
    disponiveis = {k: v for k, v in sub_scores.items() if v is not None}
    if not disponiveis:
        return None
    peso_disponivel = sum(mapa_peso[k] for k in disponiveis)
    if peso_disponivel <= 0:
        return None
    soma_ponderada = sum(mapa_peso[k] * v for k, v in disponiveis.items())
    return round(soma_ponderada / peso_disponivel, 2)
