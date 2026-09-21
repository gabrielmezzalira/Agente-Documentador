# tests/test_migracao_modo.py (novo)
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, tasks):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto] if projeto else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto, tasks):
        import routers.projects as projects_router
        from main import app
        mock_sb = _mock_client(projeto, tasks)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc
    return _make


def test_preview_migracao_conta_tasks_por_categoria(make_client):
    tasks = [
        {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [{"texto": "a", "done": False}], "bloqueado": False},
        {"id": "t2", "coluna_kanban": "planejado", "operacional_id": None, "titulo": "Y", "pontos": 2, "descricao": None, "checklist": [], "bloqueado": False},
        {"id": "t3", "coluna_kanban": "em_andamento", "operacional_id": "op-b", "titulo": "Z", "pontos": 5, "descricao": "d", "checklist": [], "bloqueado": False},
        {"id": "t4", "coluna_kanban": "concluida", "operacional_id": "op-a", "titulo": "W", "pontos": 4, "descricao": "d", "checklist": [], "bloqueado": False},
        {"id": "t5", "coluna_kanban": "planejado", "operacional_id": "op-c", "titulo": "V", "pontos": 1, "descricao": "d", "checklist": [], "bloqueado": True},
    ]
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True}, tasks=tasks)

    resp = tc.get("/projects/proj-1/migrar-modo/preview?para=PULL")

    assert resp.status_code == 200
    body = resp.json()
    assert body["entrando_na_fila"] == 1  # t1: planejado com responsável, hidratada
    assert body["vira_rascunho"] == 1  # t2: planejado sem descrição/checklist
    assert body["mantem_responsavel"] == 2  # t3: em_andamento; t5: bloqueada (mantém responsável mesmo planejada)
    assert body["sem_alteracao"] == 1  # t4: concluida


def _mock_client_completo(projeto, tasks):
    """Estende _mock_client com update de tasks/sprints e insert de
    migracoes_modo, capturando os payloads em listas (mesmo padrão das
    Tasks 2 e 11) pra assertar o que a rota de aplicação de fato gravou."""
    tasks_update = []
    migracoes_insert = []
    sprints_update = []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto] if projeto else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)

            def _update(payload):
                tasks_update.append(payload)
                uq = MagicMock()
                uq.eq = MagicMock(return_value=uq)
                uresp = MagicMock()
                uresp.data = [payload]
                uq.execute = MagicMock(return_value=uresp)
                return uq
            tbl.update = MagicMock(side_effect=_update)
        elif name == "sprints":
            def _update(payload):
                sprints_update.append(payload)
                uq = MagicMock()
                uq.eq = MagicMock(return_value=uq)
                uresp = MagicMock()
                uresp.data = [payload]
                uq.execute = MagicMock(return_value=uresp)
                return uq
            tbl.update = MagicMock(side_effect=_update)
        elif name == "migracoes_modo":
            def _insert(payload):
                migracoes_insert.append(payload)
                iq = MagicMock()
                iresp = MagicMock()
                iresp.data = [payload]
                iq.execute = MagicMock(return_value=iresp)
                return iq
            tbl.insert = MagicMock(side_effect=_insert)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_update, migracoes_insert, sprints_update


@pytest.fixture
def make_client_completo(monkeypatch, autenticar):
    def _make(projeto, tasks):
        import routers.projects as projects_router
        from main import app
        mock_sb, tasks_update, migracoes_insert, sprints_update = _mock_client_completo(projeto, tasks)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc, tasks_update, migracoes_insert, sprints_update
    return _make


def test_aplicar_migracao_para_pull_reclassifica_tasks_e_grava_auditoria(make_client_completo, monkeypatch):
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")
    tc, tasks_update, migracoes_insert, sprints_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True},
        tasks=[
            {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [{"texto": "a", "done": False}], "bloqueado": False},
            {"id": "t4", "coluna_kanban": "concluida", "operacional_id": "op-a", "titulo": "W", "pontos": 4, "descricao": "d", "checklist": [], "bloqueado": False},
            {"id": "t5", "coluna_kanban": "planejado", "operacional_id": "op-c", "titulo": "V", "pontos": 1, "descricao": "d", "checklist": [], "bloqueado": True},
        ],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    # Só t1 (planejado, não bloqueada) sofre update — t4 (concluída) e t5
    # (bloqueada) nunca disparam client.table("tasks").update(...), então a
    # lista capturada tem exatamente 1 entrada.
    assert len(tasks_update) == 1
    assert tasks_update[0]["operacional_id"] is None
    assert "entrou_na_fila_em" in tasks_update[0]
    assert migracoes_insert[0]["de_modo"] == "ATRIBUICAO"
    assert migracoes_insert[0]["para_modo"] == "PULL"
    assert migracoes_insert[0]["contagem"]["mantem_responsavel"] == 1  # t5, bloqueada
    assert migracoes_insert[0]["contagem"]["sem_alteracao"] == 1  # t4, concluída
    assert sprints_update[0]["hibrida"] is True
