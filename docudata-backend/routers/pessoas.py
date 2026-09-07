"""Painel de pessoas com acesso ao sistema.

Quem enxerga a lista é Líder e Owner; quem muda cargo é só o Owner. A separação
existe porque cargo define acesso a score e ranking, então promover alguém é uma
decisão de dono do sistema, não de operação do dia a dia.
"""
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import PessoaResponse, PessoaCargoUpdate
from services.audit import registrar_auditoria
from services.auth import get_current_pessoa, require_role
from services.supabase_client import get_client

router = APIRouter(prefix="/pessoas", tags=["pessoas"])


@router.get("", response_model=list[PessoaResponse], dependencies=[Depends(require_role("lider"))])
async def listar_pessoas():
    client = get_client()
    pessoas = (
        client.table("pessoa")
        .select("id, nome, email, cargo, created_at")
        .order("nome", desc=False)
        .execute()
        .data or []
    )
    if not pessoas:
        return []

    # Em quais projetos cada pessoa aparece como operacional. Serve para o Owner
    # não promover alguém por engano achando que é outra pessoa de mesmo nome.
    operacionais = (
        client.table("operacionais").select("email, project_id, ativo").execute().data or []
    )
    projetos = {
        p["id"]: p["name"]
        for p in (client.table("projects").select("id, name").execute().data or [])
    }
    por_email: dict[str, list[str]] = {}
    for op in operacionais:
        email = (op.get("email") or "").strip().lower()
        if not email or not op.get("ativo", True):
            continue
        nome_projeto = projetos.get(op["project_id"])
        if nome_projeto and nome_projeto not in por_email.setdefault(email, []):
            por_email[email].append(nome_projeto)

    return [
        {**p, "projetos": por_email.get((p.get("email") or "").strip().lower(), [])}
        for p in pessoas
    ]


@router.patch(
    "/{pessoa_id}/cargo",
    response_model=PessoaResponse,
    dependencies=[Depends(require_role("owner"))],
)
async def alterar_cargo(
    pessoa_id: str,
    data: PessoaCargoUpdate,
    solicitante: dict = Depends(get_current_pessoa),
):
    client = get_client()

    alvo = client.table("pessoa").select("id, cargo").eq("id", pessoa_id).execute()
    if not alvo.data:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")

    # Rebaixar a si mesmo tira o acesso a esta própria tela e não teria como ser
    # desfeito pela interface. Owner que quer sair passa o cargo para outro antes.
    if pessoa_id == solicitante["id"] and data.cargo != "owner":
        raise HTTPException(
            status_code=409,
            detail="Você não pode mudar o próprio cargo. Promova outra pessoa a Owner primeiro.",
        )

    resp = client.table("pessoa").update({"cargo": data.cargo}).eq("id", pessoa_id).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao alterar o cargo")

    registrar_auditoria(solicitante, f"/pessoas/{pessoa_id}/cargo", f"cargo -> {data.cargo}")
    return {**resp.data[0], "projetos": []}
