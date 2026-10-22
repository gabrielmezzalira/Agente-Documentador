"""Pontos são só dificuldade: não há mais orçamento, redistribuição nem preço (spec A1 §2)."""
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient


def _app(monkeypatch, autenticar, fake):
    import routers.projects as projects_router
    import routers.sprints as sprints_router
    import routers.tasks as tasks_router
    from main import app

    for mod in (projects_router, sprints_router, tasks_router):
        monkeypatch.setattr(mod, "get_client", lambda: fake)
    return autenticar(TestClient(app))


def test_endpoint_de_orcamento_nao_existe(monkeypatch, autenticar):
    tc = _app(monkeypatch, autenticar, FakeClient())
    assert tc.patch("/sprints/s1/orcamento", json={"pontos_orcamento": 10}).status_code in (404, 405)


def test_endpoint_de_redistribuir_nao_existe(monkeypatch, autenticar):
    tc = _app(monkeypatch, autenticar, FakeClient())
    resp = tc.post("/tasks/redistribuir-pontos", json={"sprint_id": "s1", "pontos_novos": 2})
    assert resp.status_code in (404, 405)


def test_criar_task_nao_e_bloqueada_por_orcamento(monkeypatch, autenticar):
    fake = FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False, "pontos_orcamento": 1}],
        "tasks": [],
    })
    # O fake não preenche os defaults de coluna do banco que o response_model exige.
    tabela = fake.table

    def tabela_com_defaults(nome):
        t = tabela(nome)
        if nome == "tasks":
            insert = t.insert
            t.insert = lambda p: insert({"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00",
                                         "updated_at": "2026-01-01T00:00:00+00:00", **p})
        return t

    fake.table = tabela_com_defaults
    tc = _app(monkeypatch, autenticar, fake)
    resp = tc.post("/tasks", json={"project_id": "p1", "titulo": "Grande", "pontos": 5, "sprint_id": "s1"})
    assert resp.status_code == 201, resp.text


def test_contrato_ignora_valor_projeto(monkeypatch, autenticar):
    fake = FakeClient({"projects": [{"id": "p1", "name": "P", "client": "C", "created_at": "2026-01-01T00:00:00+00:00"}]})
    tc = _app(monkeypatch, autenticar, fake)
    resp = tc.patch("/projects/p1/contrato", json={"tolerancia_desvio_pontos": 10, "valor_projeto": 1000})
    assert resp.status_code == 200, resp.text
    assert "valor_projeto" not in fake.tables["projects"][0]
    assert "valor_por_ponto" not in resp.json()


def test_comparacao_de_modos_nao_existe(monkeypatch, autenticar):
    import routers.metricas as metricas_router
    fake = FakeClient({"projects": [{"id": "p1"}]})
    monkeypatch.setattr(metricas_router, "get_client", lambda: fake)
    tc = _app(monkeypatch, autenticar, fake)
    assert tc.get("/metricas/p1/comparacao-modos").status_code == 404
    assert tc.get("/metricas/comparacao-modos?projeto_ids=p1").status_code in (404, 422)
