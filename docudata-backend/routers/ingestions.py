from fastapi import APIRouter

from models.schemas import IngestionResponse
from services.supabase_client import get_client

router = APIRouter(tags=["ingestions"])


@router.get("/ingestions/{projeto_id}", response_model=list[IngestionResponse])
async def list_ingestions(projeto_id: str):
    client = get_client()
    response = (
        client.table("ingestions")
        .select("*")
        .eq("project_id", projeto_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@router.get("/ingestions/{projeto_id}/{sprint}", response_model=list[IngestionResponse])
async def list_ingestions_by_sprint(projeto_id: str, sprint: int):
    client = get_client()
    response = (
        client.table("ingestions")
        .select("*")
        .eq("project_id", projeto_id)
        .eq("sprint_number", sprint)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []
