from fastapi import APIRouter, Query
from pydantic import BaseModel
from services.supabase_client import get_client

router = APIRouter(tags=["search"])


class ProjectSearchResult(BaseModel):
    project_id: str
    project_name: str
    client: str
    sprints: list[int]
    sample_context: str


class SearchResponse(BaseModel):
    query: str
    results: list[ProjectSearchResult]


@router.get("/search", response_model=SearchResponse)
async def search_stack(q: str = Query(..., min_length=1)):
    """Search all projects for a given technology/stack mentioned in any ingestion."""
    client = get_client()

    ing_resp = (
        client.table("ingestions")
        .select("project_id, sprint_number, extracted_content")
        .execute()
    )

    query_lower = q.strip().lower()
    project_sprints: dict[str, set[int]] = {}
    project_sample: dict[str, str] = {}

    for ing in (ing_resp.data or []):
        content = ing.get("extracted_content") or {}
        techs = [t.lower() for t in (content.get("tecnologias") or [])]
        if any(query_lower in t for t in techs):
            pid = ing["project_id"]
            sprint = ing.get("sprint_number", 0)
            if pid not in project_sprints:
                project_sprints[pid] = set()
                project_sample[pid] = content.get("resumo", "")
            project_sprints[pid].add(sprint)

    if not project_sprints:
        return SearchResponse(query=q, results=[])

    proj_resp = (
        client.table("projects")
        .select("id, name, client")
        .in_("id", list(project_sprints.keys()))
        .execute()
    )

    results = [
        ProjectSearchResult(
            project_id=proj["id"],
            project_name=proj["name"],
            client=proj["client"],
            sprints=sorted(project_sprints[proj["id"]]),
            sample_context=project_sample.get(proj["id"], ""),
        )
        for proj in (proj_resp.data or [])
    ]

    return SearchResponse(query=q, results=results)
