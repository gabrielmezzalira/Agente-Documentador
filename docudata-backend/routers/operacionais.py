from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    OperacionalCreate,
    OperacionalDisponivelResponse,
    OperacionalUpdate,
    OperacionalResponse,
)
from services.supabase_client import get_client

router = APIRouter(prefix="/operacionais", tags=["operacionais"])


@router.post("", response_model=OperacionalResponse, status_code=201)
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
        .select("nome, email, papel, github_login, project_id")
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
            "projetos": [],
        })
        # Preenche lacunas com o cadastro mais completo encontrado.
        for campo in ("email", "papel", "github_login"):
            if not entrada.get(campo) and o.get(campo):
                entrada[campo] = o[campo]
        nome_projeto = projetos.get(o["project_id"])
        if nome_projeto and nome_projeto not in entrada["projetos"]:
            entrada["projetos"].append(nome_projeto)

    return sorted(por_chave.values(), key=lambda e: e["nome"].lower())


@router.patch("/{operacional_id}", response_model=OperacionalResponse)
async def update_operacional(operacional_id: str, data: OperacionalUpdate):
    client = get_client()
    check = client.table("operacionais").select("id").eq("id", operacional_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    updates: dict = {}
    for field in ("nome", "email", "papel", "ativo", "github_login"):
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

    client.table("tasks").update({"operacional_id": None}).eq("operacional_id", operacional_id).execute()
    client.table("operacionais").delete().eq("id", operacional_id).execute()
