"""
Testes para DELETE /sprints/{sprint_id} (Phase 13 debug fix):

Apagar uma sprint apaga TUDO associado a ela (cascade completo): tasks,
ingestões, documentos gerados e rascunhos de planning. Antes, o endpoint só
bloqueava (409) se houvesse ingestões/docs, sem tocar em tasks — que ficavam
órfãs (sprint_id=NULL) e continuavam alimentando /metricas/{id}/cycle-time e
/performance-operacional (que consultam tasks por project_id, sem passar pela
tabela sprints), gerando dashboard inconsistente após a exclusão. ingestions,
generated_docs e planning_rascunhos não têm FK pra sprints (ligam por
project_id + sprint_number/sprint_numero), então precisam de cascade explícito
no endpoint.

Reusa o padrão de mock de tests/test_metricas_novos_endpoints.py, adaptado
para o router de sprints.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(sprint_data=None):
    client = MagicMock()
    calls = []

    sprint_resp = MagicMock()
    sprint_resp.data = [sprint_data] if sprint_data else []

    empty_resp = MagicMock()
    empty_resp.data = []

    def table_side_effect(table_name):
        tbl = MagicMock()

        def select_side_effect(cols):
            query = MagicMock()
            query.eq = MagicMock(return_value=query)
            query.limit = MagicMock(return_value=query)
            if table_name == "sprints":
                query.execute = MagicMock(return_value=sprint_resp)
            else:
                query.execute = MagicMock(return_value=empty_resp)
            return query

        def delete_side_effect():
            query = MagicMock()

            def eq_side_effect(field, value, *a, **kw):
                calls.append((table_name, field, value))
                return query

            query.eq = MagicMock(side_effect=eq_side_effect)
            query.execute = MagicMock(return_value=empty_resp)
            return query

        tbl.select = MagicMock(side_effect=select_side_effect)
        tbl.delete = MagicMock(side_effect=delete_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.sprints as sprints_router
    monkeypatch.setattr(sprints_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", "test@citi.com", "gerente"))
    return tc


def test_delete_sprint_apaga_tudo_associado(monkeypatch):
    sprint = {"id": "sprint-4", "project_id": "proj-1", "numero": 4}
    mock_sb, calls = _make_mock_client(sprint_data=sprint)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/sprints/sprint-4")
    assert resp.status_code == 204

    assert ("tasks", "sprint_id", "sprint-4") in calls
    assert ("ingestions", "project_id", "proj-1") in calls
    assert ("ingestions", "sprint_number", 4) in calls
    assert ("generated_docs", "project_id", "proj-1") in calls
    assert ("generated_docs", "sprint_number", 4) in calls
    assert ("planning_rascunhos", "project_id", "proj-1") in calls
    assert ("planning_rascunhos", "sprint_numero", 4) in calls
    assert ("sprints", "id", "sprint-4") in calls

    # sprint só é apagada por último, depois de todo o resto
    sprints_delete_idx = calls.index(("sprints", "id", "sprint-4"))
    assert sprints_delete_idx == len(calls) - 1


def test_delete_sprint_not_found(monkeypatch):
    mock_sb, calls = _make_mock_client(sprint_data=None)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/sprints/does-not-exist")
    assert resp.status_code == 404
    assert calls == []
