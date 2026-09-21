"""Hidratação de task (Entrega 3, Onda B/C) — spec
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega3-design.md §4.1.

Só é consultada quando o projeto está em modo PULL com
pull_exigir_hidratacao=true (o chamador decide isso, não esta função — aqui
é só a regra pura de "o que falta")."""


def calcular_hidratacao(task: dict) -> tuple[bool, str | None]:
    """Retorna (rascunho, motivo_rascunho). Task hidratada tem título, pontos
    > 0, descrição não vazia e pelo menos 1 item de checklist."""
    faltando = []
    if not (task.get("titulo") or "").strip():
        faltando.append("título")
    if not (task.get("pontos") or 0) > 0:
        faltando.append("pontos")
    if not (task.get("descricao") or "").strip():
        faltando.append("descrição")
    if not (task.get("checklist") or []):
        faltando.append("checklist")

    if not faltando:
        return False, None
    return True, f"Faltam: {', '.join(faltando)}"
