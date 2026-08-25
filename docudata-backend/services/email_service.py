import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


def send_email(to: str, subject: str, body_html: str) -> None:
    """Envia email via Gmail SMTP com App Password. Lança exceção se falhar."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_USER e GMAIL_APP_PASSWORD não configurados nas variáveis de ambiente")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"DocuData <{GMAIL_USER}>"
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_USER, to, msg.as_string())


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
