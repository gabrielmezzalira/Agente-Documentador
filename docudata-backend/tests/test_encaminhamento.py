import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient

HEADERS = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}


def _row(subarea: str, pid: str = "p1") -> dict:
    return {
        "id": pid, "name": "Projeto", "client": "CITi", "subarea": subarea,
        "description": None, "squad": None, "is_delivered": False,
        "created_at": "2026-10-12T12:00:00+00:00",
    }


def test_patch_subarea_recusa_projeto_de_produto(monkeypatch, autenticar):
    from main import app
    fake = FakeClient({"projects": [_row("produto")]})
    monkeypatch.setattr("routers.projects.get_client", lambda: fake)
    client = autenticar(TestClient(app), "gerente")

    resp = client.patch("/projects/p1/subarea", json={"subarea": "dados"}, headers=HEADERS)

    assert resp.status_code == 409
    assert "encaminhar" in resp.json()["detail"]
    assert fake.tables["projects"][0]["subarea"] == "produto"


def test_patch_subarea_entre_dados_e_dev_continua_funcionando(monkeypatch, autenticar):
    from main import app
    fake = FakeClient({"projects": [_row("dados")]})
    monkeypatch.setattr("routers.projects.get_client", lambda: fake)
    client = autenticar(TestClient(app), "gerente")

    resp = client.patch("/projects/p1/subarea", json={"subarea": "dev"}, headers=HEADERS)

    assert resp.status_code == 200
    assert fake.tables["projects"][0]["subarea"] == "dev"


class ClienteComRpc(FakeClient):
    """FakeClient com `rpc`: simula a função SQL `encaminhar_projeto` (troca a subárea)."""

    def __init__(self, tables, rpc_falha: str | None = None):
        super().__init__(tables)
        self.chamadas_rpc: list[tuple[str, dict]] = []
        self._rpc_falha = rpc_falha

    def rpc(self, nome, params):
        self.chamadas_rpc.append((nome, params))
        cliente = self

        class _Exec:
            def execute(self_inner):
                if cliente._rpc_falha:
                    raise Exception(cliente._rpc_falha)
                for linha in cliente.tables["projects"]:
                    if linha["id"] == params["p_project_id"]:
                        linha["subarea"] = params["p_destino"]
                        return SimpleNamespace(data=[dict(linha)])
                return SimpleNamespace(data=[])

        return _Exec()


@pytest.fixture
def preparar(monkeypatch, autenticar):
    def _preparar(subarea="produto", cargo="gerente", rpc_falha=None, projetos=None):
        from main import app
        fake = ClienteComRpc({"projects": projetos if projetos is not None else [_row(subarea)]}, rpc_falha)
        auditoria = []
        monkeypatch.setattr("routers.projects.get_client", lambda: fake)
        monkeypatch.setattr("routers.projects.registrar_auditoria", lambda pessoa, rota, acao: auditoria.append((rota, acao)))
        return autenticar(TestClient(app), cargo), fake, auditoria

    return _preparar


@pytest.mark.parametrize("destino", ["dados", "dev"])
def test_encaminhar_produto_move_o_projeto_e_audita(preparar, destino):
    client, fake, auditoria = preparar()
    resp = client.post("/projects/p1/encaminhar", json={"destino": destino, "motivo": "Discovery concluído"}, headers=HEADERS)

    assert resp.status_code == 200
    assert resp.json()["subarea"] == destino
    nome, params = fake.chamadas_rpc[0]
    assert nome == "encaminhar_projeto"
    assert params == {
        "p_project_id": "p1", "p_destino": destino, "p_motivo": "Discovery concluído",
        "p_autor": "pessoa@citi.org.br", "p_promovidos": 0,
    }
    assert auditoria == [("/projects/p1/encaminhar", f"encaminhar produto->{destino}")]


def test_encaminhar_exige_gerente(preparar):
    client, fake, _ = preparar(cargo="operacional")
    resp = client.post("/projects/p1/encaminhar", json={"destino": "dados"}, headers=HEADERS)
    assert resp.status_code == 403
    assert fake.chamadas_rpc == []


@pytest.mark.parametrize("destino", ["produto", "outra"])
def test_encaminhar_recusa_destino_invalido(preparar, destino):
    client, fake, _ = preparar()
    resp = client.post("/projects/p1/encaminhar", json={"destino": destino}, headers=HEADERS)
    assert resp.status_code == 422
    assert fake.chamadas_rpc == []


def test_encaminhar_recusa_projeto_que_nao_esta_em_produto(preparar):
    client, fake, _ = preparar(subarea="dados")
    resp = client.post("/projects/p1/encaminhar", json={"destino": "dev"}, headers=HEADERS)
    assert resp.status_code == 409
    assert fake.chamadas_rpc == []


def test_encaminhar_projeto_inexistente_retorna_404(preparar):
    client, fake, _ = preparar(projetos=[])
    assert client.post("/projects/p1/encaminhar", json={"destino": "dados"}, headers=HEADERS).status_code == 404


def test_encaminhar_corrida_na_origem_vira_409(preparar):
    client, _, _ = preparar(rpc_falha="origem_invalida")
    resp = client.post("/projects/p1/encaminhar", json={"destino": "dados"}, headers=HEADERS)
    assert resp.status_code == 409


def test_encaminhar_falha_da_funcao_nao_vaza_detalhe(preparar):
    client, _, auditoria = preparar(rpc_falha="connection refused postgres://segredo")
    resp = client.post("/projects/p1/encaminhar", json={"destino": "dados"}, headers=HEADERS)
    assert resp.status_code == 502
    assert "segredo" not in resp.text
    assert auditoria == []
