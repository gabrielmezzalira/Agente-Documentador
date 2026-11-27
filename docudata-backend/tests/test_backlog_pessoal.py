"""Backlog pessoal: gerente, líder e owner usam; cada um só enxerga as próprias linhas."""
import pytest
from fastapi.testclient import TestClient

from main import app
from tests.fake_supabase import FakeClient


@pytest.fixture
def api(monkeypatch, autenticar):
    fake = FakeClient({"backlog_pessoal": [{"id": "alheio", "pessoa_id": "outra-pessoa", "titulo": "segredo", "feito": False}]})
    monkeypatch.setattr("routers.backlog.get_client", lambda: fake)
    c = TestClient(app)
    autenticar(c, "owner")
    c.fake = fake
    c.como = lambda cargo: autenticar(TestClient(app), cargo)
    return c


def test_owner_cria_lista_marca_feito_e_apaga(api):
    item = api.post("/backlog", json={"titulo": "  Revisar PTA ", "prioridade": "alta"}).json()
    assert item["titulo"] == "Revisar PTA" and item["pessoa_id"] == "pessoa-teste"
    assert [i["id"] for i in api.get("/backlog").json()] == [item["id"]]  # o alheio não aparece
    assert item["status"] == "planejado"
    andamento = api.patch(f"/backlog/{item['id']}", json={"status": "andamento"}).json()
    assert andamento["status"] == "andamento" and andamento["concluido_em"] is None
    feito = api.patch(f"/backlog/{item['id']}", json={"status": "concluido"}).json()
    assert feito["status"] == "concluido" and feito["feito"] is True and feito["concluido_em"]
    reaberto = api.patch(f"/backlog/{item['id']}", json={"status": "planejado"}).json()
    assert reaberto["concluido_em"] is None and reaberto["feito"] is False
    assert api.delete(f"/backlog/{item['id']}").status_code == 204
    assert api.get("/backlog").json() == []


def test_nao_mexe_em_item_de_outra_pessoa(api):
    assert api.patch("/backlog/alheio", json={"status": "concluido"}).status_code == 404
    api.delete("/backlog/alheio")
    restante = api.fake.table("backlog_pessoal").select("*").execute().data
    assert [i["id"] for i in restante] == ["alheio"] and restante[0]["feito"] is False


def test_titulo_vazio_e_recusado(api):
    assert api.post("/backlog", json={"titulo": "   "}).status_code == 422


def test_operacional_nao_acessa(api):
    c = api.como("operacional")
    assert c.get("/backlog").status_code == 403
    assert c.post("/backlog", json={"titulo": "x"}).status_code == 403


@pytest.mark.parametrize("cargo", ["gerente", "lider"])
def test_gerente_e_lider_tem_o_proprio_quadro(api, cargo):
    c = api.como(cargo)
    assert c.get("/backlog").status_code == 200
    assert c.post("/backlog", json={"titulo": "x"}).status_code == 201


def test_linha_antiga_sem_status_aparece_pelo_feito(api):
    api.fake.table("backlog_pessoal").insert({"id": "velho", "pessoa_id": "pessoa-teste", "titulo": "a", "feito": True}).execute()
    assert [i["status"] for i in api.get("/backlog").json()] == ["concluido"]


def test_reordenar_grava_a_ordem_e_move_de_coluna(api):
    a = api.post("/backlog", json={"titulo": "a"}).json()["id"]
    b = api.post("/backlog", json={"titulo": "b"}).json()["id"]
    c = api.post("/backlog", json={"titulo": "c"}).json()["id"]
    r = api.post("/backlog/reordenar", json={"status": "planejado", "ids": [c, a, b]}).json()
    assert [(i["id"], i["ordem"]) for i in r] == [(c, 0), (a, 1), (b, 2)]
    # b sai para Concluído; ganha status e data de conclusão
    mov = api.post("/backlog/reordenar", json={"status": "concluido", "ids": [b]}).json()
    assert mov[0]["status"] == "concluido" and mov[0]["concluido_em"] and mov[0]["feito"] is True


def test_reordenar_recusa_item_alheio(api):
    assert api.post("/backlog/reordenar", json={"status": "planejado", "ids": ["alheio"]}).status_code == 404
    assert api.post("/backlog/reordenar", json={"status": "planejado", "ids": ["x", "x"]}).status_code == 404
