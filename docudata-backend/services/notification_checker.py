"""
Verifica sprints que estão sem planning, review ou retrospectiva e dispara emails.

Regras:
- Planning: avisa 24h após a sprint ser criada, depois a cada 24h enquanto não tiver
- Review:   avisa 5 dias após a sprint ser criada, depois a cada 24h enquanto não tiver
- Retro:    avisa 7 dias após a sprint ser criada, depois a cada 24h enquanto não tiver

Um email por tipo por sprint por dia (deduplicado via tabela sprint_notifications).
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from services.email_service import (
    email_planning_lembrete,
    email_review_lembrete,
    email_retro_lembrete,
    send_email,
)
from core.observability import registrar_falha_interna
from services.supabase_client import get_client

log = logging.getLogger("notification_checker")

# Thresholds para começar a avisar (a partir da criação da sprint)
PLANNING_THRESHOLD_HOURS = 24
REVIEW_THRESHOLD_DAYS = 5
RETRO_THRESHOLD_DAYS = 7


def _already_sent_today(client, project_id: str, sprint_numero: int, tipo: str) -> bool:
    """Retorna True se já enviamos um email deste tipo hoje para esta sprint."""
    today = date.today().isoformat()
    resp = (
        client.table("sprint_notifications")
        .select("id")
        .eq("project_id", project_id)
        .eq("sprint_numero", sprint_numero)
        .eq("tipo", tipo)
        .eq("sent_date", today)
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def _mark_sent(client, project_id: str, sprint_numero: int, tipo: str) -> None:
    today = date.today().isoformat()
    client.table("sprint_notifications").insert({
        "project_id": project_id,
        "sprint_numero": sprint_numero,
        "tipo": tipo,
        "sent_date": today,
    }).execute()


def check_and_send_notifications() -> None:
    """Ponto de entrada do scheduler. Roda a cada hora."""
    log.info("Iniciando verificação de notificações de sprint")
    try:
        _run_check()
    except Exception as exc:
        # O scheduler executa fora de uma request, mas ainda evita
        # `logger.exception`: SDKs externos podem incluir credenciais na mensagem.
        registrar_falha_interna("notification_checker", exc)


def _run_check() -> None:
    client = get_client()
    now = datetime.now(timezone.utc)

    # 1. Busca todos os projetos que têm gerente_email configurado
    projects_resp = (
        client.table("projects")
        .select("id, name, gerente_email")
        .not_.is_("gerente_email", "null")
        .execute()
    )
    projects = [p for p in (projects_resp.data or []) if p.get("gerente_email")]
    if not projects:
        log.info("Nenhum projeto com gerente_email configurado.")
        return

    project_ids = [p["id"] for p in projects]
    project_map = {p["id"]: p for p in projects}

    # 2. Busca todas as sprints desses projetos
    sprints_resp = (
        client.table("sprints")
        .select("id, project_id, numero, created_at")
        .in_("project_id", project_ids)
        .execute()
    )
    sprints = sprints_resp.data or []
    if not sprints:
        return

    # 3. Agrega ingestões por (project_id, sprint_numero, tipo_documentacao)
    ing_resp = (
        client.table("ingestions")
        .select("project_id, sprint_number, tipo_documentacao")
        .in_("project_id", project_ids)
        .execute()
    )
    # tem_tipo[(project_id, sprint_numero)][tipo] = True
    tem_tipo: dict = defaultdict(lambda: defaultdict(bool))
    for ing in (ing_resp.data or []):
        pid = ing.get("project_id")
        sn = ing.get("sprint_number")
        tipo = ing.get("tipo_documentacao")
        if pid and sn is not None and tipo:
            tem_tipo[(pid, sn)][tipo] = True

    # 4. Verifica geração de retro (generated_docs com doc_type='sprint_retro')
    retro_resp = (
        client.table("generated_docs")
        .select("project_id, sprint_number")
        .eq("doc_type", "sprint_retro")
        .in_("project_id", project_ids)
        .execute()
    )
    for doc in (retro_resp.data or []):
        pid = doc.get("project_id")
        sn = doc.get("sprint_number")
        if pid and sn is not None:
            tem_tipo[(pid, sn)]["retro"] = True

    # 5. Para cada sprint, verifica as 3 regras
    sent_count = 0
    for sprint in sprints:
        pid = sprint["project_id"]
        sn = sprint["numero"]
        project = project_map[pid]
        email = project["gerente_email"]
        nome = project["name"]

        created_at_str = sprint.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        delta = now - created_at
        horas = int(delta.total_seconds() / 3600)
        dias = delta.days

        tipos_sprint = tem_tipo.get((pid, sn), {})

        # Planning
        if horas >= PLANNING_THRESHOLD_HOURS and not tipos_sprint.get("planning"):
            if not _already_sent_today(client, pid, sn, "planning"):
                try:
                    subject, html = email_planning_lembrete(nome, sn, horas)
                    send_email(email, subject, html)
                    _mark_sent(client, pid, sn, "planning")
                    sent_count += 1
                    log.info("Email planning enviado: projeto_id=%s sprint=%s", pid, sn)
                except Exception as exc:
                    registrar_falha_interna("notification_checker.email_planning", exc)

        # Review
        if dias >= REVIEW_THRESHOLD_DAYS and not tipos_sprint.get("review"):
            if not _already_sent_today(client, pid, sn, "review"):
                try:
                    subject, html = email_review_lembrete(nome, sn, dias)
                    send_email(email, subject, html)
                    _mark_sent(client, pid, sn, "review")
                    sent_count += 1
                    log.info("Email review enviado: projeto_id=%s sprint=%s", pid, sn)
                except Exception as exc:
                    registrar_falha_interna("notification_checker.email_review", exc)

        # Retro
        if dias >= RETRO_THRESHOLD_DAYS and not tipos_sprint.get("retro"):
            if not _already_sent_today(client, pid, sn, "retro"):
                try:
                    subject, html = email_retro_lembrete(nome, sn, dias)
                    send_email(email, subject, html)
                    _mark_sent(client, pid, sn, "retro")
                    sent_count += 1
                    log.info("Email retro enviado: projeto_id=%s sprint=%s", pid, sn)
                except Exception as exc:
                    registrar_falha_interna("notification_checker.email_retro", exc)

    log.info(f"Verificação concluída. Emails enviados: {sent_count}")
