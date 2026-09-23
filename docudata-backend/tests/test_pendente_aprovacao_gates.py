"""Gates de transição do estado pendente_aprovacao em patch_task. Ver
docs/superpowers/specs/2026-09-22-task-pendente-aprovacao-design.md §4-5."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "sprints":
            # inclui "numero" além de "iniciada"/"id": o mock ignora as colunas
            # pedidas e devolve sempre a mesma linha, e services/task_events.py
            # (on_task_transition -> _log_ingestion) faz um select("numero")
            # nessa mesma tabela a cada mudança de coluna_kanban.
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"iniciada": True, "id": "sprint-1", "numero": 1}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
            tbl.insert = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK_BASE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "ordem": 0, "sprint_id": "sprint-1", "operacional_id": "op-1",
    "descricao": None, "bloqueado": False, "motivo_bloqueio": None,
    "checklist": [], "extra": False, "requer_aprovacao": False,
    "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task_overrides=None, cargo="gerente"):
        import routers.tasks as tasks_router
        from main import app
        task = {**_TASK_BASE, **(task_overrides or {})}
        mock_sb = _mock_client(task)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc
    return _make


def test_patch_bloqueia_saida_generica_de_pendente_aprovacao(make_client):
    tc = make_client({"coluna_kanban": "pendente_aprovacao"})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 422
    assert "aprovar" in resp.json()["detail"].lower()


def test_patch_bloqueia_concluida_direto_quando_requer_aprovacao(make_client):
    tc = make_client({"coluna_kanban": "em_andamento", "requer_aprovacao": True, "checklist": []})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 422
    assert "aprovação" in resp.json()["detail"].lower()


def test_patch_permite_concluida_direto_quando_nao_requer_aprovacao(make_client):
    tc = make_client({"coluna_kanban": "em_andamento", "requer_aprovacao": False, "checklist": []})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 200


def test_patch_permite_ir_para_pendente_aprovacao_com_checklist_vazio(make_client):
    tc = make_client({"coluna_kanban": "em_andamento", "checklist": []})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 200
    assert resp.json()["coluna_kanban"] == "pendente_aprovacao"


def test_patch_bloqueia_pendente_aprovacao_com_checklist_incompleto(make_client):
    tc = make_client({
        "coluna_kanban": "em_andamento",
        "checklist": [{"texto": "item", "done": False}],
    })

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 409
    assert "DoD" in resp.json()["detail"]


def test_patch_para_relogio_de_travamento_ao_entrar_em_pendente_aprovacao(make_client):
    tc = make_client({
        "coluna_kanban": "em_andamento",
        "checklist": [],
        "entrou_em_andamento_em": "2026-09-01T00:00:00+00:00",
    })

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 200
    assert resp.json()["entrou_em_andamento_em"] is None
