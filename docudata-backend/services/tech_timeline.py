"""Constrói timeline de tecnologias a partir das ingestões de um projeto.

Diferente de `generation_graph._detect_changes` (que produz transições par-a-par
para alimentar o prompt do LLM), este módulo produz uma view orientada a
*tecnologia*: para cada tech que apareceu em alguma ingestão, em qual sprint
foi introduzida e em qual deixou de aparecer.
"""


def build_tech_timeline(ingestions: list) -> dict:
    """Devolve `{em_uso_atual, timeline}` a partir de uma lista de ingestões.

    Args:
        ingestions: lista de dicts no formato retornado pela tabela `ingestions`.
            Cada item deve ter `sprint_number` e (opcionalmente)
            `extracted_content.tecnologias`.

    Returns:
        {
            "em_uso_atual": [str, ...],     # techs presentes na sprint mais recente
            "timeline": [
                {
                    "tecnologia": str,
                    "introduzida_em": int,
                    "abandonada_em": int | None,   # None = ainda em uso
                },
                ...
            ]
        }

    Sprint "mais recente" = `max(sprint_number)` entre ingestões. Comparação de
    techs é case-insensitive, mas o casing original (primeira ocorrência) é
    preservado na saída.
    """
    sprints = sorted(
        {ing.get("sprint_number") for ing in ingestions if ing.get("sprint_number") is not None}
    )
    if not sprints:
        return {"em_uso_atual": [], "timeline": []}

    by_sprint: dict[int, set[str]] = {s: set() for s in sprints}
    case_map: dict[str, str] = {}  # lower → original casing (primeira ocorrência)

    for ing in ingestions:
        sn = ing.get("sprint_number")
        if sn is None:
            continue
        techs = (ing.get("extracted_content") or {}).get("tecnologias") or []
        for t in techs:
            if not isinstance(t, str) or not t.strip():
                continue
            key = t.strip().lower()
            by_sprint[sn].add(key)
            if key not in case_map:
                case_map[key] = t.strip()

    latest = sprints[-1]
    em_uso_atual = sorted(case_map[t] for t in by_sprint[latest])

    all_techs = set().union(*by_sprint.values())
    timeline = []
    for tech_key in all_techs:
        present_in = [s for s in sprints if tech_key in by_sprint[s]]
        introduzida_em = present_in[0]
        last_seen = present_in[-1]
        # abandonada = primeira sprint após last_seen, ou None se ainda na mais recente
        abandonada_em = None
        if last_seen < latest:
            abandonada_em = next(s for s in sprints if s > last_seen)
        timeline.append({
            "tecnologia": case_map[tech_key],
            "introduzida_em": introduzida_em,
            "abandonada_em": abandonada_em,
        })

    # Ordena cronologicamente por introdução, com desempate alfabético
    timeline.sort(key=lambda x: (x["introduzida_em"], x["tecnologia"].lower()))

    return {"em_uso_atual": em_uso_atual, "timeline": timeline}
