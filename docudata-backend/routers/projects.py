from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal
from models.schemas import (
    ProjectCreate,
    ProjectResponse,
    TechTimelineResponse,
    ContratoUpdate,
    GerenteEmailUpdate,
    ProjectSubareaUpdate,
    ModosProjetoUpdate,
    ConfiguracaoHistoricoResponse,
    WipConfigUpdate,
)
from core.observability import falha_externa
from services.auth import get_current_pessoa, require_not_operacional, require_project_access
from services.supabase_client import get_client
from services.tech_timeline import build_tech_timeline
from services.hidratacao import calcular_hidratacao

router = APIRouter(prefix="/projects", tags=["projects"])

# Projeção explícita das leituras que devolvem ProjectResponse. Cobre todos os
# campos do response model mais `github_token`/`github_repo`, usados só para
# derivar `has_github_config`. Deixa de fora `gemini_api_key`: era um segredo
# legado por projeto que vinha do banco a cada listagem só para ser descartado
# depois por _sanitize.
_CAMPOS_PROJETO = (
    "id, name, client, subarea, description, squad, valor_projeto, valor_por_ponto, "
    "is_delivered, created_at, data_inicio, data_fim_contratada, "
    "tolerancia_desvio_pontos, periodo_garantia_dias, gerente_email, arquetipo, "
    "github_token, github_repo, "
    "modo_trabalho, modo_avaliacao, pull_exigir_hidratacao, pull_piso_pontos, pull_teto, wip_config"
)


def _sanitize(row: dict) -> dict:
    """Remove segredos legados e mantém apenas o status da integração de aceite."""
    has_github_config = bool(row.get("github_token")) and bool(row.get("github_repo"))
    filtered = {k: v for k, v in row.items() if k not in ("gemini_api_key", "github_token")}
    return filtered | {"has_github_config": has_github_config}


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project. Returns the inserted row with its generated UUID."""
    client = get_client()
    payload = {
        "name": data.name,
        "client": data.client,
        "subarea": data.subarea,
        "description": data.description,
        "squad": data.squad,
    }
    if data.valor_projeto is not None:
        payload["valor_projeto"] = data.valor_projeto
        payload["valor_por_ponto"] = round(data.valor_projeto / 100, 2)
    response = client.table("projects").insert(payload).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return _sanitize(response.data[0])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    subarea: Literal["dados", "dev"] = Query(...),
    pessoa: dict = Depends(get_current_pessoa),
):
    """List projects ordered by creation date (most recent first).

    Operacional só vê os projetos em que está vinculado como operacional — sem
    isso, a home page expunha a existência (nome, cliente) de todo projeto do
    CITi a qualquer conta, mesmo projetos em que a pessoa nunca trabalhou."""
    client = get_client()
    response = (
        client.table("projects")
        .select(_CAMPOS_PROJETO)
        .eq("subarea", subarea)
        .order("created_at", desc=True)
        .execute()
    )
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
        # Só os IDs que já vão ser devolvidos. Antes a consulta varria a tabela
        # inteira de ingestões — todo projeto do CITi, das duas subáreas,
        # inclusive os que o operacional não pode ver — para preencher uma
        # data de cada projeto da página.
        ids_da_pagina = [p["id"] for p in projects]
        ing_resp = (
            client.table("ingestions")
            .select("project_id, created_at")
            .in_("project_id", ids_da_pagina)
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
    response = client.table("projects").select(_CAMPOS_PROJETO).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Project not found")
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


@router.patch("/{project_id}/subarea", response_model=ProjectResponse)
async def update_project_subarea(
    project_id: str,
    data: ProjectSubareaUpdate,
    _pessoa: dict = Depends(require_not_operacional),
):
    """Move o projeto entre Dados e Dev sem alterar seus registros relacionados."""
    client = get_client()
    check = client.table("projects").select("id, subarea").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    if check.data[0].get("subarea") == data.subarea:
        response = client.table("projects").select(_CAMPOS_PROJETO).eq("id", project_id).execute()
    else:
        # Todos os vínculos usam project_id; só a classificação do projeto deve mudar.
        response = (
            client.table("projects")
            .update({"subarea": data.subarea})
            .eq("id", project_id)
            .execute()
        )
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update project subarea")
    return _sanitize(response.data[0])


@router.patch("/{project_id}/contrato", response_model=ProjectResponse)
async def update_contrato(project_id: str, data: ContratoUpdate):
    """Atualiza campos de contrato do projeto: datas, tolerancia, garantia e valor do projeto."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    campos = data.model_dump()
    valor_projeto_novo = campos.pop("valor_projeto", None)
    payload = {k: v for k, v in campos.items() if v is not None}

    try:
        if valor_projeto_novo is not None:
            valor_projeto_ja_salvo = (
                client.table("projects").select("valor_projeto").eq("id", project_id).execute()
            ).data[0].get("valor_projeto")
            # Reenviar o mesmo valor que já estava salvo (form completo, sem
            # mudança de fato nesse campo) não deve travar mesmo com sprint já
            # orçada — a trava é só contra MUDAR o valor depois do orçamento
            # existir, não contra resalvar o formulário inteiro sem tocar nele.
            if valor_projeto_novo != valor_projeto_ja_salvo:
                sprints_do_projeto = (
                    client.table("sprints")
                    .select("id, pontos_orcamento")
                    .eq("project_id", project_id)
                    .execute()
                ).data or []
                tem_orcamento = any(s.get("pontos_orcamento") is not None for s in sprints_do_projeto)
                if tem_orcamento:
                    raise HTTPException(
                        status_code=409,
                        detail="Não é possível alterar o valor do projeto: já existe orçamento de pontos definido em pelo menos uma sprint.",
                    )
                payload["valor_projeto"] = valor_projeto_novo
                payload["valor_por_ponto"] = round(valor_projeto_novo / 100, 2)

        if not payload:
            raise HTTPException(status_code=422, detail="Nenhum campo fornecido")
        for k, v in list(payload.items()):
            if hasattr(v, "isoformat"):
                payload[k] = v.isoformat()
        response = client.table("projects").update(payload).eq("id", project_id).execute()
    except HTTPException:
        raise
    except Exception as exc:
        # Sem isso, qualquer erro daqui vira "Internal Server Error" puro, sem
        # cabeçalho de CORS (o middleware nunca chega a rodar numa exceção não
        # tratada) — o navegador mostra como bloqueio de CORS, escondendo o
        # erro real. Levantar como HTTPException garante resposta formada.
        raise falha_externa(
            "supabase.projects.contrato", exc, "Não foi possível salvar o contrato", status_code=500
        )

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update contract fields")
    return _sanitize(response.data[0])


@router.patch("/{project_id}/modos", response_model=ProjectResponse)
async def update_modos(
    project_id: str,
    data: ModosProjetoUpdate,
    pessoa: dict = Depends(require_not_operacional),
):
    """RF-A1..A4/A6: troca modo de trabalho e/ou modo de avaliação do
    projeto, com parâmetros de PULL. Toda mudança de modo_trabalho ou
    modo_avaliacao grava um registro imutável em configuracao_historico."""
    client = get_client()
    atual_resp = client.table("projects").select(
        "modo_trabalho, modo_avaliacao"
    ).eq("id", project_id).execute()
    if not atual_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    atual = atual_resp.data[0]

    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        response = client.table("projects").select(_CAMPOS_PROJETO).eq("id", project_id).execute()
        return _sanitize(response.data[0])

    for campo in ("modo_trabalho", "modo_avaliacao"):
        novo = payload.get(campo)
        if novo is not None and novo != atual.get(campo):
            client.table("configuracao_historico").insert({
                "project_id": project_id,
                "campo": campo,
                "valor_anterior": atual.get(campo),
                "valor_novo": novo,
                "usuario_email": pessoa["email"],
            }).execute()

    response = client.table("projects").update(payload).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update project modos")

    # RF-A5: entrar em PULL força WIP por pessoa = 1, mesmo que o gerente não
    # tenha mexido no campo agora — sem isso um projeto migrado ficaria em
    # modo pull com WIP de atribuição, incoerente com a regra do modo.
    if payload.get("modo_trabalho") == "PULL":
        wip_atual = response.data[0].get("wip_config") or {}
        novo_wip = {**wip_atual, "por_pessoa": 1}
        response = client.table("projects").update({"wip_config": novo_wip}).eq("id", project_id).execute()

    return _sanitize(response.data[0])


@router.get("/{project_id}/modos-historico", response_model=list[ConfiguracaoHistoricoResponse])
async def get_modos_historico(project_id: str, _pessoa: dict = Depends(require_not_operacional)):
    client = get_client()
    resp = (
        client.table("configuracao_historico")
        .select("*")
        .eq("project_id", project_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return resp.data or []


@router.patch("/{project_id}/wip-config", response_model=ProjectResponse)
async def update_wip_config(
    project_id: str,
    data: WipConfigUpdate,
    _pessoa: dict = Depends(require_not_operacional),
):
    """Atualiza projects.wip_config. Em projeto PULL, por_pessoa é sempre
    forçado a 1 no servidor (RF-A5) — o valor que o cliente mandar para esse
    campo é ignorado nesse modo, nunca confiado."""
    client = get_client()
    check = client.table("projects").select("modo_trabalho, wip_config").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    projeto = check.data[0]

    wip_atual = projeto.get("wip_config") or {}
    novo_wip = dict(wip_atual)
    if data.por_coluna_em_andamento is not None:
        novo_wip["por_coluna_em_andamento"] = data.por_coluna_em_andamento
    if data.por_pessoa is not None:
        novo_wip["por_pessoa"] = data.por_pessoa
    if projeto.get("modo_trabalho") == "PULL":
        novo_wip["por_pessoa"] = 1

    response = client.table("projects").update({"wip_config": novo_wip}).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update wip_config")
    return _sanitize(response.data[0])


@router.get("/{project_id}/migrar-modo/preview")
async def preview_migrar_modo(
    project_id: str,
    para: str = Query(...),
    _pessoa: dict = Depends(require_not_operacional),
):
    """RF-M1/M2 (Entrega 3): dry-run — conta quantas tasks cairiam em cada
    categoria se a migração fosse aplicada agora, sem gravar nada."""
    if para not in ("ATRIBUICAO", "PULL"):
        raise HTTPException(status_code=422, detail="para deve ser ATRIBUICAO ou PULL")
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = client.table("tasks").select("id, coluna_kanban, operacional_id, titulo, pontos, descricao, checklist, bloqueado").eq("project_id", project_id).execute().data or []

    contagem = {"entrando_na_fila": 0, "vira_rascunho": 0, "mantem_responsavel": 0, "sem_alteracao": 0}
    for task in tasks:
        coluna = task.get("coluna_kanban")
        # "Bloqueada" no spec original é um estado lógico (RF-M2), mas neste
        # schema bloqueio é o booleano tasks.bloqueado, ortogonal à coluna —
        # checa primeiro, antes de dispachar por coluna, e nunca reclassifica
        # (mantém responsável e estado de bloqueio, igual o spec pede).
        if task.get("bloqueado"):
            contagem["mantem_responsavel"] += 1
        elif coluna == "concluida":
            contagem["sem_alteracao"] += 1
        elif coluna == "planejado":
            if para == "PULL":
                rascunho, _ = calcular_hidratacao(task)
                if rascunho:
                    contagem["vira_rascunho"] += 1
                else:
                    contagem["entrando_na_fila"] += 1
            else:
                contagem["sem_alteracao"] += 1
        elif coluna == "em_andamento":
            contagem["mantem_responsavel"] += 1
        else:
            contagem["sem_alteracao"] += 1

    return contagem
