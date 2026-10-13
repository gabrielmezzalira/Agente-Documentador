"""Promoção de requisito validado a funcionalidade do Delivery (Spec 12 §4). Idempotente e única:
usada pela rota de promoção e pelo encaminhamento (`promover_validados`)."""
from typing import Any

from services import discovery_store as store
from services.discovery_requisitos import RegraRequisitoErro

_MAX_SUFIXO = 50


def _funcionalidades_do_projeto(client: Any, project_id: str) -> list[dict]:
    return (
        client.table("funcionalidades").select("id, id_funcional, titulo")
        .eq("project_id", project_id).execute().data or []
    )


def _escolher_funcionalidade(client: Any, req: dict) -> tuple[str | None, str]:
    """(id de funcionalidade já existente para este requisito | None, id_funcional livre p/ inserir).

    A tabela `funcionalidades` não tem UNIQUE (project_id, id_funcional) nem ponteiro de volta
    para o requisito. A chave de recuperação é (project_id, id_funcional == codigo, titulo igual):
    cobre a falha entre o insert e o vínculo. Se o id_funcional já é de OUTRA funcionalidade,
    usa sufixo (-2, -3...) em vez de adotá-la por engano."""
    existentes = _funcionalidades_do_projeto(client, req["project_id"])
    ocupados = {f["id_funcional"] for f in existentes}
    for f in existentes:
        if f["id_funcional"] == req["codigo"] and f.get("titulo") == req["titulo"]:
            return f["id"], req["codigo"]
    candidato = req["codigo"]
    n = 2
    while candidato in ocupados and n <= _MAX_SUFIXO:
        candidato = f"{req['codigo']}-{n}"
        n += 1
    if candidato in ocupados:
        raise RegraRequisitoErro(409, "Não foi possível alocar um id_funcional livre para o requisito")
    return None, candidato


def promover_requisito(client: Any, requisito_id: str, autor: str) -> dict:
    req = store.buscar_requisito(client, requisito_id)
    if req is None:
        raise RegraRequisitoErro(404, "Requisito não encontrado")
    if req.get("funcionalidade_id"):
        return {"funcionalidade_id": req["funcionalidade_id"], "criada": False}
    if req["status"] != "validado":
        raise RegraRequisitoErro(409, "Só requisito validado pode ser promovido")
    if not req.get("criterios_aceite"):
        raise RegraRequisitoErro(422, "Informe ao menos um critério de aceite antes de promover")

    existente_id, id_funcional = _escolher_funcionalidade(client, req)
    if existente_id is not None:
        funcionalidade_id, criada = existente_id, False
    else:
        payload = {
            "project_id": req["project_id"], "id_funcional": id_funcional, "titulo": req["titulo"],
            "criterios_aceite": req["criterios_aceite"], "prioridade": req["prioridade_sugerida"],
        }
        if req.get("descricao"):
            payload["descricao"] = req["descricao"]
        funcionalidade_id = client.table("funcionalidades").insert(payload).execute().data[0]["id"]
        criada = True
    store.atualizar_requisito(client, requisito_id, {"funcionalidade_id": funcionalidade_id})
    store.inserir_transicao(client, requisito_id=requisito_id, campo="funcionalidade",
                            de="", para=funcionalidade_id, autor=autor, motivo=None)
    return {"funcionalidade_id": funcionalidade_id, "criada": criada}


def promover_validados_do_projeto(client: Any, project_id: str, autor: str) -> int:
    """Promove todos os validados ainda sem funcionalidade. Confere ANTES: se algum não tem
    critério de aceite, recusa tudo (o gerente corrige e tenta de novo; nada fica pela metade).
    Retorna quantos requisitos pendentes foram processados (inclui vínculo a funcionalidade órfã
    recuperada)."""
    pendentes = [r for r in store.listar_requisitos(client, project_id, "validado") if not r.get("funcionalidade_id")]
    sem_criterio = [r["codigo"] for r in pendentes if not r.get("criterios_aceite")]
    if sem_criterio:
        raise RegraRequisitoErro(422, "Requisitos validados sem critério de aceite: " + ", ".join(sem_criterio))
    for r in pendentes:
        promover_requisito(client, r["id"], autor)
    return len(pendentes)
