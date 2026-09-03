"""
Job diário de travamento automático por tempo (Parte 4 do SDD — ALERT-01).

Regra: uma task parada em em_andamento por dias_desde(entrou_em_andamento_em)
>= pontos_da_task x 2 (limiar proporcional ao ponto) vira um ALERTA visível
(travado_automatico=true) — nunca pontuação.

IMPORTANTE (NFR do SDD): este job nunca escreve em nenhum campo que alimenta fórmula de score
— quando a Phase 18 (Motor de Score) existir, nenhuma dimensão deve ler
travado_automatico. Só bloqueado_manual alimenta Autonomia.
"""

import logging
from datetime import datetime, timezone

from services.supabase_client import get_client

log = logging.getLogger("travamento_checker")


def check_travamento_automatico() -> None:
    """Ponto de entrada do scheduler. Roda uma vez por dia."""
    log.info("Iniciando verificação de travamento automático por tempo")
    client = get_client()

    resp = (
        client.table("tasks")
        .select("id, pontos, entrou_em_andamento_em, travado_automatico, travado_override")
        .eq("coluna_kanban", "em_andamento")
        .execute()
    )
    tasks = resp.data or []

    agora = datetime.now(timezone.utc)
    marcadas = 0

    for task in tasks:
        if task.get("travado_override"):
            continue
        if task.get("travado_automatico"):
            # Idempotência — já sinalizada, nada a fazer.
            continue

        entrou_em_andamento_em = task.get("entrou_em_andamento_em")
        if not entrou_em_andamento_em:
            # Task sem âncora (dado legado ou edge case) — não há como calcular dias.
            continue

        entrou_dt = datetime.fromisoformat(entrou_em_andamento_em)
        if entrou_dt.tzinfo is None:
            entrou_dt = entrou_dt.replace(tzinfo=timezone.utc)

        dias_decorridos = (agora - entrou_dt).total_seconds() / 86400
        limiar_dias = (task.get("pontos") or 0) * 2

        if dias_decorridos >= limiar_dias:
            client.table("tasks").update({"travado_automatico": True}).eq("id", task["id"]).execute()
            marcadas += 1

    log.info("Travamento automático: %d task(s) marcada(s) de %d verificada(s)", marcadas, len(tasks))
