"""Backlog pessoal: só o Owner usa, e cada um só enxerga as próprias linhas."""
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
    feito = api.patch(f"/backlog/{item['id']}", json={"feito": True}).json()
    assert feito["feito"] is True and feito["concluido_em"]
    reaberto = api.patch(f"/backlog/{item['id']}", json={"feito": False}).json()
    assert reaberto["concluido_em"] is None
    assert api.delete(f"/backlog/{item['id']}").status_code == 204
    assert api.get("/backlog").json() == []


def test_nao_mexe_em_item_de_outra_pessoa(api):
    assert api.patch("/backlog/alheio", json={"feito": True}).status_code == 404
    api.delete("/backlog/alheio")
    restante = api.fake.table("backlog_pessoal").select("*").execute().data
    assert [i["id"] for i in restante] == ["alheio"] and restante[0]["feito"] is False


def test_titulo_vazio_e_recusado(api):
    assert api.post("/backlog", json={"titulo": "   "}).status_code == 422


@pytest.mark.parametrize("cargo", ["lider", "gerente", "operacional"])
def test_so_owner_acessa(api, cargo):
    c = api.como(cargo)
    assert c.get("/backlog").status_code == 403
    assert c.post("/backlog", json={"titulo": "x"}).status_code == 403
