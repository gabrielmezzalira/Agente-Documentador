"""Excluir projeto/operacional com histórico em task_transicoes: o vínculo é
solto antes de apagar (o banco não tem ON DELETE nele até a v15)."""
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient


def _fake():
    return FakeClient({
        "projects": [{"id": "p1", "name": "Demo"}],
        "operacionais": [{"id": "op1", "project_id": "p1"}, {"id": "op2", "project_id": "outro"}],
        "tasks": [{"id": "t1", "project_id": "p1", "operacional_id": "op1"}],
        "task_transicoes": [
            {"id": "tr1", "task_id": "t1", "operacional_id": "op1"},
            {"id": "tr2", "task_id": "t9", "operacional_id": "op2"},
        ],
    })


def test_excluir_projeto_solta_transicoes_dos_operacionais_dele(monkeypatch, autenticar):
    import routers.projects as projects_router
    from main import app
    fake = _fake()
    monkeypatch.setattr(projects_router, "get_client", lambda: fake)

    resp = autenticar(TestClient(app), "gerente").delete("/projects/p1")

    assert resp.status_code == 204
    trans = {t["id"]: t for t in fake.tables["task_transicoes"]}
    assert trans["tr1"]["operacional_id"] is None
    assert trans["tr2"]["operacional_id"] == "op2"


def test_excluir_projeto_bloqueia_operacional(monkeypatch, autenticar):
    import routers.projects as projects_router
    from main import app
    fake = _fake()
    monkeypatch.setattr(projects_router, "get_client", lambda: fake)

    resp = autenticar(TestClient(app), "operacional").delete("/projects/p1")

    assert resp.status_code == 403
    assert fake.tables["projects"] != []


def test_excluir_operacional_solta_transicoes(monkeypatch, autenticar):
    import routers.operacionais as operacionais_router
    from main import app
    fake = _fake()
    monkeypatch.setattr(operacionais_router, "get_client", lambda: fake)

    resp = autenticar(TestClient(app), "gerente").delete("/operacionais/op1")

    assert resp.status_code == 204
    assert {t["id"]: t for t in fake.tables["task_transicoes"]}["tr1"]["operacional_id"] is None
