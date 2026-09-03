"""
Testes para o caminho gated de resolução de sugestões da IA (PATCH /tasks/sugestoes/{id}).

TRANS-01 / TRANS-02 (Phase 14): aceitar uma sugestão de "mover_para_concluida" passa a
delegar em patch_task — o mesmo caminho gated (DoR/DoD/WIP + task_transicoes) usado por
PATCH /tasks/{id} e POST /tasks/{id}/mover. Antes desta phase, resolve_task_sugestao
fazia um update direto de coluna_kanban, sem gate nenhum e sem gravar task_transicoes.

Casos cobertos:
  1. Caminho feliz: sugestão aceita para task sem pendências -> 200, task movida para
     "concluida" via patch_task (gate passa), task_transicoes recebe um insert.
  2. Caminho de gate: sugestão aceita para task com checklist incompleto -> patch_task
     levanta 409 (DoD), a exceção propaga e a sugestão NÃO é marcada como aceita
     (nenhum update em task_sugestoes acontece).
  3. Recusar (aceita=false) nunca chama patch_task nem move a task, independente do
     estado da task.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data, sugestao_data):
    """
    Mock do cliente Supabase para PATCH /tasks/sugestoes/{id}, cobrindo tanto a
    tabela task_sugestoes (com join de tasks) quanto o caminho interno de patch_task
    sobre a tabela tasks/task_transicoes (mesmo padrão de tests/test_tasks_dod_gate.py).
    """
    client = MagicMock()

    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]
    updated_task_row = dict(task_data)

    sugestao_row = dict(sugestao_data)

    calls = {
        "tasks_update": [],
        "task_transicoes_insert": [],
        "sugestoes_update": [],
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
                    merged = dict(updated_task_row)
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
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif table_name == "task_sugestoes":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                # list_task_sugestoes usa .is_("aceita", "null") em vez de .eq(...)
                query.is_ = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [dict(sugestao_row)]
                query.execute = MagicMock(return_value=resp)
                return query

            def update_side_effect(updates):
                calls["sugestoes_update"].append(updates)
                sugestao_row.update(updates)
                query = MagicMock()

                def eq(field, value):
                    exec_query = MagicMock()

                    def select(cols):
                        sel_query = MagicMock()
                        resp = MagicMock()
                        resp.data = [dict(sugestao_row)]
                        sel_query.execute = MagicMock(return_value=resp)
                        return sel_query

                    exec_query.select = MagicMock(side_effect=select)
                    return exec_query

                query.eq = MagicMock(side_effect=eq)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)

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
    "created_at": "2026-01-01T00:00:00+00:00",
}

_BASE_SUGESTAO = {
    "id": "sug-1",
    "task_id": "task-1",
    "acao": "mover_para_concluida",
    "motivo": "Mencionada como concluída no review",
    "origem_ingestion_id": None,
    "aceita": None,
    "criado_em": "2026-01-01T00:00:00+00:00",
    "tasks": {"titulo": "Fazer algo", "project_id": "proj-1", "coluna_kanban": "em_andamento"},
}


def test_aceitar_sugestao_caminho_feliz_move_task_e_grava_transicao(monkeypatch):
    task = dict(_BASE_TASK, checklist=[])
    sugestao = dict(_BASE_SUGESTAO)
    mock_sb, calls = _make_mock_client(task, sugestao)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/sugestoes/sug-1", json={"aceita": True})

    assert resp.status_code == 200
    data = resp.json()
    assert data["aceita"] is True

    # A sugestão aceita passou pelo mesmo caminho gated de patch_task: a task foi
    # movida via tasks.update (não via update direto fora do gate) e uma transição
    # foi registrada em task_transicoes.
    assert len(calls["tasks_update"]) == 1
    assert calls["tasks_update"][0]["coluna_kanban"] == "concluida"
    assert len(calls["task_transicoes_insert"]) == 1
    assert calls["task_transicoes_insert"][0]["campo"] == "coluna_kanban"
    assert calls["task_transicoes_insert"][0]["para"] == "concluida"

    # A sugestão foi marcada como aceita só depois do patch_task ter sucesso.
    assert len(calls["sugestoes_update"]) == 1
    assert calls["sugestoes_update"][0]["aceita"] is True


def test_aceitar_sugestao_com_checklist_incompleto_propaga_409_e_nao_resolve(monkeypatch):
    task = dict(_BASE_TASK, checklist=[{"texto": "item pendente", "done": False}])
    sugestao = dict(_BASE_SUGESTAO)
    mock_sb, calls = _make_mock_client(task, sugestao)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/sugestoes/sug-1", json={"aceita": True})

    assert resp.status_code == 409
    assert "DoD" in resp.json()["detail"]

    # O gate rejeitou antes de qualquer escrita: nem a task foi atualizada, nem a
    # sugestão foi marcada como aceita (permanece null/não resolvida).
    assert len(calls["tasks_update"]) == 0
    assert len(calls["sugestoes_update"]) == 0


def test_recusar_sugestao_nao_move_task_nem_chama_patch_task(monkeypatch):
    task = dict(_BASE_TASK, checklist=[{"texto": "item pendente", "done": False}])
    sugestao = dict(_BASE_SUGESTAO)
    mock_sb, calls = _make_mock_client(task, sugestao)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/sugestoes/sug-1", json={"aceita": False})

    assert resp.status_code == 200
    data = resp.json()
    assert data["aceita"] is False

    assert len(calls["tasks_update"]) == 0
    assert len(calls["sugestoes_update"]) == 1
    assert calls["sugestoes_update"][0]["aceita"] is False


def test_list_sugestoes_inclui_task_coluna_atual(monkeypatch):
    task = dict(_BASE_TASK, checklist=[])
    sugestao = dict(_BASE_SUGESTAO)
    mock_sb, _calls = _make_mock_client(task, sugestao)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/tasks/sugestoes", params={"project_id": "proj-1"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["task_coluna_atual"] == "em_andamento"
