from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import (
    OperacionalCreate,
    OperacionalDisponivelResponse,
    OperacionalUpdate,
    OperacionalResponse,
)
from core.observability import falha_externa
from services.auth import require_not_operacional
from services.supabase_client import get_client

router = APIRouter(prefix="/operacionais", tags=["operacionais"])


@router.post("", response_model=OperacionalResponse, status_code=201, dependencies=[Depends(require_not_operacional)])
async def create_operacional(data: OperacionalCreate):
    client = get_client()
    check = client.table("projects").select("id").eq("id", data.project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    nome_normalizado = data.nome.strip().lower()
    existentes = (
        client.table("operacionais")
        .select("nome")
        .eq("project_id", data.project_id)
        .execute()
        .data or []
    )
    if any(e["nome"].strip().lower() == nome_normalizado for e in existentes):
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um operacional com o nome '{data.nome}' neste projeto",
        )

    payload = {
        "project_id": data.project_id,
        "nome": data.nome,
    }
    if data.email is not None:
        payload["email"] = data.email
    if data.papel is not None:
        payload["papel"] = data.papel
    if data.github_login is not None:
        payload["github_login"] = data.github_login
    if data.github_email is not None:
        payload["github_email"] = data.github_email
    if (data.github_login is None or data.github_email is None) and data.email:
        # A pessoa pode ter informado usuário/email do GitHub no próprio
        # cadastro, antes de existir qualquer vínculo com projeto. Pré-preenche
        # daqui em vez de exigir que o gerente redigite o que ela já disse.
        pessoa_resp = (
            client.table("pessoa").select("github_login, github_email").eq("email", data.email).execute()
        )
        if pessoa_resp.data:
            pessoa_row = pessoa_resp.data[0]
            if data.github_login is None and pessoa_row.get("github_login"):
                payload["github_login"] = pessoa_row["github_login"]
            if data.github_email is None and pessoa_row.get("github_email"):
                payload["github_email"] = pessoa_row["github_email"]

    try:
        resp = client.table("operacionais").insert(payload).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail=f"Já existe um operacional com o nome '{data.nome}' neste projeto",
            )
        raise falha_externa(
            "supabase.operacionais.insert", exc, "Não foi possível criar o operacional", status_code=500
        )

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


@router.get("/disponiveis/{project_id}", response_model=list[OperacionalDisponivelResponse])
async def listar_operacionais_disponiveis(project_id: str):
    """Pessoas já cadastradas em outros projetos, para vincular a este sem
    redigitar. Redigitar é o que hoje cria a mesma pessoa com e-mail divergente
    e a parte em duas no ranking — o ranking casa identidade pelo e-mail.

    Agrupa por e-mail (identidade real); quem não tem e-mail é agrupado pelo
    nome normalizado, que é o melhor que dá pra fazer sem identificador."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    todos = (
        client.table("operacionais")
        .select("nome, email, papel, github_login, github_email, project_id")
        .eq("ativo", True)
        .execute()
        .data or []
    )

    chaves_do_projeto = {
        (o.get("email") or "").strip().lower() or o["nome"].strip().lower()
        for o in todos
        if o["project_id"] == project_id
    }

    projetos = {
        p["id"]: p["name"]
        for p in (client.table("projects").select("id, name").execute().data or [])
    }

    por_chave: dict[str, dict] = {}
    for o in todos:
        if o["project_id"] == project_id:
            continue
        chave = (o.get("email") or "").strip().lower() or o["nome"].strip().lower()
        if chave in chaves_do_projeto:
            continue
        entrada = por_chave.setdefault(chave, {
            "nome": o["nome"],
            "email": o.get("email"),
            "papel": o.get("papel"),
            "github_login": o.get("github_login"),
            "github_email": o.get("github_email"),
            "projetos": [],
        })
        # Preenche lacunas com o cadastro mais completo encontrado.
        for campo in ("email", "papel", "github_login", "github_email"):
            if not entrada.get(campo) and o.get(campo):
                entrada[campo] = o[campo]
        nome_projeto = projetos.get(o["project_id"])
        if nome_projeto and nome_projeto not in entrada["projetos"]:
            entrada["projetos"].append(nome_projeto)

    # Gente que só passou pelo cadastro (cargo=operacional em `pessoa`) e nunca
    # foi vinculada a projeto nenhum ainda não tem linha em `operacionais` —
    # sem isso, ela nunca aparecia aqui, mesmo já tendo conta no sistema.
    pessoas_op = (
        client.table("pessoa")
        .select("nome, email, github_login, github_email")
        .eq("cargo", "operacional")
        .execute()
        .data or []
    )
    for p in pessoas_op:
        chave = (p.get("email") or "").strip().lower() or p["nome"].strip().lower()
        if not chave or chave in chaves_do_projeto or chave in por_chave:
            continue
        por_chave[chave] = {
            "nome": p["nome"],
            "email": p.get("email"),
            "papel": None,
            "github_login": p.get("github_login"),
            "github_email": p.get("github_email"),
            "projetos": [],
        }

    return sorted(por_chave.values(), key=lambda e: e["nome"].lower())


@router.patch("/{operacional_id}", response_model=OperacionalResponse, dependencies=[Depends(require_not_operacional)])
async def update_operacional(operacional_id: str, data: OperacionalUpdate):
    client = get_client()
    check = client.table("operacionais").select("id").eq("id", operacional_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    updates: dict = {}
    for field in ("nome", "email", "papel", "ativo", "github_login", "github_email"):
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
        raise falha_externa(
            "supabase.operacionais.update", exc, "Não foi possível atualizar o operacional", status_code=500
        )

    return resp.data[0]


@router.post("/{operacional_id}/remover-do-projeto", response_model=OperacionalResponse, dependencies=[Depends(require_not_operacional)])
async def remover_do_projeto(operacional_id: str):
    """Tira a pessoa do projeto sem apagar nada.

    É o caminho certo quando alguém troca de projeto no meio da execução: a
    pontuação já travada continua valendo e o histórico dela segue contando no
    acompanhamento. A pessoa some do Kanban e das avaliações, e as tasks que
    ainda estavam com ela ficam sem responsável para o gerente redistribuir.

    Para apagar de fato, use DELETE, que é irreversível."""
    client = get_client()
    check = client.table("operacionais").select("id").eq("id", operacional_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    (
        client.table("tasks")
        .update({"operacional_id": None})
        .eq("operacional_id", operacional_id)
        .neq("coluna_kanban", "concluida")
        .execute()
    )
    resp = client.table("operacionais").update({"ativo": False}).eq("id", operacional_id).execute()
    return resp.data[0]


@router.delete("/{operacional_id}", status_code=204, dependencies=[Depends(require_not_operacional)])
async def delete_operacional(operacional_id: str):
    """Apaga a pessoa e, por cascata do banco, toda a pontuação travada dela.

    Irreversível e quase sempre a escolha errada para quem só saiu do projeto:
    para esse caso existe POST /operacionais/{id}/remover-do-projeto, que
    preserva o histórico."""
    client = get_client()
    check = client.table("operacionais").select("id").eq("id", operacional_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    client.table("tasks").update({"operacional_id": None}).eq("operacional_id", operacional_id).execute()
    client.table("operacionais").delete().eq("id", operacional_id).execute()
