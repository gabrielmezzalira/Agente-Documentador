from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import IngestionResponse
from services.supabase_client import get_client

router = APIRouter(tags=["ingestions"])


class UpdateIngestionSprint(BaseModel):
    sprint_number: int


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


@router.delete("/ingestions/{ingestion_id}", status_code=204)
async def delete_ingestion(ingestion_id: str):
    client = get_client()
    resp = client.table("ingestions").select("id").eq("id", ingestion_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    client.table("ingestions").delete().eq("id", ingestion_id).execute()


@router.patch("/ingestions/{ingestion_id}", response_model=IngestionResponse)
async def update_ingestion_sprint(ingestion_id: str, body: UpdateIngestionSprint):
    client = get_client()
    resp = client.table("ingestions").select("id").eq("id", ingestion_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    result = (
        client.table("ingestions")
        .update({"sprint_number": body.sprint_number})
        .eq("id", ingestion_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update ingestion")
    return result.data[0]
