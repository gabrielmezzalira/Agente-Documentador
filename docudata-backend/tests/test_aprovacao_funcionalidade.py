"""Funcionalidade concluída e aprovada pelo gerente (spec A1 §3)."""
from fastapi.testclient import TestClient

from services.aprovacao_funcionalidade import revogar_se_aprovada
from tests.fake_supabase import FakeClient


def _fake(status="concluida", aprovada_em=None):
    return FakeClient({
        "pessoa": [{"id": "pessoa-teste", "nome": "Gabriel"}],
        "funcionalidades": [{
            "id": "f1", "project_id": "p1", "id_funcional": "F1", "titulo": "Login",
            "criterios_aceite": [], "prioridade": "must", "status": status,
            "aprovada_em": aprovada_em, "aprovada_por": None,
            "created_at": "2026-01-01T00:00:00+00:00",
        }],
        "transicoes_status": [],
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False}],
        "tasks": [],
    }, defaults={"tasks": {"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00",
                           "updated_at": "2026-01-01T00:00:00+00:00"}})


def _tc(monkeypatch, autenticar, fake, cargo="gerente"):
    import routers.funcionalidades as func_router
    import routers.tasks as tasks_router
    from main import app
    monkeypatch.setattr(func_router, "get_client", lambda: fake)
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    return autenticar(TestClient(app), cargo)


def test_aprovar_funcionalidade_concluida(monkeypatch, autenticar):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 200, resp.text
    f = fake.tables["funcionalidades"][0]
    assert f["aprovada_em"] is not None and f["aprovada_por"] == "pessoa-teste"
    assert resp.json()["aprovada_por_nome"] == "Gabriel"
    t = fake.tables["transicoes_status"][0]
    assert (t["campo"], t["de"], t["para"]) == ("aprovacao", "pendente", "aprovada")


def test_aprovar_nao_concluida_409(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake(status="em_andamento")).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 409


def test_aprovar_duas_vezes_409(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake(aprovada_em="2026-10-01T00:00:00+00:00")).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 409


def test_operacional_nao_aprova(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake(), cargo="operacional").post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 403


def test_desfazer_aprovacao(monkeypatch, autenticar):
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    resp = _tc(monkeypatch, autenticar, fake).delete("/funcionalidades/f1/aprovacao")
    assert resp.status_code == 200, resp.text
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
    assert fake.tables["transicoes_status"][0]["para"] == "pendente"


def test_desfazer_sem_aprovacao_409(monkeypatch, autenticar):
    assert _tc(monkeypatch, autenticar, _fake()).delete("/funcionalidades/f1/aprovacao").status_code == 409


def test_revogar_se_aprovada():
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    assert revogar_se_aprovada(fake, "f1", "revogada: task reaberta") is True
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
    assert fake.tables["transicoes_status"][0]["motivo"] == "revogada: task reaberta"
    assert revogar_se_aprovada(fake, "f1", "x") is False
    assert revogar_se_aprovada(fake, None, "x") is False


def test_task_nova_em_funcionalidade_aprovada_revoga(monkeypatch, autenticar):
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    resp = _tc(monkeypatch, autenticar, fake).post(
        "/tasks", json={"project_id": "p1", "titulo": "Ajuste", "pontos": 1, "funcionalidade_id": "f1"}
    )
    assert resp.status_code == 201, resp.text
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None


def _task(**extra):
    return {
        "id": "t1", "project_id": "p1", "sprint_id": "s1", "titulo": "Tarefa",
        "pontos": 3, "coluna_kanban": "concluida", "bloqueado": False,
        "checklist": [], "ordem": 0, "extra": False, "operacional_id": None,
        "funcionalidade_id": "f1",
        "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
        **extra,
    }


def _tc_tasks(monkeypatch, autenticar, fake):
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "check_wip", lambda *a, **k: (True, None))
    monkeypatch.setattr(tasks_router, "on_task_transition", lambda *a, **k: False)
    monkeypatch.setattr(tasks_router, "rotear_evento_pos_fechamento", lambda *a, **k: None)
    return _tc(monkeypatch, autenticar, fake)


def test_reabrir_task_revoga_aprovacao(monkeypatch, autenticar):
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    fake.tables["tasks"].append(_task())
    resp = _tc_tasks(monkeypatch, autenticar, fake).patch(
        "/tasks/t1", json={"coluna_kanban": "em_andamento", "motivo": "voltou"}
    )
    assert resp.status_code == 200, resp.text
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
    assert fake.tables["transicoes_status"][0]["motivo"] == "revogada: task reaberta"


def test_vincular_task_a_funcionalidade_aprovada_revoga(monkeypatch, autenticar):
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    fake.tables["tasks"].append(_task(funcionalidade_id=None, coluna_kanban="em_andamento"))
    resp = _tc_tasks(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"funcionalidade_id": "f1"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
    assert fake.tables["transicoes_status"][0]["motivo"] == "revogada: task nova"


def test_mudar_status_da_funcionalidade_revoga_aprovacao(monkeypatch, autenticar):
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    resp = _tc(monkeypatch, autenticar, fake).patch("/funcionalidades/f1", json={"status": "em_andamento"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
    assert resp.json()["aprovada_em"] is None
    assert fake.tables["transicoes_status"][-1]["motivo"] == "revogada: status alterado"


def test_aprovar_inexistente_404(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake()).post("/funcionalidades/nao-existe/aprovar")
    assert resp.status_code == 404


def test_aprovar_com_task_aberta_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento"))
    resp = _tc(monkeypatch, autenticar, fake).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Há tasks desta funcionalidade ainda não concluídas."
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None


def test_aprovar_com_todas_as_tasks_concluidas(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["tasks"].append(_task(id="t2"))
    resp = _tc(monkeypatch, autenticar, fake).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 200, resp.text
