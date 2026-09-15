import os

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from core.rate_limit import LOGIN_RATE_LIMIT, SIGNUP_RATE_LIMIT, limiter
from models.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    OperacionalSemContaResponse,
    ResetPasswordRequest,
    SignupClaimRequest,
    SignupNovoRequest,
)
from services.auth import (
    COOKIE_NAME,
    criar_jwt,
    criar_jwt_reset_senha,
    decodificar_jwt_reset_senha,
    get_current_pessoa,
    hash_senha,
    verificar_senha,
)
from services.email_service import email_esqueci_senha, send_email
from services.supabase_client import get_client

router = APIRouter(prefix="/auth", tags=["auth"])

# O limite é por IP e conta tentativas antes de qualquer consulta ao banco: o
# 429 sai igual para e-mail existente e inexistente, então não vira oráculo de
# enumeração de contas.


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
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(request: Request, data: LoginRequest, response: Response):
    client = get_client()
    # senha_hash entra só para a verificação local; `select("*")` trazia junto
    # todo o resto da linha da pessoa para uma resposta de dois campos.
    resp = (
        client.table("pessoa")
        .select("id, nome, email, cargo, senha_hash")
        .eq("email", data.email)
        .execute()
    )
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
@limiter.limit(SIGNUP_RATE_LIMIT)
async def signup_claim(request: Request, data: SignupClaimRequest, response: Response):
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
    if data.github_login and not operacional.get("github_login"):
        client.table("operacionais").update({"github_login": data.github_login}).eq("id", data.operacional_id).execute()
    if data.github_email and not operacional.get("github_email"):
        client.table("operacionais").update({"github_email": data.github_email}).eq("id", data.operacional_id).execute()

    senha_hash = hash_senha(data.senha)
    novo = client.table("pessoa").insert({
        "email": data.email,
        "nome": operacional["nome"],
        "senha_hash": senha_hash,
        "cargo": "operacional",
        "github_login": data.github_login,
        "github_email": data.github_email,
    }).execute()
    pessoa = novo.data[0]
    _set_session_cookie(response, pessoa["id"], pessoa["email"], pessoa["cargo"])
    return {"nome": pessoa["nome"], "cargo": pessoa["cargo"]}


@router.post("/signup/novo", response_model=LoginResponse, status_code=201)
@limiter.limit(SIGNUP_RATE_LIMIT)
async def signup_novo(request: Request, data: SignupNovoRequest, response: Response):
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
        "github_login": data.github_login,
        "github_email": data.github_email,
    }).execute()
    pessoa = novo.data[0]
    _set_session_cookie(response, pessoa["id"], pessoa["email"], pessoa["cargo"])
    return {"nome": pessoa["nome"], "cargo": pessoa["cargo"]}


_MENSAGEM_FORGOT_PASSWORD = {"message": "Se o e-mail existir, você vai receber um link em instantes."}


@router.post("/forgot-password")
@limiter.limit(SIGNUP_RATE_LIMIT)
async def forgot_password(request: Request, data: ForgotPasswordRequest, response: Response):
    """Resposta idêntica exista ou não a conta (anti-enumeração) — o e-mail só
    é disparado quando a conta existe, mas o chamador nunca sabe qual caso
    ocorreu pela resposta."""
    client = get_client()
    resp = client.table("pessoa").select("id, nome, email").eq("email", data.email).execute()
    if resp.data:
        pessoa = resp.data[0]
        token = criar_jwt_reset_senha(pessoa["id"], pessoa["email"])
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        link = f"{frontend_url}/redefinir-senha?token={token}"
        subject, body_html = email_esqueci_senha(pessoa["nome"], link)
        try:
            send_email(pessoa["email"], subject, body_html)
        except Exception:
            pass  # best-effort — não revela falha de envio pro chamador (anti-enumeração)
    return _MENSAGEM_FORGOT_PASSWORD


@router.post("/reset-password")
@limiter.limit(LOGIN_RATE_LIMIT)
async def reset_password(request: Request, data: ResetPasswordRequest, response: Response):
    try:
        payload = decodificar_jwt_reset_senha(data.token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Link inválido ou expirado. Solicite um novo.")

    client = get_client()
    senha_hash = hash_senha(data.nova_senha)
    resp = client.table("pessoa").update({"senha_hash": senha_hash}).eq("id", payload["sub"]).execute()
    if not resp.data:
        raise HTTPException(status_code=400, detail="Link inválido ou expirado. Solicite um novo.")
    return {"message": "Senha redefinida com sucesso."}
