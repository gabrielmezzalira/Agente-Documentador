"""Painel de pessoas, cargo Owner e a hierarquia de acesso.

Owner é um cargo acima de Líder: alcança tudo que o Líder alcança, mais a troca
de cargo das outras pessoas. A hierarquia é o que impede uma rota restrita ao
Líder de barrar o Owner por esquecimento.
"""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from services.auth import criar_jwt, nivel

_SECRET = "test-secret-nao-usar-em-producao"

_PESSOAS = [
    {"id": "p-owner", "nome": "Gabriel", "email": "owner@citi.com", "cargo": "owner", "created_at": None},
    {"id": "p-op", "nome": "Ana", "email": "ana@citi.com", "cargo": "operacional", "created_at": None},
]


def _mock_client(pessoa_alvo=None, update_capture=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        def select_side_effect(cols):
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            if name == "pessoa":
                resp.data = [pessoa_alvo] if pessoa_alvo is not None else _PESSOAS
            elif name == "operacionais":
                resp.data = [{"email": "ana@citi.com", "project_id": "proj-1", "ativo": True}]
            elif name == "projects":
                resp.data = [{"id": "proj-1", "name": "Churn"}]
            else:
                resp.data = []
            q.execute = MagicMock(return_value=resp)
            return q

        def update_side_effect(payload):
            if update_capture is not None:
                update_capture.append(payload)
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{**_PESSOAS[1], **payload}]
            q.execute = MagicMock(return_value=resp)
            return q

        def insert_side_effect(payload):
            q = MagicMock()
            q.execute = MagicMock(return_value=MagicMock(data=[payload]))
            return q

        tbl.select = MagicMock(side_effect=select_side_effect)
        tbl.update = MagicMock(side_effect=update_side_effect)
        tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _tc(monkeypatch, client, cargo, pessoa_id="p-owner", email="owner@citi.com"):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    import routers.pessoas as pessoas_router
    import services.audit as audit_service
    monkeypatch.setattr(pessoas_router, "get_client", lambda: client)
    monkeypatch.setattr(audit_service, "get_client", lambda: client)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt(pessoa_id, email, cargo))
    return tc


def test_hierarquia_coloca_owner_acima_de_lider():
    assert nivel("owner") > nivel("lider") > nivel("gerente") > nivel("operacional")


def test_owner_passa_em_rota_restrita_a_lider(monkeypatch):
    """Sem hierarquia, toda rota de Líder barraria o Owner."""
    client = _mock_client()
    tc = _tc(monkeypatch, client, "owner")

    resp = tc.get("/pessoas")

    assert resp.status_code == 200


def test_gerente_nao_ve_o_painel_de_pessoas(monkeypatch):
    client = _mock_client()
    tc = _tc(monkeypatch, client, "gerente", "p-ger", "ger@citi.com")

    resp = tc.get("/pessoas")

    assert resp.status_code == 403


def test_listagem_traz_os_projetos_da_pessoa(monkeypatch):
    client = _mock_client()
    tc = _tc(monkeypatch, client, "lider", "p-lid", "lid@citi.com")

    resp = tc.get("/pessoas")

    assert resp.status_code == 200
    ana = next(p for p in resp.json() if p["email"] == "ana@citi.com")
    assert ana["projetos"] == ["Churn"]


def test_lider_nao_altera_cargo(monkeypatch):
    """Ver a lista é do Líder; promover é decisão do dono do sistema."""
    client = _mock_client(pessoa_alvo={"id": "p-op", "cargo": "operacional"})
    tc = _tc(monkeypatch, client, "lider", "p-lid", "lid@citi.com")

    resp = tc.patch("/pessoas/p-op/cargo", json={"cargo": "gerente"})

    assert resp.status_code == 403


def test_owner_altera_cargo(monkeypatch):
    capture = []
    client = _mock_client(pessoa_alvo={"id": "p-op", "cargo": "operacional"}, update_capture=capture)
    tc = _tc(monkeypatch, client, "owner")

    resp = tc.patch("/pessoas/p-op/cargo", json={"cargo": "gerente"})

    assert resp.status_code == 200
    assert {"cargo": "gerente"} in capture


def test_owner_nao_rebaixa_a_si_mesmo(monkeypatch):
    """Rebaixar a si mesmo tiraria o acesso à própria tela, sem volta pela UI."""
    client = _mock_client(pessoa_alvo={"id": "p-owner", "cargo": "owner"})
    tc = _tc(monkeypatch, client, "owner")

    resp = tc.patch("/pessoas/p-owner/cargo", json={"cargo": "lider"})

    assert resp.status_code == 409


def test_cargo_invalido_recusado(monkeypatch):
    client = _mock_client(pessoa_alvo={"id": "p-op", "cargo": "operacional"})
    tc = _tc(monkeypatch, client, "owner")

    resp = tc.patch("/pessoas/p-op/cargo", json={"cargo": "chefe"})

    assert resp.status_code == 422
