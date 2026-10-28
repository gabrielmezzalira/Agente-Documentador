from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import routers.acompanhamento as rota
from services.acompanhamento import (
    agrupar_por_gerente, calcular_projeto, p85, pct_tasks, previsto_de, resumo_do_grupo,
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
    assert r["sprint_atual"] == {"id": "s", "numero": 2}
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


# ── rota ──

def _fake():
    agora = datetime.now(timezone.utc)
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
        ],
        "sprints": [
            {"id": "s1", "project_id": "p1", "numero": 1, "iniciada": True, "avaliacao_completa_em": "2026-10-10T00:00:00+00:00"},
            {"id": "s2", "project_id": "p1", "numero": 2, "iniciada": True, "avaliacao_completa_em": None},
            {"id": "s3", "project_id": "p1", "numero": 3, "iniciada": False, "avaliacao_completa_em": None},
            {"id": "s4", "project_id": "p2", "numero": 1, "iniciada": True, "avaliacao_completa_em": None},
        ],
        "funcionalidades": [
            {"id": "f1", "project_id": "p1", "id_funcional": "F1", "titulo": "A", "status": "concluida", "aprovada_em": "2026-10-09T00:00:00+00:00"},
            {"id": "f2", "project_id": "p1", "id_funcional": "F2", "titulo": "B", "status": "concluida", "aprovada_em": "2026-10-12T00:00:00+00:00"},
            {"id": "f3", "project_id": "p1", "id_funcional": "F3", "titulo": "C", "status": "em_andamento", "aprovada_em": None},
            {"id": "f4", "project_id": "p1", "id_funcional": "F4", "titulo": "D", "status": "nao_iniciada", "aprovada_em": None},
            {"id": "f5", "project_id": "p2", "id_funcional": "F1", "titulo": "E", "status": "em_andamento", "aprovada_em": None},
        ],
        "tasks": [
            {"id": "t1", "project_id": "p1", "sprint_id": "s2", "funcionalidade_id": "f3", "coluna_kanban": "concluida",
             "extra": False, "pontos": 3, "travado_automatico": False, "prevista_no_inicio": True, "surgiu_na_sprint": False},
            {"id": "t2", "project_id": "p1", "sprint_id": "s2", "funcionalidade_id": "f3", "coluna_kanban": "em_andamento",
             "extra": False, "pontos": 3, "travado_automatico": True, "prevista_no_inicio": True, "surgiu_na_sprint": False},
            {"id": "t3", "project_id": "p1", "sprint_id": "s1", "funcionalidade_id": "f1", "coluna_kanban": "concluida",
             "extra": False, "pontos": 2, "travado_automatico": False, "prevista_no_inicio": True, "surgiu_na_sprint": False},
        ],
        "sprint_funcionalidades": [
            {"id": "x1", "sprint_id": "s2", "funcionalidade_id": "f3"},
            {"id": "x2", "sprint_id": "s2", "funcionalidade_id": "f4"},
        ],
        "sprint_meta_funcionalidades": [
            {"sprint_id": "s1", "funcionalidade_id": "f1"}, {"sprint_id": "s1", "funcionalidade_id": "f2"},
            {"sprint_id": "s2", "funcionalidade_id": "f3"},
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
    return autenticar(TestClient(app), cargo)


def test_rota_forma_e_numeros(monkeypatch, autenticar):
    r = _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=dados")
    assert r.status_code == 200
    j = r.json()
    assert j["subarea"] == "dados"
    assert j["totais"] == {"projetos": 3, "em_risco": 1, "metas_fechadas": 1, "metas_batidas": 0}
    assert [g["gerente"]["nome"] for g in j["grupos"]] == ["Ana", "Bruno", "Sem gerente"]
    ana = j["grupos"][0]
    assert ana["gerente"]["email"] == "ana@citi.org.br"
    assert ana["resumo"] == {"projetos": 1, "em_risco": 1, "metas_fechadas": 1, "metas_batidas": 0, "pct_funcs_aprovadas": 50.0}
    p = ana["projetos"][0]
    assert p["sprint_atual"] == {"id": "s2", "numero": 2}
    assert p["proximas_sprints"] == [{"id": "s3", "numero": 3}]
    assert p["meta"]["total"] == 1 and p["meta"]["batida"] is False
    assert p["meta"]["funcionalidades"][0]["pct_tasks"] == 50.0
    assert p["meta"]["funcionalidades"][0]["planejada_na_sprint"] is True
    assert p["planejadas_fora_da_meta"] == [{"id": "f4", "id_funcional": "F4", "titulo": "D"}]
    assert p["planejado"] == {"funcs_planejadas": 2, "funcs_planejadas_entregues": 0, "spi": 0.5}
    assert p["prazo_escopo"]["desvio_detectado"] is True
    assert p["saude"] == {"tasks_travadas": 1, "wip": 1, "p85_horas": 2.0}
    assert p["ultima_fechada"] == {"numero": 1, "meta_total": 2, "meta_entregues": 1, "meta_batida": False, "spi": 1.0}
    assert p["riscos"] == ["prazo à frente do escopo"]
    beta = j["grupos"][1]["projetos"][0]
    assert beta["sprint_atual"]["numero"] == 1 and beta["ultima_fechada"] is None and beta["prazo_escopo"]["sem_dados"] is True


def test_rota_dev_so_traz_projetos_dev(monkeypatch, autenticar):
    j = _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=dev").json()
    assert j["totais"]["projetos"] == 1 and j["grupos"][0]["projetos"][0]["nome"] == "Dev"


@pytest.mark.parametrize("cargo", ["gerente", "operacional"])
def test_so_lider(monkeypatch, autenticar, cargo):
    assert _tc(monkeypatch, autenticar, cargo).get("/acompanhamento?subarea=dados").status_code == 403


def test_subarea_invalida_422(monkeypatch, autenticar):
    assert _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=produto").status_code == 422
