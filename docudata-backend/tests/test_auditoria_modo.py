from services.sprints import congelar_modo_da_sprint, iniciar_sprint_e_ancorar_tasks
from tests.fake_supabase import FakeClient


def _fake(sprint_extra=None, modo="PULL"):
    return FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False, **(sprint_extra or {})}],
        "projects": [{"id": "p1", "modo_trabalho": modo,
                      "modo_avaliacao": "PONTOS_RELATIVO" if modo == "PULL" else "PONTOS_ATRIBUIDOS"}],
        "tasks": [],
    })


def test_congelar_grava_o_modo_do_projeto():
    fake = _fake()
    assert congelar_modo_da_sprint(fake, "s1") == "PULL"
    s = fake.tables["sprints"][0]
    assert (s["modo_trabalho"], s["modo_avaliacao"]) == ("PULL", "PONTOS_RELATIVO")


def test_congelar_nao_sobrescreve_snapshot_existente():
    fake = _fake({"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS"}, modo="PULL")
    assert congelar_modo_da_sprint(fake, "s1") == "ATRIBUICAO"
    assert fake.tables["sprints"][0]["modo_trabalho"] == "ATRIBUICAO"


def test_iniciar_sprint_grava_snapshot():
    fake = _fake()
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    assert fake.tables["sprints"][0]["modo_trabalho"] == "PULL"


def test_historico_usa_o_modo_da_sprint_e_cai_no_do_projeto():
    from routers.avaliacoes import _montar_historico
    fake = FakeClient({
        "sprints": [
            {"id": "s1", "numero": 1, "project_id": "p1", "modo_trabalho": "ATRIBUICAO"},
            {"id": "s2", "numero": 2, "project_id": "p1", "modo_trabalho": None},
        ],
        "projects": [{"id": "p1", "name": "P", "modo_trabalho": "PULL"}],
        "operacionais": [{"id": "op-1", "nome": "Ana"}],
        "avaliacoes_gerente_edicoes": [],
        "pessoa": [{"id": "g1", "nome": "Gê"}],
    })
    base = {"operacional_id": "op-1", "gerente_id": "g1", "criado_em": "2026-01-01T00:00:00+00:00",
            **{f"resposta_{i}": 3 for i in range(1, 8)}}
    itens = _montar_historico(fake, [dict(base, id="a1", sprint_id="s1"), dict(base, id="a2", sprint_id="s2")])
    modo = {i["sprint_id"]: i["modo_trabalho"] for i in itens}
    assert modo == {"s1": "ATRIBUICAO", "s2": "PULL"}


def test_ensure_sprint_row_grava_snapshot_na_sprint_nova():
    from services.sprints import ensure_sprint_row
    fake = FakeClient({
        "sprints": [],
        "projects": [{"id": "p1", "modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO"}],
    })
    ensure_sprint_row(fake, "p1", 1)
    s = fake.tables["sprints"][0]
    assert (s["modo_trabalho"], s["modo_avaliacao"]) == ("PULL", "PONTOS_RELATIVO")


def test_create_sprint_iniciada_grava_snapshot(monkeypatch, autenticar):
    from fastapi.testclient import TestClient
    import routers.sprints as router
    from main import app
    fake = FakeClient({
        "sprints": [],
        "projects": [{"id": "p1", "modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO"}],
    }, defaults={"sprints": {"id": "s9", "created_at": "2026-11-01T00:00:00+00:00",
                             "updated_at": "2026-11-01T00:00:00+00:00"}})
    monkeypatch.setattr(router, "get_client", lambda: fake)
    tc = autenticar(TestClient(app), cargo="gerente")
    resp = tc.post("/projects/p1/sprints", json={"iniciada": True})
    assert resp.status_code == 201, resp.text
    assert fake.tables["sprints"][0]["modo_trabalho"] == "PULL"


import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def projetos_api(monkeypatch, autenticar):
    def _make(fake):
        import routers.projects as projects_router
        from main import app
        monkeypatch.setattr(projects_router, "get_client", lambda: fake)
        return autenticar(TestClient(app), cargo="gerente")
    return _make


def _projeto(modo, wip):
    return FakeClient({
        "projects": [{"id": "p1", "name": "P", "modo_trabalho": modo, "modo_avaliacao": "PONTOS_ATRIBUIDOS",
                      "wip_config": wip}],
        "tasks": [], "sprints": [], "ingestions": [], "operacionais": [], "pessoa": [],
        "configuracao_historico": [], "migracoes_modo": [],
    }, defaults={"configuracao_historico": {"criado_em": "2026-11-17T10:00:00+00:00"}})


def test_ida_e_volta_restaura_o_wip_por_pessoa(projetos_api):
    fake = _projeto("ATRIBUICAO", {"por_pessoa": 3, "por_coluna_em_andamento": 5})
    tc = projetos_api(fake)
    assert tc.post("/projects/p1/migrar-modo", json={"para": "PULL"}).status_code == 200
    assert fake.tables["projects"][0]["wip_config"]["por_pessoa"] == 1
    assert tc.post("/projects/p1/migrar-modo", json={"para": "ATRIBUICAO"}).status_code == 200
    assert fake.tables["projects"][0]["wip_config"] == {"por_pessoa": 3, "por_coluna_em_andamento": 5}


def test_ida_e_volta_com_wip_nulo_volta_a_nulo(projetos_api):
    fake = _projeto("ATRIBUICAO", {"por_pessoa": None, "por_coluna_em_andamento": None})
    tc = projetos_api(fake)
    tc.post("/projects/p1/migrar-modo", json={"para": "PULL"})
    tc.post("/projects/p1/migrar-modo", json={"para": "ATRIBUICAO"})
    assert fake.tables["projects"][0]["wip_config"]["por_pessoa"] is None


def test_sair_de_pull_sem_registro_nao_mexe_no_wip(projetos_api):
    fake = _projeto("PULL", {"por_pessoa": 1, "por_coluna_em_andamento": None})
    projetos_api(fake).post("/projects/p1/migrar-modo", json={"para": "ATRIBUICAO"})
    assert fake.tables["projects"][0]["wip_config"]["por_pessoa"] == 1


def test_historico_de_modos_nao_expoe_o_registro_de_wip(projetos_api):
    fake = _projeto("ATRIBUICAO", {"por_pessoa": 3, "por_coluna_em_andamento": None})
    tc = projetos_api(fake)
    tc.post("/projects/p1/migrar-modo", json={"para": "PULL"})
    campos = {l["campo"] for l in tc.get("/projects/p1/modos-historico").json()}
    assert "wip_por_pessoa" not in campos
    assert "modo_trabalho" in campos
