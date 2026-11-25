"""Acesso por projeto em tasks, funcionalidades, sprints e sprint-funcionalidades."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app

PID, OUTRO = "proj-1", "proj-2"


class Fake:
    def __init__(self):
        self.t = {
            "pessoa": [{"id": "pessoa-teste", "nome": "Eu", "email": "pessoa@citi.org.br", "cargo": "gerente"}],
            "projects": [{"id": PID, "modo_trabalho": "ATRIBUICAO"}, {"id": OUTRO, "modo_trabalho": "ATRIBUICAO"}],
            "tasks": [
                {"id": "t-in", "project_id": PID, "coluna_kanban": "planejado", "titulo": "a", "ordem": 0},
                {"id": "t-out", "project_id": OUTRO, "coluna_kanban": "planejado", "titulo": "b", "ordem": 0},
            ],
            "funcionalidades": [
                {"id": "f-in", "project_id": PID, "titulo": "f", "status": "nao_iniciada", "id_funcional": "RF1", "criterios_aceite": ["c"], "prioridade": "must", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
                {"id": "f-out", "project_id": OUTRO, "titulo": "f", "status": "nao_iniciada", "id_funcional": "RF1", "criterios_aceite": ["c"], "prioridade": "must", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            ],
            "sprints": [
                {"id": "s-in", "project_id": PID, "numero": 1, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
                {"id": "s-out", "project_id": OUTRO, "numero": 1, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            ],
            "sprint_funcionalidades": [
                {"id": "sf-in", "sprint_id": "s-in", "funcionalidade_id": "f-in"},
                {"id": "sf-out", "sprint_id": "s-out", "funcionalidade_id": "f-out"},
            ],
            "transicoes_status": [], "task_transicoes": [], "operacionais": [],
        }
        self.writes = []

    def table(self, name):
        return Q(self, name)


class Q:
    def __init__(self, db, name):
        self.db, self.name, self.f, self.op, self.payload = db, name, [], "select", None

    def select(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def range(self, *a, **k): return self
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
        if self.op == "insert":
            row = {"id": "novo", "created_at": "2026-01-03", **self.payload}
            rows.append(row); r.data = [row]
        elif self.op == "update":
            for m in match: m.update(self.payload)
            r.data = match
        elif self.op == "delete":
            for m in match: rows.remove(m)
            r.data = match
        else:
            r.data = match
        return r


@pytest.fixture
def api(monkeypatch, autenticar, vinculos_gerente):
    fake = Fake()
    for mod in ("tasks", "funcionalidades", "sprints", "sprint_funcionalidades"):
        monkeypatch.setattr(f"routers.{mod}.get_client", lambda: fake)
    monkeypatch.setattr("services.auth.get_client", lambda: fake)
    vinculos_gerente["pessoa-teste"] = {PID}
    c = TestClient(app)
    autenticar(c, "gerente")
    c.fake = fake
    return c


def _sem_escrita(api, antes):
    assert api.fake.writes == antes


# ---- tasks ----
def test_task_leitura_de_fora_403_e_de_dentro_passa(api):
    assert api.get("/tasks/t-out").status_code == 403
    assert api.get("/tasks/t-out/transicoes").status_code == 403
    assert api.get("/tasks/t-in/transicoes").status_code == 200


def test_task_escrita_de_fora_403_sem_escrever(api):
    assert api.delete("/tasks/t-out").status_code == 403
    assert api.patch("/tasks/t-out", json={"titulo": "x"}).status_code == 403
    assert api.post("/tasks/t-out/mover", params={"coluna_destino": "em_andamento"}).status_code == 403
    assert api.post("/tasks/t-out/aprovar").status_code == 403
    assert api.post("/tasks/t-out/puxar").status_code == 403
    assert api.post("/tasks", json={"project_id": OUTRO, "titulo": "n", "funcionalidade_id": "f-out"}).status_code == 403
    _sem_escrita(api, [])
    assert any(t["id"] == "t-out" for t in api.fake.t["tasks"])


def test_reordenar_batch_barra_antes_de_escrever(api):
    itens = [{"id": "t-in", "ordem": 5}, {"id": "t-out", "ordem": 6}]
    assert api.patch("/tasks/reordenar/batch", json=itens).status_code == 403
    _sem_escrita(api, [])
    assert api.patch("/tasks/reordenar/batch", json=[{"id": "t-in", "ordem": 5}]).status_code == 200


def test_task_delete_vinculado_passa(api):
    assert api.delete("/tasks/t-in").status_code == 204


# ---- funcionalidades ----
def test_funcionalidades_de_fora_403(api):
    assert api.get("/funcionalidades", params={"project_id": OUTRO}).status_code == 403
    assert api.get("/funcionalidades/f-out").status_code == 403
    assert api.get("/funcionalidades/f-out/transicoes").status_code == 403
    assert api.post("/funcionalidades", json={"project_id": OUTRO, "id_funcional": "RF1", "titulo": "x", "criterios_aceite": ["y"], "sprint_alvo": "1"}).status_code == 403
    assert api.patch("/funcionalidades/f-out", json={"titulo": "x"}).status_code == 403
    assert api.delete("/funcionalidades/f-out").status_code == 403
    assert api.post("/funcionalidades/f-out/aprovar").status_code == 403
    _sem_escrita(api, [])


def test_funcionalidades_vinculado_passa(api):
    assert api.get("/funcionalidades/f-in/transicoes").status_code == 200
    assert api.delete("/funcionalidades/f-in").status_code == 204


# ---- sprints ----
def test_sprints_de_fora_403_sem_escrita(api):
    assert api.delete("/sprints/s-out").status_code == 403
    assert api.patch("/sprints/s-out/iniciar").status_code == 403
    assert api.patch("/sprints/s-out/health", json={"status_saude": "verde"}).status_code == 403
    assert api.get(f"/projects/{OUTRO}/sprints").status_code == 403
    _sem_escrita(api, [])


def test_sprint_health_vinculado_passa(api):
    assert api.patch("/sprints/s-in/health", json={"status_saude": "verde"}).status_code == 200


# ---- sprint-funcionalidades ----
def test_sprint_funcionalidades_de_fora_403(api):
    assert api.get("/sprint-funcionalidades/sprint/s-out").status_code == 403
    assert api.get(f"/sprint-funcionalidades/recomendadas/{OUTRO}").status_code == 403
    assert api.patch("/sprint-funcionalidades/sf-out", json={"status": "concluida"}).status_code == 403
    body = {"sprint_id": "s-out", "correlacoes": [{"funcionalidade_id": "f-out", "tasks": []}]}
    assert api.post("/sprint-funcionalidades", json=body).status_code == 403
    _sem_escrita(api, [])


def test_sprint_funcionalidades_vinculado_passa(api):
    assert api.get("/sprint-funcionalidades/sprint/s-in").status_code == 200
    assert api.get(f"/sprint-funcionalidades/recomendadas/{PID}").status_code == 200
    assert api.patch("/sprint-funcionalidades/sf-in", json={"status": "em_andamento"}).status_code == 200


# ---- fix round 1 ----
def _operacional_de_a(api, autenticar):
    api.fake.t["operacionais"].append({"id": "op-a", "project_id": PID, "email": "pessoa@citi.org.br"})
    for p in api.fake.t["projects"]:
        p["modo_trabalho"] = "PULL"
    autenticar(api, "operacional")


def test_operacional_de_a_nao_mexe_em_task_de_b(api, autenticar):
    _operacional_de_a(api, autenticar)
    assert api.post("/tasks/t-out/devolver").status_code == 403
    assert api.patch("/tasks/t-out", json={"coluna_kanban": "em_andamento"}).status_code == 403
    assert api.post("/tasks/t-out/mover", params={"coluna_destino": "em_andamento"}).status_code == 403
    assert api.post("/tasks/t-out/puxar").status_code == 403
    _sem_escrita(api, [])


def test_leituras_de_gerente_vinculado(api):
    assert api.get(f"/projects/{PID}/sprints").status_code == 200
    assert api.get("/funcionalidades", params={"project_id": PID}).status_code == 200


def test_sprint_funcionalidades_rejeita_funcionalidade_de_outro_projeto(api):
    body = {"sprint_id": "s-in", "correlacoes": [{"funcionalidade_id": "f-out", "tasks": []}]}
    assert api.post("/sprint-funcionalidades", json=body).status_code == 403
    body = {"sprint_id": "s-in", "correlacoes": [{"funcionalidade_id": "f-inexistente", "tasks": []}]}
    assert api.post("/sprint-funcionalidades", json=body).status_code == 422
    _sem_escrita(api, [])
    assert next(f for f in api.fake.t["funcionalidades"] if f["id"] == "f-out")["status"] == "nao_iniciada"


def test_sprint_funcionalidade_patch_confere_acesso_antes_da_validacao(api):
    assert api.patch("/sprint-funcionalidades/sf-out", json={}).status_code == 403
