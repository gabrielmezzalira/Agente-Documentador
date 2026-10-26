"""Persistência do aprendizado do classificador (spec A2 §4): um exemplo por
task concluída, rótulos recalculados sobre todos os exemplos e parâmetros
vigentes com histórico só quando mudam."""
from datetime import datetime, timezone

from services.classificador_estatistica import recalcular
from services.classificador_tempo import tempo_limpo
from services.regua import converter_pontos_legado

_EPS = 1e-9


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def registrar_conclusao(client, task_id: str) -> None:
    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        return
    task = resp.data[0]
    transicoes = (
        client.table("task_transicoes").select("*").eq("task_id", task_id).execute().data or []
    )
    clas = (
        client.table("task_classificacoes").select("*").eq("task_id", task_id)
        .order("criado_em", desc=True).limit(1).execute().data
    )
    clas = clas[0] if clas else None

    tempo = tempo_limpo(transicoes, task)
    if tempo:
        concluida_em = tempo["concluida_em"]
    else:
        conclusoes = [
            t["timestamp"] for t in transicoes
            if t.get("campo") == "coluna_kanban" and t.get("para") == "concluida"
        ]
        concluida_em = max(conclusoes) if conclusoes else (task.get("updated_at") or _agora())

    if clas:
        nivel_sugerido = clas["nivel_final"]
        sinais = {
            s: (v.get("nota") if isinstance(v, dict) else v)
            for s, v in (clas.get("sinais") or {}).items()
        }
    else:
        nivel_sugerido = converter_pontos_legado(task.get("pontos") or 1)
        sinais = None

    existente = client.table("task_aprendizado").select("*").eq("task_id", task_id).execute().data
    exemplo = {
        "task_id": task_id,
        "classificacao_id": clas["id"] if clas else None,
        "nivel_sugerido": nivel_sugerido,
        "operacional_id": task.get("operacional_id"),
        "gerente_id": clas.get("criado_por") if clas else None,
        "sinais": sinais,
        "tempo_bruto_s": tempo["tempo_bruto_s"] if tempo else None,
        "tempo_limpo_s": tempo["tempo_limpo_s"] if tempo else None,
        "reaberta": tempo["reaberta"] if tempo else False,
        "concluida_em": concluida_em,
        "atualizado_em": _agora(),
    }
    if existente:  # reconclusão não apaga opinião nem exclusão já registradas
        exemplo = {**existente[0], **exemplo}
    client.table("task_aprendizado").upsert(exemplo, on_conflict="task_id").execute()
    recalcular_tudo(client)


def recalcular_tudo(client) -> None:
    linhas = client.table("task_aprendizado").select("*").execute().data or []
    if not linhas:
        return
    clas_ids = [l["classificacao_id"] for l in linhas if l.get("classificacao_id")]
    opinioes: dict[str, int | None] = {}
    if clas_ids:
        for c in client.table("task_classificacoes").select("*").in_("id", clas_ids).execute().data or []:
            opinioes[c["id"]] = c.get("opiniao_gerente")

    exemplos = []
    for l in linhas:
        ex = {k: l.get(k) for k in (
            "task_id", "concluida_em", "nivel_sugerido", "tempo_limpo_s", "operacional_id",
            "gerente_id", "opiniao_operacional", "excluida", "sinais",
        )}
        ex["excluida"] = bool(ex["excluida"])
        og = opinioes.get(l.get("classificacao_id"))
        if og is not None:
            ex["opiniao_gerente"] = og
        exemplos.append(ex)

    res = recalcular(exemplos)
    agora = _agora()
    for task_id, r in res["rotulos"].items():
        client.table("task_aprendizado").update({**r, "atualizado_em": agora}).eq("task_id", task_id).execute()

    atuais = {
        (p["tipo"], p["chave"]): p
        for p in client.table("classificador_parametros").select("*").execute().data or []
    }
    for (tipo, chave), (valor, n) in res["parametros"].items():
        valor = float(valor)
        anterior = atuais.get((tipo, chave))
        if tipo == "media_nivel" and n == 0 and anterior is not None:
            valor = float(anterior["valor"])  # sem amostras: mantém o último valor
        mudou = anterior is None or abs(float(anterior["valor"]) - valor) > _EPS
        if not mudou and anterior["n_amostras"] == n:
            continue
        client.table("classificador_parametros").upsert(
            {"tipo": tipo, "chave": chave, "valor": valor, "n_amostras": n, "atualizado_em": agora},
            on_conflict="tipo,chave",
        ).execute()
        if mudou:
            client.table("classificador_parametros_hist").insert(
                {"tipo": tipo, "chave": chave, "valor": valor, "n_amostras": n}
            ).execute()


def parametros_vigentes(client) -> dict[tuple[str, str], float]:
    linhas = client.table("classificador_parametros").select("*").execute().data or []
    return {(p["tipo"], p["chave"]): float(p["valor"]) for p in linhas}


def registrar_opiniao_operacional(client, task_id: str, nivel: int) -> None:
    client.table("task_aprendizado").update(
        {"opiniao_operacional": nivel, "atualizado_em": _agora()}
    ).eq("task_id", task_id).execute()
    recalcular_tudo(client)


def definir_exclusao(client, task_id: str, excluida: bool, motivo: str | None, pessoa_id: str) -> dict:
    agora = _agora()
    campos = (
        {"excluida": True, "excluida_por": pessoa_id, "excluida_em": agora, "motivo_exclusao": motivo}
        if excluida
        else {"excluida": False, "excluida_por": None, "excluida_em": None, "motivo_exclusao": None}
    )
    client.table("task_aprendizado").update({**campos, "atualizado_em": agora}).eq("task_id", task_id).execute()
    recalcular_tudo(client)
    atual = client.table("task_aprendizado").select("*").eq("task_id", task_id).execute().data
    return atual[0] if atual else {}
