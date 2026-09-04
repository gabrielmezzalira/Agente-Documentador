"""
Testes para bloqueio manual com captura de quem resolveu (TRANS-04, TRANS-05).

Casos cobertos (per PLAN.md <behavior>):
  1. bloqueado_manual=true numa task com bloqueado_manual=false -> 200; updates
     incluem bloqueado_manual=true, bloqueado_em e bloqueado_por.
  2. bloqueado_manual=false numa task com bloqueado_manual=true, SEM
     bloqueado_resolvido_por -> 422, detail menciona "resolveu"; nenhuma escrita
     em tasks.update acontece.
  3. mesma chamada, com bloqueado_resolvido_por="operacional" -> 200; updates
     incluem bloqueado_manual=false, bloqueado_resolvido_por, bloqueado_resolvido_em.
  4. bloqueado_resolvido_por fora de {"operacional", "gerente"} -> 422 de validação
     do Pydantic (TaskUpdate), antes de chegar na lógica do endpoint.
  5. PATCH sem tocar em bloqueado_manual -> 200, nenhum campo de bloqueio em updates.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data):
    client = MagicMock()

    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]
    updated_row = dict(task_data)

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

        elif table_name == "task_transicoes":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.order = MagicMock(return_value=query)
                query.limit = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)

            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif table_name in ("operacionais", "sprints"):
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
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
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", "test@citi.com", "gerente"))
    return tc


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
    "created_at": "2026-01-01T00:00:00+00:00",
}


def test_marcar_bloqueado_manual_grava_bloqueado_em_e_por(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=False)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": True, "bloqueado_por": "Ana"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert updates["bloqueado_manual"] is True
    assert updates["bloqueado_em"] is not None
    assert updates["bloqueado_por"] == "Ana"
    assert "bloqueado_resolvido_por" not in updates


def test_desmarcar_bloqueado_manual_sem_resolvido_por_retorna_422_sem_escrever(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueado_por="Ana")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": False})

    assert resp.status_code == 422
    assert "resolveu" in resp.json()["detail"]
    assert len(calls["tasks_update"]) == 0


def test_desmarcar_bloqueado_manual_com_resolvido_por_valido_grava(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueado_por="Ana")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": False, "bloqueado_resolvido_por": "operacional"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert updates["bloqueado_manual"] is False
    assert updates["bloqueado_resolvido_por"] == "operacional"
    assert updates["bloqueado_resolvido_em"] is not None
    assert "bloqueado_em" not in updates
    assert "bloqueado_por" not in updates


def test_bloqueado_resolvido_por_invalido_e_422_de_validacao(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueado_por="Ana")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": False, "bloqueado_resolvido_por": "cliente"})

    assert resp.status_code == 422
    # Erro de validação do Pydantic acontece antes de qualquer leitura/escrita na task.
    assert len(calls["tasks_update"]) == 0


def test_patch_sem_tocar_bloqueio_nao_inclui_campos_de_bloqueio(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=False)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"titulo": "Novo título"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert "bloqueado_manual" not in updates
    assert "bloqueado_em" not in updates
    assert "bloqueado_por" not in updates
    assert "bloqueado_resolvido_por" not in updates
    assert "bloqueado_resolvido_em" not in updates
