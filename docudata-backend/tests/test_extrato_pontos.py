"""Testes para GET /operacionais/{id}/extrato (extra do usuário: log claro
de todo ponto ganho ou descontado, Gerente/Líder apenas)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _mock_client(eventos=None):
    eventos = eventos or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pontuacao_eventos":
            def select_side_effect(cols):
                q = MagicMock()
                state = {"sprint_id": None}

                def eq_effect(field, value):
                    if field == "sprint_id":
                        state["sprint_id"] = value
                    return q

                def order_effect(*a, **kw):
                    return q

                def execute_effect():
                    resp = MagicMock()
                    data = eventos
                    if state["sprint_id"] is not None:
                        data = [e for e in data if e.get("sprint_id") == state["sprint_id"]]
                    resp.data = data
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                q.order = MagicMock(side_effect=order_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase, autenticar, cargo="gerente"):
    import routers.pontuacao as pontuacao_router
    from main import app
    monkeypatch.setattr(pontuacao_router, "get_client", lambda: mock_supabase)
    return autenticar(TestClient(app), cargo=cargo)


_EVENTOS = [
    {"id": "ev-1", "operacional_id": "op-1", "sprint_id": "sprint-1", "projeto_id": "proj-1",
     "task_id": "task-1", "tipo": "entrega_concluida", "pontos": 5, "descricao": "Task concluída",
     "criado_em": "2026-09-10T00:00:00Z"},
    {"id": "ev-2", "operacional_id": "op-1", "sprint_id": "sprint-2", "projeto_id": "proj-1",
     "task_id": "task-2", "tipo": "travamento_penalidade", "pontos": -3, "descricao": "Travamento não dispensado",
     "criado_em": "2026-09-17T00:00:00Z"},
]


def test_extrato_lista_todos_os_eventos_do_operacional(monkeypatch, autenticar):
    tc = _patch_and_client(monkeypatch, _mock_client(_EVENTOS), autenticar)

    resp = tc.get("/operacionais/op-1/extrato")

    assert resp.status_code == 200
    tipos = {e["tipo"] for e in resp.json()}
    assert tipos == {"entrega_concluida", "travamento_penalidade"}


def test_extrato_filtra_por_sprint(monkeypatch, autenticar):
    tc = _patch_and_client(monkeypatch, _mock_client(_EVENTOS), autenticar)

    resp = tc.get("/operacionais/op-1/extrato?sprint_id=sprint-2")

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["tipo"] == "travamento_penalidade"


def test_extrato_bloqueia_operacional(monkeypatch, autenticar):
    tc = _patch_and_client(monkeypatch, _mock_client(_EVENTOS), autenticar, cargo="operacional")

    resp = tc.get("/operacionais/op-1/extrato")

    assert resp.status_code == 403
