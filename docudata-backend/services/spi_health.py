"""
Auto-derivação de status_saude a partir do SPI da sprint.

Regras:
  SPI >= 0.9  → verde
  SPI >= 0.7  → amarelo
  SPI <  0.7  → vermelho
  sem baseline (pontos_previstos = NULL) → não altera (mantém manual)

Chamado após:
  - baseline update (quando pontos_previstos é definido)
  - task movida para concluida
"""


def auto_update_sprint_health(client, sprint_id: str) -> str | None:
    """
    Recalcula status_saude da sprint com base no SPI atual.
    Retorna o novo status_saude, ou None se não havia baseline.
    """
    sprint = (
        client.table("sprints")
        .select("pontos_previstos")
        .eq("id", sprint_id)
        .execute()
    )
    if not sprint.data:
        return None

    pontos_previstos = sprint.data[0].get("pontos_previstos")
    if not pontos_previstos or pontos_previstos <= 0:
        return None

    tasks = (
        client.table("tasks")
        .select("pontos, coluna_kanban")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    pontos_realizados = sum(t["pontos"] for t in tasks if t["coluna_kanban"] == "concluida")
    spi = pontos_realizados / pontos_previstos

    if spi >= 0.9:
        novo_status = "verde"
    elif spi >= 0.7:
        novo_status = "amarelo"
    else:
        novo_status = "vermelho"

    client.table("sprints").update({"status_saude": novo_status}).eq("id", sprint_id).execute()
    return novo_status
