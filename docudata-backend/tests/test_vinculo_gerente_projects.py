from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app

PID = "proj-1"
OUTRO = "proj-2"


class Fake:
    """Supabase mínimo em memória para projects/pessoa/projeto_gerentes/ingestions."""

    def __init__(self):
        self.t = {
            "projects": [
                {"id": PID, "name": "A", "client": "C", "subarea": "dados", "created_at": "2026-01-01"},
                {"id": OUTRO, "name": "B", "client": "C", "subarea": "dados", "created_at": "2026-01-02"},
            ],
            "pessoa": [
                {"id": "pessoa-teste", "nome": "Eu", "email": "pessoa@citi.org.br", "cargo": "gerente"},
                {"id": "g2", "nome": "G2", "email": "g2@x", "cargo": "gerente"},
                {"id": "l1", "nome": "L1", "email": "l1@x", "cargo": "lider"},
                {"id": "op1", "nome": "Op", "email": "op@x", "cargo": "operacional"},
            ],
            "projeto_gerentes": [{"project_id": PID, "pessoa_id": "pessoa-teste", "criado_em": "x"}],
            "ingestions": [], "operacionais": [],
        }

    def table(self, name):
        return Q(self, name)


class Q:
    def __init__(self, db, name):
        self.db, self.name, self.f, self.op, self.payload = db, name, [], "select", None

    def select(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def eq(self, c, v): self.f.append((c, lambda x: x == v)); return self
    def in_(self, c, vs): self.f.append((c, lambda x: x in vs)); return self
    def insert(self, p): self.op, self.payload = "insert", p; return self
    def delete(self): self.op = "delete"; return self
    def upsert(self, p, **k): self.op, self.payload = "upsert", p; return self

    def execute(self):
        rows = self.db.t[self.name]
        match = [r for r in rows if all(fn(r.get(c)) for c, fn in self.f)]
        r = MagicMock()
        if self.op == "insert":
            row = {"id": "novo", "subarea": "dados", "created_at": "2026-01-03", **self.payload}
            rows.append(row); r.data = [row]
        elif self.op == "upsert":
            if not any(x["project_id"] == self.payload["project_id"] and x["pessoa_id"] == self.payload["pessoa_id"] for x in rows):
                rows.append({**self.payload, "criado_em": "y"})
            r.data = []
        elif self.op == "delete":
            for m in match: rows.remove(m)
            r.data = match
        else:
            r.data = match
        return r


@pytest.fixture
def api(monkeypatch, autenticar, vinculos_gerente):
    fake = Fake()
    for mod in ("routers.projects", "routers.search"):
        monkeypatch.setattr(f"{mod}.get_client", lambda: fake, raising=False)
    monkeypatch.setattr("services.auth.get_client", lambda: fake)
    vinculos_gerente["pessoa-teste"] = {PID}
    c = TestClient(app)
    c.fake = fake
    c.login = lambda cargo: autenticar(c, cargo)
    return c


def test_gerente_vinculado_le_projeto(api):
    api.login("gerente")
    assert api.get(f"/projects/{PID}").status_code == 200


def test_gerente_nao_vinculado_403(api):
    api.login("gerente")
    assert api.get(f"/projects/{OUTRO}").status_code == 403
    assert api.patch(f"/projects/{OUTRO}/delivered").status_code == 403


def test_lider_ve_qualquer_projeto(api):
    api.login("lider")
    assert api.get(f"/projects/{OUTRO}").status_code == 200


def test_operacional_nao_vinculado_403(api):
    api.login("operacional")
    assert api.get(f"/projects/{PID}").status_code == 403


def test_lista_filtrada_para_gerente(api):
    api.login("gerente")
    ids = [p["id"] for p in api.get("/projects?subarea=dados").json()]
    assert ids == [PID]
    api.login("lider")
    assert len(api.get("/projects?subarea=dados").json()) == 2


def test_criar_vincula_criador(api):
    api.login("gerente")
    r = api.post("/projects", json={"name": "N", "client": "C", "subarea": "dados"})
    assert r.status_code == 201
    assert {"project_id": "novo", "pessoa_id": "pessoa-teste"} .items() <= api.fake.t["projeto_gerentes"][-1].items()


def test_operacional_nao_cria_projeto(api):
    api.login("operacional")
    r = api.post("/projects", json={"name": "N", "client": "C", "subarea": "dados"})
    assert r.status_code == 403


def test_listar_e_candidatos(api):
    api.login("gerente")
    g = api.get(f"/projects/{PID}/gerentes").json()
    assert [x["pessoa_id"] for x in g] == ["pessoa-teste"]
    cand = {x["pessoa_id"] for x in api.get(f"/projects/{PID}/gerentes/candidatos").json()}
    assert cand == {"g2", "l1"}


def test_vincular_e_desvincular(api):
    api.login("gerente")
    r = api.post(f"/projects/{PID}/gerentes", json={"pessoa_id": "g2"})
    assert r.status_code == 201
    assert {x["pessoa_id"] for x in r.json()} == {"pessoa-teste", "g2"}
    assert api.delete(f"/projects/{PID}/gerentes/g2").status_code == 204


def test_vincular_operacional_422(api):
    api.login("gerente")
    assert api.post(f"/projects/{PID}/gerentes", json={"pessoa_id": "op1"}).status_code == 422


def test_remover_ultimo_409(api):
    api.login("gerente")
    r = api.delete(f"/projects/{PID}/gerentes/pessoa-teste")
    assert r.status_code == 409
    assert r.json()["detail"] == "O projeto precisa de pelo menos um gerente."


def test_gerente_nao_vinculado_nao_gerencia(api):
    api.login("gerente")
    assert api.post(f"/projects/{OUTRO}/gerentes", json={"pessoa_id": "g2"}).status_code == 403


def test_busca_filtrada(api):
    api.fake.t["ingestions"] = [
        {"project_id": PID, "sprint_number": 1, "extracted_content": {"tecnologias": ["Spark"], "resumo": "a"}},
        {"project_id": OUTRO, "sprint_number": 1, "extracted_content": {"tecnologias": ["Spark"], "resumo": "b"}},
    ]
    api.login("gerente")
    res = api.get("/search?q=spark&subarea=dados").json()["results"]
    assert [x["project_id"] for x in res] == [PID]
    api.login("lider")
    assert len(api.get("/search?q=spark&subarea=dados").json()["results"]) == 2


def test_desvincular_pessoa_nao_vinculada_404(api):
    api.login("gerente")
    api.post(f"/projects/{PID}/gerentes", json={"pessoa_id": "g2"})
    assert api.delete(f"/projects/{PID}/gerentes/l1").status_code == 404


def test_lider_vincula_e_desvincula_sem_estar_vinculado(api):
    api.login("lider")
    assert api.post(f"/projects/{PID}/gerentes", json={"pessoa_id": "g2"}).status_code == 201
    assert api.delete(f"/projects/{PID}/gerentes/g2").status_code == 204


def test_operacional_desativado_403(api):
    api.fake.t["operacionais"] = [
        {"id": "o1", "project_id": PID, "email": "pessoa@citi.org.br", "ativo": False}
    ]
    api.login("operacional")
    assert api.get(f"/projects/{PID}").status_code == 403


def test_operacional_ativo_200(api):
    api.fake.t["operacionais"] = [
        {"id": "o1", "project_id": PID, "email": "pessoa@citi.org.br", "ativo": True}
    ]
    api.login("operacional")
    assert api.get(f"/projects/{PID}").status_code == 200


def _sem_tabela(api):
    orig = api.fake.table

    def table(name):
        if name == "projeto_gerentes":
            raise Exception("{'code': 'PGRST205', 'message': \"Could not find the table 'public.projeto_gerentes'\"}")
        return orig(name)

    api.fake.table = table


def test_antes_da_v16_listar_candidatos_e_503(api):
    api.login("lider")
    _sem_tabela(api)
    r = api.get(f"/projects/{PID}/gerentes")
    assert r.status_code == 200 and r.json() == []
    assert api.get(f"/projects/{PID}/gerentes/candidatos").status_code == 200
    r = api.post(f"/projects/{PID}/gerentes", json={"pessoa_id": "g2"})
    assert r.status_code == 503
    assert r.json()["detail"] == "Migração v16 pendente: vínculo de gerentes indisponível."
    assert api.delete(f"/projects/{PID}/gerentes/g2").status_code == 503
