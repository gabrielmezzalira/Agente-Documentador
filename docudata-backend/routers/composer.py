from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, field_validator

from services.supabase_client import get_client

router = APIRouter(prefix="/composer", tags=["composer"])

# ---------------------------------------------------------------------------
# Constante do sistema — prompt para geração do planning
# ---------------------------------------------------------------------------

_PLANNING_SYSTEM_PROMPT = """Você é um assistente especializado em documentação de projetos de dados do CITi.
Sua tarefa é gerar um documento de Planning em markdown, em português, de forma objetiva e estruturada.

O documento deve conter as seguintes seções:
1. **Objetivo da Sprint** — uma frase descrevendo o foco principal da sprint
2. **Funcionalidades Selecionadas** — lista das funcionalidades com os critérios de aceite recortados para esta sprint
3. **Responsabilidades** — quem é responsável por cada funcionalidade (se informado)
4. **Transbordos da Sprint Anterior** — funcionalidades que não foram concluídas na sprint anterior e entram nesta
5. **Throughput de Referência** — média de funcionalidades concluídas nas últimas 3 sprints (informação de contexto)

Retorne APENAS o markdown, sem texto antes ou depois, sem blocos de código, sem backticks."""


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


class GerarBody(BaseModel):
    project_id: str
    sprint_numero: int


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
    import traceback
    step = "init"
    try:
        client = get_client()

        step = "upsert_rascunho"
        (
            client.table("planning_rascunhos")
            .upsert(
                {
                    "project_id": project_id,
                    "sprint_numero": sprint_numero,
                    "step_atual": 1,
                    "dados_json": {},
                },
                on_conflict="project_id,sprint_numero",
                ignore_duplicates=True,
            )
            .execute()
        )

        step = "fetch_rascunho"
        fetch_resp = (
            client.table("planning_rascunhos")
            .select("*")
            .eq("project_id", project_id)
            .eq("sprint_numero", sprint_numero)
            .execute()
        )
        if not fetch_resp.data:
            raise HTTPException(status_code=500, detail="Falha ao criar/buscar rascunho")
        rascunho = fetch_resp.data[0]

        step = "throughput_ref"
        throughput_ref = calcular_throughput_ref(project_id, sprint_numero, client)

        step = "transbordos"
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Composer failed at step={step}: {type(e).__name__}: {str(e)[:500]}\n{traceback.format_exc()[:800]}",
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


# ---------------------------------------------------------------------------
# Helper: montar contexto de texto para o Gemini
# ---------------------------------------------------------------------------


def _montar_contexto_gerar(
    rascunho: dict,
    funcs_map: dict,
    projeto: dict,
    throughput_ref: Optional[float],
    transbordos: list[dict],
) -> str:
    """Monta o bloco de contexto que será enviado como HumanMessage ao Gemini."""
    dados: dict = rascunho.get("dados_json") or {}
    sprint_numero: int = rascunho.get("sprint_numero", 0)
    selecionadas: list[str] = dados.get("funcionalidades_selecionadas") or []
    recortes: dict = dados.get("recortes") or {}
    alocacoes: dict = dados.get("alocacoes") or {}
    transbordos_ids: list[str] = dados.get("transbordos") or []

    linhas: list[str] = [
        f"Projeto: {projeto.get('name', '')}",
        f"Cliente: {projeto.get('client', '')}",
        f"Sprint: {sprint_numero}",
        "",
    ]

    if throughput_ref is not None:
        linhas.append(
            f"Throughput de referência (últimas 3 sprints): {throughput_ref} funcionalidades/sprint"
        )
    else:
        linhas.append("Throughput de referência: sem dados disponíveis")
    linhas.append("")

    # Transbordos da sprint anterior
    if transbordos:
        linhas.append("## Transbordos da sprint anterior (não concluídos):")
        for t in transbordos:
            linhas.append(f"- {t.get('titulo', t.get('id', ''))}")
        linhas.append("")
    elif transbordos_ids:
        linhas.append("## Transbordos da sprint anterior:")
        for tid in transbordos_ids:
            func = funcs_map.get(tid)
            titulo = func.get("titulo", tid) if func else tid
            linhas.append(f"- {titulo}")
        linhas.append("")

    # Funcionalidades selecionadas com critérios recortados
    linhas.append("## Funcionalidades selecionadas para esta sprint:")
    for func_id in selecionadas:
        func = funcs_map.get(func_id)
        if not func:
            continue
        titulo = func.get("titulo", func_id)
        criterios: list[str] = func.get("criterios_aceite") or []
        indices = [i for i in (recortes.get(func_id) or []) if i < len(criterios)]
        responsavel = alocacoes.get(func_id, "")

        linhas.append(f"\n### {titulo}")
        if responsavel:
            linhas.append(f"Responsável: {responsavel}")
        if indices:
            linhas.append("Critérios de aceite para esta sprint:")
            for i in indices:
                linhas.append(f"  - {criterios[i]}")
        else:
            linhas.append("Critérios de aceite: (nenhum recorte especificado)")

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Endpoint: POST /gerar
# ---------------------------------------------------------------------------


@router.post("/gerar")
async def gerar_planning(body: GerarBody):
    """Gera o texto do planning via Gemini sem persistir.

    Retorna {"markdown": str}. A persistência ocorre somente em POST /confirmar.
    Conforme D-06: preview via react-markdown, confirmação explícita antes de oficializar.
    """
    client = get_client()

    # Buscar o rascunho (404 se não existe)
    rascunho_resp = (
        client.table("planning_rascunhos")
        .select("*")
        .eq("project_id", body.project_id)
        .eq("sprint_numero", body.sprint_numero)
        .execute()
    )
    if not rascunho_resp.data:
        raise HTTPException(
            status_code=404,
            detail=f"Rascunho não encontrado para projeto {body.project_id} sprint {body.sprint_numero}",
        )
    rascunho = rascunho_resp.data[0]

    # Buscar projeto para obter gemini_api_key (422 se ausente/vazia)
    proj_resp = (
        client.table("projects")
        .select("name, client, gemini_api_key")
        .eq("id", body.project_id)
        .execute()
    )
    if not proj_resp.data:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    projeto = proj_resp.data[0]
    api_key = (projeto.get("gemini_api_key") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="Este projeto não tem uma chave de API do Gemini configurada.",
        )

    # Buscar todas as funcionalidades do projeto
    funcs_resp = (
        client.table("funcionalidades")
        .select("*")
        .eq("project_id", body.project_id)
        .execute()
    )
    funcs_map: dict[str, dict] = {
        f["id"]: f for f in (funcs_resp.data or [])
    }

    # Calcular throughput_ref e transbordos para contexto
    throughput_ref = calcular_throughput_ref(body.project_id, body.sprint_numero, client)

    sprint_anterior = str(body.sprint_numero - 1)
    transbordos_resp = (
        client.table("funcionalidades")
        .select("id, titulo, sprint_alvo, status")
        .eq("project_id", body.project_id)
        .eq("sprint_alvo", sprint_anterior)
        .neq("status", "concluida")
        .execute()
    )
    transbordos = transbordos_resp.data or []

    # Montar contexto
    contexto = _montar_contexto_gerar(rascunho, funcs_map, projeto, throughput_ref, transbordos)

    # Chamar Gemini
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        max_tokens=2048,
        google_api_key=api_key,
    )
    try:
        result = await llm.ainvoke(
            [
                SystemMessage(content=_PLANNING_SYSTEM_PROMPT),
                HumanMessage(content=contexto),
            ]
        )
        markdown: str = result.content  # type: ignore[assignment]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini failed: {exc}")

    # NÃO persistir — retornar apenas o markdown (D-06)
    return {"markdown": markdown}
