from datetime import date, datetime, timezone
from statistics import mean, quantiles

from fastapi import APIRouter, HTTPException

from services.supabase_client import get_client

router = APIRouter(prefix="/projects", tags=["painel"])


def _parse_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val)[:10])
    except Exception:
        return None


def _parse_dt(val) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return None


def calcular_bloco_a(proj: dict, funcs: list[dict]) -> dict:
    data_inicio = _parse_date(proj.get("data_inicio"))
    data_fim = _parse_date(proj.get("data_fim_contratada"))

    if data_inicio is None or data_fim is None:
        return {"sem_dados": True}

    hoje = date.today()
    total_dias = (data_fim - data_inicio).days
    pct_prazo = 0.0
    if total_dias > 0:
        dias_consumidos = max((hoje - data_inicio).days, 0)
        pct_prazo = round(min(dias_consumidos / total_dias * 100, 100.0), 1)

    total_funcs = len(funcs)
    concluidas = sum(1 for f in funcs if f.get("status") == "concluida")
    aprovadas = sum(1 for f in funcs if f.get("status_cliente") == "aprovado")

    pct_escopo = round(concluidas / total_funcs * 100, 1) if total_funcs > 0 else 0.0
    pct_aprovado = round(aprovadas / total_funcs * 100, 1) if total_funcs > 0 else 0.0

    tolerancia = proj.get("tolerancia_desvio_pontos") or 0
    desvio = pct_prazo - pct_aprovado
    desvio_detectado = desvio > tolerancia

    return {
        "sem_dados": False,
        "pct_prazo_consumido": pct_prazo,
        "pct_escopo_concluido": pct_escopo,
        "pct_aprovado_cliente": pct_aprovado,
        "desvio_detectado": desvio_detectado,
        "desvio_pontos": round(desvio, 1),
    }


def calcular_bloco_b(funcs: list[dict], transicoes: list[dict], revisao_recente: dict | None = None, execucoes_aceite: list[dict] | None = None) -> dict:
    hoje = datetime.now(timezone.utc)

    ultima_transicao_status: dict[str, datetime] = {}
    ultima_ts_enviado: dict[str, datetime] = {}

    for t in transicoes:
        fid = t.get("funcionalidade_id")
        if not fid:
            continue
        campo = t.get("campo")
        ts = _parse_dt(t.get("timestamp"))
        if ts is None:
            continue

        if campo == "status":
            ultima_transicao_status[fid] = ts

        if campo == "status_cliente" and t.get("para") == "enviado":
            prev = ultima_ts_enviado.get(fid)
            if prev is None or ts > prev:
                ultima_ts_enviado[fid] = ts

    travadas = []
    aguardando_cliente = []
    em_ajuste = []

    for f in funcs:
        fid = f.get("id")
        status = f.get("status")
        status_cliente = f.get("status_cliente")
        titulo = f.get("titulo", "")

        if status == "em_andamento":
            ref_ts = ultima_transicao_status.get(fid)
            if ref_ts is None:
                created_dt = _parse_dt(f.get("created_at"))
                ref_ts = created_dt if created_dt else hoje
            dias = (hoje - ref_ts).days
            if dias > 7:
                travadas.append({"id": fid, "titulo": titulo, "dias": dias})

        if status_cliente == "enviado" and fid in ultima_ts_enviado:
            ts_enviado = ultima_ts_enviado[fid]
            dias_corridos = (hoje - ts_enviado).days
            dias_uteis = round(dias_corridos * 5 / 7, 1)
            if dias_uteis > 5:
                aguardando_cliente.append({"id": fid, "titulo": titulo, "dias_uteis": dias_uteis})

        if status == "em_ajuste":
            em_ajuste.append({"id": fid, "titulo": titulo})

    if revisao_recente:
        achados_raw: list[dict] = revisao_recente.get("achados") or []
        achados_criticos = [
            a for a in achados_raw
            if a.get("severidade") in ("CRITICA", "ALTA") and a.get("confianca") == "ALTA"
        ]
        relatorio_gerente = revisao_recente.get("relatorio_gerente")
        relatorio_tecnico = revisao_recente.get("relatorio_tecnico")
        data_revisao = revisao_recente.get("data_revisao")
    else:
        achados_criticos = []
        relatorio_gerente = None
        relatorio_tecnico = None
        data_revisao = None

    # Calcular funcionalidades concluídas com suíte de aceite falhando (per D-09)
    aceite_por_func: dict[str, dict] = {}
    for ea in (execucoes_aceite or []):
        fid = ea.get("funcionalidade_id")
        if fid:
            aceite_por_func[fid] = ea

    funcionalidades_com_aceite_falhando = []
    for f in funcs:
        if f.get("status") != "concluida":
            continue
        fid = f.get("id")
        ea = aceite_por_func.get(fid)
        if ea and ea.get("concluido_em"):
            gates: list[dict] = ea.get("gates") or []
            tem_falha = any(g.get("resultado") in ("falhou", "erro") for g in gates)
            if tem_falha:
                funcionalidades_com_aceite_falhando.append({"id": fid, "titulo": f.get("titulo", "")})

    return {
        "travadas": travadas,
        "aguardando_cliente": aguardando_cliente,
        "em_ajuste": em_ajuste,
        "achados_criticos": achados_criticos,
        "relatorio_gerente": relatorio_gerente,
        "relatorio_tecnico": relatorio_tecnico,
        "data_revisao": data_revisao,
        "funcionalidades_com_aceite_falhando": funcionalidades_com_aceite_falhando,
    }


def _calcular_cobertura_aceite(funcs: list[dict], execucoes_aceite: list[dict]) -> float | None:
    """Calcula a porcentagem de funcionalidades concluídas com cobertura de aceite (per D-10)."""
    concluidas = [f for f in funcs if f.get("status") == "concluida"]
    if not concluidas:
        return None
    aceite_por_func: dict[str, dict] = {ea["funcionalidade_id"]: ea for ea in execucoes_aceite if ea.get("funcionalidade_id")}
    com_cobertura = sum(
        1 for f in concluidas
        if f.get("id") in aceite_por_func and aceite_por_func[f["id"]].get("concluido_em")
    )
    return round(com_cobertura / len(concluidas) * 100, 1)


def calcular_bloco_c(funcs: list[dict], transicoes: list[dict]) -> dict:
    trans_by_func: dict[str, list[dict]] = {}
    for t in transicoes:
        fid = t.get("funcionalidade_id")
        if fid:
            trans_by_func.setdefault(fid, []).append(t)

    cycle_times: list[float] = []
    for f in funcs:
        if f.get("status") != "concluida":
            continue
        fid = f.get("id")
        ts_list = trans_by_func.get(fid, [])

        ts_inicio = None
        ts_fim = None
        for t in ts_list:
            if t.get("campo") == "status" and t.get("para") == "em_andamento" and ts_inicio is None:
                ts_inicio = _parse_dt(t.get("timestamp"))
            if t.get("campo") == "status" and t.get("para") == "concluida":
                ts_fim = _parse_dt(t.get("timestamp"))

        if ts_inicio and ts_fim and ts_fim > ts_inicio:
            ct = (ts_fim - ts_inicio).total_seconds() / 86400
            cycle_times.append(ct)

    wip = sum(1 for f in funcs if f.get("status") in ("em_andamento", "em_ajuste"))

    now = datetime.now(timezone.utc)
    created_dates = [_parse_dt(f.get("created_at")) for f in funcs if f.get("created_at")]
    created_dates = [d for d in created_dates if d is not None]
    if created_dates:
        earliest = min(created_dates)
        weeks = max((now - earliest).days / 7, 1)
    else:
        weeks = 1

    total_concluidas = len(cycle_times)
    throughput = round(total_concluidas / weeks, 2) if weeks > 0 else 0.0

    p50 = None
    p85 = None
    if len(cycle_times) >= 2:
        p50 = round(quantiles(cycle_times, n=100)[49], 1)
        p85 = round(quantiles(cycle_times, n=100)[84], 1)
    elif len(cycle_times) == 1:
        p50 = round(cycle_times[0], 1)
        p85 = round(cycle_times[0], 1)

    return {
        "throughput_por_semana": throughput,
        "wip": wip,
        "cycle_time_p50_dias": p50,
        "cycle_time_p85_dias": p85,
        "total_concluidas": total_concluidas,
    }


def calcular_bloco_d(funcs: list[dict], transicoes: list[dict]) -> dict:
    from collections import defaultdict

    now = datetime.now(timezone.utc)
    duracoes_por_fase: dict[str, list[float]] = defaultdict(list)
    detalhe: dict[str, dict[str, float]] = {}

    for t in transicoes:
        dur = t.get("duracao_fase_anterior_segundos")
        if dur is None:
            continue
        campo = t.get("campo")
        if campo != "status":
            continue
        fase = t.get("de")
        if not fase:
            continue
        fid = t.get("funcionalidade_id")
        dias = dur / 86400
        duracoes_por_fase[fase].append(dias)
        if fid:
            if fid not in detalhe:
                detalhe[fid] = {}
            detalhe[fid][fase] = detalhe[fid].get(fase, 0) + dias

    fases_resumo = {}
    for fase, vals in duracoes_por_fase.items():
        media = round(mean(vals), 1)
        p85_val = None
        if len(vals) >= 2:
            p85_val = round(quantiles(vals, n=100)[84], 1)
        elif len(vals) == 1:
            p85_val = round(vals[0], 1)
        fases_resumo[fase] = {
            "media_dias": media,
            "p85_dias": p85_val,
            "amostras": len(vals),
        }

    trans_by_func: dict[str, list[dict]] = {}
    for t in transicoes:
        fid = t.get("funcionalidade_id")
        if fid:
            trans_by_func.setdefault(fid, []).append(t)

    eficiencias = []
    for f in funcs:
        fid = f.get("id")
        ts_list = trans_by_func.get(fid, [])

        tempo_andamento = 0.0
        tempo_total = 0.0
        for t in ts_list:
            dur = t.get("duracao_fase_anterior_segundos")
            if dur is None:
                continue
            if t.get("campo") == "status":
                tempo_total += dur / 86400
                if t.get("de") == "em_andamento":
                    tempo_andamento += dur / 86400

        if tempo_total <= 0:
            created = _parse_dt(f.get("created_at"))
            if created:
                tempo_total = (now - created).total_seconds() / 86400

        if tempo_total > 0:
            eficiencias.append(tempo_andamento / tempo_total * 100)

    eficiencia_media = round(mean(eficiencias), 1) if eficiencias else None

    func_map = {f["id"]: f for f in funcs if f.get("id")}
    detalhe_list = []
    for fid, tempos in detalhe.items():
        if fid in func_map:
            detalhe_list.append({
                "id": fid,
                "titulo": func_map[fid].get("titulo", ""),
                "tempos_por_fase": {k: round(v, 2) for k, v in tempos.items()},
            })

    return {
        "fases_resumo": fases_resumo,
        "eficiencia_fluxo_pct": eficiencia_media,
        "detalhe_por_funcionalidade": detalhe_list,
    }


@router.get("/{project_id}/painel")
async def get_painel(project_id: str):
    client = get_client()

    proj_result = client.table("projects").select("*").eq("id", project_id).single().execute()
    if not proj_result.data:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    proj = proj_result.data

    func_result = client.table("funcionalidades").select("*").eq("project_id", project_id).execute()
    func_list: list[dict] = func_result.data or []

    trans_list: list[dict] = []
    if func_list:
        func_ids = [f["id"] for f in func_list]
        trans_result = (
            client.table("transicoes_status")
            .select("*")
            .in_("funcionalidade_id", func_ids)
            .order("timestamp", desc=False)
            .execute()
        )
        trans_list = trans_result.data or []

    revisao_resp = (
        client.table("revisoes_diarias")
        .select("achados, relatorio_gerente, relatorio_tecnico, data_revisao")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    revisao_recente = revisao_resp.data[0] if revisao_resp.data else None

    # Buscar execuções de aceite para calcular cobertura (per D-09, D-10)
    execucoes_resp = (
        client.table("execucoes_aceite")
        .select("funcionalidade_id, commit_sha, gates, disparado_em, concluido_em")
        .eq("project_id", project_id)
        .order("disparado_em", desc=True)
        .execute()
    )
    execucoes_aceite_raw: list[dict] = execucoes_resp.data or []

    # Deduplica mantendo apenas a execução mais recente por funcionalidade_id
    # (query já está ordenada DESC por disparado_em, então o primeiro de cada func é o mais recente)
    seen_func_ids: set[str] = set()
    execucoes_aceite_list: list[dict] = []
    for ea in execucoes_aceite_raw:
        fid = ea.get("funcionalidade_id")
        if fid and fid not in seen_func_ids:
            seen_func_ids.add(fid)
            execucoes_aceite_list.append(ea)

    bloco_a = calcular_bloco_a(proj, func_list)
    bloco_b = calcular_bloco_b(func_list, trans_list, revisao_recente, execucoes_aceite=execucoes_aceite_list)
    bloco_c = calcular_bloco_c(func_list, trans_list)
    bloco_d = calcular_bloco_d(func_list, trans_list)

    # cobertura_aceite é campo separado no response root — NÃO altera pct_escopo_concluido (per D-10)
    cobertura_aceite = _calcular_cobertura_aceite(func_list, execucoes_aceite_list)

    return {
        "bloco_a": bloco_a,
        "bloco_b": bloco_b,
        "bloco_c": bloco_c,
        "bloco_d": bloco_d,
        "cobertura_aceite": cobertura_aceite,
    }
