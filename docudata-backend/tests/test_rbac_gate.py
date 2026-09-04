"""Testes do gate global de enforcement (RBAC-02, RBAC-03) — require_not_operacional
via /metricas/{id}/spi, require_project_access via GET /tasks."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client_projeto_existe():
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        def select_side_effect(cols):
            query = MagicMock()
            query.eq = MagicMock(return_value=query)
            query.order = MagicMock(return_value=query)
            resp = MagicMock()
            resp.data = [{"id": "proj-1"}] if name == "projects" else []
            query.execute = MagicMock(return_value=resp)
            return query

        tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _mock_client_operacional_vinculado(vinculado: bool):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"id": "op-1"}] if vinculado else []
                query.execute = MagicMock(return_value=resp)
                return query
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.order = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = []
                query.execute = MagicMock(return_value=resp)
                return query
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_rota_protegida_sem_cookie_retorna_401(monkeypatch):
    from main import app
    tc = TestClient(app)

    resp = tc.get("/metricas/proj-1/spi")

    assert resp.status_code == 401


def test_operacional_bloqueado_em_rota_require_not_operacional(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    resp = tc.get("/metricas/proj-1/spi", cookies={"docudata_session": token})

    assert resp.status_code == 403


def test_gerente_acessa_rota_require_not_operacional(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb = _mock_client_projeto_existe()
    import routers.metricas as metricas_router
    monkeypatch.setattr(metricas_router, "get_client", lambda: mock_sb)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")

    resp = tc.get("/metricas/proj-1/spi", cookies={"docudata_session": token})

    assert resp.status_code == 200


def test_require_project_access_operacional_sem_vinculo_403(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb = _mock_client_operacional_vinculado(vinculado=False)
    import services.auth as auth_service
    import routers.tasks as tasks_router
    monkeypatch.setattr(auth_service, "get_client", lambda: mock_sb)
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    resp = tc.get("/tasks", params={"project_id": "proj-1"}, cookies={"docudata_session": token})

    assert resp.status_code == 403


def test_require_project_access_operacional_com_vinculo_200(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb = _mock_client_operacional_vinculado(vinculado=True)
    import services.auth as auth_service
    import routers.tasks as tasks_router
    monkeypatch.setattr(auth_service, "get_client", lambda: mock_sb)
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    resp = tc.get("/tasks", params={"project_id": "proj-1"}, cookies={"docudata_session": token})

    assert resp.status_code == 200


def test_require_project_access_gerente_sem_operacionais_bypass_200(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb = _mock_client_operacional_vinculado(vinculado=False)
    import services.auth as auth_service
    import routers.tasks as tasks_router
    monkeypatch.setattr(auth_service, "get_client", lambda: mock_sb)
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")

    resp = tc.get("/tasks", params={"project_id": "proj-1"}, cookies={"docudata_session": token})

    assert resp.status_code == 200
