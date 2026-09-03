"""
Testes para o job diário check_travamento_automatico e para o endpoint
POST /tasks/{id}/travado/override (ALERT-01, ALERT-03).

Casos cobertos (per PLAN.md <behavior>):
  Job:
    1. pontos=2 (limiar=4 dias), entrou_em_andamento_em 5 dias atrás,
       travado_automatico=False, travado_override=False -> update(travado_automatico=True).
    2. mesma task mas entrou_em_andamento_em 2 dias atrás (< limiar) -> nenhum update.
    3. travado_override=True (mesmo cruzando limiar) -> nenhum update.
    4. travado_automatico=True já (idempotência) -> nenhum update redundante.
    5. entrou_em_andamento_em=None (legado) -> pulada sem erro, nenhum update.
    6. select inicial filtra só coluna_kanban=em_andamento.
  Endpoint:
    7. POST /tasks/{id}/travado/override?autor=... numa task em em_andamento ->
       200; updates incluem travado_override=True, travado_override_por,
       travado_override_em; travado_automatico NÃO aparece em updates.
    8. mesma chamada numa task fora de em_andamento -> 409, nenhuma escrita.
    9. task inexistente -> 404.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


# ── Job ──────────────────────────────────────────────────────────────────────

def _make_job_mock_client(tasks_data):
    client = MagicMock()
    calls = {"tasks_update": [], "eq_filters": []}

    def table_side_effect(table_name):
        tbl = MagicMock()
        if table_name == "tasks":
            def select_side_effect(cols):
                query = MagicMock()

                def eq_side_effect(field, value):
                    calls["eq_filters"].append((field, value))
                    return query

                query.eq = MagicMock(side_effect=eq_side_effect)
                resp = MagicMock()
                resp.data = tasks_data
                query.execute = MagicMock(return_value=resp)
                return query

            def update_side_effect(updates):
                q = MagicMock()

                def eq_then_execute(field, value):
                    calls["tasks_update"].append({"updates": updates, "id": value})
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(updates, id=value)]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_then_execute)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _iso(dias_atras: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias_atras)).isoformat()


def test_job_marca_travado_quando_limiar_cruzado(monkeypatch):
    import services.travamento_checker as checker
    task = {
        "id": "task-1", "pontos": 2, "entrou_em_andamento_em": _iso(5),
        "travado_automatico": False, "travado_override": False,
    }
    mock_sb, calls = _make_job_mock_client([task])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert len(calls["tasks_update"]) == 1
    assert calls["tasks_update"][0]["id"] == "task-1"
    assert calls["tasks_update"][0]["updates"] == {"travado_automatico": True}


def test_job_nao_marca_quando_abaixo_do_limiar(monkeypatch):
    import services.travamento_checker as checker
    task = {
        "id": "task-1", "pontos": 2, "entrou_em_andamento_em": _iso(2),
        "travado_automatico": False, "travado_override": False,
    }
    mock_sb, calls = _make_job_mock_client([task])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert len(calls["tasks_update"]) == 0


def test_job_nao_marca_quando_travado_override_true(monkeypatch):
    import services.travamento_checker as checker
    task = {
        "id": "task-1", "pontos": 1, "entrou_em_andamento_em": _iso(30),
        "travado_automatico": False, "travado_override": True,
    }
    mock_sb, calls = _make_job_mock_client([task])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert len(calls["tasks_update"]) == 0


def test_job_idempotente_quando_ja_travado_automatico(monkeypatch):
    import services.travamento_checker as checker
    task = {
        "id": "task-1", "pontos": 1, "entrou_em_andamento_em": _iso(30),
        "travado_automatico": True, "travado_override": False,
    }
    mock_sb, calls = _make_job_mock_client([task])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert len(calls["tasks_update"]) == 0


def test_job_pula_task_sem_entrou_em_andamento_em(monkeypatch):
    import services.travamento_checker as checker
    task = {
        "id": "task-1", "pontos": 3, "entrou_em_andamento_em": None,
        "travado_automatico": False, "travado_override": False,
    }
    mock_sb, calls = _make_job_mock_client([task])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert len(calls["tasks_update"]) == 0


def test_job_filtra_select_por_coluna_em_andamento(monkeypatch):
    import services.travamento_checker as checker
    mock_sb, calls = _make_job_mock_client([])
    monkeypatch.setattr(checker, "get_client", lambda: mock_sb)

    checker.check_travamento_automatico()

    assert ("coluna_kanban", "em_andamento") in calls["eq_filters"]


# ── Endpoint POST /tasks/{id}/travado/override ─────────────────────────────

def _make_endpoint_mock_client(task_data):
    client = MagicMock()
    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)] if task_data else []
    updated_row = dict(task_data) if task_data else {}

    calls = {"tasks_update": []}

    def table_side_effect(table_name):
        tbl = MagicMock()
        if table_name == "tasks":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.execute = MagicMock(return_value=task_select_resp)
                return query

            def update_side_effect(updates):
                calls["tasks_update"].append(updates)
                query = MagicMock()

                def eq_then_execute(field, value):
                    exec_query = MagicMock()
                    merged = dict(updated_row)
                    merged.update(updates)
                    resp = MagicMock()
                    resp.data = [merged]
                    exec_query.execute = MagicMock(return_value=resp)
                    return exec_query

                query.eq = MagicMock(side_effect=eq_then_execute)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        else:
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(app)


_BASE_TASK = {
    "id": "task-1",
    "project_id": "proj-1",
    "titulo": "Fazer algo",
    "pontos": 2,
    "coluna_kanban": "em_andamento",
    "ordem": 0,
    "sprint_id": "sprint-1",
    "operacional_id": None,
    "descricao": None,
    "bloqueado": False,
    "motivo_bloqueio": None,
    "checklist": [],
    "contador_reaberturas": 0,
    "bloqueado_manual": False,
    "bloqueado_em": None,
    "bloqueado_por": None,
    "bloqueado_resolvido_por": None,
    "bloqueado_resolvido_em": None,
    "entrou_em_andamento_em": "2026-01-01T00:00:00+00:00",
    "travado_automatico": True,
    "travado_override": False,
    "travado_override_por": None,
    "travado_override_em": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


def test_override_em_task_em_andamento_grava_supressao_sem_tocar_automatico(monkeypatch):
    task = dict(_BASE_TASK)
    mock_sb, calls = _make_endpoint_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks/task-1/travado/override", params={"autor": "Gerente X"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert updates["travado_override"] is True
    assert updates["travado_override_por"] == "Gerente X"
    assert updates["travado_override_em"] is not None
    assert "travado_automatico" not in updates


def test_override_em_task_fora_de_em_andamento_retorna_409_sem_escrever(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="planejado")
    mock_sb, calls = _make_endpoint_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks/task-1/travado/override")

    assert resp.status_code == 409
    assert "Em Andamento" in resp.json()["detail"]
    assert len(calls["tasks_update"]) == 0


def test_override_em_task_inexistente_retorna_404(monkeypatch):
    mock_sb, calls = _make_endpoint_mock_client(None)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks/task-nao-existe/travado/override")

    assert resp.status_code == 404
    assert len(calls["tasks_update"]) == 0
