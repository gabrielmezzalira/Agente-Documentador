"""Testes para GET /performance real (Phase 19, PERF-06).

RBAC: restrito a cargo=lider (já coberto por test_performance_stub.py pro
comportamento anterior — este arquivo cobre o corpo real da resposta).
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(pesos=None, operacionais=None, pontuacao=None, projetos=None):
    pesos = pesos if pesos is not None else [
        {"arquetipo": "padrao", "peso_gerente": 0.35, "peso_entrega": 0.20, "peso_qualidade": 0.20,
         "peso_autonomia": 0.15, "peso_evolucao": 0.10, "peso_commit_qualidade": 0.50},
        {"arquetipo": "consultoria_discovery", "peso_gerente": 0.35, "peso_entrega": 0.20, "peso_qualidade": 0.20,
         "peso_autonomia": 0.15, "peso_evolucao": 0.10, "peso_commit_qualidade": 0.50},
    ]
    operacionais = operacionais or []
    pontuacao = pontuacao or []
    projetos = projetos or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pesos_arquetipo":
            q = MagicMock()
            resp = MagicMock()
            resp.data = pesos
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_operacional_sprint":
            # Diferente do mock do Task 6 (onde só há um operacional nos dados
            # de teste, então "não filtrar" não vaza nada) — aqui há duas
            # pessoas (op-1 e op-2) na MESMA lista `pontuacao`, então o mock
            # PRECISA filtrar de verdade por `.in_(...)`, senão o ranking da
            # Ana vazaria as linhas da Bia (e vice-versa).
            def select_side_effect(cols):
                q = MagicMock()
                state = {"ids": None}

                def in_side_effect(field, values):
                    state["ids"] = set(values)
                    return q

                def execute_side_effect():
                    resp = MagicMock()
                    if state["ids"] is None:
                        resp.data = pontuacao
                    else:
                        resp.data = [p for p in pontuacao if p["operacional_id"] in state["ids"]]
                    return resp

                q.in_ = MagicMock(side_effect=in_side_effect)
                q.gt = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.execute = MagicMock(side_effect=execute_side_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = projetos
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _client_as(monkeypatch, mock_supabase, cargo):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.performance as performance_router
    monkeypatch.setattr(performance_router, "get_client", lambda: mock_supabase)
    # registrar_auditoria usa services.audit.get_client (referência separada) —
    # sem isolar aqui, o teste de sucesso bateria no Supabase real configurado
    # no .env via main.py:load_dotenv(). Mesmo isolamento que
    # test_performance_stub.py já faz pro teste de audit log.
    import services.audit as audit_service
    monkeypatch.setattr(audit_service, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", cargo))
    return tc


_LINHA = {
    "operacional_id": "op-1", "sprint_id": "sprint-1", "projeto_id": "proj-1",
    "sprint_fim": "2026-09-05T00:00:00+00:00", "gerente_media": 5.0, "gerente_pergunta6": 5,
    "entrega_pontos_concluidos": 10, "entrega_pontos_alocados": 10,
    "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 2,
    "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
    "qualidade_commit_media": None,
}


def test_ranking_ordenado_por_score_desc(monkeypatch):
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
            {"id": "op-2", "nome": "Bia", "email": "bia@citi.com", "ativo": True},
        ],
        pontuacao=[
            dict(_LINHA, operacional_id="op-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
            dict(_LINHA, operacional_id="op-2", entrega_pontos_concluidos=2, entrega_pontos_alocados=10),
        ],
        projetos=[{"id": "proj-1", "arquetipo": "padrao"}],
    )
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/performance")

    assert resp.status_code == 200
    body = resp.json()
    assert [p["nome"] for p in body["sprint"]] == ["Ana", "Bia"]


def test_gerente_recebe_403(monkeypatch):
    client = _mock_client()
    tc = _client_as(monkeypatch, client, "gerente")

    resp = tc.get("/performance")

    assert resp.status_code == 403


def test_operacional_recebe_403(monkeypatch):
    client = _mock_client()
    tc = _client_as(monkeypatch, client, "operacional")

    resp = tc.get("/performance")

    assert resp.status_code == 403
