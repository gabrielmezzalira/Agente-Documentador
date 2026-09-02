from fastapi import APIRouter, HTTPException, Query

from models.schemas import OperacionalCreate, OperacionalUpdate, OperacionalResponse
from services.supabase_client import get_client

router = APIRouter(prefix="/operacionais", tags=["operacionais"])


@router.post("", response_model=OperacionalResponse, status_code=201)
async def create_operacional(data: OperacionalCreate):
    client = get_client()
    check = client.table("projects").select("id").eq("id", data.project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    payload = {
        "project_id": data.project_id,
        "nome": data.nome,
    }
    if data.email is not None:
        payload["email"] = data.email
    if data.papel is not None:
        payload["papel"] = data.papel

    try:
        resp = client.table("operacionais").insert(payload).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail=f"Já existe um operacional com o nome '{data.nome}' neste projeto",
            )
        raise HTTPException(status_code=500, detail=f"Failed to create operacional: {exc}")

    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create operacional")
    return resp.data[0]


@router.get("/projects/{project_id}", response_model=list[OperacionalResponse])
async def list_operacionais(project_id: str, ativo: bool = Query(default=True)):
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    query = (
        client.table("operacionais")
        .select("*")
        .eq("project_id", project_id)
        .order("nome", desc=False)
    )
    if ativo:
        query = query.eq("ativo", True)

    return query.execute().data or []


@router.patch("/{operacional_id}", response_model=OperacionalResponse)
async def update_operacional(operacional_id: str, data: OperacionalUpdate):
    client = get_client()
    check = client.table("operacionais").select("id").eq("id", operacional_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    updates: dict = {}
    for field in ("nome", "email", "papel", "ativo"):
        val = getattr(data, field, None)
        if val is not None:
            updates[field] = val

    if not updates:
        return client.table("operacionais").select("*").eq("id", operacional_id).execute().data[0]

    try:
        resp = client.table("operacionais").update(updates).eq("id", operacional_id).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "23505" in msg:
            raise HTTPException(status_code=409, detail="Nome já em uso neste projeto")
        raise HTTPException(status_code=500, detail=f"Failed to update: {exc}")

    return resp.data[0]


@router.delete("/{operacional_id}", status_code=204)
async def delete_operacional(operacional_id: str):
    client = get_client()
    check = client.table("operacionais").select("id").eq("id", operacional_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    # Bloqueia se houver tasks vinculadas
    has_tasks = (
        client.table("tasks")
        .select("id")
        .eq("operacional_id", operacional_id)
        .limit(1)
        .execute()
    ).data
    if has_tasks:
        raise HTTPException(
            status_code=409,
            detail="Operacional possui tasks associadas. Reatribua-as antes de excluir.",
        )

    client.table("operacionais").delete().eq("id", operacional_id).execute()
