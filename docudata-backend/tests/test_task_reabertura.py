"""
Testes para reabertura de task (TRANS-03): task_reaberturas + tasks.contador_reaberturas.

Regra: reabertura é estritamente a transição coluna_kanban: concluida -> em_andamento.
Nenhuma outra saída de "concluida" conta. motivo é opcional em todo o caminho.

Casos cobertos (per PLAN.md <behavior>):
  1. concluida -> em_andamento grava task_reaberturas (task_id, transicao_id,
     operacional_id, motivo, timestamp) e contador_reaberturas = (atual ou 0) + 1.
  2. mesma transição com contador_reaberturas já em 2 -> novo valor é 3.
  3. em_andamento -> concluida (não é reabertura) -> nenhuma linha em task_reaberturas,
     contador_reaberturas não aparece em updates.
  4. concluida -> planejado (saída de concluida que não é para em_andamento) -> nenhuma
     linha em task_reaberturas.
  5. motivo ausente -> reabertura grava motivo=None sem erro.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data):
    client = MagicMock()

    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]
    updated_row = dict(task_data)

    calls = {
        "tasks_update": [],
        "task_transicoes_insert": [],
        "task_reaberturas_insert": [],
    }

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
                calls["task_transicoes_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id=f"transicao-{len(calls['task_transicoes_insert'])}")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif table_name == "task_reaberturas":
            def insert_side_effect(payload):
                calls["task_reaberturas_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="reabertura-1")]
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
    "coluna_kanban": "concluida",
    "ordem": 0,
    "sprint_id": "sprint-1",
    "operacional_id": "op-1",
    "descricao": None,
    "bloqueado": False,
    "motivo_bloqueio": None,
    "checklist": [],
    "contador_reaberturas": 0,
    "created_at": "2026-01-01T00:00:00+00:00",
}


def test_reabertura_concluida_para_em_andamento_grava_task_reaberturas_e_incrementa(monkeypatch):
    task = dict(_BASE_TASK, contador_reaberturas=0)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento", "motivo": "Bug encontrado em produção"})

    assert resp.status_code == 200
    assert len(calls["task_reaberturas_insert"]) == 1
    reabertura = calls["task_reaberturas_insert"][0]
    assert reabertura["task_id"] == "task-1"
    assert reabertura["transicao_id"] == "transicao-1"
    assert reabertura["operacional_id"] == "op-1"
    assert reabertura["motivo"] == "Bug encontrado em produção"
    assert reabertura["timestamp"] is not None

    assert calls["tasks_update"][-1]["contador_reaberturas"] == 1


def test_reabertura_incrementa_a_partir_de_contador_existente(monkeypatch):
    task = dict(_BASE_TASK, contador_reaberturas=2)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 200
    assert calls["tasks_update"][-1]["contador_reaberturas"] == 3


def test_em_andamento_para_concluida_nao_e_reabertura(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="em_andamento", checklist=[], contador_reaberturas=0)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 200
    assert len(calls["task_reaberturas_insert"]) == 0
    assert "contador_reaberturas" not in calls["tasks_update"][-1]


def test_concluida_para_planejado_nao_e_reabertura(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="concluida", contador_reaberturas=0)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "planejado"})

    assert resp.status_code == 200
    assert len(calls["task_reaberturas_insert"]) == 0
    assert "contador_reaberturas" not in calls["tasks_update"][-1]


def test_reabertura_sem_motivo_grava_motivo_none(monkeypatch):
    task = dict(_BASE_TASK, contador_reaberturas=0)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 200
    assert len(calls["task_reaberturas_insert"]) == 1
    assert calls["task_reaberturas_insert"][0]["motivo"] is None
