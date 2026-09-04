from fastapi import APIRouter, Depends, HTTPException, Response

from models.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    OperacionalSemContaResponse,
    SignupClaimRequest,
    SignupNovoRequest,
)
from services.auth import (
    COOKIE_NAME,
    criar_jwt,
    get_current_pessoa,
    hash_senha,
    verificar_senha,
)
from services.supabase_client import get_client

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, pessoa_id: str, email: str, cargo: str) -> None:
    token = criar_jwt(pessoa_id, email, cargo)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=8 * 3600,
    )


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, response: Response):
    client = get_client()
    resp = client.table("pessoa").select("*").eq("email", data.email).execute()
    if not resp.data:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    pessoa = resp.data[0]
    if not verificar_senha(data.senha, pessoa["senha_hash"]):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    _set_session_cookie(response, pessoa["id"], pessoa["email"], pessoa["cargo"])
    return {"nome": pessoa["nome"], "cargo": pessoa["cargo"]}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
async def me(pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    resp = client.table("pessoa").select("nome, email, cargo").eq("id", pessoa["id"]).execute()
    if not resp.data:
        raise HTTPException(status_code=401, detail="Sessão inválida")
    row = resp.data[0]
    return {"nome": row["nome"], "email": row["email"], "cargo": row["cargo"]}


@router.get("/operacionais-sem-conta", response_model=list[OperacionalSemContaResponse])
async def operacionais_sem_conta():
    client = get_client()
    ops = client.table("operacionais").select("id, nome, email, project_id").eq("ativo", True).execute().data or []
    pessoas = client.table("pessoa").select("email").execute().data or []
    emails_com_conta = {p["email"] for p in pessoas}
    projects = client.table("projects").select("id, name").execute().data or []
    nome_por_projeto = {p["id"]: p["name"] for p in projects}

    resultado = []
    for op in ops:
        if op.get("email") and op["email"] in emails_com_conta:
            continue
        resultado.append({
            "operacional_id": op["id"],
            "nome": op["nome"],
            "project_id": op["project_id"],
            "project_name": nome_por_projeto.get(op["project_id"], "—"),
        })
    return resultado


@router.post("/signup/claim", response_model=LoginResponse, status_code=201)
async def signup_claim(data: SignupClaimRequest, response: Response):
    client = get_client()
    op_resp = client.table("operacionais").select("*").eq("id", data.operacional_id).execute()
    if not op_resp.data:
        raise HTTPException(status_code=404, detail="Operacional não encontrado")
    operacional = op_resp.data[0]

    if operacional.get("email") and operacional["email"] != data.email:
        raise HTTPException(status_code=403, detail="Email não confere com o cadastro deste operacional")

    existing = client.table("pessoa").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este email")

    if not operacional.get("email"):
        client.table("operacionais").update({"email": data.email}).eq("id", data.operacional_id).execute()

    senha_hash = hash_senha(data.senha)
    novo = client.table("pessoa").insert({
        "email": data.email,
        "nome": operacional["nome"],
        "senha_hash": senha_hash,
        "cargo": "operacional",
    }).execute()
    pessoa = novo.data[0]
    _set_session_cookie(response, pessoa["id"], pessoa["email"], pessoa["cargo"])
    return {"nome": pessoa["nome"], "cargo": pessoa["cargo"]}


@router.post("/signup/novo", response_model=LoginResponse, status_code=201)
async def signup_novo(data: SignupNovoRequest, response: Response):
    client = get_client()
    existing = client.table("pessoa").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este email")

    senha_hash = hash_senha(data.senha)
    novo = client.table("pessoa").insert({
        "email": data.email,
        "nome": data.nome,
        "senha_hash": senha_hash,
        "cargo": "operacional",
    }).execute()
    pessoa = novo.data[0]
    _set_session_cookie(response, pessoa["id"], pessoa["email"], pessoa["cargo"])
    return {"nome": pessoa["nome"], "cargo": pessoa["cargo"]}
