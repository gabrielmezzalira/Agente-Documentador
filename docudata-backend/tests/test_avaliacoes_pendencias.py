"""Testes para GET /avaliacoes/{sprint_id}/pendencias (AVAL-02, AVAL-04)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(tasks=None, operacionais=None, avaliacoes=None, outras_operacionais=None, projects=None):
    tasks = tasks or []
    operacionais = operacionais or []
    avaliacoes = avaliacoes or []
    outras_operacionais = outras_operacionais or []
    projects = projects or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()

                def in_side_effect(field, values):
                    inner = MagicMock()
                    resp = MagicMock()
                    resp.data = [o for o in operacionais if o["id"] in values]
                    inner.execute = MagicMock(return_value=resp)
                    return inner

                def eq_side_effect(field, value):
                    inner = MagicMock()

                    def neq_side_effect(f2, v2):
                        inner2 = MagicMock()
                        resp = MagicMock()
                        resp.data = [o for o in outras_operacionais if o.get(field) == value and o.get(f2) != v2]
                        inner2.execute = MagicMock(return_value=resp)
                        return inner2

                    inner.neq = MagicMock(side_effect=neq_side_effect)
                    return inner

                q.in_ = MagicMock(side_effect=in_side_effect)
                q.eq = MagicMock(side_effect=eq_side_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()

                def eq_side_effect(field, value):
                    inner = MagicMock()
                    resp = MagicMock()
                    resp.data = [a for a in avaliacoes if a.get(field) == value]
                    inner.execute = MagicMock(return_value=resp)
                    return inner

                def in_side_effect_top(f2, values):
                    chained = MagicMock()
                    r2 = MagicMock()
                    r2.data = sorted(
                        [a for a in avaliacoes if a.get(f2) in values],
                        key=lambda a: a["criado_em"], reverse=True,
                    )
                    chained.order = MagicMock(return_value=chained)
                    chained.limit = MagicMock(return_value=chained)
                    chained.execute = MagicMock(return_value=r2)
                    return chained

                q.eq = MagicMock(side_effect=eq_side_effect)
                q.in_ = MagicMock(side_effect=in_side_effect_top)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "projects":
            def select_side_effect(cols):
                q = MagicMock()

                def eq_side_effect(field, value):
                    inner = MagicMock()
                    resp = MagicMock()
                    resp.data = [p for p in projects if p.get(field) == value]
                    inner.execute = MagicMock(return_value=resp)
                    return inner

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")
    tc.cookies.set("docudata_session", token)
    return tc


_OP_1 = {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "project_id": "proj-1"}
_OP_2 = {"id": "op-2", "nome": "Bruno", "email": None, "project_id": "proj-1"}


def test_lista_operacionais_com_task_sem_avaliacao(monkeypatch):
    mock_sb = _mock_client(
        tasks=[{"operacional_id": "op-1"}, {"operacional_id": "op-2"}],
        operacionais=[_OP_1, _OP_2],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/avaliacoes/sprint-1/pendencias")

    assert resp.status_code == 200
    nomes = {p["nome"] for p in resp.json()}
    assert nomes == {"Ana", "Bruno"}


def test_exclui_quem_ja_tem_avaliacao(monkeypatch):
    mock_sb = _mock_client(
        tasks=[{"operacional_id": "op-1"}, {"operacional_id": "op-2"}],
        operacionais=[_OP_1, _OP_2],
        avaliacoes=[{"operacional_id": "op-1", "sprint_id": "sprint-1"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/avaliacoes/sprint-1/pendencias")

    nomes = {p["nome"] for p in resp.json()}
    assert nomes == {"Bruno"}


def test_inclui_ultima_avaliacao_outro_projeto_quando_existe(monkeypatch):
    outra_op = {"id": "op-1-outro-proj", "project_id": "proj-2", "email": "ana@citi.com"}
    aval_anterior = {
        "id": "aval-1", "operacional_id": "op-1-outro-proj", "sprint_id": "sprint-x",
        "criado_em": "2026-01-01T00:00:00+00:00",
        "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_6": 5, "resposta_7": 5,
    }
    mock_sb = _mock_client(
        tasks=[{"operacional_id": "op-1"}],
        operacionais=[_OP_1],
        outras_operacionais=[outra_op],
        avaliacoes=[aval_anterior],
        projects=[{"id": "proj-2", "name": "Projeto Y"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/avaliacoes/sprint-1/pendencias")

    body = resp.json()
    assert body[0]["ultima_avaliacao_outro_projeto"]["project_name"] == "Projeto Y"
    assert body[0]["ultima_avaliacao_outro_projeto"]["resposta_6"] == 5


def test_sem_email_nao_busca_avaliacao_anterior(monkeypatch):
    mock_sb = _mock_client(tasks=[{"operacional_id": "op-2"}], operacionais=[_OP_2])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/avaliacoes/sprint-1/pendencias")

    assert resp.json()[0]["ultima_avaliacao_outro_projeto"] is None
