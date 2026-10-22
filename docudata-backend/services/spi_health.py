"""
Auto-derivação de status_saude a partir do SPI da sprint.

  SPI >= 0.9 → verde · SPI >= 0.7 → amarelo · SPI < 0.7 → vermelho
  previsto = 0 (sprint sem tasks previstas) → não altera (mantém manual)

SPI = pontos concluídos (sem extras) ÷ previsto (services/previsto_sprint.py).
Chamado depois que uma task vai para concluída.
"""
from services.previsto_sprint import previsto_da_sprint


def auto_update_sprint_health(client, sprint_id: str) -> str | None:
    previsto = previsto_da_sprint(client, sprint_id)["previsto"]
    if previsto <= 0:
        return None

    tasks = (
        client.table("tasks")
        .select("pontos, coluna_kanban, extra")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    realizados = sum(t["pontos"] for t in tasks if t["coluna_kanban"] == "concluida" and not t.get("extra"))
    spi = realizados / previsto

    if spi >= 0.9:
        novo_status = "verde"
    elif spi >= 0.7:
        novo_status = "amarelo"
    else:
        novo_status = "vermelho"

    client.table("sprints").update({"status_saude": novo_status}).eq("id", sprint_id).execute()
    return novo_status
