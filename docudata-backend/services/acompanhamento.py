"""Painel de acompanhamento dos projetos, agrupado por gerente (Rodada B1, entrega 2).

Tudo que calcula é função pura sobre dicts já carregados; `montar_acompanhamento`
só lê em lote e monta as entradas.
"""
from datetime import datetime, timedelta, timezone
from statistics import quantiles

from routers.painel import calcular_bloco_a
from services.status_projeto import ORDEM_STATUS, diagnostico, motivos, sinais_do_projeto, status_de
from services.metas import _lotes, funcionalidade_entregue, metas_das_sprints, resultado_meta
from services.supabase_paginacao import ler_tudo

SEM_GERENTE = "Sem gerente"
SPRINTS_NO_MAPA = 6
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
    return {"id": s["id"], "numero": s["numero"], "fechada": bool(s.get("avaliacao_completa_em"))}


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


# ── funções puras do dashboard ──

def sprints_relativas(sprints: list[dict]) -> list[dict]:
    """Até 6 sprints iniciadas, da atual (rel 0) para trás, por `numero` decrescente."""
    iniciadas = sorted((s for s in sprints if s.get("iniciada") is not False), key=lambda s: s["numero"], reverse=True)
    return [{"numero": s["numero"], "id": s["id"], "rel": -i} for i, s in enumerate(iniciadas[:SPRINTS_NO_MAPA])]


def _dt(v) -> datetime:
    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def janela_da_sprint(sprint: dict, anterior: dict | None, agora: datetime) -> tuple[datetime | None, datetime]:
    """Início: `data_inicio` 00:00 UTC; sem ela, o fechamento da anterior; sem nenhum, None. Fim: o fechamento ou agora."""
    if sprint.get("data_inicio"):
        d = _dt(sprint["data_inicio"])
        inicio = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    elif anterior and anterior.get("avaliacao_completa_em"):
        inicio = _dt(anterior["avaliacao_completa_em"])
    else:
        inicio = None
    fim = _dt(sprint["avaliacao_completa_em"]) if sprint.get("avaliacao_completa_em") else agora
    return inicio, fim


def features_entregues_na_janela(funcs: list[dict], inicio: datetime | None, fim: datetime) -> int | None:
    """Fechada no início, aberta no fim."""
    if inicio is None:
        return None
    return sum(1 for f in funcs if f.get("status") == "concluida" and f.get("aprovada_em") and inicio <= _dt(f["aprovada_em"]) < fim)


def variacao(atual: float | None, anterior: float | None) -> float | None:
    if atual is None or anterior is None:
        return None
    return round(atual - anterior, 2)


def mapa_do_projeto(sprints: list[dict], funcs: list[dict], tasks_por_sprint: dict[str, list[dict]],
                    metas: dict[str, set[str]], agora: datetime) -> tuple[list[dict], list[float | None], int | None, int | None]:
    """(6 posições -5..0, SPI sem arredondar de cada posição, features entregues na sprint atual, idem na -1)."""
    por_numero = sorted((s for s in sprints if s.get("iniciada") is not False), key=lambda s: s["numero"])
    funcs_por_id = {f["id"]: f for f in funcs}
    por_rel = {r["rel"]: r for r in sprints_relativas(sprints)}
    posicoes: list[dict] = []
    spis_brutos: list[float | None] = []
    features: dict[int, int | None] = {}
    for rel in range(-(SPRINTS_NO_MAPA - 1), 1):
        ref = por_rel.get(rel)
        if ref is None:
            posicoes.append({"rel": rel, "numero": None, "spi": None, "meta_total": 0, "meta_entregues": 0, "meta_batida": None})
            spis_brutos.append(None)
            continue
        sp = next(s for s in por_numero if s["id"] == ref["id"])
        fechada_em = sp.get("avaliacao_completa_em")
        meta = {f for f in metas.get(sp["id"], set()) if f in funcs_por_id}
        entregues = {i for i, f in funcs_por_id.items() if funcionalidade_entregue(f, fechada_em)}
        res = resultado_meta(meta, entregues)
        spi = spi_de(tasks_por_sprint.get(sp["id"], []))
        spis_brutos.append(spi)
        posicoes.append({"rel": rel, "numero": sp["numero"], "spi": round(spi, 2) if spi is not None else None,
                         "meta_total": res["total"], "meta_entregues": res["entregues"], "meta_batida": res["batida"]})
        if rel >= -1:
            idx = por_numero.index(sp)
            inicio, fim = janela_da_sprint(sp, por_numero[idx - 1] if idx > 0 else None, agora)
            features[rel] = features_entregues_na_janela(funcs, inicio, fim)
    return posicoes, spis_brutos, features.get(0), features.get(-1)


def _media(valores: list[float]) -> float | None:
    return sum(valores) / len(valores) if valores else None


def montar_kpis(itens: list[dict]) -> dict:
    """`itens`: projetos calculados com `_status`, `_feat`, `_feat_ant`, `_spi`, `_spi_ant`."""
    contagem = {s: sum(1 for i in itens if i["_status"] == s) for s in ORDEM_STATUS}
    feat = [i["_feat"] for i in itens if i["_feat"] is not None]
    spis = [i["_spi"] for i in itens if i["_spi"] is not None]
    # variações só entre os mesmos projetos: os que têm o valor na sprint atual e na -1
    par_feat = [(i["_feat"], i["_feat_ant"]) for i in itens if i["_feat"] is not None and i["_feat_ant"] is not None]
    par_spi = [(i["_spi"], i["_spi_ant"]) for i in itens if i["_spi"] is not None and i["_spi_ant"] is not None]
    medio = _media(spis)
    com_meta = [i for i in itens if i["ultima_fechada"] and i["ultima_fechada"]["meta_total"] > 0]
    return {
        "projetos": len(itens), "criticos": contagem["critico"], "atencao": contagem["atencao"],
        "sem_dados": contagem["sem_dados"], "saudaveis": contagem["saudavel"],
        "features_entregues": sum(feat) if feat else None,
        "features_entregues_var": sum(a for a, _ in par_feat) - sum(b for _, b in par_feat) if par_feat else None,
        "spi_medio": round(medio, 2) if medio is not None else None,
        "spi_medio_var": variacao(_media([a for a, _ in par_spi]), _media([b for _, b in par_spi])),
        "metas_batidas": sum(1 for i in com_meta if i["ultima_fechada"]["meta_batida"]),
        "metas_fechadas": len(com_meta),
        "projetos_sem_meta": sum(1 for i in itens if i["sprint_atual"] and i["meta"]["total"] == 0),
        "tasks_travadas": sum(i["saude"]["tasks_travadas"] for i in itens),
    }


# ── carregador em lote ──

def _em_lote(ids: list[str], consulta) -> list[dict]:
    saida: list[dict] = []
    for lote in _lotes(ids):
        saida += consulta(lote)
    return saida


def carregar_projetos(client, subarea: str, agora: datetime | None = None,
                      gerente_email: str | None = None) -> tuple[list[dict], list[dict], dict[str, dict]]:
    """Lê tudo em lote. Devolve (projetos calculados já filtrados, gerentes da subárea, pessoas por email)."""
    agora = agora or datetime.now(timezone.utc)
    projetos = ler_tudo(lambda: client.table("projects")
                        .select("id, name, client, data_inicio, data_fim_contratada, tolerancia_desvio_pontos, gerente_email")
                        .eq("subarea", subarea).order("id"))
    todos = projetos
    if gerente_email:
        alvo = gerente_email.strip().lower()
        projetos = [p for p in projetos
                    if ((p.get("gerente_email") or "").strip().lower() == "" if alvo == "sem"
                        else (p.get("gerente_email") or "").strip().lower() == alvo)]
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
    no_mapa = [r["id"] for v in sprints_por_proj.values() for r in sprints_relativas(v)]
    sprint_ids = list(dict.fromkeys(atuais + fechadas + no_mapa))

    metas = metas_das_sprints(client, sprint_ids)
    sf = _em_lote(atuais, lambda l: ler_tudo(lambda: client.table("sprint_funcionalidades")
                  .select("sprint_id, funcionalidade_id").in_("sprint_id", l).order("id")))
    planejadas: dict[str, set[str]] = {}
    for r in sf:
        planejadas.setdefault(r["sprint_id"], set()).add(r["funcionalidade_id"])

    corte = agora - timedelta(days=JANELA_P85_DIAS)
    aprend = ler_tudo(lambda: client.table("task_aprendizado")
                      .select("task_id, tempo_limpo_s, concluida_em, excluida")
                      .gte("concluida_em", corte.isoformat()).eq("excluida", False)
                      .order("task_id").order("concluida_em"))
    projeto_da_task = {t["id"]: t["project_id"] for t in tasks}
    horas: dict[str, list[float]] = {}
    for a in aprend:
        if a["task_id"] not in projeto_da_task or a.get("excluida") or a.get("tempo_limpo_s") is None or not a.get("concluida_em"):
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
        sps, ts = sprints_por_proj.get(p["id"], []), tasks_por_proj.get(p["id"], [])
        c = calcular_projeto(p, sps, funcs_por_proj.get(p["id"], []), ts, planejadas, metas, horas.get(p["id"], []))
        por_sprint: dict[str, list[dict]] = {}
        for t in ts:
            if t.get("sprint_id"):
                por_sprint.setdefault(t["sprint_id"], []).append(t)
        mapa, spis_brutos, feat, feat_ant = mapa_do_projeto(sps, funcs_por_proj.get(p["id"], []), por_sprint, metas, agora)
        spi_atual = mapa[-1]["spi"]
        sinais = sinais_do_projeto({
            "spi_atual": spis_brutos[-1], "spis_recentes": list(reversed(spis_brutos)),
            "prazo_escopo": c["prazo_escopo"], "tolerancia": p.get("tolerancia_desvio_pontos"),
            "ultima_fechada": c["ultima_fechada"], "travadas": c["saude"]["tasks_travadas"],
            "tem_meta_atual": c["meta"]["total"] > 0, "tem_planejamento_atual": c["planejado"]["funcs_planejadas"] > 0,
            "tem_gerente": bool((p.get("gerente_email") or "").strip()), "tem_sprint": c["sprint_atual"] is not None,
        })
        status = status_de(sinais)
        c.update({
            "_gerente_email": p.get("gerente_email"), "_status": status, "_sinais": sinais,
            "_mapa": mapa, "_feat": feat, "_feat_ant": feat_ant, "_spi": spi_atual, "_spi_ant": mapa[-2]["spi"],
            "_motivos": motivos(sinais), "_diagnostico": diagnostico(status, sinais),
        })
        calculados.append(c)

    emails = sorted({(p.get("gerente_email") or "").strip().lower() for p in todos} - {""},
                    key=lambda e: ((por_email.get(e) or {}).get("nome") or e).casefold())
    gerentes = [{"nome": (por_email.get(e) or {}).get("nome") or e, "email": e} for e in emails]
    return calculados, gerentes, por_email


def montar_acompanhamento(client, subarea: str, agora: datetime | None = None, gerente_email: str | None = None) -> dict:
    itens, gerentes, por_email = carregar_projetos(client, subarea, agora, gerente_email)

    def nome_do_gerente(i: dict) -> str:
        email = (i.get("_gerente_email") or "").strip().lower()
        return ((por_email.get(email) or {}).get("nome") or email) if email else SEM_GERENTE

    fila = sorted((i for i in itens if i["_status"] != "saudavel"),
                  key=lambda i: (ORDEM_STATUS[i["_status"]], -len(i["_sinais"]), (i["nome"] or "").casefold()))
    status_por_id = {i["id"]: i["_status"] for i in itens}
    por_gerente = [{
        "nome": g["gerente"]["nome"], "email": g["gerente"]["email"],
        "projetos": g["resumo"]["projetos"],
        "criticos": sum(1 for p in g["projetos"] if status_por_id[p["id"]] == "critico"),
        "atencao": sum(1 for p in g["projetos"] if status_por_id[p["id"]] == "atencao"),
        "metas_batidas": g["resumo"]["metas_batidas"], "metas_fechadas": g["resumo"]["metas_fechadas"],
    } for g in agrupar_por_gerente(itens, por_email)]
    com_datas = [i for i in itens if not i["prazo_escopo"].get("sem_dados")]
    ordenados = sorted(itens, key=lambda i: (i["nome"] or "").casefold())
    return {
        "subarea": subarea, "filtro_gerente": gerente_email, "gerentes": gerentes,
        "kpis": montar_kpis(itens),
        "fila": [{"projeto_id": i["id"], "nome": i["nome"], "gerente": nome_do_gerente(i),
                  "status": i["_status"], "motivos": i["_motivos"]} for i in fila],
        "mapa": [{"projeto_id": i["id"], "nome": i["nome"], "sprints": i["_mapa"]} for i in ordenados],
        "dispersao": {
            "pontos": [{"projeto_id": i["id"], "nome": i["nome"],
                        "pct_prazo": i["prazo_escopo"]["pct_prazo_consumido"],
                        "pct_escopo": i["prazo_escopo"]["pct_escopo_concluido"],
                        "travadas": i["saude"]["tasks_travadas"], "status": i["_status"]} for i in com_datas],
            "sem_datas": len(itens) - len(com_datas),
        },
        "por_gerente": por_gerente,
        "projetos": [{"id": i["id"], "nome": i["nome"], "status": i["_status"],
                      "motivos": i["_motivos"], "diagnostico": i["_diagnostico"]} for i in ordenados],
    }
