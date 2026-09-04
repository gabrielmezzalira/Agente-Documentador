"""
Testes para os dois novos endpoints de métricas (Phase 13 quick task):

  1. GET /metricas/{project_id}/performance-operacional (MET-01 + MET-06)
  2. GET /metricas/{project_id}/cycle-time/stats (MET-02)

Reusa o padrão de mock `_make_mock_client`/`_patch_and_client` de
tests/test_project_usage.py, adaptado para as tabelas `operacionais`,
`tasks` e `task_transicoes` que estes endpoints consultam.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(
    project_exists=True,
    operacionais_data=None,
    tasks_data=None,
    transicoes_by_task=None,
):
    """
    Cria um mock do cliente Supabase que responde às queries esperadas pelos
    handlers de performance-operacional e cycle-time/stats.

    transicoes_by_task: dict task_id -> list[dict] com
      {"duracao_fase_anterior_segundos": int, "timestamp": str}
      (o handler usa .order(...).limit(1), então basta o primeiro item da lista)
    """
    client = MagicMock()

    proj_resp = MagicMock()
    proj_resp.data = [{"id": "test-project-id"}] if project_exists else []

    operacionais_resp = MagicMock()
    operacionais_resp.data = list(operacionais_data) if operacionais_data is not None else []

    tasks_resp = MagicMock()
    tasks_resp.data = list(tasks_data) if tasks_data is not None else []

    transicoes_by_task = transicoes_by_task or {}

    def table_side_effect(table_name):
        tbl = MagicMock()

        def select_side_effect(cols):
            query = MagicMock()
            query.eq = MagicMock(return_value=query)
            query.order = MagicMock(return_value=query)
            query.limit = MagicMock(return_value=query)

            if table_name == "projects":
                query.execute = MagicMock(return_value=proj_resp)
            elif table_name == "operacionais":
                query.execute = MagicMock(return_value=operacionais_resp)
            elif table_name == "tasks":
                query.execute = MagicMock(return_value=tasks_resp)
            elif table_name == "task_transicoes":
                # captura o task_id pelo primeiro .eq("task_id", <id>) — como todos os
                # métodos de filtro retornam o mesmo `query` mock, registramos o task_id
                # via closure sobre os args de .eq
                captured = {}
                orig_eq = query.eq

                def eq_side_effect(field, value, *a, **kw):
                    if field == "task_id":
                        captured["task_id"] = value
                    return query

                query.eq = MagicMock(side_effect=eq_side_effect)

                def trans_execute():
                    resp = MagicMock()
                    task_id = captured.get("task_id")
                    rows = transicoes_by_task.get(task_id, [])
                    resp.data = rows[:1] if rows else []
                    return resp

                query.execute = MagicMock(side_effect=trans_execute)
            else:
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
            return query

        tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    """Injeta o mock via monkeypatch no módulo routers.metricas, que o router importa diretamente."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.metricas as metricas_router
    monkeypatch.setattr(metricas_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", "test@citi.com", "gerente"))
    return tc


# ─── performance-operacional (MET-01 + MET-06) ────────────────────────────────

def test_performance_operacional_agrega_por_operacional(monkeypatch):
    operacionais = [
        {"id": "op-1", "nome": "Ana"},
        {"id": "op-2", "nome": "Bruno"},
    ]
    tasks = [
        # op-1: 2 concluidas (pontos 2 + 3 = 5 realizados), 1 em_andamento (pontos 1)
        {"operacional_id": "op-1", "pontos": 2, "coluna_kanban": "concluida"},
        {"operacional_id": "op-1", "pontos": 3, "coluna_kanban": "concluida"},
        {"operacional_id": "op-1", "pontos": 1, "coluna_kanban": "em_andamento"},
        # op-2: 1 concluida (pontos 1), 1 planejado (pontos 2) — nada mais concluído
        {"operacional_id": "op-2", "pontos": 1, "coluna_kanban": "concluida"},
        {"operacional_id": "op-2", "pontos": 2, "coluna_kanban": "planejado"},
    ]
    mock_sb = _make_mock_client(operacionais_data=operacionais, tasks_data=tasks)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/test-project-id/performance-operacional")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    by_id = {row["operacional_id"]: row for row in data}

    op1 = by_id["op-1"]
    assert op1["operacional_nome"] == "Ana"
    assert op1["pontos_atribuidos"] == 6  # 2 + 3 + 1
    assert op1["pontos_realizados"] == 5  # 2 + 3
    assert op1["tasks_concluidas"] == 2
    assert op1["spi"] == round(5 / 6, 3)

    op2 = by_id["op-2"]
    assert op2["operacional_nome"] == "Bruno"
    assert op2["pontos_atribuidos"] == 3  # 1 + 2
    assert op2["pontos_realizados"] == 1
    assert op2["tasks_concluidas"] == 1
    assert op2["spi"] == round(1 / 3, 3)


def test_performance_operacional_operacional_sem_tasks_retorna_zeros(monkeypatch):
    operacionais = [{"id": "op-1", "nome": "Ana"}]
    mock_sb = _make_mock_client(operacionais_data=operacionais, tasks_data=[])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/test-project-id/performance-operacional")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["pontos_atribuidos"] == 0
    assert data[0]["pontos_realizados"] == 0
    assert data[0]["tasks_concluidas"] == 0
    assert data[0]["spi"] is None


def test_performance_operacional_project_not_found(monkeypatch):
    mock_sb = _make_mock_client(project_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/does-not-exist/performance-operacional")
    assert resp.status_code == 404


# ─── cycle-time/stats (MET-02) ─────────────────────────────────────────────────

def test_cycle_time_stats_multi_task_p50_p85(monkeypatch):
    tasks = [
        {"id": "t1", "sprint_id": None, "operacional_id": None, "coluna_kanban": "concluida"},
        {"id": "t2", "sprint_id": None, "operacional_id": None, "coluna_kanban": "concluida"},
        {"id": "t3", "sprint_id": None, "operacional_id": None, "coluna_kanban": "concluida"},
        {"id": "t4", "sprint_id": None, "operacional_id": None, "coluna_kanban": "concluida"},
        {"id": "t5", "sprint_id": None, "operacional_id": None, "coluna_kanban": "concluida"},
    ]
    # cycle_time_horas esperados: [10, 20, 30, 40, 50] (segundos = horas * 3600)
    transicoes_by_task = {
        "t1": [{"duracao_fase_anterior_segundos": 10 * 3600, "timestamp": "2026-01-01T00:00:00+00:00"}],
        "t2": [{"duracao_fase_anterior_segundos": 20 * 3600, "timestamp": "2026-01-01T00:00:00+00:00"}],
        "t3": [{"duracao_fase_anterior_segundos": 30 * 3600, "timestamp": "2026-01-01T00:00:00+00:00"}],
        "t4": [{"duracao_fase_anterior_segundos": 40 * 3600, "timestamp": "2026-01-01T00:00:00+00:00"}],
        "t5": [{"duracao_fase_anterior_segundos": 50 * 3600, "timestamp": "2026-01-01T00:00:00+00:00"}],
    }
    mock_sb = _make_mock_client(tasks_data=tasks, transicoes_by_task=transicoes_by_task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/test-project-id/cycle-time/stats")
    assert resp.status_code == 200
    data = resp.json()

    import statistics
    expected_q = statistics.quantiles([10, 20, 30, 40, 50], n=100, method="inclusive")
    expected_p50 = round(expected_q[49], 1)
    expected_p85 = round(expected_q[84], 1)

    assert data["p50_horas"] == expected_p50
    assert data["p85_horas"] == expected_p85


def test_cycle_time_stats_zero_tasks_returns_none(monkeypatch):
    mock_sb = _make_mock_client(tasks_data=[])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/test-project-id/cycle-time/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["p50_horas"] is None
    assert data["p85_horas"] is None


def test_cycle_time_stats_single_task_returns_that_value(monkeypatch):
    tasks = [{"id": "t1", "sprint_id": None, "operacional_id": None, "coluna_kanban": "concluida"}]
    transicoes_by_task = {
        "t1": [{"duracao_fase_anterior_segundos": 15 * 3600, "timestamp": "2026-01-01T00:00:00+00:00"}],
    }
    mock_sb = _make_mock_client(tasks_data=tasks, transicoes_by_task=transicoes_by_task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/test-project-id/cycle-time/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["p50_horas"] == 15.0
    assert data["p85_horas"] == 15.0


def test_cycle_time_stats_existing_cycle_time_endpoint_unchanged(monkeypatch):
    """/cycle-time (sem /stats) continua retornando a lista por-task, não afetada."""
    tasks = [{"id": "t1", "sprint_id": None, "operacional_id": None, "coluna_kanban": "concluida", "titulo": "Task 1"}]
    transicoes_by_task = {
        "t1": [{"duracao_fase_anterior_segundos": 15 * 3600, "timestamp": "2026-01-01T00:00:00+00:00"}],
    }
    mock_sb = _make_mock_client(tasks_data=tasks, transicoes_by_task=transicoes_by_task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/test-project-id/cycle-time")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["cycle_time_horas"] == 15.0
    assert data[0]["task_titulo"] == "Task 1"
