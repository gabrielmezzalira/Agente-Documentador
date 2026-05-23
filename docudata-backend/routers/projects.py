from fastapi import APIRouter, HTTPException
from models.schemas import ProjectCreate, ProjectResponse
from services.supabase_client import get_client

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project. Returns the inserted row with its generated UUID."""
    client = get_client()
    response = client.table("projects").insert({
        "name": data.name,
        "client": data.client,
        "description": data.description,
    }).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return response.data[0]


@router.get("", response_model=list[ProjectResponse])
async def list_projects():
    """List all projects ordered by creation date (most recent first)."""
    client = get_client()
    response = client.table("projects").select("*").order("created_at", desc=True).execute()
    return response.data


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a single project by UUID. Returns 404 if not found."""
    client = get_client()
    response = client.table("projects").select("*").eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return response.data[0]
