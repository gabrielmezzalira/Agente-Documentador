"""Agregação de métricas por modo de trabalho/avaliação (Entrega 2). Usa
SEMPRE o modo congelado por sprint (sprints.modo_trabalho/modo_avaliacao),
nunca o modo ATUAL do projeto — um projeto pode já ter trocado de modo, e o
valor atual não representaria o histórico de sprints antigas. Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §3."""


def _agrupar_sprints_por_modo(sprints: list[dict]) -> dict[tuple[str, str], list[dict]]:
    grupos: dict[tuple[str, str], list[dict]] = {}
    for s in sprints:
        modo_trabalho = s.get("modo_trabalho")
        modo_avaliacao = s.get("modo_avaliacao")
        if not modo_trabalho or not modo_avaliacao:
            continue  # sprint ainda não fechada, sem modo congelado
        grupos.setdefault((modo_trabalho, modo_avaliacao), []).append(s)
    return grupos


def _metricas_do_grupo(client, sprints_do_grupo: list[dict]) -> dict:
    sprint_ids = [s["id"] for s in sprints_do_grupo]
    sprint_ids_set = set(sprint_ids)

    tasks_raw = (
        client.table("tasks")
        .select("sprint_id, pontos, coluna_kanban")
        .in_("sprint_id", sprint_ids)
        .execute()
        .data or []
    )
    # Filtra em Python por segurança: o backend real filtra via .in_() no
    # servidor, mas mocks de teste (e possíveis implementações futuras do
    # cliente) podem devolver linhas de fora do grupo.
    tasks = [t for t in tasks_raw if t.get("sprint_id") in sprint_ids_set]
    pontos_realizados_total = sum(t["pontos"] for t in tasks if t.get("coluna_kanban") == "concluida")
    pontos_previstos_total = sum(s.get("pontos_orcamento") or 0 for s in sprints_do_grupo) or None
    spi_medio = (
        round(pontos_realizados_total / pontos_previstos_total, 3)
        if pontos_previstos_total else None
    )

    pont_rows_raw = (
        client.table("pontuacao_operacional_sprint")
        .select("sprint_id, entrega_pontos_concluidos, entrega_pontos_alocados")
        .in_("sprint_id", sprint_ids)
        .execute()
        .data or []
    )
    pont_rows = [r for r in pont_rows_raw if r.get("sprint_id") in sprint_ids_set]
    alocados_total = sum(r.get("entrega_pontos_alocados") or 0 for r in pont_rows)
    concluidos_travados_total = sum(r.get("entrega_pontos_concluidos") or 0 for r in pont_rows)
    entrega_media = round(concluidos_travados_total / alocados_total, 3) if alocados_total else None

    return {
        "sprints_count": len(sprints_do_grupo),
        "pontos_previstos_total": pontos_previstos_total,
        "pontos_realizados_total": pontos_realizados_total,
        "spi_medio": spi_medio,
        "entrega_media": entrega_media,
    }


def _comparar(client, sprints: list[dict]) -> list[dict]:
    grupos = _agrupar_sprints_por_modo(sprints)
    resultado = []
    for (modo_trabalho, modo_avaliacao), sprints_do_grupo in grupos.items():
        resultado.append({
            "modo_trabalho": modo_trabalho,
            "modo_avaliacao": modo_avaliacao,
            **_metricas_do_grupo(client, sprints_do_grupo),
        })
    return resultado


def comparar_modos_do_projeto(client, project_id: str) -> list[dict]:
    sprints = (
        client.table("sprints")
        .select("id, project_id, numero, modo_trabalho, modo_avaliacao, pontos_orcamento")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    return _comparar(client, sprints)


def comparar_modos_entre_projetos(client, project_ids: list[str]) -> list[dict]:
    """Mesma agregação de comparar_modos_do_projeto, mas junta as sprints de
    TODOS os projetos informados num único grupo por modo — cada projeto
    pode contribuir sprints pra mais de um grupo se já trocou de modo."""
    sprints = (
        client.table("sprints")
        .select("id, project_id, numero, modo_trabalho, modo_avaliacao, pontos_orcamento")
        .in_("project_id", project_ids)
        .execute()
        .data or []
    )
    return _comparar(client, sprints)
