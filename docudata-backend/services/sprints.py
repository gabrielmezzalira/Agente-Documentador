"""Helpers compartilhados pra entidade Sprint."""
import logging
from datetime import datetime, timezone
from typing import Optional

from services.previsto_sprint import marcar_foto_do_inicio

logger = logging.getLogger(__name__)


def ensure_sprint_row(client, project_id: str, numero: int) -> None:
    """Cria sprint no banco se ainda não existir. Idempotente.

    Usado por /ingest e /sprint-docs/* para garantir que toda ingestão tem uma
    sprint row correspondente (importante pro GET /projects/{id}/sprints listar
    todas sprints com atividade, mesmo as não criadas explicitamente pelo
    botão "+ Nova sprint").
    """
    existing = (
        client.table("sprints")
        .select("id")
        .eq("project_id", project_id)
        .eq("numero", numero)
        .execute()
    )
    if existing.data:
        return
    try:
        criada = client.table("sprints").insert({"project_id": project_id, "numero": numero}).execute()
    except Exception:
        # Race condition (UNIQUE violation) ou outro erro — outra request criou primeiro
        return
    try:
        if criada.data:
            congelar_modo_da_sprint(client, criada.data[0]["id"])
    except Exception:
        # Sem snapshot o fechamento cai no modo atual do projeto.
        logger.warning("Falha ao congelar o modo da sprint do projeto %s #%s", project_id, numero, exc_info=True)


def renumerar_sprint(client, project_id: str, sprint_id: str, antigo: int, novo: int) -> None:
    """Troca o número da sprint e de tudo que a referencia por (project_id, número):
    ingestões, documentos gerados, rascunhos de planning e o sprint_alvo (texto) das
    funcionalidades. O chamador garante que `novo` está livre no projeto."""
    if antigo == novo:
        return
    client.table("sprints").update({"numero": novo}).eq("id", sprint_id).execute()
    client.table("ingestions").update({"sprint_number": novo}).eq("project_id", project_id).eq("sprint_number", antigo).execute()
    client.table("generated_docs").update({"sprint_number": novo}).eq("project_id", project_id).eq("sprint_number", antigo).execute()
    client.table("planning_rascunhos").update({"sprint_numero": novo}).eq("project_id", project_id).eq("sprint_numero", antigo).execute()
    client.table("funcionalidades").update({"sprint_alvo": str(novo)}).eq("project_id", project_id).eq("sprint_alvo", str(antigo)).execute()


def normalizar_sprint_unica(client, project_id: str) -> None:
    """Projeto com uma única sprint sempre a chama de Sprint 1."""
    linhas = client.table("sprints").select("id, numero").eq("project_id", project_id).execute().data or []
    if len(linhas) == 1 and linhas[0]["numero"] != 1:
        renumerar_sprint(client, project_id, linhas[0]["id"], linhas[0]["numero"], 1)


def congelar_modo_da_sprint(client, sprint_id: str) -> Optional[str]:
    """Grava em sprints.modo_trabalho/modo_avaliacao o modo vigente do projeto
    quando a sprint começa. Só preenche o que ainda está nulo (o snapshot de
    uma sprint nunca muda depois). No-op se sprint ou projeto não existem.
    Devolve o modo_trabalho efetivo da sprint."""
    linhas = (
        client.table("sprints").select("project_id, modo_trabalho, modo_avaliacao").eq("id", sprint_id).execute().data
    )
    if not linhas:
        return None
    sprint = linhas[0]
    if sprint.get("modo_trabalho") and sprint.get("modo_avaliacao"):
        return sprint["modo_trabalho"]
    projeto = (
        client.table("projects")
        .select("modo_trabalho, modo_avaliacao")
        .eq("id", sprint.get("project_id"))
        .execute()
        .data
    )
    if not projeto:
        return sprint.get("modo_trabalho")
    modo_trabalho = sprint.get("modo_trabalho") or projeto[0].get("modo_trabalho") or "ATRIBUICAO"
    modo_avaliacao = sprint.get("modo_avaliacao") or projeto[0].get("modo_avaliacao") or "PONTOS_ATRIBUIDOS"
    client.table("sprints").update(
        {"modo_trabalho": modo_trabalho, "modo_avaliacao": modo_avaliacao}
    ).eq("id", sprint_id).execute()
    return modo_trabalho


def get_current_sprint_number(client, project_id: str) -> int:
    """Resolve a sprint vigente sem depender de uma chamada HTTP interna."""
    sprints_resp = (
        client.table("sprints").select("numero, iniciada").eq("project_id", project_id).execute()
    )
    linhas = sprints_resp.data or []
    numeros = {row["numero"] for row in linhas}
    if not numeros:
        return 1

    # Sprint só planejada (não iniciada) nunca é a atual: a vigente é a iniciada mais recente.
    iniciadas = {row["numero"] for row in linhas if row.get("iniciada")}
    if iniciadas:
        return max(iniciadas)

    plannings = (
        client.table("ingestions")
        .select("sprint_number, created_at")
        .eq("project_id", project_id)
        .eq("tipo_documentacao", "planning")
        .order("created_at", desc=True)
        .execute()
    )
    for row in plannings.data or []:
        if row["sprint_number"] in numeros:
            return row["sprint_number"]
    return max(numeros)


def get_current_sprint_id(client, project_id: str) -> Optional[str]:
    """Resolve o id (uuid) da sprint atual do projeto — mesma lógica de
    GET /projects/{id}/current-sprint (routers/commit_ingest.py), mas devolve
    o id em vez do número. Usado pelo Motor de Score (Phase 18) pra rotear
    eventos tardios (services/pontuacao.py)."""
    sprints_resp = client.table("sprints").select("id, numero, iniciada").eq("project_id", project_id).execute()
    sprints_rows = sprints_resp.data or []
    if not sprints_rows:
        return None
    iniciadas_rows = [r for r in sprints_rows if r.get("iniciada")]
    if iniciadas_rows:
        return max(iniciadas_rows, key=lambda r: r["numero"])["id"]
    numero_para_id = {row["numero"]: row["id"] for row in sprints_rows}

    plannings = (
        client.table("ingestions")
        .select("sprint_number, created_at")
        .eq("project_id", project_id)
        .eq("tipo_documentacao", "planning")
        .order("created_at", desc=True)
        .execute()
    )
    for row in (plannings.data or []):
        if row["sprint_number"] in numero_para_id:
            return numero_para_id[row["sprint_number"]]

    maior_numero = max(numero_para_id)
    return numero_para_id[maior_numero]


def compute_planejado_vs_entregue(client, project_id: str, numero: int) -> list[dict]:
    """Monta a tabela 'planejado vs. entregue' da Review a partir do kanban real
    da sprint — 1 linha por task, 'entregue' = task concluída ao final da sprint.

    motivo_nao/causa_raiz_num ficam sempre vazios (dependem de julgamento humano,
    o gerente completa manualmente); recalculado do zero a cada chamada.
    """
    sprint_resp = (
        client.table("sprints")
        .select("id")
        .eq("project_id", project_id)
        .eq("numero", numero)
        .limit(1)
        .execute()
    )
    if not sprint_resp.data:
        return []
    sprint_id = sprint_resp.data[0]["id"]

    tasks_resp = (
        client.table("tasks")
        .select("titulo, coluna_kanban")
        .eq("sprint_id", sprint_id)
        .order("coluna_kanban")
        .order("ordem")
        .execute()
    )
    tasks = tasks_resp.data or []
    return [
        {
            "item": t["titulo"],
            "entregue": "S" if t["coluna_kanban"] == "concluida" else "N",
            "motivo_nao": "",
            "causa_raiz_num": "",
        }
        for t in tasks
    ]


def iniciar_sprint_e_ancorar_tasks(client, sprint_id: str) -> None:
    """Marca a sprint como iniciada e ancora o relógio de travamento automático
    (ALERT-01) das tasks que já estavam nela (planejado ou em_andamento) e ainda
    não tinham relógio rodando.

    Sem isso, uma task criada em Planejado para uma sprint futura ficaria sem
    âncora até alguém movê-la manualmente pra Em Andamento — o que é exatamente
    o cenário que motivou o relógio passar a contar desde Planejado: um
    operacional pode estar trabalhando nela sem nunca arrastar o card. O relógio
    só é ancorado a partir de AGORA (não retroativo à criação da task), porque
    antes da sprint iniciar o tempo parado não deveria contar.

    Chamado tanto pelo botão "Iniciar próxima sprint" quanto, implicitamente,
    pela confirmação da Avaliação Semanal da sprint anterior (routers/avaliacoes.py).

    Em projeto Pull, tasks sem dono (fila) não são ancoradas: a âncora nasce
    quando alguém puxa a task.

    Também tira a foto do previsto (tasks não extras da sprint ganham
    prevista_no_inicio)."""
    ja_iniciada = bool(
        (client.table("sprints").select("iniciada").eq("id", sprint_id).execute().data or [{}])[0].get("iniciada")
    )
    client.table("sprints").update({
        "iniciada": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", sprint_id).execute()
    # A foto pertence ao momento em que a sprint realmente começou: chamadas
    # repetidas não podem promover tasks que surgiram depois.
    if not ja_iniciada:
        marcar_foto_do_inicio(client, sprint_id)

    # Snapshot do modo no início da sprint (idempotente); decide o Pull abaixo.
    em_pull = congelar_modo_da_sprint(client, sprint_id) == "PULL"

    agora_iso = datetime.now(timezone.utc).isoformat()
    pendentes = (
        client.table("tasks")
        .select("id, operacional_id")
        .eq("sprint_id", sprint_id)
        .neq("coluna_kanban", "concluida")
        .is_("entrou_em_andamento_em", "null")
        .execute()
        .data or []
    )
    for t in pendentes:
        # Em Pull a task da fila (sem dono) não tem relógio: o tempo de espera
        # não é do operacional. A âncora nasce quando alguém puxa.
        if em_pull and not t.get("operacional_id"):
            continue
        client.table("tasks").update({"entrou_em_andamento_em": agora_iso}).eq("id", t["id"]).execute()

    # Com a sprint em curso o nível das tasks dela fica fixo (spec A2 §5).
    from services.classificador_ciclo import travar_nivel

    todas = client.table("tasks").select("id").eq("sprint_id", sprint_id).execute().data or []
    travar_nivel(client, [t["id"] for t in todas])
