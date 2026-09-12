"""
Job diário de travamento automático por tempo (Parte 4 do SDD — ALERT-01).

Regra: uma task ativa (planejado ou em_andamento — ALERT-04, 2026-09-10: o
relógio deixou de exigir em_andamento porque um operacional pode estar
trabalhando na task sem nunca arrastar o card) parada por
dias_desde(entrou_em_andamento_em) >= pontos_da_task x 1.5 (limiar proporcional
ao ponto) vira um alerta visível (travado_automatico=true). O fator era 2 e foi
baixado em 2026-09-07: com sprint de uma semana, x2 fazia uma task de 4 pontos
só travar em 8 dias, ou seja, depois da sprint acabar — o alerta praticamente
nunca disparava a tempo.

`entrou_em_andamento_em` só é ancorado quando a sprint da task já começou
(sprints.iniciada) — ver services/sprints.py::iniciar_sprint_e_ancorar_tasks —
então uma task planejada para uma sprint futura não conta tempo antes da hora.

Revisão 2026-09-07 (decisão do Líder): o travamento deixou de ser só alerta. Cada
marcação grava um evento em task_travamentos, e o fechamento da sprint desconta
os pontos daquela task dos pontos concluídos do operacional — penaliza a dimensão
Entrega. O evento carrega timestamp para o cutoff do fechamento evitar dupla
contagem, e é marcado como dispensado quando o gerente dá override no alerta.

Autonomia continua alimentada exclusivamente por bloqueado_manual: travamento por
tempo penaliza Entrega, nunca Autonomia.
"""

import logging
from datetime import datetime, timezone

from services.supabase_client import get_client

log = logging.getLogger("travamento_checker")

# Dias de tolerância por ponto da task antes do alerta de atraso disparar.
LIMIAR_DIAS_POR_PONTO = 1.5


def check_travamento_automatico() -> None:
    """Ponto de entrada do scheduler. Roda uma vez por dia."""
    log.info("Iniciando verificação de travamento automático por tempo")
    client = get_client()

    resp = (
        client.table("tasks")
        .select("id, pontos, operacional_id, entrou_em_andamento_em, travado_automatico")
        .in_("coluna_kanban", ["planejado", "em_andamento"])
        .execute()
    )
    tasks = resp.data or []

    agora = datetime.now(timezone.utc)
    marcadas = 0

    for task in tasks:
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
        limiar_dias = (task.get("pontos") or 0) * LIMIAR_DIAS_POR_PONTO

        if dias_decorridos >= limiar_dias:
            client.table("tasks").update({"travado_automatico": True}).eq("id", task["id"]).execute()
            _registrar_travamento(client, task)
            marcadas += 1

    log.info("Travamento automático: %d task(s) marcada(s) de %d verificada(s)", marcadas, len(tasks))


def _registrar_travamento(client, task: dict) -> None:
    """Grava o evento que o fechamento da sprint vai ler para penalizar Entrega.
    Best-effort: falha aqui não pode impedir a marcação do alerta em si."""
    try:
        client.table("task_travamentos").insert({
            "task_id": task["id"],
            "operacional_id": task.get("operacional_id"),
            "pontos": task.get("pontos") or 0,
        }).execute()
    except Exception:
        log.warning("Falha ao registrar evento de travamento da task %s", task["id"])
