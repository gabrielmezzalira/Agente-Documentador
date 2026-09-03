"""
Testes para o relógio entrou_em_andamento_em — set/reset ponta a ponta em
patch_task/create_task (ALERT-01, ALERT-02).

Casos cobertos (per PLAN.md <behavior>):
  1. PATCH planejado -> em_andamento: updates incluem entrou_em_andamento_em
     (não nulo), travado_automatico=False, travado_override=False,
     travado_override_por=None, travado_override_em=None.
  2. PATCH concluida -> em_andamento (reabertura): mesmo resultado do caso 1.
  3. PATCH em_andamento -> concluida (saindo): updates incluem
     entrou_em_andamento_em=None + os mesmos 4 resets.
  4. PATCH em_andamento -> planejado (saindo, caminho diferente): mesmo reset.
  5. PATCH sem mudar coluna_kanban: nenhum dos 5 campos aparece em updates.
  6. PATCH planejado -> concluida direto (nunca passou por em_andamento):
     nenhum dos 5 campos aparece em updates.
  7. POST /tasks criando já em em_andamento: payload de insert inclui
     entrou_em_andamento_em setado.
  8. POST /tasks criando em planejado (default): payload de insert NÃO inclui
     entrou_em_andamento_em.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data):
    client = MagicMock()

    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]
    updated_row = dict(task_data)

    calls = {"tasks_update": [], "tasks_insert": []}

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

            def insert_side_effect(payload):
                calls["tasks_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                merged = dict(updated_row)
                merged.update(payload)
                merged.setdefault("id", "task-new")
                resp.data = [merged]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

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

        elif table_name == "task_reaberturas":
            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="reabertura-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif table_name == "projects":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"id": "proj-1", "wip_config": {}}]
                query.execute = MagicMock(return_value=resp)
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
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(app)


_BASE_TASK = {
    "id": "task-1",
    "project_id": "proj-1",
    "titulo": "Fazer algo",
    "pontos": 2,
    "coluna_kanban": "planejado",
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
    "entrou_em_andamento_em": None,
    "travado_automatico": False,
    "travado_override": False,
    "travado_override_por": None,
    "travado_override_em": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


def _assert_seta_relogio(updates):
    assert updates["entrou_em_andamento_em"] is not None
    assert updates["travado_automatico"] is False
    assert updates["travado_override"] is False
    assert updates["travado_override_por"] is None
    assert updates["travado_override_em"] is None


def _assert_reseta_relogio(updates):
    assert updates["entrou_em_andamento_em"] is None
    assert updates["travado_automatico"] is False
    assert updates["travado_override"] is False
    assert updates["travado_override_por"] is None
    assert updates["travado_override_em"] is None


def test_planejado_para_em_andamento_seta_relogio(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="planejado")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 200
    _assert_seta_relogio(calls["tasks_update"][-1])


def test_reabertura_concluida_para_em_andamento_tambem_seta_relogio(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="concluida", travado_automatico=True, travado_override=True)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "em_andamento"})

    assert resp.status_code == 200
    _assert_seta_relogio(calls["tasks_update"][-1])


def test_em_andamento_para_concluida_reseta_relogio(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="em_andamento", entrou_em_andamento_em="2026-01-01T00:00:00+00:00")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 200
    _assert_reseta_relogio(calls["tasks_update"][-1])


def test_em_andamento_para_planejado_reseta_relogio(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="em_andamento", entrou_em_andamento_em="2026-01-01T00:00:00+00:00")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "planejado"})

    assert resp.status_code == 200
    _assert_reseta_relogio(calls["tasks_update"][-1])


def test_patch_sem_mudar_coluna_nao_escreve_campos_de_travamento(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="em_andamento")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"titulo": "Novo título"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    for campo in (
        "entrou_em_andamento_em", "travado_automatico",
        "travado_override", "travado_override_por", "travado_override_em",
    ):
        assert campo not in updates


def test_planejado_para_concluida_direto_nao_escreve_campos_de_travamento(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="planejado")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    for campo in (
        "entrou_em_andamento_em", "travado_automatico",
        "travado_override", "travado_override_por", "travado_override_em",
    ):
        assert campo not in updates


def test_post_task_criada_em_em_andamento_ancora_relogio(monkeypatch):
    task = dict(_BASE_TASK)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1",
        "titulo": "Task nova",
        "pontos": 3,
        "coluna_kanban": "em_andamento",
    })

    assert resp.status_code == 201
    payload = calls["tasks_insert"][-1]
    assert payload.get("entrou_em_andamento_em") is not None


def test_post_task_criada_em_planejado_nao_ancora_relogio(monkeypatch):
    task = dict(_BASE_TASK)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1",
        "titulo": "Task nova",
        "pontos": 3,
    })

    assert resp.status_code == 201
    payload = calls["tasks_insert"][-1]
    assert "entrou_em_andamento_em" not in payload
