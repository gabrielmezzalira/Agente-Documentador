"""Tela de acompanhamento do classificador de nível (spec A2 §7). Só líder/owner."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import ExclusaoAprendizadoPayload
from services.auth import require_role
from services.classificador_aprendizado import definir_exclusao, parametros_vigentes_com_amostras
from services.classificador_ciclo import classificacao_atual
from services.classificador_estatistica import metricas_acuracia
from services.supabase_client import get_client
from services.supabase_paginacao import ler_tudo

router = APIRouter(prefix="/classificador", tags=["classificador"], dependencies=[Depends(require_role("lider"))])

_LOTE_IN = 100
_NIVEIS = (1, 2, 3, 5)
_COLUNAS_EXEMPLO = (
    "task_id, nivel_sugerido, nivel_real, nivel_pelo_tempo, tempo_normalizado_s, alerta, excluida, "
    "excluida_em, motivo_exclusao, gerente_id, operacional_id, opiniao_operacional, classificacao_id, concluida_em"
)


def _semana(iso: str) -> str:
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    return (d - timedelta(days=d.weekday())).isoformat()


def _mes(iso: str) -> str:
    return iso[:7]


def _dia(iso: str) -> str:
    return iso[:10]


def _em_lotes(client, tabela: str, colunas: str, coluna_id: str, ids: list[str]) -> list[dict]:
    ids = list(dict.fromkeys(i for i in ids if i))
    saida: list[dict] = []
    for i in range(0, len(ids), _LOTE_IN):
        saida += client.table(tabela).select(colunas).in_(coluna_id, ids[i:i + _LOTE_IN]).execute().data or []
    return saida


def _titulos_projetos(client, task_ids: list[str]) -> dict[str, dict]:
    tasks = _em_lotes(client, "tasks", "id, titulo, project_id", "id", task_ids)
    projetos = {p["id"]: p["name"] for p in _em_lotes(client, "projects", "id, name", "id", [t["project_id"] for t in tasks])}
    return {t["id"]: {"titulo": t.get("titulo"), "projeto": projetos.get(t.get("project_id"))} for t in tasks}


def _ultimo_por_grupo(linhas: list[dict], grupo) -> dict:
    """Último valor (por criado_em) de cada grupo."""
    saida: dict = {}
    for l in sorted(linhas, key=lambda r: r["criado_em"]):
        saida[grupo(l)] = l
    return saida


def _opinioes(exemplos: list[dict], opiniao_de, chave_pessoa: str, params, tipo: str, nomes: dict) -> list[dict]:
    por_pessoa: dict[str, list[int]] = {}
    for e in exemplos:
        op, pessoa = opiniao_de(e), e.get(chave_pessoa)
        if op is None or not pessoa or e.get("nivel_pelo_tempo") is None:
            continue
        h = por_pessoa.setdefault(pessoa, [0, 0])
        h[1] += 1
        h[0] += int(op == e["nivel_pelo_tempo"])
    return [
        {"pessoa_id": p, "nome": nomes.get(p), "peso": params.get((tipo, p), (0.0, 0))[0],
         "acuracia": a / n, "n": n}
        for p, (a, n) in sorted(por_pessoa.items())
    ]


@router.get("/resumo")
def resumo(periodo: str = Query("tudo", pattern="^(30|90|tudo)$"), gerente_id: str | None = None):
    client = get_client()
    todos = ler_tudo(lambda: client.table("task_aprendizado").select(_COLUNAS_EXEMPLO).order("task_id"))
    params = parametros_vigentes_com_amostras(client)

    # Médias por nível: todas as tasks (inclusive excluídas) x as que contam.
    medias = []
    for nivel in _NIVEIS:
        do_nivel = [e for e in todos if e.get("nivel_real") == nivel]
        tempos = [float(e["tempo_normalizado_s"]) for e in do_nivel if (e.get("tempo_normalizado_s") or 0) > 0]
        sem_excl, n_param = params.get(("media_nivel", str(nivel)), (0.0, 0))
        medias.append({
            "nivel": nivel,
            "media_s": sum(tempos) / len(tempos) if tempos else 0,
            "media_sem_excluidas_s": sem_excl if n_param > 0 else 0,
            "n": sum(1 for e in do_nivel if not e.get("excluida")),
            "n_total": len(do_nivel),
        })

    corte = None
    if periodo != "tudo":
        corte = (datetime.now(timezone.utc) - timedelta(days=int(periodo))).isoformat()
    filtrados = [
        e for e in todos
        if (corte is None or (e.get("concluida_em") or "") >= corte)
        and (gerente_id is None or e.get("gerente_id") == gerente_id)
    ]
    validos = [e for e in filtrados if not e.get("excluida") and e.get("nivel_real") is not None]
    acuracia = metricas_acuracia([(e["nivel_sugerido"], e["nivel_real"]) for e in validos])
    por_mes: dict[str, list[tuple[int, int]]] = {}
    for e in validos:
        por_mes.setdefault(_mes(e["concluida_em"]), []).append((e["nivel_sugerido"], e["nivel_real"]))
    evolucao_acuracia = [
        {"mes": m, "mais_menos_um": metricas_acuracia(p)["mais_menos_um"], "n": len(p)}
        for m, p in sorted(por_mes.items())
    ]

    alertas_ex = [e for e in filtrados if e.get("alerta") and not e.get("excluida") and e.get("nivel_real") is not None]
    excl_ex = [e for e in todos if e.get("excluida") and (gerente_id is None or e.get("gerente_id") == gerente_id)]
    info = _titulos_projetos(client, [e["task_id"] for e in alertas_ex + excl_ex])

    # Nomes: gerentes via pessoa; operacionais via operacionais (aprendizado.operacional_id aponta para lá).
    ids_gerentes = {e["gerente_id"] for e in todos if e.get("gerente_id")} | {k[1] for k in params if k[0] in ("vies_gerente", "peso_opiniao_gerente")}
    ids_ops = {e["operacional_id"] for e in todos if e.get("operacional_id")} | {k[1] for k in params if k[0] in ("ritmo_pessoa", "peso_opiniao_operacional")}
    nomes_g = {p["id"]: p["nome"] for p in _em_lotes(client, "pessoa", "id, nome", "id", list(ids_gerentes))}
    nomes_o = {o["id"]: o["nome"] for o in _em_lotes(client, "operacionais", "id, nome", "id", list(ids_ops))}

    alertas = []
    for e in alertas_ex:
        i = info.get(e["task_id"], {})
        alertas.append({
            "task_id": e["task_id"], "titulo": i.get("titulo"), "projeto": i.get("projeto"),
            "operacional": nomes_o.get(e.get("operacional_id")),
            "tempo_normalizado_s": e.get("tempo_normalizado_s"),
            "media_nivel_s": params.get(("media_nivel", str(e["nivel_real"])), (0.0, 0))[0],
            "nivel_real": e["nivel_real"],
        })
    excluidas = [{
        "task_id": e["task_id"], "titulo": info.get(e["task_id"], {}).get("titulo"),
        "motivo_exclusao": e.get("motivo_exclusao"), "excluida_em": e.get("excluida_em"),
    } for e in excl_ex]

    hist = ler_tudo(lambda: (
        client.table("classificador_parametros_hist").select("tipo, chave, valor, criado_em")
        .in_("tipo", ["media_nivel", "peso_sinal"]).order("criado_em").order("id")
    ))
    evolucao_medias = [
        {"semana": s, "nivel": int(c), "media_s": float(l["valor"])}
        for (t, c, s), l in sorted(_ultimo_por_grupo(
            [h for h in hist if h["tipo"] == "media_nivel"], lambda h: (h["tipo"], h["chave"], _semana(h["criado_em"]))
        ).items(), key=lambda kv: (kv[0][2], kv[0][1]))
    ]
    evolucao_pesos = [
        {"data": d, "sinal": c, "peso": float(l["valor"])}
        for (t, c, d), l in sorted(_ultimo_por_grupo(
            [h for h in hist if h["tipo"] == "peso_sinal"], lambda h: (h["tipo"], h["chave"], _dia(h["criado_em"]))
        ).items(), key=lambda kv: (kv[0][2], kv[0][1]))
    ]

    opiniao_gerente = {
        e["task_id"]: None for e in validos  # preenchido abaixo
    }
    clas = _em_lotes(client, "task_classificacoes", "id, opiniao_gerente", "id", [e["classificacao_id"] for e in validos if e.get("classificacao_id")])
    por_clas = {c["id"]: c.get("opiniao_gerente") for c in clas}
    for e in validos:
        opiniao_gerente[e["task_id"]] = por_clas.get(e.get("classificacao_id"))

    return {
        "medias": medias,
        "evolucao_medias": evolucao_medias,
        "alertas": alertas,
        "excluidas": excluidas,
        "acuracia": acuracia,
        "evolucao_acuracia": evolucao_acuracia,
        "pesos_sinais": [{"sinal": k[1], "peso": v[0]} for k, v in sorted(params.items()) if k[0] == "peso_sinal"],
        "evolucao_pesos": evolucao_pesos,
        "vies_gerentes": [
            {"gerente_id": k[1], "nome": nomes_g.get(k[1]), "vies": v[0], "n": v[1]}
            for k, v in sorted(params.items()) if k[0] == "vies_gerente"
        ],
        "opinioes": {
            "gerentes": _opinioes(validos, lambda e: opiniao_gerente.get(e["task_id"]), "gerente_id", params, "peso_opiniao_gerente", nomes_g),
            "operacionais": _opinioes(validos, lambda e: e.get("opiniao_operacional"), "operacional_id", params, "peso_opiniao_operacional", nomes_o),
        },
        "ritmos": [
            {"pessoa_id": k[1], "nome": nomes_o.get(k[1]), "ritmo": v[0], "n": v[1]}
            for k, v in sorted(params.items()) if k[0] == "ritmo_pessoa"
        ],
        "gerentes": [{"id": g, "nome": nomes_g.get(g)} for g in sorted({e["gerente_id"] for e in todos if e.get("gerente_id")})],
    }


@router.get("/revisao")
def revisao():
    client = get_client()
    candidatas = ler_tudo(lambda: (
        client.table("task_classificacoes").select("task_id, criado_em")
        .in_("status", ["em_revisao", "provisoria"]).order("criado_em").order("id")
    ))
    ids = list(dict.fromkeys(c["task_id"] for c in candidatas))
    atuais: dict[str, dict] = {}
    for i in range(0, len(ids), _LOTE_IN):
        linhas = ler_tudo(lambda: (
            client.table("task_classificacoes")
            .select("task_id, status, nivel_final, motivo_revisao, criado_em")
            .in_("task_id", ids[i:i + _LOTE_IN]).order("criado_em", desc=True).order("id")
        ))
        for l in linhas:  # decrescente: a primeira de cada task é a atual
            atuais.setdefault(l["task_id"], l)
    pendentes = [l for l in atuais.values() if l["status"] in ("em_revisao", "provisoria")]
    info = _titulos_projetos(client, [l["task_id"] for l in pendentes])
    return [
        {"task_id": l["task_id"], "titulo": info.get(l["task_id"], {}).get("titulo"),
         "projeto": info.get(l["task_id"], {}).get("projeto"), "status": l["status"],
         "nivel_final": l.get("nivel_final"), "motivo_revisao": l.get("motivo_revisao"), "criado_em": l["criado_em"]}
        for l in pendentes
    ]


@router.get("/tasks/{task_id}")
def detalhe_task(task_id: str):
    client = get_client()
    atual = classificacao_atual(client, task_id)
    if atual is None:
        raise HTTPException(status_code=404, detail="Task sem classificação")
    parecidas = list(atual.get("parecidas") or [])
    titulos = {t["id"]: t.get("titulo") for t in _em_lotes(client, "tasks", "id, titulo", "id", [p.get("task_id") for p in parecidas])}
    atual["parecidas"] = [{**p, "titulo": titulos.get(p.get("task_id"))} for p in parecidas]
    exemplo = client.table("task_aprendizado").select("*").eq("task_id", task_id).execute().data
    return {"classificacao": atual, "aprendizado": exemplo[0] if exemplo else None}


@router.patch("/aprendizado/{task_id}")
def excluir_exemplo(task_id: str, payload: ExclusaoAprendizadoPayload, pessoa: dict = Depends(require_role("lider"))):
    client = get_client()
    existe = client.table("task_aprendizado").select("task_id").eq("task_id", task_id).execute().data
    if not existe:
        raise HTTPException(status_code=404, detail="Exemplo não encontrado")
    return definir_exclusao(client, task_id, payload.excluida, payload.motivo, pessoa["id"])
