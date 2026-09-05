"""Motor de cálculo do Motor de Score (Phase 18).

Fecha pontuacao_operacional_sprint no momento em que o gerente confirma a
avaliação semanal (routers/avaliacoes.py::confirmar_avaliacao_semanal).

O cálculo é feito uma única vez, a partir do estado final de
tasks/task_transicoes/task_reaberturas/avaliacoes_gerente — não é um contador
incremental mantido ao longo da sprint. Por isso reatribuição mid-sprint não
precisa de tratamento especial: o cálculo simplesmente lê o estado atual (e o
histórico de transições, pra "quem completou") quando roda.
"""
from datetime import datetime, timezone

from services.sprints import get_current_sprint_id


def calcular_e_travar_pontuacao(client, sprint_id: str) -> list[dict]:
    """Calcula e trava uma linha de pontuacao_operacional_sprint por operacional
    com task na sprint. Idempotente: se já existir alguma linha para esta
    sprint, retorna as existentes sem recalcular."""
    existentes = (
        client.table("pontuacao_operacional_sprint")
        .select("*")
        .eq("sprint_id", sprint_id)
        .execute()
        .data
    )
    if existentes:
        return existentes

    sprint_resp = client.table("sprints").select("id, project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        return []
    project_id = sprint_resp.data[0]["project_id"]

    cutoff_resp = (
        client.table("pontuacao_operacional_sprint")
        .select("finalizado_em")
        .eq("projeto_id", project_id)
        .order("finalizado_em", desc=True)
        .limit(1)
        .execute()
    )
    cutoff = cutoff_resp.data[0]["finalizado_em"] if cutoff_resp.data else None

    tasks = (
        client.table("tasks")
        .select("id, operacional_id, pontos, coluna_kanban, bloqueado_resolvido_por, bloqueado_resolvido_em")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    if not tasks:
        return []

    task_ids_concluidas = [t["id"] for t in tasks if t.get("coluna_kanban") == "concluida"]
    quem_completou = _resolver_quem_completou(client, task_ids_concluidas)

    pontos_concluidos: dict[str, int] = {}
    pontos_alocados: dict[str, int] = {}
    tasks_concluidas: dict[str, int] = {}
    bloqueios_totais: dict[str, int] = {}
    bloqueios_proprio: dict[str, int] = {}

    for task in tasks:
        pontos = task.get("pontos") or 0
        if task.get("coluna_kanban") == "concluida":
            operacional_id = quem_completou.get(task["id"]) or task.get("operacional_id")
            if operacional_id:
                pontos_concluidos[operacional_id] = pontos_concluidos.get(operacional_id, 0) + pontos
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos
                tasks_concluidas[operacional_id] = tasks_concluidas.get(operacional_id, 0) + 1
        else:
            operacional_id = task.get("operacional_id")
            if operacional_id:
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos

        if task.get("bloqueado_resolvido_em") and task.get("operacional_id"):
            resolvido_em = task["bloqueado_resolvido_em"]
            if cutoff is None or resolvido_em > cutoff:
                op = task["operacional_id"]
                bloqueios_totais[op] = bloqueios_totais.get(op, 0) + 1
                if task.get("bloqueado_resolvido_por") == "operacional":
                    bloqueios_proprio[op] = bloqueios_proprio.get(op, 0) + 1

    reaberturas = _contar_reaberturas(client, [t["id"] for t in tasks], cutoff)

    eventos_tardios = (
        client.table("eventos_pontuacao_tardios")
        .select("operacional_id, dimensao")
        .eq("sprint_id_alvo", sprint_id)
        .execute()
        .data or []
    )
    for evento in eventos_tardios:
        op = evento["operacional_id"]
        if evento["dimensao"] == "qualidade_reaberturas":
            reaberturas[op] = reaberturas.get(op, 0) + 1
        elif evento["dimensao"] == "autonomia_bloqueios_totais":
            bloqueios_totais[op] = bloqueios_totais.get(op, 0) + 1
        elif evento["dimensao"] == "autonomia_bloqueios_resolvidos_proprio":
            bloqueios_proprio[op] = bloqueios_proprio.get(op, 0) + 1

    avaliacoes = (
        client.table("avaliacoes_gerente")
        .select("operacional_id, resposta_1, resposta_2, resposta_3, resposta_4, resposta_5, resposta_6, resposta_7")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    avaliacao_por_operacional = {a["operacional_id"]: a for a in avaliacoes}

    operacional_ids = (
        set(pontos_alocados)
        | set(pontos_concluidos)
        | set(reaberturas)
        | set(bloqueios_totais)
        | set(avaliacao_por_operacional)
    )
    if not operacional_ids:
        return []

    agora = datetime.now(timezone.utc).isoformat()
    linhas = []
    for operacional_id in operacional_ids:
        aval = avaliacao_por_operacional.get(operacional_id)
        gerente_media = None
        gerente_pergunta6 = None
        if aval:
            notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_7"]]
            gerente_media = round(sum(notas) / len(notas), 2)
            gerente_pergunta6 = aval["resposta_6"]

        linhas.append({
            "operacional_id": operacional_id,
            "sprint_id": sprint_id,
            "projeto_id": project_id,
            "sprint_fim": agora,
            "gerente_media": gerente_media,
            "gerente_pergunta6": gerente_pergunta6,
            "entrega_pontos_concluidos": pontos_concluidos.get(operacional_id, 0),
            "entrega_pontos_alocados": pontos_alocados.get(operacional_id, 0),
            "qualidade_reaberturas": reaberturas.get(operacional_id, 0),
            "qualidade_tasks_concluidas": tasks_concluidas.get(operacional_id, 0),
            "autonomia_bloqueios_resolvidos_proprio": bloqueios_proprio.get(operacional_id, 0),
            "autonomia_bloqueios_totais": bloqueios_totais.get(operacional_id, 0),
            "arquetipo": None,
            "finalizado_em": agora,
        })

    resp = client.table("pontuacao_operacional_sprint").insert(linhas).execute()
    return resp.data or []


def _resolver_quem_completou(client, task_ids: list[str]) -> dict[str, str]:
    """Pra cada task_id concluída, acha quem estava alocado no momento da
    transição pra 'concluida' (via snapshot gravado por _registrar_task_transicao,
    Task 2). Se a task tiver sido concluída mais de uma vez (reabertura), pega
    a transição mais recente."""
    if not task_ids:
        return {}
    transicoes = (
        client.table("task_transicoes")
        .select("task_id, operacional_id, timestamp")
        .in_("task_id", task_ids)
        .eq("campo", "coluna_kanban")
        .eq("para", "concluida")
        .order("timestamp", desc=True)
        .execute()
        .data or []
    )
    resultado: dict[str, str] = {}
    for row in transicoes:
        if row["task_id"] not in resultado and row.get("operacional_id"):
            resultado[row["task_id"]] = row["operacional_id"]
    return resultado


def _contar_reaberturas(client, task_ids: list[str], cutoff: str | None = None) -> dict[str, int]:
    if not task_ids:
        return {}
    query = (
        client.table("task_reaberturas")
        .select("operacional_id, timestamp")
        .in_("task_id", task_ids)
    )
    if cutoff is not None:
        query = query.gt("timestamp", cutoff)
    rows = query.execute().data or []
    contagem: dict[str, int] = {}
    for row in rows:
        op = row.get("operacional_id")
        if op:
            contagem[op] = contagem.get(op, 0) + 1
    return contagem


def rotear_evento_pos_fechamento(client, task: dict, dimensao: str) -> None:
    """Se a sprint de origem da task já tiver pontuacao_operacional_sprint
    travada, redireciona o evento de qualidade/autonomia pra sprint ativa do
    projeto (via ledger eventos_pontuacao_tardios) em vez de descartá-lo.

    Sem efeito se a sprint de origem ainda não fechou (fluxo normal — o
    evento será capturado no próprio fechamento dessa sprint) ou se a sprint
    ativa também já estiver travada (evento fica só no histórico de
    task_transicoes/task_reaberturas, sem afetar nenhuma pontuação)."""
    sprint_id_origem = task.get("sprint_id")
    if not sprint_id_origem:
        return

    travada = (
        client.table("pontuacao_operacional_sprint")
        .select("id")
        .eq("sprint_id", sprint_id_origem)
        .execute()
        .data
    )
    if not travada:
        return

    sprint_ativa_id = get_current_sprint_id(client, task["project_id"])
    if not sprint_ativa_id:
        return

    sprint_ativa_travada = (
        client.table("pontuacao_operacional_sprint")
        .select("id")
        .eq("sprint_id", sprint_ativa_id)
        .execute()
        .data
    )
    if sprint_ativa_travada:
        return

    operacional_id = task.get("operacional_id")
    if not operacional_id:
        return

    client.table("eventos_pontuacao_tardios").insert({
        "operacional_id": operacional_id,
        "sprint_id_alvo": sprint_ativa_id,
        "dimensao": dimensao,
        "task_id": task.get("id"),
    }).execute()


def calcular_spi_operacional(client, operacional_id: str) -> dict:
    """SPI em duas camadas: soma dentro de cada projeto, depois média simples
    entre projetos se o operacional atuou em mais de um. Teto 100."""
    linhas = (
        client.table("pontuacao_operacional_sprint")
        .select("projeto_id, entrega_pontos_concluidos, entrega_pontos_alocados")
        .eq("operacional_id", operacional_id)
        .execute()
        .data or []
    )

    por_projeto_raw: dict[str, dict] = {}
    for linha in linhas:
        acumulado = por_projeto_raw.setdefault(linha["projeto_id"], {"concluidos": 0, "alocados": 0})
        acumulado["concluidos"] += linha["entrega_pontos_concluidos"]
        acumulado["alocados"] += linha["entrega_pontos_alocados"]

    por_projeto = []
    for projeto_id, soma in por_projeto_raw.items():
        spi_projeto = None
        if soma["alocados"] > 0:
            spi_projeto = round(min(soma["concluidos"] / soma["alocados"] * 100, 100), 2)
        por_projeto.append({"projeto_id": projeto_id, "spi": spi_projeto})

    validos = [p["spi"] for p in por_projeto if p["spi"] is not None]
    spi_operacional = round(sum(validos) / len(validos), 2) if validos else None

    return {"operacional_id": operacional_id, "spi": spi_operacional, "por_projeto": por_projeto}
