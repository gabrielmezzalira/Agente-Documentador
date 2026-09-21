"""Contagem de elegibilidade e avaliação semanal por sprint (Entrega 1 —
extra do usuário: contador "N/M" no card da sprint).

Reusa a MESMA derivação de hoje (operacional com task na sprint) usada por
routers/avaliacoes.py::_operacionais_com_task_na_sprint — não a elegibilidade
temporal nova da Entrega 2 (entrada/saída no projeto). Trocar a derivação
aqui mudaria quem "conta como pendente" em projetos ATRIBUICAO hoje, o que
violaria a promessa de zero mudança de comportamento desta entrega. Ver
docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md §3."""


def contar_avaliacao_por_sprint(client, sprint_ids: list[str]) -> dict[str, dict]:
    """Para cada sprint_id, quantos operacionais têm task nela (elegíveis) e
    quantos desses já têm avaliacoes_gerente registrada (avaliados). Uma
    consulta batelada — evita N chamadas quando o chamador lista várias
    sprints de uma vez (GET /projects/{id}/sprints)."""
    if not sprint_ids:
        return {}

    tasks_resp = (
        client.table("tasks").select("sprint_id, operacional_id").in_("sprint_id", sprint_ids).execute()
    )
    elegiveis_por_sprint: dict[str, set[str]] = {sid: set() for sid in sprint_ids}
    for row in (tasks_resp.data or []):
        sid = row.get("sprint_id")
        op = row.get("operacional_id")
        if sid in elegiveis_por_sprint and op:
            elegiveis_por_sprint[sid].add(op)

    aval_resp = (
        client.table("avaliacoes_gerente").select("sprint_id, operacional_id").in_("sprint_id", sprint_ids).execute()
    )
    avaliados_por_sprint: dict[str, set[str]] = {sid: set() for sid in sprint_ids}
    for row in (aval_resp.data or []):
        sid = row.get("sprint_id")
        op = row.get("operacional_id")
        if sid in avaliados_por_sprint and op:
            avaliados_por_sprint[sid].add(op)

    return {
        sid: {
            "elegiveis": len(elegiveis_por_sprint[sid]),
            # Só conta quem ainda é elegível — evita avaliados > elegiveis se
            # um dado antigo ficou órfão (avaliação de alguém que não tem
            # mais task na sprint).
            "avaliados": len(avaliados_por_sprint[sid] & elegiveis_por_sprint[sid]),
        }
        for sid in sprint_ids
    }
