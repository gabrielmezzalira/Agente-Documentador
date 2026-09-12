"""Testes para GET /sprint-docs/review/planejado-entregue (prefill da tabela planejado x entregue)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(project_exists=True, sprint_data=None, tasks=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "proj-1", "name": "Projeto X", "client": "Cliente Y"}] if project_exists else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(sprint_data) if sprint_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(tasks) if tasks is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.sprint_docs as sprint_docs_router
    monkeypatch.setattr(sprint_docs_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_devolve_tabela_calculada_a_partir_do_kanban(monkeypatch):
    mock_sb = _make_mock_client(
        sprint_data=[{"id": "sprint-1"}],
        tasks=[
            {"titulo": "Ajustar login", "coluna_kanban": "concluida"},
            {"titulo": "Subir ambiente", "coluna_kanban": "planejado"},
        ],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/sprint-docs/review/planejado-entregue", params={"projeto_id": "proj-1", "sprint_numero": 3})

    assert resp.status_code == 200
    body = resp.json()
    assert body["itens_planejados_entregues"] == [
        {"item": "Ajustar login", "entregue": "S", "motivo_nao": "", "causa_raiz_num": ""},
        {"item": "Subir ambiente", "entregue": "N", "motivo_nao": "", "causa_raiz_num": ""},
    ]


def test_404_quando_projeto_nao_existe(monkeypatch):
    mock_sb = _make_mock_client(project_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/sprint-docs/review/planejado-entregue", params={"projeto_id": "proj-inexistente", "sprint_numero": 1})

    assert resp.status_code == 404
