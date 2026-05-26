from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from models.schemas import ProjectCreate, ProjectResponse, ProjectCostResponse
from services.supabase_client import get_client

router = APIRouter(prefix="/projects", tags=["projects"])


def _sanitize(row: dict) -> dict:
    """Strip gemini_api_key from row and inject has_api_key bool."""
    has_key = bool(row.get("gemini_api_key"))
    return {k: v for k, v in row.items() if k != "gemini_api_key"} | {"has_api_key": has_key}


class ApiKeyUpdate(BaseModel):
    gemini_api_key: Optional[str] = None


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project. Returns the inserted row with its generated UUID."""
    client = get_client()
    payload = {"name": data.name, "client": data.client, "description": data.description}
    if data.budget_usd is not None:
        payload["budget_usd"] = data.budget_usd
    if data.gemini_api_key:
        payload["gemini_api_key"] = data.gemini_api_key
    response = client.table("projects").insert(payload).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return _sanitize(response.data[0])


@router.get("", response_model=list[ProjectResponse])
async def list_projects():
    """List all projects ordered by creation date (most recent first)."""
    client = get_client()
    response = client.table("projects").select("*").order("created_at", desc=True).execute()
    projects = [_sanitize(row) for row in response.data]

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
    response = client.table("projects").select("*").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return _sanitize(response.data[0])


@router.patch("/{project_id}/api-key", response_model=ProjectResponse)
async def update_api_key(project_id: str, data: ApiKeyUpdate):
    """Set or clear the Gemini API key for an existing project."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    response = (
        client.table("projects")
        .update({"gemini_api_key": data.gemini_api_key or None})
        .eq("id", project_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update API key")
    return _sanitize(response.data[0])


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
    return _sanitize(response.data[0])


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Delete a project and all its ingestions and generated docs (cascade)."""
    client = get_client()
    response = client.table("projects").select("id").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    client.table("projects").delete().eq("id", project_id).execute()
