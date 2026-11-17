from fastapi.testclient import TestClient

from routers.metricas import _cycle_time_segundos
from tests.fake_supabase import FakeClient


def _transicoes(**ts):
    linhas = []
    for para, quando in ts.items():
        linhas.append({"task_id": "t1", "campo": "coluna_kanban", "para": para, "timestamp": quando,
                       "duracao_fase_anterior_segundos": 1})
    return FakeClient({"task_transicoes": linhas})


def test_pull_em_posterior_a_transicao_antiga_e_o_inicio():
    fake = _transicoes(em_andamento="2026-11-01T10:00:00+00:00", concluida="2026-11-03T10:00:00+00:00")
    # puxada de novo depois de devolvida: o tempo na fila não conta
    assert _cycle_time_segundos(fake, "t1", "2026-11-03T00:00:00+00:00") == 10 * 3600


def test_pull_em_anterior_a_transicao_nao_muda_nada():
    fake = _transicoes(em_andamento="2026-11-02T10:00:00+00:00", concluida="2026-11-03T10:00:00+00:00")
    assert _cycle_time_segundos(fake, "t1", "2026-11-01T00:00:00+00:00") == 24 * 3600


def test_sem_pull_em_usa_a_transicao():
    fake = _transicoes(em_andamento="2026-11-02T10:00:00+00:00", concluida="2026-11-03T10:00:00+00:00")
    assert _cycle_time_segundos(fake, "t1", None) == 24 * 3600


def test_cycle_time_de_sprint_inexistente_devolve_lista_vazia(monkeypatch, autenticar):
    import routers.metricas as metricas
    from main import app
    fake = FakeClient({
        "projects": [{"id": "p1"}],
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1}],
        "tasks": [{"id": "t1", "project_id": "p1", "sprint_id": "s1", "coluna_kanban": "concluida",
                   "titulo": "X", "operacional_id": None, "pull_em": None}],
        "operacionais": [],
        "task_transicoes": [
            {"task_id": "t1", "campo": "coluna_kanban", "para": "em_andamento",
             "timestamp": "2026-11-02T10:00:00+00:00", "duracao_fase_anterior_segundos": 1},
            {"task_id": "t1", "campo": "coluna_kanban", "para": "concluida",
             "timestamp": "2026-11-03T10:00:00+00:00", "duracao_fase_anterior_segundos": 1},
        ],
    })
    monkeypatch.setattr(metricas, "get_client", lambda: fake)
    tc = autenticar(TestClient(app))
    ok = tc.get("/metricas/p1/cycle-time", params={"sprint_numero": 1})
    assert ok.status_code == 200 and len(ok.json()) == 1
    resp = tc.get("/metricas/p1/cycle-time", params={"sprint_numero": 99})
    assert resp.status_code == 200
    assert resp.json() == []
