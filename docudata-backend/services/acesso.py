"""
Regra central de acesso por projeto.

owner/lider enxergam todos os projetos; gerente só os vinculados em
`projeto_gerentes`; operacional só aqueles em que consta (por e-mail) em
`operacionais`. Antes da migração v16 (tabela ausente) o gerente é tratado
como antes: vê tudo, com um aviso no log.
"""
import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)

SEM_ACESSO = "Você não tem acesso a este projeto"

_avisou_tabela_ausente = False

# entidade -> (tabela, coluna_project_id) ou (tabela, None, coluna_pai, entidade_pai)
_ENTIDADES = {
    "task": ("tasks", "project_id"),
    "sprint": ("sprints", "project_id"),
    "funcionalidade": ("funcionalidades", "project_id"),
    "doc": ("generated_docs", "project_id"),
    "ingestion": ("ingestions", "project_id"),
    "proposta": ("propostas_melhoria", "project_id"),
    "solicitacao": ("solicitacoes_task", "project_id"),
    "operacional": ("operacionais", "project_id"),
    # sem project_id próprio: resolvem pelo pai
    "sprint_funcionalidade": ("sprint_funcionalidades", None, "sprint_id", "sprint"),
    "sugestao": ("task_sugestoes", None, "task_id", "task"),
    "avaliacao": ("avaliacoes_gerente", None, "sprint_id", "sprint"),
}


def _tabela_ausente(exc: Exception) -> bool:
    texto = str(exc)
    return "projeto_gerentes" in texto and any(m in texto for m in ("PGRST205", "42P01", "does not exist"))


def _ids_vinculados_gerente(client, pessoa_id: str) -> set[str] | None:
    """Projetos vinculados ao gerente; None se a tabela ainda não existe (pré-v16)."""
    global _avisou_tabela_ausente
    try:
        resp = client.table("projeto_gerentes").select("project_id").eq("pessoa_id", pessoa_id).execute()
    except Exception as exc:
        if not _tabela_ausente(exc):
            raise
        if not _avisou_tabela_ausente:
            _avisou_tabela_ausente = True
            logger.warning("Tabela projeto_gerentes ausente: gerentes veem todos os projetos até a migração v16.")
        return None
    return {r["project_id"] for r in (resp.data or [])}


def projetos_visiveis(client, pessoa: dict) -> set[str] | None:
    """None = todos os projetos."""
    cargo = pessoa.get("cargo")
    if cargo in ("owner", "lider"):
        return None
    vinculados: set[str] = set()
    if cargo == "gerente":
        vinculados = _ids_vinculados_gerente(client, pessoa["id"])
        if vinculados is None:
            return None
    resp = client.table("operacionais").select("project_id").eq("email", pessoa.get("email")).eq("ativo", True).execute()
    como_operacional = {r["project_id"] for r in (resp.data or [])}
    # Quem é gerente num projeto (ex.: PM do PTA) pode ser operacional em
    # outro; sem somar os dois, o projeto em que trabalha some da lista.
    return vinculados | como_operacional


def tem_acesso(client, pessoa: dict, project_id: str) -> bool:
    if pessoa.get("cargo") == "operacional":
        # consulta pontual: mesma query de sempre, sem varrer todos os vínculos
        check = (
            client.table("operacionais").select("id")
            .eq("project_id", project_id).eq("email", pessoa.get("email")).eq("ativo", True).execute()
        )
        return bool(check.data)
    visiveis = projetos_visiveis(client, pessoa)
    return visiveis is None or project_id in visiveis


def exigir_acesso(client, pessoa: dict, project_id: str) -> None:
    if not tem_acesso(client, pessoa, project_id):
        raise HTTPException(status_code=403, detail=SEM_ACESSO)


def project_id_de(client, entidade: str, objeto_id: str) -> str:
    cfg = _ENTIDADES.get(entidade)
    if cfg is None:
        raise ValueError(f"entidade desconhecida: {entidade}")
    tabela, coluna = cfg[0], cfg[1]
    coluna_sel = coluna or cfg[2]
    resp = client.table(tabela).select(coluna_sel).eq("id", objeto_id).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Não encontrado")
    valor = resp.data[0].get(coluna_sel)
    if coluna is not None:
        if not valor:
            raise HTTPException(status_code=404, detail="Não encontrado")
        return valor
    return project_id_de(client, cfg[3], valor)


def exigir_acesso_por(client, pessoa: dict, entidade: str, objeto_id: str) -> str:
    project_id = project_id_de(client, entidade, objeto_id)
    exigir_acesso(client, pessoa, project_id)
    return project_id


def gerentes_por_projeto(client) -> dict[str, list[dict]]:
    """project_id -> gerentes vinculados ([{nome, email}], do vínculo mais antigo ao mais novo).
    Vazio se a tabela ainda não existe (pré-v16)."""
    try:
        vinculos = (
            client.table("projeto_gerentes").select("project_id, pessoa_id, criado_em")
            .order("criado_em").execute().data or []
        )
    except Exception as exc:
        if not _tabela_ausente(exc):
            raise
        return {}
    if not vinculos:
        return {}
    pessoas = client.table("pessoa").select("id, nome, email").in_("id", list({v["pessoa_id"] for v in vinculos})).execute().data or []
    por_id = {p["id"]: p for p in pessoas}
    saida: dict[str, list[dict]] = {}
    for v in vinculos:
        p = por_id.get(v["pessoa_id"])
        if p and p.get("email"):
            saida.setdefault(v["project_id"], []).append({"nome": p.get("nome") or p["email"], "email": p["email"]})
    return saida


def vincular_gerente(client, project_id: str, pessoa_id: str, criado_por: str | None) -> None:
    """Idempotente; tolera a tabela ausente (pré-v16)."""
    try:
        client.table("projeto_gerentes").upsert(
            {"project_id": project_id, "pessoa_id": pessoa_id, "criado_por": criado_por},
            on_conflict="project_id,pessoa_id", ignore_duplicates=True,
        ).execute()
    except Exception as exc:
        if not _tabela_ausente(exc):
            raise
        logger.warning("Tabela projeto_gerentes ausente: vínculo não gravado (migração v16 pendente).")
