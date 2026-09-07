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

    # Em quais projetos cada pessoa aparece. Duas fontes, porque o vínculo é
    # gravado de dois jeitos diferentes conforme o cargo: operacional entra na
    # tabela operacionais (por projeto), gerente entra em projects.gerente_email
    # (usado pra lembrete por email). Sem juntar as duas, todo gerente aparecia
    # com "—" mesmo estando de fato vinculado a um projeto.
    operacionais = (
        client.table("operacionais").select("email, project_id, ativo").execute().data or []
    )
    projects_rows = client.table("projects").select("id, name, gerente_email").execute().data or []
    projetos = {p["id"]: p["name"] for p in projects_rows}

    por_email: dict[str, list[str]] = {}

    def _adicionar(email: str | None, nome_projeto: str | None) -> None:
        chave = (email or "").strip().lower()
        if not chave or not nome_projeto:
            return
        if nome_projeto not in por_email.setdefault(chave, []):
            por_email[chave].append(nome_projeto)

    for op in operacionais:
        if not op.get("ativo", True):
            continue
        _adicionar(op.get("email"), projetos.get(op["project_id"]))

    for proj in projects_rows:
        _adicionar(proj.get("gerente_email"), proj.get("name"))

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
