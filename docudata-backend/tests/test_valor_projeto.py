"""Testes para projects.valor_projeto / valor_por_ponto (criação e edição via contrato, com trava)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(project_exists=True, sprints_com_orcamento=None, insert_ok=True):
    client = MagicMock()
    calls = {"insert": [], "update": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "proj-1"}] if project_exists else []
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                calls["insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="new-proj-id", is_delivered=False, created_at="2026-09-06T00:00:00+00:00")] if insert_ok else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                calls["update"].append(payload)
                q = MagicMock()

                def eq_side_effect(field, value):
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(payload, id=value, name="X", client="Y", is_delivered=False, created_at="2026-09-06T00:00:00+00:00")]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.not_ = MagicMock()
                q.not_.is_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(sprints_com_orcamento) if sprints_com_orcamento is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_create_project_com_valor_projeto_calcula_valor_por_ponto(monkeypatch):
    mock_sb, calls = _make_mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/projects", json={"name": "Proj X", "client": "Cliente Y", "valor_projeto": 35000})

    assert resp.status_code == 201
    assert calls["insert"][0]["valor_projeto"] == 35000
    assert calls["insert"][0]["valor_por_ponto"] == 350.0


def test_update_contrato_com_valor_projeto_quando_nenhuma_sprint_tem_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(sprints_com_orcamento=[])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"valor_projeto": 10000})

    assert resp.status_code == 200
    assert calls["update"][0]["valor_projeto"] == 10000
    assert calls["update"][0]["valor_por_ponto"] == 100.0


def test_update_contrato_bloqueia_valor_projeto_se_ja_ha_sprint_com_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(sprints_com_orcamento=[{"id": "sprint-1", "pontos_orcamento": 20}])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"valor_projeto": 10000})

    assert resp.status_code == 409
    assert calls["update"] == []


def test_update_contrato_outros_campos_funcionam_mesmo_com_valor_travado(monkeypatch):
    mock_sb, calls = _make_mock_client(sprints_com_orcamento=[{"id": "sprint-1", "pontos_orcamento": 20}])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"arquetipo": "consultoria_discovery"})

    assert resp.status_code == 200
    assert calls["update"][0] == {"arquetipo": "consultoria_discovery"}
