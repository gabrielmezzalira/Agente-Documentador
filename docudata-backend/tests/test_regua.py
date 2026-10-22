"""Régua única de dificuldade (spec A1 §1)."""
import pytest
from pydantic import ValidationError

from models.schemas import TaskCreate, TaskUpdate
from services.regua import (
    MENSAGEM_NIVEL_INVALIDO,
    NIVEIS,
    ROTULOS,
    ajuste_pontos_reabertura,
    converter_pontos_legado,
)


def test_niveis_da_regua():
    assert NIVEIS == (1, 2, 3, 5)
    assert ROTULOS == {1: "simples", 2: "moderada", 3: "complexa", 5: "muito complexa"}


@pytest.mark.parametrize("antigo,novo", [(1, 1), (2, 2), (3, 3), (4, 3), (5, 5), (8, 5), (13, 5)])
def test_converter_pontos_legado(antigo, novo):
    assert converter_pontos_legado(antigo) == novo


def test_ajuste_reabertura_vazio_quando_ja_esta_na_regua():
    assert ajuste_pontos_reabertura({"pontos": 3}) == {}


def test_ajuste_reabertura_converte_e_guarda_original():
    assert ajuste_pontos_reabertura({"pontos": 8}) == {"pontos": 5, "pontos_legado": 8}


@pytest.mark.parametrize("pontos", [1, 2, 3, 5])
def test_task_create_aceita_niveis(pontos):
    assert TaskCreate(project_id="p", titulo="t", pontos=pontos).pontos == pontos


@pytest.mark.parametrize("pontos", [0, 4, 8])
def test_task_create_rejeita_fora_da_regua(pontos):
    with pytest.raises(ValidationError) as exc:
        TaskCreate(project_id="p", titulo="t", pontos=pontos)
    assert MENSAGEM_NIVEL_INVALIDO in str(exc.value)


def test_task_update_rejeita_fora_da_regua_e_aceita_none():
    assert TaskUpdate().pontos is None
    with pytest.raises(ValidationError) as exc:
        TaskUpdate(pontos=4)
    assert MENSAGEM_NIVEL_INVALIDO in str(exc.value)


from fastapi.testclient import TestClient  # noqa: E402

from tests.fake_supabase import FakeClient  # noqa: E402


def _client_task_concluida_legada():
    return FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": True}],
        "tasks": [{
            "id": "t1", "project_id": "p1", "sprint_id": "s1", "titulo": "Legada",
            "pontos": 8, "coluna_kanban": "concluida", "bloqueado": False,
            "checklist": [], "ordem": 0, "extra": False, "operacional_id": None,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
        }],
    })


def test_reabrir_task_legada_converte_pontos(monkeypatch, autenticar):
    import routers.tasks as tasks_router
    from main import app

    fake = _client_task_concluida_legada()
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    monkeypatch.setattr(tasks_router, "check_wip", lambda *a, **k: (True, None))
    monkeypatch.setattr(tasks_router, "on_task_transition", lambda *a, **k: False)
    monkeypatch.setattr(tasks_router, "rotear_evento_pos_fechamento", lambda *a, **k: None)
    tc = autenticar(TestClient(app))

    resp = tc.patch("/tasks/t1", json={"coluna_kanban": "em_andamento", "motivo": "voltou"})

    assert resp.status_code == 200, resp.text
    task = fake.tables["tasks"][0]
    assert task["pontos"] == 5
    assert task["pontos_legado"] == 8


def test_migracao_regua_espelha_converter_pontos_legado():
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")
    bloco = sql.split("Rodada A1")[1]
    assert "WHEN pontos <= 1 THEN 1" in bloco
    assert "WHEN pontos = 2 THEN 2" in bloco
    assert "WHEN pontos <= 4 THEN 3" in bloco
    assert "ELSE 5" in bloco
    assert "CHECK (pontos IN (1, 2, 3, 5) OR coluna_kanban = 'concluida')" in bloco
    for coluna in ("pontos_legado", "aprovada_em", "aprovada_por", "prevista_no_inicio", "surgiu_na_sprint"):
        assert coluna in bloco
    assert "coluna_kanban <> 'concluida'" in bloco
    assert "t.surgiu_na_sprint = false" in bloco
    assert bloco.index("UPDATE tasks\nSET pontos_legado") < bloco.index("ADD CONSTRAINT tasks_pontos_check")
