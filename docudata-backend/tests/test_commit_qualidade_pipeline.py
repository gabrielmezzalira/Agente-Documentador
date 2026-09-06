"""Testes para o pipeline de qualidade de commit via IA (Phase 19).

Estende POST /ingest/commit (Phase 4) — não cria gatilho novo. Só roda pra
arquetipo=padrao (consultoria/discovery não tem commit). Best-effort: falha
na avaliação de qualidade nunca derruba a ingestão de conhecimento já
existente.
"""
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from models.schemas import ConteudoEstruturado, AvaliacaoQualidadeCommit


def _mock_client(arquetipo="padrao", operacionais=None, commit_qualidade_insert=None):
    operacionais = operacionais if operacionais is not None else []
    commit_qualidade_insert = commit_qualidade_insert if commit_qualidade_insert is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"gemini_api_key": "fake-key", "arquetipo": arquetipo}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "sprint-1"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "ingestions":
            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="ingestion-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                filtros: dict = {}

                def eq_side_effect(field, value):
                    filtros[field] = value
                    return q

                q.eq = MagicMock(side_effect=eq_side_effect)

                def execute_side_effect():
                    resp = MagicMock()
                    if "github_login" in filtros:
                        resp.data = [o for o in operacionais if o.get("github_login") == filtros["github_login"]]
                    elif "email" in filtros:
                        resp.data = [o for o in operacionais if o.get("email") == filtros["email"]]
                    else:
                        resp.data = operacionais
                    return resp

                q.execute = MagicMock(side_effect=execute_side_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "commit_qualidade":
            def insert_side_effect(payload):
                commit_qualidade_insert.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="cq-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_PAYLOAD = {
    "project_id": "proj-1", "sprint_number": 1, "commit_hash": "abc1234",
    "commit_message": "fix: corrige bug [task:11111111-1111-1111-1111-111111111111]",
    "author": "Ana Silva", "author_email": "ana@citi.com", "date": "2026-01-01T00:00:00Z",
}


def _client(monkeypatch, mock_supabase):
    import routers.commit_ingest as commit_router
    monkeypatch.setattr(commit_router, "get_client", lambda: mock_supabase)
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def _mock_gemini(monkeypatch, conteudo: ConteudoEstruturado, avaliacao: AvaliacaoQualidadeCommit):
    import routers.commit_ingest as commit_router

    class _FakeStructuredExtracao:
        async def ainvoke(self, messages):
            fake_msg = MagicMock()
            fake_msg.usage_metadata = {"input_tokens": 10, "output_tokens": 10}
            return {"parsed": conteudo, "raw": fake_msg}

    class _FakeStructuredQualidade:
        async def ainvoke(self, messages):
            return avaliacao

    class _FakeLLM:
        def with_structured_output(self, schema, **kwargs):
            if schema is ConteudoEstruturado:
                return _FakeStructuredExtracao()
            return _FakeStructuredQualidade()

    monkeypatch.setattr(commit_router, "ChatGoogleGenerativeAI", lambda **kwargs: _FakeLLM())


_CONTEUDO = ConteudoEstruturado(
    resumo="r", tarefas=[], decisoes=[], problemas=[], contexto_cliente="", proximos_passos=[], tecnologias=[],
)


def test_padrao_com_email_bate_grava_commit_qualidade(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(
        arquetipo="padrao",
        operacionais=[{"id": "op-1", "email": "ana@citi.com"}],
        commit_qualidade_insert=insert_capture,
    )
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=8, evidencia="Boa cobertura de testes"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert len(insert_capture) == 1
    assert insert_capture[0]["operacional_id"] == "op-1"
    assert insert_capture[0]["nota"] == 8
    assert insert_capture[0]["task_id"] == "11111111-1111-1111-1111-111111111111"
    assert insert_capture[0]["projeto_id"] == "proj-1"


def test_consultoria_discovery_nao_avalia_qualidade(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(arquetipo="consultoria_discovery", commit_qualidade_insert=insert_capture)
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=8, evidencia="x"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert insert_capture == []


def test_github_login_tem_prioridade_sobre_email(monkeypatch):
    insert_capture = []
    payload = dict(_PAYLOAD, author_github_login="anasilva-gh")
    mock_sb = _mock_client(
        arquetipo="padrao",
        operacionais=[
            {"id": "op-por-email", "email": "ana@citi.com"},
            {"id": "op-por-github", "github_login": "anasilva-gh"},
        ],
        commit_qualidade_insert=insert_capture,
    )
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=8, evidencia="x"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=payload)

    assert resp.status_code == 201
    assert insert_capture[0]["operacional_id"] == "op-por-github"


def test_sem_github_login_cai_pro_email(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(
        arquetipo="padrao",
        operacionais=[{"id": "op-1", "email": "ana@citi.com"}],
        commit_qualidade_insert=insert_capture,
    )
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=8, evidencia="x"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert insert_capture[0]["operacional_id"] == "op-1"


def test_sem_email_correspondente_grava_operacional_id_none(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(arquetipo="padrao", operacionais=[], commit_qualidade_insert=insert_capture)
    _mock_gemini(monkeypatch, _CONTEUDO, AvaliacaoQualidadeCommit(nota=5, evidencia="x"))
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert insert_capture[0]["operacional_id"] is None


def test_falha_na_avaliacao_de_qualidade_nao_derruba_ingestao(monkeypatch):
    insert_capture = []
    mock_sb = _mock_client(arquetipo="padrao", operacionais=[{"id": "op-1"}], commit_qualidade_insert=insert_capture)

    import routers.commit_ingest as commit_router

    class _FakeStructuredExtracao:
        async def ainvoke(self, messages):
            fake_msg = MagicMock()
            fake_msg.usage_metadata = {"input_tokens": 10, "output_tokens": 10}
            return {"parsed": _CONTEUDO, "raw": fake_msg}

    class _FakeStructuredQualidadeQuebrado:
        async def ainvoke(self, messages):
            raise RuntimeError("Gemini indisponível")

    class _FakeLLM:
        def with_structured_output(self, schema, **kwargs):
            if schema is ConteudoEstruturado:
                return _FakeStructuredExtracao()
            return _FakeStructuredQualidadeQuebrado()

    monkeypatch.setattr(commit_router, "ChatGoogleGenerativeAI", lambda **kwargs: _FakeLLM())
    tc = _client(monkeypatch, mock_sb)

    resp = tc.post("/ingest/commit", json=_PAYLOAD)

    assert resp.status_code == 201
    assert insert_capture == []
