"""Painel de acompanhamento dos projetos, agrupado por gerente (Rodada B1, entrega 2).

Tudo que calcula é função pura sobre dicts já carregados; `montar_acompanhamento`
só lê em lote e monta as entradas.
"""
from datetime import datetime, timedelta, timezone
from statistics import quantiles

from routers.painel import calcular_bloco_a
from services.metas import _lotes, funcionalidade_entregue, metas_das_sprints, resultado_meta
from services.supabase_paginacao import ler_tudo

SEM_GERENTE = "Sem gerente"
JANELA_P85_DIAS = 30


# ── funções puras ──

def pct_tasks(tasks_da_func: list[dict]) -> float | None:
    tasks = [t for t in tasks_da_func if not t.get("extra")]
    if not tasks:
        return None
    concluidas = sum(1 for t in tasks if t.get("coluna_kanban") == "concluida")
    return round(concluidas / len(tasks) * 100, 1)


def previsto_de(tasks_da_sprint: list[dict]) -> int:
    """Mesma regra de services/previsto_sprint.py::previsto_da_sprint, sobre tasks já carregadas."""
    planejado = sum(t["pontos"] for t in tasks_da_sprint if not t.get("extra") and t.get("prevista_no_inicio"))
    surgiu = sum(
        t["pontos"] for t in tasks_da_sprint
        if not t.get("extra") and t.get("surgiu_na_sprint") and not t.get("prevista_no_inicio")
    )
    return planejado + surgiu


def spi_de(tasks_da_sprint: list[dict]) -> float | None:
    previsto = previsto_de(tasks_da_sprint)
    if previsto <= 0:
        return None
    realizado = sum(
        t["pontos"] for t in tasks_da_sprint if t.get("coluna_kanban") == "concluida" and not t.get("extra")
    )
    return round(realizado / previsto, 3)


def p85(valores: list[float]) -> float | None:
    if not valores:
        return None
    if len(valores) == 1:
        return round(valores[0], 1)
    return round(quantiles(valores, n=100)[84], 1)


def escolher_sprints(sprints: list[dict]) -> tuple[dict | None, list[dict], dict | None]:
    """(atual, próximas, última fechada)."""
    iniciadas = [s for s in sprints if s.get("iniciada") is not False]
    atual = max(iniciadas, key=lambda s: s["numero"]) if iniciadas else None
    proximas = sorted((s for s in sprints if s.get("iniciada") is False), key=lambda s: s["numero"])
    fechadas = [s for s in sprints if s.get("avaliacao_completa_em")]
    ultima = max(fechadas, key=lambda s: s["numero"]) if fechadas else None
    return atual, proximas, ultima


def _ref(s: dict) -> dict:
    return {"id": s["id"], "numero": s["numero"]}


def _aprovada(f: dict) -> bool:
    return f.get("status") == "concluida" and bool(f.get("aprovada_em"))


def calcular_projeto(
    projeto: dict, sprints: list[dict], funcs: list[dict], tasks: list[dict],
    planejadas_por_sprint: dict[str, set[str]], metas: dict[str, set[str]],
    tempos_limpos_h: list[float],
) -> dict:
    """`planejadas_por_sprint`: sprint_id -> funcionalidade_ids de sprint_funcionalidades;
    `metas`: sprint_id -> meta atual; `tempos_limpos_h`: horas das tasks concluídas na janela."""
    atual, proximas, ultima = escolher_sprints(sprints)
    funcs_por_id = {f["id"]: f for f in funcs}
    tasks_por_sprint: dict[str, list[dict]] = {}
    tasks_por_func: dict[str, list[dict]] = {}
    for t in tasks:
        if t.get("sprint_id"):
            tasks_por_sprint.setdefault(t["sprint_id"], []).append(t)
        if t.get("funcionalidade_id"):
            tasks_por_func.setdefault(t["funcionalidade_id"], []).append(t)

    meta_out = {"total": 0, "entregues": 0, "batida": None, "funcionalidades": []}
    fora_da_meta: list[dict] = []
    planejado = {"funcs_planejadas": 0, "funcs_planejadas_entregues": 0, "spi": None}
    if atual is not None:
        fechada_em = atual.get("avaliacao_completa_em")
        meta = {f for f in metas.get(atual["id"], set()) if f in funcs_por_id}
        planejadas = {f for f in planejadas_por_sprint.get(atual["id"], set()) if f in funcs_por_id}
        entregues = {i for i, f in funcs_por_id.items() if funcionalidade_entregue(f, fechada_em)}
        meta_out = {
            **resultado_meta(meta, entregues),
            "funcionalidades": [
                {
                    "id": f["id"], "id_funcional": f.get("id_funcional"), "titulo": f.get("titulo"),
                    "status": f.get("status"), "aprovada": _aprovada(f),
                    "pct_tasks": pct_tasks(tasks_por_func.get(f["id"], [])),
                    "planejada_na_sprint": f["id"] in planejadas,
                }
                for f in sorted((funcs_por_id[i] for i in meta), key=lambda f: f.get("id_funcional") or "")
            ],
        }
        fora_da_meta = [
            {"id": f["id"], "id_funcional": f.get("id_funcional"), "titulo": f.get("titulo")}
            for f in sorted((funcs_por_id[i] for i in planejadas - meta), key=lambda f: f.get("id_funcional") or "")
        ]
        planejado = {
            "funcs_planejadas": len(planejadas),
            "funcs_planejadas_entregues": len(planejadas & entregues),
            "spi": spi_de(tasks_por_sprint.get(atual["id"], [])),
        }

    prazo_escopo = calcular_bloco_a(projeto, funcs)
    saude = {
        "tasks_travadas": sum(1 for t in tasks if t.get("travado_automatico") and t.get("coluna_kanban") != "concluida"),
        "wip": sum(1 for f in funcs if f.get("status") == "em_andamento"),
        "p85_horas": p85(tempos_limpos_h),
    }

    ultima_out = None
    if ultima is not None:
        meta_u = {f for f in metas.get(ultima["id"], set()) if f in funcs_por_id}
        entregues_u = {i for i, f in funcs_por_id.items() if funcionalidade_entregue(f, ultima["avaliacao_completa_em"])}
        res = resultado_meta(meta_u, entregues_u)
        ultima_out = {
            "numero": ultima["numero"], "meta_total": res["total"], "meta_entregues": res["entregues"],
            "meta_batida": res["batida"], "spi": spi_de(tasks_por_sprint.get(ultima["id"], [])),
        }

    riscos: list[str] = []
    if prazo_escopo.get("desvio_detectado"):
        riscos.append("prazo à frente do escopo")
    if ultima_out and ultima_out["meta_total"] > 0 and ultima_out["meta_entregues"] / ultima_out["meta_total"] < 0.5:
        riscos.append("meta da última sprint abaixo de 50%")
    if ultima_out and ultima_out["spi"] is not None and ultima_out["spi"] < 0.7:
        riscos.append("SPI da última sprint abaixo de 0,7")

    return {
        "id": projeto["id"], "nome": projeto.get("name"), "cliente": projeto.get("client"),
        "sprint_atual": _ref(atual) if atual else None,
        "proximas_sprints": [_ref(s) for s in proximas],
        "meta": meta_out, "planejadas_fora_da_meta": fora_da_meta, "planejado": planejado,
        "prazo_escopo": prazo_escopo, "saude": saude, "riscos": riscos, "ultima_fechada": ultima_out,
        "_total_funcs": len(funcs), "_funcs_aprovadas": sum(1 for f in funcs if _aprovada(f)),
    }


def resumo_do_grupo(projetos: list[dict]) -> dict:
    com_meta = [p for p in projetos if p["ultima_fechada"] and p["ultima_fechada"]["meta_total"] > 0]
    total_funcs = sum(p["_total_funcs"] for p in projetos)
    aprovadas = sum(p["_funcs_aprovadas"] for p in projetos)
    return {
        "projetos": len(projetos),
        "em_risco": sum(1 for p in projetos if p["riscos"]),
        "metas_fechadas": len(com_meta),
        "metas_batidas": sum(1 for p in com_meta if p["ultima_fechada"]["meta_batida"]),
        "pct_funcs_aprovadas": round(aprovadas / total_funcs * 100, 1) if total_funcs else 0.0,
    }


def agrupar_por_gerente(projetos: list[dict], pessoas_por_email: dict[str, dict]) -> list[dict]:
    """`projetos`: saída de calcular_projeto + chave `_gerente_email`."""
    grupos: dict[str, dict] = {}
    for p in projetos:
        email = (p.get("_gerente_email") or "").strip().lower()
        if email:
            pessoa = pessoas_por_email.get(email) or {}
            gerente = {"nome": pessoa.get("nome") or email, "email": email}
        else:
            email = ""
            gerente = {"nome": SEM_GERENTE, "email": None}
        grupos.setdefault(email, {"gerente": gerente, "projetos": []})["projetos"].append(p)
    saida = []
    for g in grupos.values():
        projs = sorted(g["projetos"], key=lambda p: (p["nome"] or "").casefold())
        saida.append({"gerente": g["gerente"], "resumo": resumo_do_grupo(projs),
                      "projetos": [{k: v for k, v in p.items() if not k.startswith("_")} for p in projs]})
    saida.sort(key=lambda g: (g["gerente"]["email"] is None, g["gerente"]["nome"].casefold()))
    return saida


# ── carregador em lote ──

def _em_lote(ids: list[str], consulta) -> list[dict]:
    saida: list[dict] = []
    for lote in _lotes(ids):
        saida += consulta(lote)
    return saida


def montar_acompanhamento(client, subarea: str, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now(timezone.utc)
    projetos = ler_tudo(lambda: client.table("projects")
                        .select("id, name, client, data_inicio, data_fim_contratada, tolerancia_desvio_pontos, gerente_email")
                        .eq("subarea", subarea).order("id"))
    pids = [p["id"] for p in projetos]

    sprints = _em_lote(pids, lambda l: ler_tudo(lambda: client.table("sprints")
                       .select("id, project_id, numero, iniciada, data_inicio, avaliacao_completa_em")
                       .in_("project_id", l).order("id")))
    funcs = _em_lote(pids, lambda l: ler_tudo(lambda: client.table("funcionalidades")
                     .select("id, project_id, id_funcional, titulo, status, aprovada_em")
                     .in_("project_id", l).order("id")))
    tasks = _em_lote(pids, lambda l: ler_tudo(lambda: client.table("tasks")
                     .select("id, project_id, sprint_id, funcionalidade_id, coluna_kanban, extra, pontos, "
                             "travado_automatico, prevista_no_inicio, surgiu_na_sprint")
                     .in_("project_id", l).order("id")))

    sprints_por_proj: dict[str, list[dict]] = {}
    for s in sprints:
        sprints_por_proj.setdefault(s["project_id"], []).append(s)
    atuais = [a["id"] for a in (escolher_sprints(v)[0] for v in sprints_por_proj.values()) if a]
    fechadas = [u["id"] for u in (escolher_sprints(v)[2] for v in sprints_por_proj.values()) if u]
    sprint_ids = list(dict.fromkeys(atuais + fechadas))

    metas = metas_das_sprints(client, sprint_ids)
    sf = _em_lote(atuais, lambda l: ler_tudo(lambda: client.table("sprint_funcionalidades")
                  .select("sprint_id, funcionalidade_id").in_("sprint_id", l).order("id")))
    planejadas: dict[str, set[str]] = {}
    for r in sf:
        planejadas.setdefault(r["sprint_id"], set()).add(r["funcionalidade_id"])

    concluidas = [t["id"] for t in tasks if t.get("coluna_kanban") == "concluida"]
    corte = agora - timedelta(days=JANELA_P85_DIAS)
    aprend = _em_lote(concluidas, lambda l: ler_tudo(lambda: client.table("task_aprendizado")
                      .select("task_id, tempo_limpo_s, concluida_em, excluida")
                      .in_("task_id", l).order("task_id")))
    projeto_da_task = {t["id"]: t["project_id"] for t in tasks}
    horas: dict[str, list[float]] = {}
    for a in aprend:
        if a.get("excluida") or a.get("tempo_limpo_s") is None or not a.get("concluida_em"):
            continue
        dt = datetime.fromisoformat(str(a["concluida_em"]).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= corte:
            horas.setdefault(projeto_da_task[a["task_id"]], []).append(a["tempo_limpo_s"] / 3600)

    pessoas = ler_tudo(lambda: client.table("pessoa").select("id, nome, email").order("id"))
    por_email = {(p.get("email") or "").lower(): p for p in pessoas}

    funcs_por_proj: dict[str, list[dict]] = {}
    for f in funcs:
        funcs_por_proj.setdefault(f["project_id"], []).append(f)
    tasks_por_proj: dict[str, list[dict]] = {}
    for t in tasks:
        tasks_por_proj.setdefault(t["project_id"], []).append(t)

    calculados = []
    for p in projetos:
        c = calcular_projeto(p, sprints_por_proj.get(p["id"], []), funcs_por_proj.get(p["id"], []),
                             tasks_por_proj.get(p["id"], []), planejadas, metas, horas.get(p["id"], []))
        c["_gerente_email"] = p.get("gerente_email")
        calculados.append(c)

    grupos = agrupar_por_gerente(calculados, por_email)
    totais = {
        "projetos": len(calculados),
        "em_risco": sum(1 for p in calculados if p["riscos"]),
        "metas_fechadas": sum(g["resumo"]["metas_fechadas"] for g in grupos),
        "metas_batidas": sum(g["resumo"]["metas_batidas"] for g in grupos),
    }
    return {"subarea": subarea, "totais": totais, "grupos": grupos}
