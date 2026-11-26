"""Modo Atribuição: toda task nasce com responsável. Material de apoio é só do gerente."""
import pytest
from fastapi.testclient import TestClient

from main import app
from tests.fake_supabase import FakeClient

ATR, PUL = "p-atr", "p-pull"


@pytest.fixture
def api(monkeypatch, autenticar, vinculos_gerente):
    fake = FakeClient({
        "projects": [{"id": ATR, "modo_trabalho": "ATRIBUICAO"}, {"id": PUL, "modo_trabalho": "PULL"}],
        "tasks": [{"id": "t1", "project_id": ATR, "titulo": "a", "coluna_kanban": "planejado"}],
        "funcionalidades": [{"id": "f1", "project_id": ATR, "created_at": "2026-01-01"}, {"id": "f2", "project_id": PUL, "created_at": "2026-01-01"}],
        "operacionais": [],
    }, defaults={"tasks": {"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00"}})
    monkeypatch.setattr("routers.tasks.get_client", lambda: fake)
    vinculos_gerente["pessoa-teste"] = {ATR, PUL}
    c = TestClient(app)
    autenticar(c, "gerente")
    c.fake = fake
    c.como = lambda cargo: autenticar(TestClient(app), cargo)
    return c


def test_atribuicao_sem_responsavel_e_recusada_e_nada_e_criado(api):
    r = api.post("/tasks", json={"project_id": ATR, "titulo": "Nova", "funcionalidade_id": "f1", "nivel_gerente": 2})
    assert r.status_code == 422 and "precisa de um responsável" in r.json()["detail"]
    assert len(api.fake.tables["tasks"]) == 1


def test_responsavel_vazio_tambem_conta_como_ausente(api):
    r = api.post("/tasks", json={"project_id": ATR, "titulo": "Nova", "funcionalidade_id": "f1", "operacional_id": "", "nivel_gerente": 2})
    assert r.status_code == 422 and "precisa de um responsável" in r.json()["detail"]
    assert len(api.fake.tables["tasks"]) == 1


def test_pull_continua_sem_responsavel_e_nao_cai_na_regra(api):
    # em Pull a task nasce sem dono, na fila: a regra de Atribuição não pode barrar
    r = api.post("/tasks", json={"project_id": PUL, "titulo": "Fila", "funcionalidade_id": "f2", "nivel_gerente": 2})
    assert r.status_code == 201
    assert len(api.fake.tables["tasks"]) == 2


def test_operacional_nao_edita_material_de_apoio(api):
    r = api.como("operacional").patch("/tasks/t1", json={"material_apoio": "# oi"})
    assert r.status_code == 403
    assert "material_apoio" in r.json()["detail"]


def test_material_de_apoio_tem_tamanho_maximo():
    from pydantic import ValidationError
    from models.schemas import TaskCreate, TaskUpdate

    with pytest.raises(ValidationError):
        TaskUpdate(material_apoio="x" * 20001)
    with pytest.raises(ValidationError):
        TaskCreate(project_id="p", titulo="t", funcionalidade_id="f", material_apoio="x" * 20001)
    assert TaskUpdate(material_apoio="x" * 20000).material_apoio
