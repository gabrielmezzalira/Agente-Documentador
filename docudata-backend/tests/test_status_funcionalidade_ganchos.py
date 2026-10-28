"""Toda escrita de task recalcula o status da funcionalidade (B1, entrega 1)."""
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient


def _fake():
    func = {"project_id": "p1", "titulo": "F", "criterios_aceite": [], "prioridade": "must",
            "aprovada_em": None, "aprovada_por": None, "created_at": "2026-01-01T00:00:00+00:00"}
    return FakeClient({
        "pessoa": [{"id": "pessoa-teste", "nome": "Gabriel"}],
        "funcionalidades": [
            {**func, "id": "fA", "id_funcional": "A", "status": "nao_iniciada"},
            {**func, "id": "fB", "id_funcional": "B", "status": "nao_iniciada"},
        ],
        "transicoes_status": [],
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False}],
        "tasks": [],
    }, defaults={"tasks": {"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00",
                           "updated_at": "2026-01-01T00:00:00+00:00"}})


def _task(tid="t1", **extra):
    return {
        "id": tid, "project_id": "p1", "sprint_id": "s1", "titulo": "Tarefa", "pontos": 3,
        "coluna_kanban": "planejado", "bloqueado": False, "checklist": [], "ordem": 0,
        "extra": False, "operacional_id": None, "funcionalidade_id": "fA",
        "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
        **extra,
    }


def _tc(monkeypatch, autenticar, fake):
    import routers.tasks as tasks_router
    from main import app
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    monkeypatch.setattr(tasks_router, "check_wip", lambda *a, **k: (True, None))
    monkeypatch.setattr(tasks_router, "on_task_transition", lambda *a, **k: False)
    monkeypatch.setattr(tasks_router, "rotear_evento_pos_fechamento", lambda *a, **k: None)
    return autenticar(TestClient(app), "gerente")


def _status(fake, fid):
    return next(f["status"] for f in fake.tables["funcionalidades"] if f["id"] == fid)


def _transicoes(fake, fid):
    return [t for t in fake.tables["transicoes_status"] if t["funcionalidade_id"] == fid]


def test_criar_task_planejada_mantem_nao_iniciada_sem_transicao(monkeypatch, autenticar):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post(
        "/tasks", json={"project_id": "p1", "titulo": "Nova", "pontos": 1, "funcionalidade_id": "fA"})
    assert resp.status_code == 201, resp.text
    assert _status(fake, "fA") == "nao_iniciada"
    assert _transicoes(fake, "fA") == []


def test_criar_task_em_andamento_muda_status(monkeypatch, autenticar):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post(
        "/tasks", json={"project_id": "p1", "titulo": "Nova", "pontos": 1,
                        "funcionalidade_id": "fA", "coluna_kanban": "em_andamento"})
    assert resp.status_code == 201, resp.text
    assert _status(fake, "fA") == "em_andamento"


def test_mover_para_em_andamento_e_concluir(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    tc = _tc(monkeypatch, autenticar, fake)
    assert tc.post("/tasks/t1/mover", params={"coluna_destino": "em_andamento"}).status_code == 200
    assert _status(fake, "fA") == "em_andamento"
    assert len(_transicoes(fake, "fA")) == 1
    assert tc.patch("/tasks/t1", json={"coluna_kanban": "concluida"}).status_code == 200
    assert _status(fake, "fA") == "concluida"
    assert len(_transicoes(fake, "fA")) == 2


def test_trocar_de_funcionalidade_sincroniza_antiga_e_nova(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["funcionalidades"][0]["status"] = "em_andamento"
    fake.tables["tasks"].append(_task(coluna_kanban="planejado"))
    fake.tables["tasks"].append(_task("t2", coluna_kanban="planejado", funcionalidade_id="fA"))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"funcionalidade_id": "fB"})
    assert resp.status_code == 200, resp.text
    assert _status(fake, "fA") == "nao_iniciada"  # antiga recalculada (t2 planejada)
    assert _status(fake, "fB") == "nao_iniciada"
    fake.tables["tasks"][1]["coluna_kanban"] = "em_andamento"
    fake.tables["funcionalidades"][1]["status"] = "concluida"
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"funcionalidade_id": "fA"})
    assert resp.status_code == 200, resp.text
    assert _status(fake, "fA") == "em_andamento"
    assert _status(fake, "fB") == "concluida"  # ficou sem tasks: não mexe


def test_trocar_de_funcionalidade_recalcula_a_nova(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["funcionalidades"][0]["status"] = "em_andamento"
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento"))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"funcionalidade_id": "fB"})
    assert resp.status_code == 200, resp.text
    assert _status(fake, "fB") == "em_andamento"
    assert _status(fake, "fA") == "em_andamento"  # sem tasks: mantém


def test_excluir_ultima_task_aberta_conclui_funcionalidade(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["funcionalidades"][0]["status"] = "em_andamento"
    fake.tables["tasks"] += [_task("t1", coluna_kanban="concluida"), _task("t2", coluna_kanban="em_andamento")]
    resp = _tc(monkeypatch, autenticar, fake).delete("/tasks/t2")
    assert resp.status_code == 204, resp.text
    assert _status(fake, "fA") == "concluida"


def test_excluir_sprint_sincroniza_funcionalidades(monkeypatch, autenticar):
    import routers.sprints as sprints_router
    from main import app
    fake = _fake()
    fake.tables["funcionalidades"][0]["status"] = "em_andamento"
    fake.tables["sprints"][0]["numero"] = 1
    fake.tables["tasks"] += [
        _task("t1", coluna_kanban="concluida", sprint_id=None),
        _task("t2", coluna_kanban="em_andamento"),
    ]
    monkeypatch.setattr(sprints_router, "get_client", lambda: fake)
    resp = autenticar(TestClient(app), "gerente").delete("/sprints/s1")
    assert resp.status_code in (200, 204), resp.text
    assert _status(fake, "fA") == "concluida"


def test_falha_do_gancho_nao_muda_a_resposta(monkeypatch, autenticar):
    import routers.tasks as tasks_router

    def quebra(*a, **k):
        raise RuntimeError("boom")

    fake = _fake()
    fake.tables["tasks"].append(_task())
    tc = _tc(monkeypatch, autenticar, fake)
    monkeypatch.setattr(tasks_router, "sincronizar_status", quebra)
    assert tc.patch("/tasks/t1", json={"coluna_kanban": "em_andamento"}).status_code == 200
