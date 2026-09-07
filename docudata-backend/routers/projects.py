from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from models.schemas import (
    ProjectCreate,
    ProjectResponse,
    TechTimelineResponse,
    ContratoUpdate,
    GerenteEmailUpdate,
)
from services.auth import get_current_pessoa, require_project_access
from services.supabase_client import get_client
from services.tech_timeline import build_tech_timeline

router = APIRouter(prefix="/projects", tags=["projects"])


def _sanitize(row: dict) -> dict:
    """Strip sensitive keys from row; inject has_api_key and has_github_config bools.

    - gemini_api_key → nunca enviado; has_api_key: bool calculado a partir dele
    - github_token   → nunca enviado (T-11-02); has_github_config: bool calculado
    - github_repo    → nunca enviado como campo sensível; apenas afeta has_github_config
    """
    has_key = bool(row.get("gemini_api_key"))
    has_github_config = bool(row.get("github_token")) and bool(row.get("github_repo"))
    filtered = {k: v for k, v in row.items() if k not in ("gemini_api_key", "github_token")}
    return filtered | {"has_api_key": has_key, "has_github_config": has_github_config}


class ApiKeyUpdate(BaseModel):
    gemini_api_key: Optional[str] = None


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project. Returns the inserted row with its generated UUID."""
    client = get_client()
    payload = {"name": data.name, "client": data.client, "description": data.description, "squad": data.squad}
    if data.valor_projeto is not None:
        payload["valor_projeto"] = data.valor_projeto
        payload["valor_por_ponto"] = round(data.valor_projeto / 100, 2)
    if data.gemini_api_key:
        payload["gemini_api_key"] = data.gemini_api_key
    response = client.table("projects").insert(payload).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return _sanitize(response.data[0])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(pessoa: dict = Depends(get_current_pessoa)):
    """List projects ordered by creation date (most recent first).

    Operacional só vê os projetos em que está vinculado como operacional — sem
    isso, a home page expunha a existência (nome, cliente) de todo projeto do
    CITi a qualquer conta, mesmo projetos em que a pessoa nunca trabalhou."""
    client = get_client()
    response = client.table("projects").select("*").order("created_at", desc=True).execute()
    rows = response.data or []

    if pessoa["cargo"] == "operacional":
        vinculos = (
            client.table("operacionais")
            .select("project_id")
            .eq("email", pessoa["email"])
            .eq("ativo", True)
            .execute()
            .data or []
        )
        ids_permitidos = {v["project_id"] for v in vinculos}
        rows = [r for r in rows if r["id"] in ids_permitidos]

    projects = [_sanitize(row) for row in rows]

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


@router.get("/{project_id}", response_model=ProjectResponse, dependencies=[Depends(require_project_access)])
async def get_project(project_id: str):
    """Get a single project by UUID. Returns 404 if not found, 403 se o
    operacional não estiver vinculado a este projeto."""
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


@router.patch("/{project_id}/gerente-email", response_model=ProjectResponse)
async def update_gerente_email(project_id: str, data: GerenteEmailUpdate):
    """Atualiza ou limpa o email do gerente responsável pelo projeto."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    response = (
        client.table("projects")
        .update({"gerente_email": data.gerente_email or None})
        .eq("id", project_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update gerente email")
    return _sanitize(response.data[0])


@router.patch("/{project_id}/contrato", response_model=ProjectResponse)
async def update_contrato(project_id: str, data: ContratoUpdate):
    """Atualiza campos de contrato do projeto: datas, tolerancia, garantia e valor do projeto."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    campos = data.model_dump()
    valor_projeto = campos.pop("valor_projeto", None)
    payload = {k: v for k, v in campos.items() if v is not None}

    if valor_projeto is not None:
        sprints_com_orcamento = (
            client.table("sprints")
            .select("id")
            .eq("project_id", project_id)
            .not_.is_("pontos_orcamento", "null")
            .execute()
        ).data or []
        if sprints_com_orcamento:
            raise HTTPException(
                status_code=409,
                detail="Não é possível alterar o valor do projeto: já existe orçamento de pontos definido em pelo menos uma sprint.",
            )
        payload["valor_projeto"] = valor_projeto
        payload["valor_por_ponto"] = round(valor_projeto / 100, 2)

    if not payload:
        raise HTTPException(status_code=422, detail="Nenhum campo fornecido")
    for k, v in list(payload.items()):
        if hasattr(v, "isoformat"):
            payload[k] = v.isoformat()
    response = client.table("projects").update(payload).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update contract fields")
    return _sanitize(response.data[0])
