"""Elegibilidade temporal por vínculo com o projeto (Entrega 2) — substitui
"tem task na sprint" como definição de elegível em toda a cadeia de
Avaliação Semanal. Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.

Comparação de timestamp é string simples (ISO 8601, mesmo formato que
datetime.now(timezone.utc).isoformat() já usa em services/pontuacao.py para
o cutoff) — sem .or_()/.lte() do supabase-py, sem precedente nesta base."""


def listar_vinculados_no_projeto(client, project_id: str, momento_iso: str) -> list[dict]:
    """Operacionais vinculados ao projeto no momento informado: data_entrada
    já passou e data_saida é nula ou posterior ao momento. Filtra em Python
    (não via query composta) — mesmo padrão já usado em services/performance.py
    para agregações que não cabem numa única query simples."""
    todos = (
        client.table("operacionais")
        .select("id, nome, email, project_id, data_entrada, data_saida")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    vinculados = []
    for op in todos:
        entrada = op.get("data_entrada")
        saida = op.get("data_saida")
        if entrada and entrada > momento_iso:
            continue
        if saida and saida <= momento_iso:
            continue
        vinculados.append(op)
    return vinculados
