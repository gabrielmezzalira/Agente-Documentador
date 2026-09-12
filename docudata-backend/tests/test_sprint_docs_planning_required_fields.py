"""Testes de obrigatoriedade de campos em POST /sprint-docs/planning."""
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient


def _make_mock_client(project_data=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(project_data)] if project_data else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "sprint-1"}]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "ingestions":
            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="ingestion-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "generated_docs":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "doc-1", "content": "# Planning gerado", "created_at": "2026-09-12T00:00:00+00:00"}]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase, generation_result=None):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.sprint_docs as sprint_docs_router
    monkeypatch.setattr(sprint_docs_router, "get_client", lambda: mock_supabase)
    monkeypatch.setattr(sprint_docs_router, "get_gemini_api_key", lambda: "fake-key")
    monkeypatch.setattr(
        sprint_docs_router.generation_graph,
        "ainvoke",
        AsyncMock(return_value=generation_result or {"erro_contexto": None}),
    )
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


_PROJECT = {"id": "proj-1", "name": "Projeto X", "client": "Cliente Y", "gemini_api_key": "fake-key"}

_CAMPOS_BASE = {
    "projeto_id": "proj-1",
    "sprint_numero": "3",
    "descricao": "Planejamento da sprint 3",
    "itens_backlog": '[{"item": "Implementar login"}]',
    "squad": "Ana, Bruno",
    "periodo_inicio": "2026-09-01",
    "periodo_fim": "2026-09-14",
    "horas_disponiveis": "80",
    "horas_estimadas": "70",
    "contexto_livre": "Foco em fechar o módulo de autenticação.",
    "sem_dependencias": "true",
    "sem_riscos": "true",
    "sem_carry_over": "true",
}


def test_bloqueia_quando_campo_descritivo_obrigatorio_falta(monkeypatch):
    mock_sb = _make_mock_client(project_data=_PROJECT)
    tc = _patch_and_client(monkeypatch, mock_sb)

    campos = dict(_CAMPOS_BASE)
    del campos["squad"]

    resp = tc.post("/sprint-docs/planning", data=campos)

    assert resp.status_code == 422


def test_bloqueia_quando_backlog_vazio(monkeypatch):
    mock_sb = _make_mock_client(project_data=_PROJECT)
    tc = _patch_and_client(monkeypatch, mock_sb)

    campos = dict(_CAMPOS_BASE)
    campos["itens_backlog"] = "[]"

    resp = tc.post("/sprint-docs/planning", data=campos)

    assert resp.status_code == 422
    assert "backlog" in resp.json()["detail"].lower()


def test_bloqueia_riscos_vazio_sem_confirmar_ausencia(monkeypatch):
    mock_sb = _make_mock_client(project_data=_PROJECT)
    tc = _patch_and_client(monkeypatch, mock_sb)

    campos = dict(_CAMPOS_BASE)
    campos["riscos_items"] = "[]"
    campos["sem_riscos"] = "false"

    resp = tc.post("/sprint-docs/planning", data=campos)

    assert resp.status_code == 422
    assert "risco" in resp.json()["detail"].lower()


def test_permite_riscos_vazio_quando_confirmado(monkeypatch):
    mock_sb = _make_mock_client(project_data=_PROJECT)
    tc = _patch_and_client(monkeypatch, mock_sb)

    campos = dict(_CAMPOS_BASE)
    campos["riscos_items"] = "[]"
    campos["sem_riscos"] = "true"

    resp = tc.post("/sprint-docs/planning", data=campos)

    assert resp.status_code == 201


def test_permite_riscos_preenchido_mesmo_sem_confirmar_ausencia(monkeypatch):
    mock_sb = _make_mock_client(project_data=_PROJECT)
    tc = _patch_and_client(monkeypatch, mock_sb)

    campos = dict(_CAMPOS_BASE)
    campos["riscos_items"] = '[{"risco": "Atraso de terceiros"}]'
    campos["sem_riscos"] = "false"

    resp = tc.post("/sprint-docs/planning", data=campos)

    assert resp.status_code == 201
