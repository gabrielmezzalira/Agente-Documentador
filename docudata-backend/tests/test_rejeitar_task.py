"""POST /tasks/{id}/rejeitar — só gerente/líder, limpa responsável e volta
pra planejado sem penalidade. Ver spec §4."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task, fila_existente=None):
    fila_existente = fila_existente or []
    tasks_update = []
    transicoes_insert = []
    envios = []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()

                def eq_effect(field, value):
                    if field == "coluna_kanban" and value == "planejado":
                        resp_fila = MagicMock()
                        resp_fila.data = fila_existente
                        q2 = MagicMock()
                        q2.execute = MagicMock(return_value=resp_fila)
                        return q2
                    return q

                q.eq = MagicMock(side_effect=eq_effect)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                tasks_update.append(payload)
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
                transicoes_insert.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"nome": "Davi", "email": "davi@citi.com"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"name": "Projeto X"}]
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
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_update, transicoes_insert, envios


_TASK_PENDENTE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "pendente_aprovacao", "ordem": 0, "sprint_id": "sprint-1",
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": True, "travado_automatico": False,
    "entrou_em_andamento_em": None, "pull_em": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task=None, cargo="gerente", fila_existente=None):
        import routers.tasks as tasks_router
        from main import app
        mock_sb, tasks_update, transicoes_insert, envios = _mock_client(task or _TASK_PENDENTE, fila_existente)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        monkeypatch.setattr(
            tasks_router, "send_email",
            lambda to, subject, html: envios.append((to, subject, html)),
        )
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, tasks_update, transicoes_insert, envios
    return _make


def test_rejeitar_limpa_responsavel_e_volta_pra_planejado(make_client):
    tc, tasks_update, _, _ = make_client()

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": "Faltou cobrir o edge case"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["coluna_kanban"] == "planejado"
    assert body["operacional_id"] is None
    assert tasks_update[-1]["travado_automatico"] is False


def test_rejeitar_exige_motivo(make_client):
    tc, tasks_update, _, _ = make_client()

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": ""})

    assert resp.status_code == 422
    assert tasks_update == []


def test_rejeitar_avisa_operacional_por_email(make_client):
    tc, _, _, envios = make_client()

    tc.post("/tasks/task-1/rejeitar", json={"motivo": "Faltou cobrir o edge case"})

    assert len(envios) == 1
    to, subject, html = envios[0]
    assert to == "davi@citi.com"
    assert "Faltou cobrir o edge case" in html


def test_rejeitar_rejeita_task_que_nao_esta_pendente(make_client):
    task = {**_TASK_PENDENTE, "coluna_kanban": "em_andamento"}
    tc, tasks_update, _, _ = make_client(task=task)

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": "x"})

    assert resp.status_code == 409
    assert tasks_update == []


def test_rejeitar_bloqueia_operacional(make_client):
    tc, tasks_update, _, _ = make_client(cargo="operacional")

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": "x"})

    assert resp.status_code == 403
    assert tasks_update == []
