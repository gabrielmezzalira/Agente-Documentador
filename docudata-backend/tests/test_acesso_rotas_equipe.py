"""Acesso por projeto: equipe, pontos, solicitações, painel, métricas, GitHub e discovery.

Gerente de fora leva 403 (404 no discovery); vinculado passa da conferência.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app

PID, OUTRO = "proj-1", "proj-2"


class Fake:
    def __init__(self):
        self.t = {
            "pessoa": [{"id": "pessoa-teste", "nome": "Eu", "email": "pessoa@citi.org.br", "cargo": "gerente"}],
            "projects": [
                {"id": PID, "name": "A", "client": "C", "squad": "s", "subarea": "dados"},
                {"id": OUTRO, "name": "B", "client": "C", "squad": "s", "subarea": "dados"},
            ],
            "operacionais": [
                {"id": "o-in", "project_id": PID, "nome": "Ana", "ativo": True, "email": "a@x"},
                {"id": "o-out", "project_id": OUTRO, "nome": "Bia", "ativo": True, "email": "b@x"},
            ],
            "sprints": [
                {"id": "s-in", "project_id": PID, "numero": 1},
                {"id": "s-out", "project_id": OUTRO, "numero": 1},
            ],
            "solicitacoes_task": [
                {"id": "sol-in", "project_id": PID, "operacional_id": "o-in", "status": "pendente"},
                {"id": "sol-out", "project_id": OUTRO, "operacional_id": "o-out", "status": "pendente"},
            ],
            "project_repositories": [
                {"id": "r-out", "project_id": OUTRO, "active": True},
            ],
        }
        self.writes = []

    def table(self, name):
        return Q(self, name)


class Q:
    def __init__(self, db, name):
        self.db, self.name, self.f, self.op, self.payload = db, name, [], "select", None

    def __getattr__(self, _nome):
        return lambda *a, **k: self

    def eq(self, c, v): self.f.append((c, lambda x: x == v)); return self
    def in_(self, c, vs): self.f.append((c, lambda x: x in vs)); return self
    def insert(self, p): self.op, self.payload = "insert", p; return self
    def update(self, p): self.op, self.payload = "update", p; return self
    def delete(self): self.op = "delete"; return self

    def execute(self):
        rows = self.db.t.setdefault(self.name, [])
        match = [r for r in rows if all(fn(r.get(c)) for c, fn in self.f)]
        r = MagicMock()
        if self.op != "select":
            self.db.writes.append((self.name, self.op))
        if self.op == "update":
            for m in match: m.update(self.payload)
        r.data = match if self.op != "insert" else [{"id": "novo", **self.payload}]
        return r


@pytest.fixture
def api(monkeypatch, autenticar, vinculos_gerente):
    fake = Fake()
    for mod in ("operacionais", "pontuacao", "solicitacoes", "painel", "metricas", "github_integration", "discovery", "propostas"):
        monkeypatch.setattr(f"routers.{mod}.get_client", lambda: fake)
    monkeypatch.setattr("services.auth.get_client", lambda: fake)
    vinculos_gerente["pessoa-teste"] = {PID}
    c = TestClient(app, raise_server_exceptions=False)
    autenticar(c, "gerente")
    c.fake = fake
    return c


def test_operacionais(api):
    assert api.get(f"/operacionais/projects/{OUTRO}").status_code == 403
    assert api.get(f"/operacionais/disponiveis/{OUTRO}").status_code == 403
    assert api.post("/operacionais", json={"project_id": OUTRO, "nome": "X"}).status_code == 403
    assert api.patch("/operacionais/o-out", json={"nome": "Y"}).status_code == 403
    assert api.post("/operacionais/o-out/remover-do-projeto").status_code == 403
    assert api.delete("/operacionais/o-out").status_code == 403
    assert api.fake.writes == []
    assert api.get(f"/operacionais/projects/{PID}").status_code != 403
    assert api.get(f"/operacionais/disponiveis/{PID}").status_code != 403
    assert api.patch("/operacionais/o-in", json={"nome": "Y"}).status_code != 403
    assert api.delete("/operacionais/o-in").status_code == 204


def test_pontuacao(api):
    assert api.get(f"/projects/{OUTRO}/spi").status_code == 403
    assert api.get("/operacionais/o-out/spi").status_code == 403
    assert api.get("/operacionais/o-out/extrato").status_code == 403
    # sprint de outro projeto com operacional do meu projeto
    assert api.get("/operacionais/o-in/extrato", params={"sprint_id": "s-out"}).status_code == 403
    assert api.get("/operacionais/o-in/extrato", params={"sprint_id": "s-in"}).status_code != 403
    assert api.get("/operacionais/o-in/spi").status_code != 403
    assert api.get(f"/projects/{PID}/spi").status_code != 403


def test_solicitacoes(api):
    assert api.get(f"/solicitacoes-task/projects/{OUTRO}").status_code == 403
    assert api.get(f"/solicitacoes-task/projects/{PID}").status_code != 403
    assert api.patch("/solicitacoes-task/sol-out", json={"status": "atendida"}).status_code == 403
    assert api.post("/solicitacoes-task", json={"operacional_id": "o-out"}).status_code == 403
    assert api.fake.writes == []
    assert api.patch("/solicitacoes-task/sol-in", json={"status": "atendida"}).status_code != 403


@pytest.mark.parametrize("caminho", [
    "/projects/{}/painel", "/metricas/{}/spi", "/metricas/{}/throughput", "/metricas/{}/cycle-time",
    "/metricas/{}/cfd", "/metricas/{}/performance-operacional", "/metricas/{}/cycle-time/stats",
    "/projects/{}/repositories",
])
def test_painel_metricas_repositorios(api, caminho):
    assert api.get(caminho.format(OUTRO)).status_code == 403
    assert api.get(caminho.format(PID)).status_code != 403


def test_github_sessao_conexao_e_desconectar(api):
    assert api.post(f"/projects/{OUTRO}/repositories/github/session").status_code == 403
    assert api.post(f"/projects/{OUTRO}/repositories", json={"connection_token": "t", "repositories": []}).status_code == 403
    assert api.delete(f"/projects/{OUTRO}/repositories/r-out").status_code == 403
    assert api.fake.writes == []
    # repositório de outro projeto pelo caminho do meu: não encontrado
    assert api.delete(f"/projects/{PID}/repositories/r-out").status_code != 403


def test_discovery_mantem_404(api, monkeypatch):
    monkeypatch.setattr("services.discovery_store.buscar_requisito", lambda c, i: {"id": i, "project_id": OUTRO, "status": "proposto"})
    monkeypatch.setattr("services.discovery_store.buscar_reuniao", lambda c, i: {"id": i, "project_id": OUTRO})
    assert api.get("/discovery/requisitos/r1").status_code == 404
    assert api.patch("/discovery/requisitos/r1", json={"titulo": "titulo novo"}).status_code == 404
    assert api.post("/discovery/requisitos/r1/promover").status_code == 404
    assert api.post("/discovery/reunioes/m1/analisar").status_code == 404
    assert api.get("/discovery/reunioes/m1/transcricao").status_code == 404
    assert api.get(f"/discovery/projetos/{OUTRO}/requisitos").status_code == 403


def _como(api, autenticar, cargo):
    autenticar(api, cargo)


def test_operacional_de_fora_403(api, autenticar):
    autenticar(api, "operacional")
    assert api.get(f"/operacionais/projects/{OUTRO}").status_code == 403
    assert api.get(f"/operacionais/disponiveis/{PID}").status_code == 403
    assert api.get(f"/projects/{OUTRO}/propostas").status_code == 403


def test_lider_passa_em_qualquer_projeto(api, autenticar):
    autenticar(api, "lider")
    assert api.get(f"/operacionais/projects/{OUTRO}").status_code != 403
    assert api.get(f"/projects/{OUTRO}/painel").status_code != 403


def test_proposta_decisao_de_fora_403(api):
    api.fake.t["propostas_melhoria"] = [{"id": "p-out", "project_id": OUTRO, "status": "pendente"}]
    assert api.post("/propostas/p-out/decisao", json={"acao": "recusar", "motivo": "x"}).status_code == 403


def test_disponiveis_gerente_nao_ve_nomes_de_projetos_alheios(api, autenticar):
    api.fake.t["operacionais"].append(
        {"id": "o-3", "project_id": OUTRO, "nome": "Caio", "ativo": True, "email": "c@x"})
    api.fake.t["operacionais"].append(
        {"id": "o-4", "project_id": PID, "nome": "Dani", "ativo": True, "email": "d@x"})
    r = api.get(f"/operacionais/disponiveis/{PID}")
    assert r.status_code == 200
    assert all(p != "B" for e in r.json() for p in e["projetos"])
    autenticar(api, "lider")
    r = api.get(f"/operacionais/disponiveis/{PID}")
    assert any("B" in e["projetos"] for e in r.json())
