"""PATCH /tasks/reordenar/batch — autorização por cargo e por dono da task."""
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient

_T = {"created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00"}


def _fake():
    return FakeClient({
        "operacionais": [{"id": "op-me", "project_id": "p1", "email": "pessoa@citi.org.br"}],
        "tasks": [
            {"id": "t-minha", "project_id": "p1", "operacional_id": "op-me", "ordem": 0, **_T},
            {"id": "t-alheia", "project_id": "p1", "operacional_id": "op-outro", "ordem": 1, **_T},
            {"id": "t-fila", "project_id": "p1", "operacional_id": None, "ordem": 2, **_T},
        ],
    })


def _tc(monkeypatch, autenticar, fake, cargo):
    import routers.tasks as tasks_router
    from main import app
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    return autenticar(TestClient(app), cargo)


def _ordens(fake):
    return {t["id"]: t["ordem"] for t in fake.tables["tasks"]}


def test_operacional_reordenando_task_alheia_403_sem_gravar(monkeypatch, autenticar):
    fake = _fake()
    c = _tc(monkeypatch, autenticar, fake, "operacional")
    r = c.patch("/tasks/reordenar/batch", json=[{"id": "t-minha", "ordem": 5}, {"id": "t-alheia", "ordem": 6}])
    assert r.status_code == 403
    assert _ordens(fake) == {"t-minha": 0, "t-alheia": 1, "t-fila": 2}


def test_operacional_reordenando_fila_do_pull_403(monkeypatch, autenticar):
    fake = _fake()
    c = _tc(monkeypatch, autenticar, fake, "operacional")
    assert c.patch("/tasks/reordenar/batch", json=[{"id": "t-fila", "ordem": 9}]).status_code == 403
    assert _ordens(fake)["t-fila"] == 2


def test_operacional_reordenando_as_proprias_200(monkeypatch, autenticar):
    fake = _fake()
    c = _tc(monkeypatch, autenticar, fake, "operacional")
    r = c.patch("/tasks/reordenar/batch", json=[{"id": "t-minha", "ordem": 7}])
    assert r.status_code == 200
    assert _ordens(fake)["t-minha"] == 7


def test_gerente_reordena_qualquer_task_200(monkeypatch, autenticar):
    fake = _fake()
    c = _tc(monkeypatch, autenticar, fake, "gerente")
    r = c.patch("/tasks/reordenar/batch", json=[{"id": "t-alheia", "ordem": 4}, {"id": "t-fila", "ordem": 3}])
    assert r.status_code == 200
    assert _ordens(fake)["t-alheia"] == 4 and _ordens(fake)["t-fila"] == 3
