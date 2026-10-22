"""Régua única de dificuldade das tasks (spec A1 §1).

Os pontos de uma task são só o nível de dificuldade dela — não existe total de
pontos do projeto. Os rótulos são provisórios até o agente classificador (A2)."""

NIVEIS: tuple[int, ...] = (1, 2, 3, 5)
ROTULOS: dict[int, str] = {1: "simples", 2: "moderada", 3: "complexa", 5: "muito complexa"}
MENSAGEM_NIVEL_INVALIDO = "Use um nível da régua: 1, 2, 3 ou 5"


def converter_pontos_legado(pontos: int) -> int:
    """Nível mais próximo para pontos livres de antes da régua. Espelhada no
    UPDATE da migração em supabase_schema.sql — as duas precisam concordar."""
    if pontos <= 1:
        return 1
    if pontos == 2:
        return 2
    if pontos <= 4:
        return 3
    return 5


def ajuste_pontos_reabertura(task: dict) -> dict:
    """Task concluída antes da régua pode ter pontos fora dela; ao reabrir,
    a constraint do banco exige um nível válido. Guarda o original."""
    pontos = task.get("pontos")
    if pontos in NIVEIS or pontos is None:
        return {}
    return {"pontos": converter_pontos_legado(pontos), "pontos_legado": pontos}
