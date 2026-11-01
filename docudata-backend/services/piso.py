"""Piso por pessoa (B1): 0,5 × máx(mediana do squad na sprint −1, mediana da subárea no trimestre anterior). Puro."""
from datetime import datetime, timezone
from statistics import median


def realizados_por_pessoa(tasks: list[dict]) -> dict[str, float]:
    """Pontos concluídos (sem extras) por operacional."""
    saida: dict[str, float] = {}
    for t in tasks:
        if t.get("coluna_kanban") == "concluida" and not t.get("extra") and t.get("operacional_id"):
            saida[t["operacional_id"]] = saida.get(t["operacional_id"], 0.0) + t["pontos"]
    return saida


def squad(tasks: list[dict]) -> set[str]:
    return {t["operacional_id"] for t in tasks if t.get("operacional_id")}


def realizados_do_squad(tasks: list[dict]) -> dict[str, float]:
    """Realizado de cada pessoa do squad; quem tem task mas nada concluído conta 0."""
    feito = realizados_por_pessoa(tasks)
    return {p: feito.get(p, 0.0) for p in squad(tasks)}


def mediana(valores) -> float | None:
    valores = list(valores)
    return float(median(valores)) if valores else None


def piso(mediana_squad: float | None, mediana_subarea: float | None) -> float | None:
    existentes = [m for m in (mediana_squad, mediana_subarea) if m is not None]
    return round(0.5 * max(existentes), 1) if existentes else None


def _dt(v) -> datetime:
    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def trimestre_do_instante(d: datetime) -> str:
    return f"{d.year}-T{(d.month - 1) // 3 + 1}"


def trimestre_de(sprint: dict) -> str | None:
    """Trimestre civil do fechamento; sem ele, o de `data_fim`; sem nenhum, None."""
    ref = sprint.get("avaliacao_completa_em") or sprint.get("data_fim")
    return trimestre_do_instante(_dt(ref)) if ref else None


def trimestre_anterior(t: str) -> str:
    ano, tri = t.split("-T")
    ano, tri = int(ano), int(tri)
    return f"{ano - 1}-T4" if tri == 1 else f"{ano}-T{tri - 1}"
