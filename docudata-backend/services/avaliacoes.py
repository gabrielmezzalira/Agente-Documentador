"""Contagem de elegibilidade e avaliação semanal por sprint (Entrega 1 —
extra do usuário: contador "N/M" no card da sprint).

Entrega 2: elegibilidade passa a ser vínculo temporal com o projeto
(services.elegibilidade.listar_vinculados_no_projeto), não mais "tem task na
sprint" — corrige o bug de PULL onde quem não puxava nada nunca contava.
Ver docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4.

Nuance aceita: este contador usa "vinculado agora" (momento da consulta),
não o momento exato do fechamento de cada sprint individualmente — é um
contador de exibição (chip N/M), não a fonte de verdade. A fonte de
verdade real (o que efetivamente vira linha em pontuacao_operacional_sprint)
usa o momento exato do fechamento, em services/pontuacao.py."""
from datetime import datetime, timezone

from services.elegibilidade import listar_vinculados_no_projeto


def contar_avaliacao_por_sprint(client, project_id: str, sprint_ids: list[str]) -> dict[str, dict]:
    """Para cada sprint_id, quantos operacionais estão vinculados ao projeto
    (elegíveis) e quantos desses já têm avaliacoes_gerente registrada
    (avaliados). Uma consulta batelada — evita N chamadas quando o chamador
    lista várias sprints de uma vez (GET /projects/{id}/sprints)."""
    if not sprint_ids:
        return {}

    momento = datetime.now(timezone.utc).isoformat()
    vinculados = listar_vinculados_no_projeto(client, project_id, momento)
    elegiveis_ids = {op["id"] for op in vinculados}

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
            "elegiveis": len(elegiveis_ids),
            # Só conta quem ainda é elegível — evita avaliados > elegiveis se
            # um dado antigo ficou órfão (avaliação de alguém que saiu do
            # projeto depois de ter sido avaliado).
            "avaliados": len(avaliados_por_sprint[sid] & elegiveis_ids),
        }
        for sid in sprint_ids
    }
