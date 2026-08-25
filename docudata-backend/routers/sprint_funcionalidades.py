"""Sprint Funcionalidades — vincula funcionalidades a sprints com tasks e status de conclusão."""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase_client import get_client

router = APIRouter(prefix="/sprint-funcionalidades", tags=["sprint-funcionalidades"])


class TaskItem(BaseModel):
    texto: str
    responsavel: str = ""


class Correlacao(BaseModel):
    funcionalidade_id: Optional[str] = None
    tasks: list[TaskItem] = []


class BatchCreate(BaseModel):
    sprint_id: str
    correlacoes: list[Correlacao]


class SprintFuncionalidadeUpdate(BaseModel):
    status: Optional[str] = None
    tasks: Optional[list[dict]] = None


@router.post("")
def create_sprint_funcionalidades(data: BatchCreate):
    """Cria ou atualiza sprint_funcionalidades a partir das correlações confirmadas pelo gerente.

    Atualiza funcionalidades.status para em_andamento se ainda estavam como nao_iniciada.
    """
    client = get_client()

    sprint_resp = client.table("sprints").select("id, project_id, numero").eq("id", data.sprint_id).execute()
    if not sprint_resp.data:
        raise HTTPException(status_code=404, detail="Sprint não encontrada")

    results = []
    func_ids_to_update: list[str] = []

    for corr in data.correlacoes:
        func_id = corr.funcionalidade_id
        if not func_id:
            continue

        tasks_payload = [t.model_dump() for t in corr.tasks]

        try:
            resp = client.table("sprint_funcionalidades").upsert(
                {
                    "sprint_id": data.sprint_id,
                    "funcionalidade_id": func_id,
                    "tasks": tasks_payload,
                    "status": "em_andamento",
                },
                on_conflict="sprint_id,funcionalidade_id",
            ).execute()
            results.extend(resp.data or [])
            func_ids_to_update.append(func_id)
        except Exception as exc:
            print(f"[sprint_funcionalidades] Erro ao upsert func {func_id}: {exc}")

    # Promove funcionalidades de nao_iniciada → em_andamento
    for func_id in func_ids_to_update:
        try:
            func_resp = client.table("funcionalidades").select("status").eq("id", func_id).execute()
            if func_resp.data and func_resp.data[0]["status"] == "nao_iniciada":
                client.table("funcionalidades").update({"status": "em_andamento"}).eq("id", func_id).execute()
        except Exception as exc:
            print(f"[sprint_funcionalidades] Erro ao atualizar status func {func_id}: {exc}")

    return {"created": len(results), "sprint_funcionalidades": results}


@router.get("/sprint/{sprint_id}")
def get_sprint_funcionalidades(sprint_id: str):
    """Lista sprint_funcionalidades de uma sprint com dados da funcionalidade."""
    client = get_client()
    resp = client.table("sprint_funcionalidades").select(
        "*, funcionalidades(id, id_funcional, titulo, status, prioridade)"
    ).eq("sprint_id", sprint_id).execute()
    return resp.data or []


@router.patch("/{sf_id}")
def update_sprint_funcionalidade(sf_id: str, data: SprintFuncionalidadeUpdate):
    """Atualiza status ou tasks de uma sprint_funcionalidade.

    Se status = concluida, propaga para funcionalidades.status.
    """
    client = get_client()

    updates: dict[str, Any] = {}
    if data.status is not None:
        if data.status not in ("em_andamento", "concluida"):
            raise HTTPException(status_code=422, detail="Status inválido. Use: em_andamento | concluida")
        updates["status"] = data.status
    if data.tasks is not None:
        updates["tasks"] = data.tasks

    if not updates:
        raise HTTPException(status_code=422, detail="Nenhum campo para atualizar")

    resp = client.table("sprint_funcionalidades").update(updates).eq("id", sf_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="sprint_funcionalidade não encontrada")

    sf = resp.data[0]

    if data.status == "concluida":
        func_id = sf.get("funcionalidade_id")
        if func_id:
            try:
                client.table("funcionalidades").update({"status": "concluida"}).eq("id", func_id).execute()
            except Exception as exc:
                print(f"[sprint_funcionalidades] Erro ao concluir funcionalidade {func_id}: {exc}")

    return sf


@router.get("/recomendadas/{project_id}")
def get_funcionalidades_recomendadas(project_id: str):
    """Retorna funcionalidades em_andamento do projeto para sugestão na próxima planning."""
    client = get_client()
    resp = (
        client.table("funcionalidades")
        .select("id, id_funcional, titulo, status, sprint_alvo")
        .eq("project_id", project_id)
        .eq("status", "em_andamento")
        .execute()
    )
    return resp.data or []
