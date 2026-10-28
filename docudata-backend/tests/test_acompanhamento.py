from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import routers.acompanhamento as rota
from services.acompanhamento import (
    montar_kpis,
    agrupar_por_gerente, calcular_projeto, features_entregues_na_janela, janela_da_sprint, p85, pct_tasks,
    previsto_de, resumo_do_grupo, sprints_relativas, variacao,
)
from services.previsto_sprint import previsto_da_sprint
from tests.fake_supabase import FakeClient


def func(i, status="em_andamento", aprovada_em=None):
    return {"id": i, "id_funcional": i.upper(), "titulo": f"Func {i}", "status": status, "aprovada_em": aprovada_em}


def task(i, pontos=2, **kw):
    return {"id": i, "pontos": pontos, "extra": False, "coluna_kanban": "backlog", "prevista_no_inicio": False,
            "surgiu_na_sprint": False, "travado_automatico": False, **kw}


def proj(**kw):
    return {"id": "p", "name": "Proj", "client": "Cli", "data_inicio": None, "data_fim_contratada": None,
            "tolerancia_desvio_pontos": 20, **kw}


def sprint(i, numero, **kw):
    return {"id": i, "numero": numero, "iniciada": True, "avaliacao_completa_em": None, **kw}


def calc(sprints, funcs, tasks=(), planejadas=None, metas=None, horas=(), projeto=None):
    return calcular_projeto(projeto or proj(), list(sprints), list(funcs), list(tasks), planejadas or {}, metas or {}, list(horas))


# ── puras ──

def test_pct_tasks():
    assert pct_tasks([]) is None
    assert pct_tasks([task("a", extra=True, coluna_kanban="concluida")]) is None
    ts = [task("a", coluna_kanban="concluida"), task("b"), task("c"), task("x", extra=True, coluna_kanban="concluida")]
    assert pct_tasks(ts) == 33.3


def test_p85():
    assert p85([]) is None
    assert p85([30.0]) == 30.0
    assert p85(list(range(1, 101))) == pytest.approx(85.85, abs=0.1)


def test_previsto_de_bate_com_previsto_da_sprint():
    tasks = [
        task("a", 3, prevista_no_inicio=True),
        task("b", 2, surgiu_na_sprint=True),
        task("c", 5, extra=True, prevista_no_inicio=True),
        task("d", 4, extra=True, surgiu_na_sprint=True),
        task("e", 1, surgiu_na_sprint=True, prevista_no_inicio=True),
        task("f", 8),
    ]
    client = FakeClient({"tasks": [{**t, "sprint_id": "s1"} for t in tasks]})
    assert previsto_de(tasks) == previsto_da_sprint(client, "s1")["previsto"] == 6


def test_meta_x_planejado_e_listas_de_divergencia():
    funcs = [func("f1"), func("f2"), func("f3", "concluida", "2026-10-01T00:00:00+00:00")]
    tasks = [task("t1", funcionalidade_id="f1", coluna_kanban="concluida"), task("t2", funcionalidade_id="f1")]
    r = calc([sprint("s", 2)], funcs, tasks, planejadas={"s": {"f2", "f3"}}, metas={"s": {"f1", "f2"}})
    assert r["sprint_atual"] == {"id": "s", "numero": 2, "fechada": False}
    assert r["meta"]["total"] == 2 and r["meta"]["entregues"] == 0 and r["meta"]["batida"] is False
    assert [f["id_funcional"] for f in r["meta"]["funcionalidades"]] == ["F1", "F2"]
    f1, f2 = r["meta"]["funcionalidades"]
    assert (f1["planejada_na_sprint"], f1["pct_tasks"], f1["aprovada"]) == (False, 50.0, False)
    assert (f2["planejada_na_sprint"], f2["pct_tasks"]) == (True, None)
    assert r["planejadas_fora_da_meta"] == [{"id": "f3", "id_funcional": "F3", "titulo": "Func f3"}]
    assert r["planejado"]["funcs_planejadas"] == 2 and r["planejado"]["funcs_planejadas_entregues"] == 1


def test_sem_sprint_e_sem_meta():
    r = calc([], [func("f1")])
    assert r["sprint_atual"] is None and r["ultima_fechada"] is None
    assert r["meta"] == {"total": 0, "entregues": 0, "batida": None, "funcionalidades": []}
    assert r["riscos"] == []


def test_atual_e_proximas():
    r = calc([sprint("a", 1), sprint("b", 2), sprint("c", 3, iniciada=False), sprint("d", 4, iniciada=False)], [])
    assert r["sprint_atual"]["numero"] == 2
    assert [s["numero"] for s in r["proximas_sprints"]] == [3, 4]


def test_ultima_fechada_respeita_aprovada_em_posterior_ao_fechamento():
    funcs = [func("f1", "concluida", "2026-10-09T10:00:00+00:00"), func("f2", "concluida", "2026-10-11T10:00:00+00:00")]
    s = sprint("s", 1, avaliacao_completa_em="2026-10-10T00:00:00+00:00")
    r = calc([s], funcs, metas={"s": {"f1", "f2"}})
    assert r["ultima_fechada"] == {"numero": 1, "meta_total": 2, "meta_entregues": 1, "meta_batida": False, "spi": None}


def test_risco_a_prazo_a_frente_do_escopo():
    p = proj(data_inicio="2020-01-01", data_fim_contratada="2020-12-31")
    r = calc([sprint("s", 1)], [func("f1")], projeto=p)
    assert r["riscos"] == ["prazo à frente do escopo"]


def test_risco_b_meta_abaixo_de_50():
    s = sprint("s", 1, avaliacao_completa_em="2026-10-10T00:00:00+00:00")
    funcs = [func("f1", "concluida", "2026-10-01T00:00:00+00:00"), func("f2"), func("f3")]
    r = calc([s], funcs, metas={"s": {"f1", "f2", "f3"}})
    assert r["riscos"] == ["meta da última sprint abaixo de 50%"]
    r = calc([s], funcs[:2], metas={"s": {"f1", "f2"}})
    assert r["riscos"] == []  # exatamente 50% não dispara


def test_risco_c_spi_abaixo_de_0_7():
    s = sprint("s", 1, avaliacao_completa_em="2026-10-10T00:00:00+00:00")
    tasks = [task("a", 3, sprint_id="s", prevista_no_inicio=True, coluna_kanban="concluida"),
             task("b", 7, sprint_id="s", prevista_no_inicio=True)]
    r = calc([s], [], tasks)
    assert r["ultima_fechada"]["spi"] == 0.3
    assert r["riscos"] == ["SPI da última sprint abaixo de 0,7"]


def test_saude():
    funcs = [func("f1"), func("f2", "nao_iniciada"), func("f3")]
    tasks = [task("a", travado_automatico=True), task("b", travado_automatico=True, coluna_kanban="concluida"), task("c")]
    r = calc([sprint("s", 1)], funcs, tasks, horas=[10.0, 20.0])
    assert r["saude"]["tasks_travadas"] == 1 and r["saude"]["wip"] == 2
    assert r["saude"]["p85_horas"] == p85([10.0, 20.0])


def _p(nome, email, ultima, riscos=(), total=0, aprovadas=0):
    return {"id": nome, "nome": nome, "ultima_fechada": ultima, "riscos": list(riscos),
            "_total_funcs": total, "_funcs_aprovadas": aprovadas, "_gerente_email": email}


def _u(total, entregues):
    return {"numero": 1, "meta_total": total, "meta_entregues": entregues, "meta_batida": (entregues == total) if total else None, "spi": None}


def test_resumo_do_grupo():
    ps = [_p("a", "x", _u(2, 2), total=4, aprovadas=1), _p("b", "x", _u(2, 1), ["r"], total=4, aprovadas=3),
          _p("c", "x", _u(0, 0)), _p("d", "x", None)]
    assert resumo_do_grupo(ps) == {"projetos": 4, "em_risco": 1, "metas_fechadas": 2, "metas_batidas": 1,
                                   "pct_funcs_aprovadas": 50.0}


def test_ordem_dos_grupos_e_sem_gerente_por_ultimo():
    ps = [_p("Zeta", None, None), _p("Beta", "bia@x.com", None), _p("Alfa", "BIA@x.com", None), _p("Mid", "ana@x.com", None)]
    pessoas = {"bia@x.com": {"nome": "Bia"}, "ana@x.com": {"nome": "Ana"}}
    g = agrupar_por_gerente(ps, pessoas)
    assert [x["gerente"]["nome"] for x in g] == ["Ana", "Bia", "Sem gerente"]
    assert [p["nome"] for p in g[1]["projetos"]] == ["Alfa", "Beta"]
    assert g[2]["gerente"]["email"] is None
    assert all(not k.startswith("_") for k in g[0]["projetos"][0])


# ── puras do dashboard ──

def test_sprints_relativas_com_duas_e_com_oito():
    r = sprints_relativas([sprint("b", 2), sprint("a", 1), sprint("c", 3, iniciada=False)])
    assert [(x["rel"], x["numero"], x["id"]) for x in r] == [(0, 2, "b"), (-1, 1, "a")]
    r = sprints_relativas([sprint(f"s{n}", n) for n in range(1, 9)])
    assert [(x["rel"], x["numero"]) for x in r] == [(0, 8), (-1, 7), (-2, 6), (-3, 5), (-4, 4), (-5, 3)]
    assert sprints_relativas([]) == []


AGORA = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def test_janela_da_sprint():
    s = sprint("s", 2, data_inicio="2026-10-01", avaliacao_completa_em="2026-10-15T10:00:00+00:00")
    assert janela_da_sprint(s, None, AGORA) == (datetime(2026, 10, 1, tzinfo=timezone.utc),
                                                datetime(2026, 10, 15, 10, tzinfo=timezone.utc))
    # sem fechamento: até agora; sem data_inicio: fechamento da anterior; sem nenhum: None
    aberta = sprint("s", 2)
    ant = sprint("a", 1, avaliacao_completa_em="2026-09-30T00:00:00+00:00")
    assert janela_da_sprint(aberta, ant, AGORA) == (datetime(2026, 9, 30, tzinfo=timezone.utc), AGORA)
    assert janela_da_sprint(aberta, None, AGORA) == (None, AGORA)
    assert janela_da_sprint(aberta, sprint("a", 1), AGORA) == (None, AGORA)


def test_features_entregues_na_janela_limites():
    ini, fim = datetime(2026, 10, 1, tzinfo=timezone.utc), datetime(2026, 10, 15, tzinfo=timezone.utc)
    funcs = [func("a", "concluida", "2026-10-01T00:00:00+00:00"), func("b", "concluida", "2026-10-15T00:00:00+00:00"),
             func("c", "concluida", "2026-10-10T00:00:00+00:00"), func("d", "concluida", "2026-09-30T23:59:59+00:00"),
             func("e", "em_andamento", "2026-10-10T00:00:00+00:00"), func("f", "concluida", None)]
    assert features_entregues_na_janela(funcs, ini, fim) == 2
    assert features_entregues_na_janela(funcs, None, fim) is None


def test_variacao():
    assert variacao(0.78, 0.87) == -0.09
    assert variacao(4, 2) == 2
    assert variacao(None, 1) is None and variacao(1, None) is None


# ── rota ──

def _fake():
    agora = AGORA
    recente = (agora - timedelta(days=2)).isoformat()
    antigo = (agora - timedelta(days=60)).isoformat()
    return FakeClient({
        "pessoa": [{"id": "g1", "nome": "Ana", "email": "ana@citi.org.br"},
                   {"id": "g2", "nome": "Bruno", "email": "bruno@citi.org.br"}],
        "projects": [
            {"id": "p1", "name": "Alfa", "client": "C1", "subarea": "dados", "gerente_email": "ANA@citi.org.br",
             "data_inicio": "2020-01-01", "data_fim_contratada": "2020-12-31", "tolerancia_desvio_pontos": 20},
            {"id": "p2", "name": "Beta", "client": "C2", "subarea": "dados", "gerente_email": "bruno@citi.org.br"},
            {"id": "p3", "name": "Gama", "client": "C3", "subarea": "dados", "gerente_email": None},
            {"id": "p4", "name": "Dev", "client": "C4", "subarea": "dev", "gerente_email": "ana@citi.org.br"},
            {"id": "p5", "name": "Delta", "client": "C5", "subarea": "dados", "gerente_email": "bruno@citi.org.br",
             "data_inicio": "2026-01-01", "data_fim_contratada": "2099-12-31", "tolerancia_desvio_pontos": 20},
        ],
        "sprints": [
            {"id": "s1", "project_id": "p1", "numero": 1, "iniciada": True, "data_inicio": "2026-09-20",
             "avaliacao_completa_em": "2026-10-10T00:00:00+00:00"},
            {"id": "s2", "project_id": "p1", "numero": 2, "iniciada": True, "data_inicio": None, "avaliacao_completa_em": None},
            {"id": "s3", "project_id": "p1", "numero": 3, "iniciada": False, "avaliacao_completa_em": None},
            {"id": "s4", "project_id": "p2", "numero": 1, "iniciada": True, "avaliacao_completa_em": None},
            {"id": "s5", "project_id": "p5", "numero": 1, "iniciada": True, "data_inicio": "2026-10-01", "avaliacao_completa_em": None},
        ],
        "funcionalidades": [
            {"id": "f1", "project_id": "p1", "id_funcional": "F1", "titulo": "A", "status": "concluida", "aprovada_em": "2026-10-09T00:00:00+00:00"},
            {"id": "f2", "project_id": "p1", "id_funcional": "F2", "titulo": "B", "status": "concluida", "aprovada_em": "2026-10-12T00:00:00+00:00"},
            {"id": "f3", "project_id": "p1", "id_funcional": "F3", "titulo": "C", "status": "em_andamento", "aprovada_em": None},
            {"id": "f4", "project_id": "p1", "id_funcional": "F4", "titulo": "D", "status": "nao_iniciada", "aprovada_em": None},
            {"id": "f5", "project_id": "p2", "id_funcional": "F1", "titulo": "E", "status": "em_andamento", "aprovada_em": None},
            {"id": "f6", "project_id": "p5", "id_funcional": "F1", "titulo": "G", "status": "concluida", "aprovada_em": "2026-10-20T00:00:00+00:00"},
        ],
        "tasks": [
            {"id": "t1", "project_id": "p1", "sprint_id": "s2", "funcionalidade_id": "f3", "coluna_kanban": "concluida",
             "extra": False, "pontos": 3, "travado_automatico": False, "prevista_no_inicio": True, "surgiu_na_sprint": False},
            {"id": "t2", "project_id": "p1", "sprint_id": "s2", "funcionalidade_id": "f3", "coluna_kanban": "em_andamento",
             "extra": False, "pontos": 3, "travado_automatico": True, "prevista_no_inicio": True, "surgiu_na_sprint": False},
            {"id": "t3", "project_id": "p1", "sprint_id": "s1", "funcionalidade_id": "f1", "coluna_kanban": "concluida",
             "extra": False, "pontos": 2, "travado_automatico": False, "prevista_no_inicio": True, "surgiu_na_sprint": False},
            {"id": "t5", "project_id": "p5", "sprint_id": "s5", "funcionalidade_id": "f6", "coluna_kanban": "concluida",
             "extra": False, "pontos": 3, "travado_automatico": False, "prevista_no_inicio": True, "surgiu_na_sprint": False},
        ],
        "sprint_funcionalidades": [
            {"id": "x1", "sprint_id": "s2", "funcionalidade_id": "f3"},
            {"id": "x2", "sprint_id": "s2", "funcionalidade_id": "f4"},
            {"id": "x3", "sprint_id": "s5", "funcionalidade_id": "f6"},
        ],
        "sprint_meta_funcionalidades": [
            {"sprint_id": "s1", "funcionalidade_id": "f1"}, {"sprint_id": "s1", "funcionalidade_id": "f2"},
            {"sprint_id": "s2", "funcionalidade_id": "f3"},
            {"sprint_id": "s5", "funcionalidade_id": "f6"},
        ],
        "task_aprendizado": [
            {"task_id": "t1", "tempo_limpo_s": 7200, "concluida_em": recente, "excluida": False},
            {"task_id": "t3", "tempo_limpo_s": 360000, "concluida_em": antigo, "excluida": False},
        ],
    })


def _tc(monkeypatch, autenticar, cargo="lider"):
    from main import app
    fake = _fake()
    monkeypatch.setattr(rota, "get_client", lambda: fake)
    original = rota.montar_acompanhamento
    monkeypatch.setattr(rota, "montar_acompanhamento", lambda *a, **k: original(*a, agora=AGORA, **k))
    return autenticar(TestClient(app), cargo)


def test_rota_kpis_fila_mapa_dispersao_e_gerentes(monkeypatch, autenticar):
    r = _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=dados")
    assert r.status_code == 200
    j = r.json()
    assert j["subarea"] == "dados" and j["filtro_gerente"] is None
    assert j["gerentes"] == [{"nome": "Ana", "email": "ana@citi.org.br"}, {"nome": "Bruno", "email": "bruno@citi.org.br"}]
    k = j["kpis"]
    assert (k["projetos"], k["criticos"], k["atencao"], k["sem_dados"], k["saudaveis"]) == (4, 1, 1, 1, 1)
    # f2 (p1, 12/10) cai na janela da s2 (inicia no fechamento da s1); f6 (p5, 20/10) na da s5
    assert k["features_entregues"] == 2
    assert k["features_entregues_var"] == 0  # só Alfa tem as duas: 1 na s2 e 1 na s1 (f1); Delta não tem -1
    assert k["spi_medio"] == 0.75 and k["spi_medio_var"] == -0.5  # só Alfa tem as duas: 0.5 contra 1.0
    assert (k["metas_fechadas"], k["metas_batidas"], k["projetos_sem_meta"]) == (1, 0, 1)
    assert k["tasks_travadas"] == 1
    assert [f["nome"] for f in j["fila"]] == ["Alfa", "Beta", "Gama"]
    assert [f["status"] for f in j["fila"]] == ["critico", "atencao", "sem_dados"]
    assert j["fila"][0]["gerente"] == "Ana" and j["fila"][2]["gerente"] == "Sem gerente"
    assert j["fila"][0]["motivos"][0] == "SPI 0,5"
    alfa = next(m for m in j["mapa"] if m["nome"] == "Alfa")
    assert [s["rel"] for s in alfa["sprints"]] == [-5, -4, -3, -2, -1, 0]
    assert [s["numero"] for s in alfa["sprints"]] == [None, None, None, None, 1, 2]
    assert alfa["sprints"][4] == {"rel": -1, "numero": 1, "spi": 1.0, "meta_total": 2, "meta_entregues": 1, "meta_batida": False}
    assert alfa["sprints"][5]["spi"] == 0.5 and alfa["sprints"][0]["spi"] is None and alfa["sprints"][0]["meta_batida"] is None
    assert len(j["mapa"]) == 4
    assert j["dispersao"]["sem_datas"] == 2
    assert {p["nome"] for p in j["dispersao"]["pontos"]} == {"Alfa", "Delta"}
    alfa_pt = next(p for p in j["dispersao"]["pontos"] if p["nome"] == "Alfa")
    assert alfa_pt["pct_prazo"] == 100.0 and alfa_pt["pct_escopo"] == 50.0 and alfa_pt["travadas"] == 1
    assert j["por_gerente"] == [
        {"nome": "Ana", "email": "ana@citi.org.br", "projetos": 1, "criticos": 1, "atencao": 0, "metas_batidas": 0, "metas_fechadas": 1},
        {"nome": "Bruno", "email": "bruno@citi.org.br", "projetos": 2, "criticos": 0, "atencao": 1, "metas_batidas": 0, "metas_fechadas": 0},
        {"nome": "Sem gerente", "email": None, "projetos": 1, "criticos": 0, "atencao": 0, "metas_batidas": 0, "metas_fechadas": 0},
    ]
    assert {p["id"] for p in j["projetos"]} == {"p1", "p2", "p3", "p5"}
    delta = next(p for p in j["projetos"] if p["id"] == "p5")
    assert delta["status"] == "saudavel" and delta["diagnostico"] == "Saudável."


def test_rota_filtra_por_gerente_sem_diferenciar_maiusculas(monkeypatch, autenticar):
    j = _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=dados&gerente_email=ANA@citi.org.br").json()
    assert j["filtro_gerente"] == "ANA@citi.org.br"
    assert len(j["gerentes"]) == 2  # a lista do filtro continua completa
    assert j["kpis"]["projetos"] == 1 and [f["nome"] for f in j["fila"]] == ["Alfa"]
    assert [m["nome"] for m in j["mapa"]] == ["Alfa"] and j["dispersao"]["sem_datas"] == 0
    assert [g["nome"] for g in j["por_gerente"]] == ["Ana"]


def test_rota_filtro_sem_gerente(monkeypatch, autenticar):
    j = _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=dados&gerente_email=sem").json()
    assert j["kpis"]["projetos"] == 1 and [f["nome"] for f in j["fila"]] == ["Gama"]
    assert [g["nome"] for g in j["por_gerente"]] == ["Sem gerente"]


def test_rota_dev_so_traz_projetos_dev(monkeypatch, autenticar):
    j = _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=dev").json()
    assert j["kpis"]["projetos"] == 1 and j["projetos"][0]["nome"] == "Dev"


@pytest.mark.parametrize("cargo", ["gerente", "operacional"])
def test_so_lider(monkeypatch, autenticar, cargo):
    assert _tc(monkeypatch, autenticar, cargo).get("/acompanhamento?subarea=dados").status_code == 403


def test_subarea_invalida_422(monkeypatch, autenticar):
    assert _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=produto").status_code == 422


def test_sprint_atual_ja_fechada_marca_fechada():
    from services.acompanhamento import _ref, escolher_sprints
    sp = [sprint("a", 1, avaliacao_completa_em="2026-10-01T00:00:00+00:00"), sprint("b", 2, iniciada=False)]
    atual, proximas, _ = escolher_sprints(sp)
    assert _ref(atual)["fechada"] is True and _ref(proximas[0])["fechada"] is False


def test_aprendizado_inclui_task_reaberta_e_ignora_excluida_e_de_outra_subarea():
    from services.acompanhamento import carregar_projetos
    fake = _fake()
    recente = (AGORA - timedelta(days=1)).isoformat()
    fake.tables["task_aprendizado"] += [
        {"task_id": "t2", "tempo_limpo_s": 3600, "concluida_em": recente, "excluida": False},  # reaberta (coluna != concluida)
        {"task_id": "t2", "tempo_limpo_s": 999999, "concluida_em": recente, "excluida": True},
        {"task_id": "fora", "tempo_limpo_s": 999999, "concluida_em": recente, "excluida": False},
    ]
    p = next(p for p in carregar_projetos(fake, "dados", AGORA)[0] if p["nome"] == "Alfa")
    assert p["saude"]["p85_horas"] == p85([1.0, 2.0])


def _item(feat, feat_ant, spi, spi_ant):
    return {"_status": "saudavel", "_feat": feat, "_feat_ant": feat_ant, "_spi": spi, "_spi_ant": spi_ant,
            "ultima_fechada": None, "sprint_atual": None, "meta": {"total": 0}, "saude": {"tasks_travadas": 0}}


def test_variacoes_comparam_so_projetos_com_atual_e_anterior():
    base = [_item(2, 1, 0.8, 0.6), _item(1, 1, 1.0, 1.0)]
    k = montar_kpis(base)
    assert (k["features_entregues"], k["features_entregues_var"]) == (3, 1)
    assert (k["spi_medio"], k["spi_medio_var"]) == (0.9, 0.1)
    # um projeto sem a sprint -1 entra nos valores atuais, mas não na variação
    k = montar_kpis(base + [_item(10, None, 0.1, None)])
    assert k["features_entregues"] == 13 and k["features_entregues_var"] == 1
    assert k["spi_medio"] == 0.63 and k["spi_medio_var"] == 0.1


def test_variacoes_sem_par_sao_none_e_features_sem_janela_e_none():
    k = montar_kpis([_item(2, None, 0.8, None), _item(None, 1, None, 0.5)])
    assert k["features_entregues_var"] is None and k["spi_medio_var"] is None
    assert k["features_entregues"] == 2
    k = montar_kpis([_item(None, None, None, None)])
    assert k["features_entregues"] is None and k["spi_medio"] is None


def test_status_usa_spi_sem_arredondar():
    from services.acompanhamento import carregar_projetos
    t = lambda i, pts, col: {"id": i, "project_id": "p", "sprint_id": "s", "funcionalidade_id": None, "coluna_kanban": col,
                             "extra": False, "pontos": pts, "travado_automatico": False, "prevista_no_inicio": True,
                             "surgiu_na_sprint": False}
    fake = FakeClient({
        "pessoa": [], "projects": [{"id": "p", "name": "Borda", "client": "C", "subarea": "dados", "gerente_email": "a@x.com"}],
        "sprints": [{"id": "s", "project_id": "p", "numero": 1, "iniciada": True, "data_inicio": None, "avaliacao_completa_em": None}],
        "funcionalidades": [], "tasks": [t("a", 349, "concluida"), t("b", 151, "backlog")],
        "sprint_funcionalidades": [], "sprint_meta_funcionalidades": [], "task_aprendizado": [],
    })
    p = carregar_projetos(fake, "dados", AGORA)[0][0]  # SPI bruto 0,698, que arredonda para 0,70
    assert p["_mapa"][-1]["spi"] == 0.7
    assert p["_status"] == "critico" and "spi_critico" in [s["codigo"] for s in p["_sinais"]]
