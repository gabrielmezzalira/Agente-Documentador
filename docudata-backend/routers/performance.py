from fastapi import APIRouter, Depends, HTTPException

from models.schemas import PerformanceResponse
from services.audit import registrar_auditoria
from services.auth import get_current_pessoa, require_role
from services.performance import listar_pessoas_ativas, calcular_ranking_pessoa
from services.supabase_client import get_client

router = APIRouter(tags=["performance"])


@router.get("/performance", response_model=PerformanceResponse, dependencies=[Depends(require_role("lider"))])
async def performance(pessoa: dict = Depends(get_current_pessoa)):
    registrar_auditoria(pessoa, "/performance", "acesso")
    client = get_client()

    pesos_rows = client.table("pesos_arquetipo").select("*").execute().data or []
    pesos_por_arquetipo = {r["arquetipo"]: r for r in pesos_rows}
    if not pesos_por_arquetipo:
        raise HTTPException(status_code=500, detail="pesos_arquetipo não configurado")

    janelas: dict[str, list[dict]] = {"sprint": [], "quinzenal": [], "mensal": []}
    for pessoa_ranking in listar_pessoas_ativas(client):
        ranking = calcular_ranking_pessoa(client, pessoa_ranking, pesos_por_arquetipo)
        for nome_janela, dados in ranking.items():
            if dados is None or dados.get("score_final") is None:
                continue
            janelas[nome_janela].append({
                "email": pessoa_ranking["email"],
                "nome": pessoa_ranking["nome"],
                **dados,
            })

    for nome_janela in janelas:
        janelas[nome_janela].sort(key=lambda r: r["score_final"], reverse=True)

    return janelas
