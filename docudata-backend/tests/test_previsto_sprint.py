"""Previsto da sprint = foto do início + o que surgiu, sem extras (spec A1 §4)."""
from services.previsto_sprint import (
    marcar_foto_do_inicio,
    marcas_ao_entrar_na_sprint,
    previsto_da_sprint,
)
from services.sprints import iniciar_sprint_e_ancorar_tasks
from tests.fake_supabase import FakeClient


def _task(id_, pontos, sprint="s1", **extra):
    base = {"id": id_, "sprint_id": sprint, "pontos": pontos, "extra": False,
            "prevista_no_inicio": False, "surgiu_na_sprint": False,
            "coluna_kanban": "planejado", "entrou_em_andamento_em": None}
    base.update(extra)
    return base


def test_previsto_soma_foto_e_surgiu_sem_extras():
    fake = FakeClient({"tasks": [
        _task("a", 3, prevista_no_inicio=True),
        _task("b", 2, prevista_no_inicio=True),
        _task("c", 5, surgiu_na_sprint=True),
        _task("d", 5, extra=True, surgiu_na_sprint=True),
        _task("e", 1),                      # sem marca: sprint ainda não começou para ela
        _task("f", 3, sprint="s2", prevista_no_inicio=True),
    ]})
    assert previsto_da_sprint(fake, "s1") == {"previsto": 10, "planejado_no_inicio": 5, "surgiu_na_sprint": 5}


def test_previsto_sprint_vazia():
    assert previsto_da_sprint(FakeClient({"tasks": []}), "s1") == {"previsto": 0, "planejado_no_inicio": 0, "surgiu_na_sprint": 0}


def test_marcas_ao_entrar_na_sprint():
    assert marcas_ao_entrar_na_sprint(sprint_iniciada=True, extra=False) == {"prevista_no_inicio": False, "surgiu_na_sprint": True}
    assert marcas_ao_entrar_na_sprint(sprint_iniciada=True, extra=True) == {"prevista_no_inicio": False, "surgiu_na_sprint": False}
    assert marcas_ao_entrar_na_sprint(sprint_iniciada=False, extra=False) == {"prevista_no_inicio": False, "surgiu_na_sprint": False}


def test_foto_do_inicio_marca_so_nao_extras_da_sprint():
    fake = FakeClient({"tasks": [_task("a", 3), _task("b", 2, extra=True), _task("c", 1, sprint="s2")]})
    marcar_foto_do_inicio(fake, "s1")
    marcadas = {t["id"]: t["prevista_no_inicio"] for t in fake.tables["tasks"]}
    assert marcadas == {"a": True, "b": False, "c": False}


def test_iniciar_sprint_tira_a_foto_e_ancora():
    fake = FakeClient({
        "sprints": [{"id": "s1", "iniciada": False}],
        "tasks": [_task("a", 3), _task("b", 2, coluna_kanban="concluida")],
    })
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    a, b = fake.tables["tasks"]
    assert fake.tables["sprints"][0]["iniciada"] is True
    assert a["prevista_no_inicio"] is True and a["entrou_em_andamento_em"] is not None
    assert b["prevista_no_inicio"] is True and b["entrou_em_andamento_em"] is None


# ── marcas via endpoints (create / move) ──────────────────────────────────

def _app_tasks(monkeypatch, autenticar, fake):
    from fastapi.testclient import TestClient
    import routers.tasks as tasks_router
    from main import app

    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    tabela = fake.table

    def tabela_com_defaults(nome):
        t = tabela(nome)
        if nome == "tasks":
            insert = t.insert
            t.insert = lambda p: insert({"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00",
                                         "updated_at": "2026-01-01T00:00:00+00:00", **p})
        return t

    fake.table = tabela_com_defaults
    return autenticar(TestClient(app))


_COMPLETA = {"project_id": "p1", "titulo": "T", "bloqueado": False, "ordem": 0,
             "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00"}


def _base_fake(tasks=()):
    return FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [
            {"id": "s-ini", "project_id": "p1", "iniciada": True},
            {"id": "s-fut", "project_id": "p1", "iniciada": False},
        ],
        "tasks": list(tasks),
    })


def test_criar_task_em_sprint_iniciada_surge_na_sprint(monkeypatch, autenticar):
    fake = _base_fake()
    tc = _app_tasks(monkeypatch, autenticar, fake)
    resp = tc.post("/tasks", json={"project_id": "p1", "titulo": "T", "pontos": 3, "sprint_id": "s-ini"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["surgiu_na_sprint"] is True and resp.json()["prevista_no_inicio"] is False


def test_criar_task_extra_ou_em_sprint_futura_nao_surge(monkeypatch, autenticar):
    fake = _base_fake()
    tc = _app_tasks(monkeypatch, autenticar, fake)
    r1 = tc.post("/tasks", json={"project_id": "p1", "titulo": "E", "pontos": 3, "sprint_id": "s-ini", "extra": True})
    r2 = tc.post("/tasks", json={"project_id": "p1", "titulo": "F", "pontos": 3, "sprint_id": "s-fut"})
    for r in (r1, r2):
        assert r.status_code == 201, r.text
        assert r.json()["surgiu_na_sprint"] is False and r.json()["prevista_no_inicio"] is False


def test_mover_task_para_sprint_iniciada_marca_surgiu_e_zera_foto(monkeypatch, autenticar):
    fake = _base_fake([_task("t1", 3, sprint="s-fut", **_COMPLETA, prevista_no_inicio=True)])
    tc = _app_tasks(monkeypatch, autenticar, fake)
    resp = tc.patch("/tasks/t1", json={"sprint_id": "s-ini"})
    assert resp.status_code == 200, resp.text
    t = fake.tables["tasks"][0]
    assert t["surgiu_na_sprint"] is True and t["prevista_no_inicio"] is False


def test_mover_task_para_sprint_futura_zera_as_duas_marcas(monkeypatch, autenticar):
    fake = _base_fake([_task("t1", 3, sprint="s-ini", **_COMPLETA, surgiu_na_sprint=True)])
    tc = _app_tasks(monkeypatch, autenticar, fake)
    resp = tc.patch("/tasks/t1", json={"sprint_id": "s-fut"})
    assert resp.status_code == 200, resp.text
    t = fake.tables["tasks"][0]
    assert t["surgiu_na_sprint"] is False and t["prevista_no_inicio"] is False


def test_patch_com_mesma_sprint_nao_mexe_nas_marcas(monkeypatch, autenticar):
    fake = _base_fake([_task("t1", 3, sprint="s-ini", **_COMPLETA, prevista_no_inicio=True)])
    tc = _app_tasks(monkeypatch, autenticar, fake)
    resp = tc.patch("/tasks/t1", json={"sprint_id": "s-ini", "titulo": "Novo"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["prevista_no_inicio"] is True


def test_iniciar_de_novo_nao_refaz_a_foto():
    fake = FakeClient({"sprints": [{"id": "s1", "iniciada": False}], "tasks": [_task("a", 3)]})
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    fake.tables["tasks"].append(_task("b", 5, surgiu_na_sprint=True))
    antes = previsto_da_sprint(fake, "s1")
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    assert fake.tables["tasks"][1]["prevista_no_inicio"] is False
    assert previsto_da_sprint(fake, "s1") == antes == {"previsto": 8, "planejado_no_inicio": 3, "surgiu_na_sprint": 5}
