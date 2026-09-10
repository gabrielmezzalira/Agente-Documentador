import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")

RESEND_FROM = os.environ.get("RESEND_FROM", "DocuData <onboarding@resend.dev>")


def send_email(to: str, subject: str, body_html: str) -> None:
    """Envia email via Resend API. Lança exceção se falhar."""
    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY não configurado nas variáveis de ambiente")

    resend.Emails.send({
        "from": RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": body_html,
    })


def _base_template(titulo: str, corpo: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f7f7fa; margin: 0; padding: 32px 16px; }}
  .card {{ background: #ffffff; border-radius: 12px; max-width: 520px; margin: 0 auto; padding: 32px; border: 1px solid #e8e8ed; }}
  .badge {{ display: inline-block; background: #fff7ed; color: #c2410c; border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 700; margin-bottom: 16px; }}
  h2 {{ font-size: 20px; font-weight: 800; color: #111116; margin: 0 0 8px; }}
  p {{ font-size: 14px; color: #374151; line-height: 1.6; margin: 0 0 12px; }}
  .footer {{ margin-top: 24px; font-size: 11px; color: #9696a0; }}
</style></head>
<body>
  <div class="card">
    <div class="badge">DocuData · Lembrete</div>
    <h2>{titulo}</h2>
    {corpo}
    <div class="footer">Este email foi enviado automaticamente pelo DocuData. Para parar de receber lembretes, remova o email do projeto nas Configurações.</div>
  </div>
</body>
</html>"""


def email_planning_lembrete(projeto_nome: str, sprint_numero: int, horas_sem_planning: int) -> tuple[str, str]:
    """Retorna (subject, html) para lembrete de planning."""
    subject = f"[DocuData] Sprint {sprint_numero} de {projeto_nome} sem planning"
    corpo = f"""
    <p>A sprint <strong>{sprint_numero}</strong> do projeto <strong>{projeto_nome}</strong> foi criada há <strong>{horas_sem_planning} horas</strong> e ainda não tem documento de planning registrado.</p>
    <p>Acesse o DocuData e faça o upload do documento de planning para manter o histórico do projeto atualizado.</p>
    """
    return subject, _base_template(f"Sprint {sprint_numero} sem planning", corpo)


def email_review_lembrete(projeto_nome: str, sprint_numero: int, dias_sem_review: int) -> tuple[str, str]:
    """Retorna (subject, html) para lembrete de review."""
    subject = f"[DocuData] Sprint {sprint_numero} de {projeto_nome} sem review"
    corpo = f"""
    <p>Já se passaram <strong>{dias_sem_review} dias</strong> desde o início da sprint <strong>{sprint_numero}</strong> do projeto <strong>{projeto_nome}</strong> e ainda não há documento de review registrado.</p>
    <p>Faça o upload do documento de review no DocuData para fechar o ciclo desta sprint.</p>
    """
    return subject, _base_template(f"Sprint {sprint_numero} sem review", corpo)


def email_retro_lembrete(projeto_nome: str, sprint_numero: int, dias_sem_retro: int) -> tuple[str, str]:
    """Retorna (subject, html) para lembrete de retrospectiva."""
    subject = f"[DocuData] Sprint {sprint_numero} de {projeto_nome} sem retrospectiva"
    corpo = f"""
    <p>Já se passaram <strong>{dias_sem_retro} dias</strong> desde o início da sprint <strong>{sprint_numero}</strong> do projeto <strong>{projeto_nome}</strong> e ainda não há retrospectiva registrada.</p>
    <p>Acesse o DocuData e registre a retrospectiva desta sprint para preservar os aprendizados do time.</p>
    """
    return subject, _base_template(f"Sprint {sprint_numero} sem retrospectiva", corpo)


def email_task_atribuida(projeto_nome: str, operacional_nome: str, task_titulo: str, sprint_numero: int | None) -> tuple[str, str]:
    """Retorna (subject, html) para o aviso de atribuição de uma task a um operacional."""
    subject = f"[DocuData] Nova task atribuída: {task_titulo}"
    onde = f" (Sprint {sprint_numero})" if sprint_numero is not None else ""
    corpo = f"""
    <p>Olá, <strong>{operacional_nome}</strong>. Você foi designado(a) para a task <strong>{task_titulo}</strong>{onde} no projeto <strong>{projeto_nome}</strong>.</p>
    <p>Acesse o DocuData para ver os detalhes e o checklist da task.</p>
    """
    return subject, _base_template("Nova task atribuída a você", corpo)


def email_solicitacao_task(
    projeto_nome: str, operacional_nome: str, sprint_numero: int | None, sugestao: str | None = None
) -> tuple[str, str]:
    """Retorna (subject, html) para o pedido de task extra feito pelo operacional."""
    subject = f"[DocuData] {operacional_nome} está livre e pediu mais uma task"
    onde = f" da sprint <strong>{sprint_numero}</strong>" if sprint_numero is not None else ""
    sugestao_html = f"""
    <p style="background:#f8fafc;border-radius:8px;padding:10px 14px;"><strong>Sugestão de {operacional_nome}:</strong><br>{sugestao}</p>
    """ if sugestao else ""
    corpo = f"""
    <p><strong>{operacional_nome}</strong> concluiu tudo que estava atribuído a ele(a){onde} no projeto <strong>{projeto_nome}</strong> e está pedindo mais trabalho.</p>
    {sugestao_html}
    <p>Abra o Kanban do projeto e, se houver algo disponível, atribua uma task marcada como <strong>extra</strong>. Task extra não consome o orçamento de pontos da sprint.</p>
    <p>Se não houver nada agora, é só recusar o pedido. Ele não fica pendente pra sempre.</p>
    """
    return subject, _base_template("Pedido de nova task", corpo)


def email_task_concluida(projeto_nome: str, operacional_nome: str, task_titulo: str, sprint_numero: int | None) -> tuple[str, str]:
    """Retorna (subject, html) para o aviso de conclusão de task por um operacional."""
    subject = f"[DocuData] Task concluída: {task_titulo}"
    onde = f" (Sprint {sprint_numero})" if sprint_numero is not None else ""
    corpo = f"""
    <p><strong>{operacional_nome}</strong> marcou a task <strong>{task_titulo}</strong>{onde} como concluída no projeto <strong>{projeto_nome}</strong>.</p>
    <p>Acesse o DocuData para conferir o resultado.</p>
    """
    return subject, _base_template("Task concluída", corpo)
