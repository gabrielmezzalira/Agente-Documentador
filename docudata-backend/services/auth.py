"""
Autenticação e RBAC (Phase 16). JWT em cookie httpOnly — sem tabela de
sessão, o próprio token é a fonte de verdade (sub=pessoa.id, email, cargo,
exp). Sem refresh token no MVP: expirado, pede login de novo.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Cookie, Depends, HTTPException

from services.supabase_client import get_client

_JWT_ALG = "HS256"
_JWT_EXP_HOURS = 8
COOKIE_NAME = "docudata_session"

# Hierarquia de acesso. Um cargo alcança tudo que os abaixo dele alcançam, então
# require_role("lider") também passa para owner. Sem isso, cada rota restrita ao
# Líder precisaria listar owner à mão e uma delas ia ficar para trás.
_HIERARQUIA = ["operacional", "gerente", "lider", "owner"]


def nivel(cargo: str) -> int:
    return _HIERARQUIA.index(cargo) if cargo in _HIERARQUIA else -1


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_jwt(pessoa_id: str, email: str, cargo: str) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": pessoa_id,
        "email": email,
        "cargo": cargo,
        "iat": agora,
        "exp": agora + timedelta(hours=_JWT_EXP_HOURS),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=_JWT_ALG)


def decodificar_jwt(token: str) -> dict:
    return jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[_JWT_ALG])


async def get_current_pessoa(
    session: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
) -> dict:
    if not session:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = decodificar_jwt(session)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    return {"id": payload["sub"], "email": payload["email"], "cargo": payload["cargo"]}


def require_role(cargo_minimo: str):
    """Exige o cargo informado ou qualquer um acima dele na hierarquia."""
    async def _dep(pessoa: dict = Depends(get_current_pessoa)) -> dict:
        if nivel(pessoa["cargo"]) < nivel(cargo_minimo):
            raise HTTPException(status_code=403, detail=f"Acesso restrito a {cargo_minimo}")
        return pessoa
    return _dep


async def require_not_operacional(pessoa: dict = Depends(get_current_pessoa)) -> dict:
    if pessoa["cargo"] == "operacional":
        raise HTTPException(status_code=403, detail="Acesso restrito a Gerente/Líder")
    return pessoa


async def require_project_access(project_id: str, pessoa: dict = Depends(get_current_pessoa)) -> dict:
    if pessoa["cargo"] in ("owner", "lider", "gerente"):
        return pessoa
    client = get_client()
    check = (
        client.table("operacionais")
        .select("id")
        .eq("project_id", project_id)
        .eq("email", pessoa["email"])
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=403, detail="Você não tem acesso a este projeto")
    return pessoa
