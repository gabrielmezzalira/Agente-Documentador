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
    return texto[:limite] if isinstance(texto, str) else ""


def _textos(valor: Any) -> list[str]:
    """Lista de textos: só aceita list; ignora itens que não são str (conteúdo não confiável)."""
    if not isinstance(valor, list):
        return []
    return [_corte(x, _ITEM_MAX) for x in valor[:LIMITE_LISTA] if isinstance(x, str)]


def _red_flags_criticas(conteudo: dict) -> list[str]:
    brutas = conteudo.get("red_flags")
    if not isinstance(brutas, list):
        return []
    saida = []
    for f in brutas[:LIMITE_RED_FLAGS]:
        if isinstance(f, dict) and f.get("severity") == "critical" and isinstance(f.get("text"), str) and f["text"]:
            saida.append(_corte(f["text"], _ITEM_MAX))
    return saida


def _ordenar_requisitos(requisitos: list[dict]) -> list[dict]:
    """Rejeitados, validados e com conflito primeiro (o agente não pode re-sugerir rejeitados); código dentro do grupo."""
    def chave(q: dict):
        prioritario = q.get("status") in ("rejeitado", "validado") or bool(q.get("conflito"))
        return (0 if prioritario else 1, str(q.get("codigo") or ""))
    return sorted(requisitos, key=chave)


def compilar_contexto(client: Any, project_id: str) -> dict:
    reunioes = store.listar_reunioes(client, project_id)[-LIMITE_REUNIOES:]
    todos = _ordenar_requisitos(store.listar_requisitos(client, project_id))
    conflitos = [q["codigo"] for q in todos if q.get("conflito") and q["status"] != "rejeitado"]  # antes do corte
    requisitos = todos[:LIMITE_REQUISITOS]
    contagem = store.contar_evidencias(client, [r["id"] for r in requisitos])

    resumo_reunioes = []
    flags_por_reuniao = []
    for r in reunioes:
        c = r.get("conteudo_estruturado")
        c = c if isinstance(c, dict) else {}
        resumo_reunioes.append({
            "id": r["id"], "tipo": r["tipo"], "ocorrida_em": r.get("ocorrida_em"),
            "analise_status": r["analise_status"], "resumo": _corte(c.get("resumo"), _RESUMO_MAX),
            "decisoes": _textos(c.get("decisoes")),
            "problemas": _textos(c.get("problemas")),
        })
        flags_por_reuniao.append(_red_flags_criticas(c))

    # Teto de red flags: ficam as das reuniões mais recentes; saída em ordem cronológica.
    restante, escolhidas = LIMITE_RED_FLAGS, []
    for flags in reversed(flags_por_reuniao):
        if restante <= 0:
            break
        pegas = flags[:restante]
        escolhidas.append(pegas)
        restante -= len(pegas)
    red_flags = [t for grupo in reversed(escolhidas) for t in grupo]

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
            "criterios_aceite": _textos(q.get("criterios_aceite")),
        } for q in requisitos],
        "requisitos_truncados": len(todos) > LIMITE_REQUISITOS,
        "conflitos_abertos": conflitos,
        "red_flags_criticas": red_flags,
    }
