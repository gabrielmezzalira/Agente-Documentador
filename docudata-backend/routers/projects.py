import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from typing import Literal, Optional
from models.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectCostResponse,
    ProjectUsageResponse,
    UsageBucket,
    UsageItem,
    TechTimelineResponse,
)
from services.supabase_client import get_client
from services.tech_timeline import build_tech_timeline

router = APIRouter(prefix="/projects", tags=["projects"])

_PROJECT_COLUMNS = (
    "id, name, client, subarea, description, squad, budget_usd, "
    "is_delivered, created_at"
)


def _public_project(row: dict) -> dict:
    """Mantém respostas de projeto limitadas aos campos públicos do domínio."""
    return {key: row.get(key) for key in (
        "id", "name", "client", "subarea", "description", "squad",
        "budget_usd", "is_delivered", "created_at", "last_ingestion_at",
    ) if key in row}


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project. Returns the inserted row with its generated UUID."""
    client = get_client()
    payload = {
        "name": data.name,
        "client": data.client,
        "subarea": data.subarea,
        "description": data.description,
        "squad": data.squad,
    }
    if data.budget_usd is not None:
        payload["budget_usd"] = data.budget_usd
    response = client.table("projects").insert(payload).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return _public_project(response.data[0])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(subarea: Literal["dados", "dev"]):
    """List all projects ordered by creation date (most recent first)."""
    client = get_client()
    response = (
        client.table("projects")
        .select(_PROJECT_COLUMNS)
        .eq("subarea", subarea)
        .order("created_at", desc=True)
        .execute()
    )
    projects = [_public_project(row) for row in response.data]

    if projects:
        ing_resp = (
            client.table("ingestions")
            .select("project_id, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        latest_by_project: dict = {}
        for ing in (ing_resp.data or []):
            pid = ing["project_id"]
            if pid not in latest_by_project:
                latest_by_project[pid] = ing["created_at"]
        for p in projects:
            p["last_ingestion_at"] = latest_by_project.get(p["id"])

    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a single project by UUID. Returns 404 if not found."""
    client = get_client()
    response = client.table("projects").select(_PROJECT_COLUMNS).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return _public_project(response.data[0])


@router.get("/{project_id}/cost", response_model=ProjectCostResponse)
async def get_project_cost(project_id: str):
    """Return aggregated token usage and cost for a project from its ingestions."""
    client = get_client()
    project_resp = client.table("projects").select("budget_usd").eq("id", project_id).execute()
    if not project_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    budget_usd = project_resp.data[0].get("budget_usd")

    ing_resp = (
        client.table("ingestions")
        .select("input_tokens, output_tokens, cost_usd")
        .eq("project_id", project_id)
        .execute()
    )
    gen_resp = (
        client.table("generated_docs")
        .select("input_tokens, output_tokens, cost_usd")
        .eq("project_id", project_id)
        .execute()
    )
    rows = (ing_resp.data or []) + (gen_resp.data or [])
    total_in = sum(r.get("input_tokens") or 0 for r in rows)
    total_out = sum(r.get("output_tokens") or 0 for r in rows)
    total_cost = sum(r.get("cost_usd") or 0.0 for r in rows)

    return ProjectCostResponse(
        project_id=project_id,
        total_usd=round(total_cost, 6),
        budget_usd=budget_usd,
        input_tokens=total_in,
        output_tokens=total_out,
    )


_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@router.get("/{project_id}/usage", response_model=ProjectUsageResponse)
async def get_project_usage(
    project_id: str,
    month: Optional[str] = Query(default=None),
):
    """Retorna custo e tokens do projeto para um mês específico (padrão: mês atual em America/Sao_Paulo).

    Agrega exclusivamente as colunas cost_usd, input_tokens e output_tokens já salvas
    em ingestions e generated_docs — não recalcula nenhum valor.
    """
    client = get_client()

    # 1. Verificar existência do projeto
    proj_check = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj_check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Resolver o mês
    tz_sp = ZoneInfo("America/Sao_Paulo")
    if month is None:
        now_sp = datetime.now(tz=tz_sp)
        month = now_sp.strftime("%Y-%m")
    else:
        if not _MONTH_RE.match(month):
            raise HTTPException(
                status_code=422,
                detail="Formato invalido para 'month'. Use YYYY-MM.",
            )

    # 3. Calcular intervalo UTC do mês
    year, mon = int(month[:4]), int(month[5:7])
    start_local = datetime(year, mon, 1, tzinfo=tz_sp)
    if mon == 12:
        end_local = datetime(year + 1, 1, 1, tzinfo=tz_sp)
    else:
        end_local = datetime(year, mon + 1, 1, tzinfo=tz_sp)
    start_iso = start_local.astimezone(timezone.utc).isoformat()
    end_iso = end_local.astimezone(timezone.utc).isoformat()

    # 4. Buscar linhas de ingestions e generated_docs no intervalo
    ing_resp = (
        client.table("ingestions")
        .select("id, created_at, tipo_documentacao, input_tokens, output_tokens, cost_usd")
        .eq("project_id", project_id)
        .gte("created_at", start_iso)
        .lt("created_at", end_iso)
        .execute()
    )
    gen_resp = (
        client.table("generated_docs")
        .select("id, created_at, doc_type, input_tokens, output_tokens, cost_usd")
        .eq("project_id", project_id)
        .gte("created_at", start_iso)
        .lt("created_at", end_iso)
        .execute()
    )

    ing_rows = ing_resp.data or []
    gen_rows = gen_resp.data or []

    # 5. Agregar totais — apenas colunas pré-existentes, sem recalculo
    all_rows = ing_rows + gen_rows
    total_usd = round(sum(r.get("cost_usd") or 0.0 for r in all_rows), 6)
    total_in = sum(r.get("input_tokens") or 0 for r in all_rows)
    total_out = sum(r.get("output_tokens") or 0 for r in all_rows)

    # 6. Construir breakdown por tipo
    def _label_ing(row: dict) -> str:
        return f"ingestion:{row.get('tipo_documentacao') or 'upload'}"

    def _label_gen(row: dict) -> str:
        if (row.get("input_tokens") or 0) == 0 and (row.get("output_tokens") or 0) == 0 and float(row.get("cost_usd") or 0) == 0.0:
            return "generation:manual"
        return f"generation:{row.get('doc_type')}"

    breakdown: dict[str, UsageBucket] = {}
    for row in ing_rows:
        k = _label_ing(row)
        b = breakdown.setdefault(k, UsageBucket(input_tokens=0, output_tokens=0, cost_usd=0.0, count=0))
        b.input_tokens += row.get("input_tokens") or 0
        b.output_tokens += row.get("output_tokens") or 0
        b.cost_usd = round(b.cost_usd + float(row.get("cost_usd") or 0), 8)
        b.count += 1
    for row in gen_rows:
        k = _label_gen(row)
        b = breakdown.setdefault(k, UsageBucket(input_tokens=0, output_tokens=0, cost_usd=0.0, count=0))
        b.input_tokens += row.get("input_tokens") or 0
        b.output_tokens += row.get("output_tokens") or 0
        b.cost_usd = round(b.cost_usd + float(row.get("cost_usd") or 0), 8)
        b.count += 1

    # 7. Construir lista cronológica de itens (limit 100)
    raw_items: list[UsageItem] = []
    for row in ing_rows:
        if not row.get("id") or not row.get("created_at"):
            continue
        raw_items.append(UsageItem(
            source="ingestion",
            id=row["id"],
            label=_label_ing(row),
            created_at=row["created_at"],
            input_tokens=row.get("input_tokens") or 0,
            output_tokens=row.get("output_tokens") or 0,
            cost_usd=float(row.get("cost_usd") or 0),
        ))
    for row in gen_rows:
        if not row.get("id") or not row.get("created_at"):
            continue
        raw_items.append(UsageItem(
            source="generated_doc",
            id=row["id"],
            label=_label_gen(row),
            created_at=row["created_at"],
            input_tokens=row.get("input_tokens") or 0,
            output_tokens=row.get("output_tokens") or 0,
            cost_usd=float(row.get("cost_usd") or 0),
        ))
    raw_items.sort(key=lambda x: str(x.created_at), reverse=True)
    truncated = len(raw_items) > 100
    items = raw_items[:100]

    return ProjectUsageResponse(
        project_id=project_id,
        month=month,
        total_usd=total_usd,
        input_tokens=total_in,
        output_tokens=total_out,
        breakdown=breakdown,
        items=items,
        truncated=truncated,
    )


@router.patch("/{project_id}/delivered", response_model=ProjectResponse)
async def toggle_delivered(project_id: str):
    """Toggle the delivered status of a project."""
    client = get_client()
    check = client.table("projects").select("id, is_delivered").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    current = check.data[0].get("is_delivered", False)
    response = (
        client.table("projects")
        .update({"is_delivered": not current})
        .eq("id", project_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update project")
    return _public_project(response.data[0])


@router.get("/{project_id}/technologies", response_model=TechTimelineResponse)
async def get_technologies(project_id: str):
    """Retorna stack atual + timeline de introdução/abandono por tecnologia."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    response = (
        client.table("ingestions")
        .select("sprint_number, extracted_content")
        .eq("project_id", project_id)
        .execute()
    )
    return build_tech_timeline(response.data or [])


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Delete a project and all its ingestions and generated docs (cascade)."""
    client = get_client()
    response = client.table("projects").select("id").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    client.table("projects").delete().eq("id", project_id).execute()
