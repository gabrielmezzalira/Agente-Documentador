from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    SprintCreate,
    SprintHealthUpdate,
    SprintResponse,
    SprintStatusResponse,
    SprintBaselineUpdate,
    SprintBaselineResponse,
)
from services.auth import require_not_operacional, require_project_access
from services.supabase_client import get_client
from services.spi_health import auto_update_sprint_health

router = APIRouter(tags=["sprints"])

_VALID_HEALTH = {"verde", "amarelo", "vermelho"}


@router.post("/projects/{project_id}/sprints", response_model=SprintResponse, status_code=201, dependencies=[Depends(require_project_access)])
async def create_sprint(project_id: str, data: SprintCreate):
    """Cria uma sprint para o projeto. Se `numero` não vier, usa max(numero)+1 (ou 1 se primeira)."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    numero = data.numero
    if numero is None:
        existing = (
            client.table("sprints")
            .select("numero")
            .eq("project_id", project_id)
            .order("numero", desc=True)
            .limit(1)
            .execute()
        )
        numero = (existing.data[0]["numero"] + 1) if existing.data else 1

    try:
        response = (
            client.table("sprints")
            .insert({"project_id": project_id, "numero": numero})
            .execute()
        )
    except Exception as exc:
        # Provável violação do UNIQUE (project_id, numero)
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail=f"Sprint {numero} já existe neste projeto",
            )
        raise HTTPException(status_code=500, detail=f"Failed to create sprint: {exc}")

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create sprint")
    return response.data[0]


@router.get("/projects/{project_id}/sprints", response_model=list[SprintStatusResponse], dependencies=[Depends(require_project_access)])
async def list_sprints(project_id: str):
    """Lista sprints do projeto + agregados de mínimo obrigatório.

    Para cada sprint, calcula em uma única passada:
    - tem_planning / tem_review (≥1 ingestão do tipo correspondente)
    - dailys_count (ingestões com tipo_documentacao='daily')
    - ingestions_count (total de ingestões da sprint, qualquer tipo)
    - docs_gerados_count (generated_docs com sprint_number daquela sprint)
    - pendencias (subset de ['planning','review'] que está faltando)
    """
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    sprints_resp = (
        client.table("sprints")
        .select("*")
        .eq("project_id", project_id)
        .order("numero", desc=True)
        .execute()
    )
    sprints = sprints_resp.data or []
    if not sprints:
        return []

    ing_resp = (
        client.table("ingestions")
        .select("sprint_number, tipo_documentacao")
        .eq("project_id", project_id)
        .execute()
    )
    docs_resp = (
        client.table("generated_docs")
        .select("sprint_number")
        .eq("project_id", project_id)
        .execute()
    )

    # Agrega ingestões por (sprint_number, tipo)
    ing_by_sprint: defaultdict = defaultdict(
        lambda: {"planning": 0, "daily": 0, "review": 0, "total": 0}
    )
    for ing in (ing_resp.data or []):
        sn = ing.get("sprint_number")
        if sn is None:
            continue
        ing_by_sprint[sn]["total"] += 1
        tipo = ing.get("tipo_documentacao")
        if tipo in ("planning", "daily", "review"):
            ing_by_sprint[sn][tipo] += 1

    # Conta docs gerados por sprint
    docs_by_sprint: defaultdict = defaultdict(int)
    for d in (docs_resp.data or []):
        sn = d.get("sprint_number")
        if sn is not None:
            docs_by_sprint[sn] += 1

    enriched = []
    for sprint in sprints:
        n = sprint["numero"]
        agg = ing_by_sprint[n]
        pendencias = []
        if agg["planning"] == 0:
            pendencias.append("planning")
        if agg["review"] == 0:
            pendencias.append("review")
        enriched.append({
            **sprint,
            "tem_planning": agg["planning"] > 0,
            "tem_review": agg["review"] > 0,
            "dailys_count": agg["daily"],
            "ingestions_count": agg["total"],
            "docs_gerados_count": docs_by_sprint[n],
            "pendencias": pendencias,
        })
    return enriched


@router.patch("/sprints/{sprint_id}/baseline", response_model=SprintBaselineResponse, dependencies=[Depends(require_not_operacional)])
async def update_baseline(sprint_id: str, data: SprintBaselineUpdate):
    """Define ou atualiza o baseline da sprint. Uma vez lockado, campos numéricos são imutáveis."""
    client = get_client()
    check = client.table("sprints").select("*").eq("id", sprint_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Sprint not found")
    sprint = check.data[0]

    if sprint.get("baseline_locked_at"):
        raise HTTPException(
            status_code=409,
            detail=f"Baseline já lockado em {sprint['baseline_locked_at']}. Não pode ser alterado.",
        )

    updates: dict = {}
    if data.pontos_previstos is not None:
        updates["pontos_previstos"] = data.pontos_previstos
    if data.faturamento_previsto is not None:
        updates["faturamento_previsto"] = data.faturamento_previsto
    if data.data_inicio is not None:
        updates["data_inicio"] = data.data_inicio.isoformat()
    if data.data_fim is not None:
        updates["data_fim"] = data.data_fim.isoformat()
    if data.lock:
        updates["baseline_locked_at"] = datetime.now(timezone.utc).isoformat()

    if not updates:
        return sprint

    resp = client.table("sprints").update(updates).eq("id", sprint_id).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to update baseline")

    if "pontos_previstos" in updates:
        try:
            auto_update_sprint_health(client, sprint_id)
        except Exception:
            pass  # best-effort

    return resp.data[0]


@router.delete("/sprints/{sprint_id}", status_code=204, dependencies=[Depends(require_not_operacional)])
async def delete_sprint(sprint_id: str):
    """
    Remove uma sprint e TUDO associado a ela (cascade completo):
    tasks, ingestões e documentos gerados. Sem confirmação adicional no backend —
    o frontend já exige confirmação explícita do usuário antes de chamar este endpoint.

    ingestions/generated_docs não têm FK pra sprints (ligam por project_id +
    sprint_number), então o cascade é feito aqui em vez de depender do banco.
    """
    client = get_client()
    check = client.table("sprints").select("id, project_id, numero").eq("id", sprint_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Sprint not found")

    sprint = check.data[0]
    project_id = sprint["project_id"]
    numero = sprint["numero"]

    # tasks.sprint_id é FK real — apaga explícito (não depende da migration de
    # ON DELETE CASCADE já ter sido aplicada em produção). task_transicoes e
    # task_sugestoes cascadeiam a partir de tasks no schema.
    client.table("tasks").delete().eq("sprint_id", sprint_id).execute()

    # ingestions e generated_docs ligam por (project_id, sprint_number) — sem FK.
    client.table("ingestions").delete().eq("project_id", project_id).eq("sprint_number", numero).execute()
    client.table("generated_docs").delete().eq("project_id", project_id).eq("sprint_number", numero).execute()
    client.table("planning_rascunhos").delete().eq("project_id", project_id).eq("sprint_numero", numero).execute()

    client.table("sprints").delete().eq("id", sprint_id).execute()


@router.patch("/sprints/{sprint_id}/health", response_model=SprintResponse, dependencies=[Depends(require_not_operacional)])
async def update_health(sprint_id: str, data: SprintHealthUpdate):
    """Atualiza semáforo de saúde e plano de correção da sprint."""
    if data.status_saude is not None and data.status_saude not in _VALID_HEALTH:
        raise HTTPException(
            status_code=400,
            detail=f"status_saude deve ser um de {sorted(_VALID_HEALTH)} ou null",
        )

    client = get_client()
    check = client.table("sprints").select("id").eq("id", sprint_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Sprint not found")

    payload = {
        "status_saude": data.status_saude,
        "plano_correcao": data.plano_correcao,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.table("sprints").update(payload).eq("id", sprint_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update sprint health")
    return response.data[0]
