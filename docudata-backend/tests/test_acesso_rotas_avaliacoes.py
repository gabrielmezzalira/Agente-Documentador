"""Acesso por projeto: avaliações; chave do Gemini só para líder/owner."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app

PID, OUTRO = "proj-1", "proj-2"


class Fake:
    def __init__(self):
        self.t = {
            "pessoa": [{"id": "pessoa-teste", "nome": "Eu", "email": "pessoa@citi.org.br", "cargo": "gerente"}],
            "projects": [{"id": PID, "name": "A"}, {"id": OUTRO, "name": "B"}],
            "operacionais": [
                {"id": "o-in", "project_id": PID, "nome": "Ana"},
                {"id": "o-out", "project_id": OUTRO, "nome": "Bia"},
            ],
            "sprints": [
                {"id": "s-in", "project_id": PID, "numero": 1},
                {"id": "s-out", "project_id": OUTRO, "numero": 1},
            ],
            "avaliacoes_gerente": [
                {"id": "a-in", "sprint_id": "s-in", "operacional_id": "o-in", "gerente_id": "pessoa-teste", "criado_em": "2026-01-01T00:00:00+00:00", **{f"resposta_{i}": 3 for i in range(1, 8)}},
                {"id": "a-out", "sprint_id": "s-out", "operacional_id": "o-out", "gerente_id": "pessoa-teste", "criado_em": "2026-01-01T00:00:00+00:00", **{f"resposta_{i}": 3 for i in range(1, 8)}},
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
        r.data = match if self.op != "insert" else [{"id": "novo", **self.payload}]
        return r


@pytest.fixture
def api(monkeypatch, autenticar, vinculos_gerente):
    fake = Fake()
    monkeypatch.setattr("routers.avaliacoes.get_client", lambda: fake)
    monkeypatch.setattr("services.auth.get_client", lambda: fake)
    vinculos_gerente["pessoa-teste"] = {PID}
    c = TestClient(app, raise_server_exceptions=False)
    autenticar(c, "gerente")
    c.fake = fake
    return c


def test_historico_filtrado(api):
    r = api.get("/avaliacoes/historico")
    assert r.status_code == 200
    assert [i["id"] for i in r.json()] == ["a-in"]
    assert api.get("/avaliacoes/historico", params={"project_id": OUTRO}).status_code == 403
    assert api.get("/avaliacoes/historico", params={"sprint_id": "s-out"}).status_code == 403
    assert api.get("/avaliacoes/historico", params={"project_id": PID}).status_code == 200


def test_historico_sem_vinculo_vazio(api, vinculos_gerente):
    vinculos_gerente["pessoa-teste"] = set()
    assert api.get("/avaliacoes/historico").json() == []


def test_lider_ve_tudo(api, autenticar):
    autenticar(api, "lider")
    assert len(api.get("/avaliacoes/historico").json()) == 2


def test_rotas_de_fora(api):
    assert api.get("/avaliacoes/s-out/pendencias").status_code == 403
    assert api.get("/avaliacoes/s-out/elegiveis").status_code == 403
    assert api.post("/avaliacoes/s-out/confirmar").status_code == 403
    assert api.get("/avaliacoes/a-out/edicoes").status_code == 403
    corpo = {f"resposta_{i}": 3 for i in range(1, 8)}
    assert api.patch("/avaliacoes/a-out", json={**corpo, "motivo": "ajuste de nota"}).status_code == 403
    assert api.fake.writes == []
    assert api.get("/avaliacoes/s-in/pendencias").status_code != 403
    assert api.get("/avaliacoes/s-in/elegiveis").status_code != 403
    assert api.get("/avaliacoes/a-in/edicoes").status_code != 403


def test_post_exige_mesmo_projeto(api):
    corpo = {f"resposta_{i}": 3 for i in range(1, 8)}
    for sprint, op in (("s-out", "o-out"), ("s-in", "o-out"), ("s-out", "o-in")):
        r = api.post("/avaliacoes", json={"sprint_id": sprint, "operacional_id": op, **corpo})
        assert r.status_code == 403, (sprint, op, r.text)
    assert api.fake.writes == []


def test_settings_gemini(api, autenticar, monkeypatch):
    monkeypatch.setattr("routers.settings.get_gemini_api_key_status", lambda: {"configured": True, "source": "env", "masked": None, "model": "m"})
    assert api.get("/settings/gemini").status_code == 403
    assert api.put("/settings/gemini/api-key", json={"api_key": "x"}).status_code == 403
    autenticar(api, "lider")
    assert api.get("/settings/gemini").status_code != 403
