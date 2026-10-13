"""Contexto cumulativo do Discovery (Spec 12 §5). É a ÚNICA função que compila isso: todo agente
(perguntas ao vivo, opções de solução, documentos) lê por aqui. Nunca devolve transcrição bruta.

Limites (a saída é sempre limitada, mesmo com milhares de itens): até LIMITE_REQUISITOS requisitos
(ordem por código), LIMITE_REUNIOES reuniões (as mais recentes), LIMITE_LISTA itens por lista,
LIMITE_RED_FLAGS red flags críticas; textos cortados (título 200, descrição 400, resumo 800, demais 300).
"""
from typing import Any

from services import discovery_store as store

LIMITE_REQUISITOS = 200
LIMITE_REUNIOES = 50
LIMITE_RED_FLAGS = 50
LIMITE_LISTA = 10
_RESUMO_MAX = 800
_TITULO_MAX = 200
_DESCRICAO_MAX = 400
_ITEM_MAX = 300


def _corte(texto: Any, limite: int) -> str:
    return str(texto or "")[:limite]


def _lista(valor: Any) -> list:
    return valor[:LIMITE_LISTA] if isinstance(valor, list) else []


def compilar_contexto(client: Any, project_id: str) -> dict:
    reunioes = store.listar_reunioes(client, project_id)[-LIMITE_REUNIOES:]
    requisitos = store.listar_requisitos(client, project_id)[:LIMITE_REQUISITOS]
    contagem = store.contar_evidencias(client, [r["id"] for r in requisitos])

    red_flags: list[str] = []
    resumo_reunioes = []
    for r in reunioes:
        c = r.get("conteudo_estruturado")
        c = c if isinstance(c, dict) else {}
        resumo_reunioes.append({
            "id": r["id"], "tipo": r["tipo"], "ocorrida_em": r.get("ocorrida_em"),
            "analise_status": r["analise_status"], "resumo": _corte(c.get("resumo"), _RESUMO_MAX),
            "decisoes": [_corte(x, _ITEM_MAX) for x in _lista(c.get("decisoes"))],
            "problemas": [_corte(x, _ITEM_MAX) for x in _lista(c.get("problemas"))],
        })
        if len(red_flags) < LIMITE_RED_FLAGS:
            red_flags += [_corte(f.get("text"), _ITEM_MAX) for f in (c.get("red_flags") or [])[:LIMITE_RED_FLAGS]
                          if isinstance(f, dict) and f.get("severity") == "critical"]
    red_flags = red_flags[:LIMITE_RED_FLAGS]

    return {
        "project_id": project_id,
        "reunioes": resumo_reunioes,
        "requisitos": [{
            "codigo": q["codigo"], "titulo": _corte(q.get("titulo"), _TITULO_MAX),
            "descricao": _corte(q.get("descricao"), _DESCRICAO_MAX),
            "tipo": q["tipo"], "lente": q.get("lente"), "status": q["status"],
            "prioridade_sugerida": q["prioridade_sugerida"],
            "motivo_decisao": _corte(q["motivo_decisao"], _ITEM_MAX) if q.get("motivo_decisao") else None,
            "conflito": bool(q.get("conflito")), "n_evidencias": contagem.get(q["id"], 0),
            "criterios_aceite": [_corte(x, _ITEM_MAX) for x in _lista(q.get("criterios_aceite"))],
        } for q in requisitos],
        "conflitos_abertos": [q["codigo"] for q in requisitos if q.get("conflito") and q["status"] != "rejeitado"],
        "red_flags_criticas": red_flags,
    }
