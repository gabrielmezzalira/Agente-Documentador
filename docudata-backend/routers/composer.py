from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.supabase_client import get_client

router = APIRouter(prefix="/composer", tags=["composer"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class RascunhoResponse(BaseModel):
    rascunho: dict
    throughput_ref: Optional[float]
    transbordos: list[dict]


class PatchRascunhoBody(BaseModel):
    step_atual: int
    dados_json: dict


class ConfirmarBody(BaseModel):
    project_id: str
    sprint_numero: int
    markdown: str

    @field_validator("markdown")
    @classmethod
    def markdown_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("markdown não pode ser vazio")
        return v


# ---------------------------------------------------------------------------
# Helper: calcular throughput de referência (últimas 3 sprints)
# ---------------------------------------------------------------------------


def calcular_throughput_ref(
    project_id: str, sprint_numero: int, client
) -> Optional[float]:
    """Throughput médio das últimas 3 sprints anteriores (N-1, N-2, N-3).

    Retorna funcionalidades concluídas / número de sprints de referência,
    ou None se não houver dados. Unidade: funcionalidades/sprint.

    ATENÇÃO: sprint_alvo é texto no banco — comparar sempre com str(N), nunca com int.
    """
    sprints_ref = [sprint_numero - 1, sprint_numero - 2, sprint_numero - 3]
    sprints_ref = [s for s in sprints_ref if s > 0]
    if not sprints_ref:
        return None

    funcs_resp = (
        client.table("funcionalidades")
        .select("id")
        .eq("project_id", project_id)
        .in_("sprint_alvo", [str(s) for s in sprints_ref])
        .eq("status", "concluida")
        .execute()
    )
    funcs = funcs_resp.data or []
    if not funcs:
        return None

    return round(len(funcs) / len(sprints_ref), 1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/rascunho/{project_id}/{sprint_numero}", response_model=RascunhoResponse)
async def get_rascunho(project_id: str, sprint_numero: int):
    """Retorna o rascunho da sprint (criando-o via upsert se não existir).

    Também retorna throughput_ref (últimas 3 sprints) e lista de transbordos
    (funcionalidades com sprint_alvo == N-1 e status != concluida).
    """
    client = get_client()

    # Upsert: cria o rascunho se não existir; retorna o existente se já houver.
    upsert_resp = (
        client.table("planning_rascunhos")
        .upsert(
            {
                "project_id": project_id,
                "sprint_numero": sprint_numero,
                "step_atual": 1,
                "dados_json": {},
            },
            on_conflict="project_id,sprint_numero",
        )
        .execute()
    )
    if not upsert_resp.data:
        raise HTTPException(status_code=500, detail="Falha ao criar/buscar rascunho")
    rascunho = upsert_resp.data[0]

    # Throughput de referência (funcionalidades/sprint das últimas 3 sprints)
    throughput_ref = calcular_throughput_ref(project_id, sprint_numero, client)

    # Transbordos: funcionalidades da sprint anterior (N-1) não concluídas.
    # ATENÇÃO: sprint_alvo é str no banco — comparar com str(sprint_numero - 1).
    sprint_anterior = str(sprint_numero - 1)
    transbordos_resp = (
        client.table("funcionalidades")
        .select("id, titulo, sprint_alvo, status, criterios_aceite")
        .eq("project_id", project_id)
        .eq("sprint_alvo", sprint_anterior)
        .neq("status", "concluida")
        .execute()
    )
    transbordos = transbordos_resp.data or []

    return RascunhoResponse(
        rascunho=rascunho,
        throughput_ref=throughput_ref,
        transbordos=transbordos,
    )


@router.patch("/rascunho/{project_id}/{sprint_numero}")
async def patch_rascunho(
    project_id: str, sprint_numero: int, body: PatchRascunhoBody
):
    """Atualiza step_atual e dados_json do rascunho.

    Retorna 404 se o rascunho não existir (o frontend deve chamar GET antes de PATCH).
    """
    client = get_client()

    # Verificar que o rascunho existe antes de atualizar.
    check_resp = (
        client.table("planning_rascunhos")
        .select("id")
        .eq("project_id", project_id)
        .eq("sprint_numero", sprint_numero)
        .execute()
    )
    if not check_resp.data:
        raise HTTPException(
            status_code=404,
            detail=f"Rascunho não encontrado para projeto {project_id} sprint {sprint_numero}",
        )

    update_resp = (
        client.table("planning_rascunhos")
        .update(
            {
                "step_atual": body.step_atual,
                "dados_json": body.dados_json,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("project_id", project_id)
        .eq("sprint_numero", sprint_numero)
        .execute()
    )
    if not update_resp.data:
        raise HTTPException(status_code=500, detail="Falha ao atualizar rascunho")

    return update_resp.data[0]


@router.post("/confirmar", status_code=201)
async def confirmar_planning(body: ConfirmarBody):
    """Oficializa o planning: insere em generated_docs e deleta o rascunho.

    ORDEM OBRIGATÓRIA (D-07 / Pitfall 3):
      1. INSERT em generated_docs
      2. Se sucesso: DELETE do rascunho
    Se o insert falhar, o rascunho é preservado.
    """
    client = get_client()

    # Verificar que o rascunho existe (Pitfall 2).
    rascunho_resp = (
        client.table("planning_rascunhos")
        .select("id")
        .eq("project_id", body.project_id)
        .eq("sprint_numero", body.sprint_numero)
        .execute()
    )
    if not rascunho_resp.data:
        raise HTTPException(
            status_code=404,
            detail=f"Rascunho não encontrado para projeto {body.project_id} sprint {body.sprint_numero}",
        )

    # 1. INSERT em generated_docs PRIMEIRO (D-07).
    insert_resp = (
        client.table("generated_docs")
        .insert(
            {
                "project_id": body.project_id,
                "doc_type": "planning",
                "sprint_number": body.sprint_numero,
                "content": body.markdown,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0,
            }
        )
        .execute()
    )
    if not insert_resp.data:
        # Insert falhou — NÃO deletar o rascunho.
        raise HTTPException(
            status_code=500, detail="Falha ao salvar o documento de planning"
        )

    doc = insert_resp.data[0]

    # 2. DELETE do rascunho SOMENTE após insert bem-sucedido (D-07).
    client.table("planning_rascunhos").delete().eq(
        "project_id", body.project_id
    ).eq("sprint_numero", body.sprint_numero).execute()

    return {
        "doc_id": doc["id"],
        "content": doc["content"],
        "created_at": doc["created_at"],
    }
