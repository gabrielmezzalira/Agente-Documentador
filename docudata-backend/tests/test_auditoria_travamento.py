from datetime import datetime, timedelta, timezone

from services.sprints import iniciar_sprint_e_ancorar_tasks
from tests.fake_supabase import FakeClient


def _fake(modo):
    return FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False}],
        "projects": [{"id": "p1", "modo_trabalho": modo, "modo_avaliacao": "PONTOS_ATRIBUIDOS"}],
        "tasks": [
            {"id": "fila", "sprint_id": "s1", "coluna_kanban": "planejado", "operacional_id": None,
             "entrou_em_andamento_em": None, "extra": False},
            {"id": "dono", "sprint_id": "s1", "coluna_kanban": "planejado", "operacional_id": "op-1",
             "entrou_em_andamento_em": None, "extra": False},
        ],
    })


def _anc(fake, task_id):
    return next(t for t in fake.tables["tasks"] if t["id"] == task_id)["entrou_em_andamento_em"]


def test_iniciar_sprint_em_pull_nao_ancora_task_da_fila():
    fake = _fake("PULL")
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    assert _anc(fake, "fila") is None
    assert _anc(fake, "dono") is not None


def test_iniciar_sprint_em_atribuicao_continua_ancorando_tudo():
    fake = _fake("ATRIBUICAO")
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    assert _anc(fake, "fila") is not None


def test_job_ignora_task_sem_dono(monkeypatch):
    import services.travamento_checker as job
    velho = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    fake = FakeClient({"tasks": [
        {"id": "fila", "pontos": 1, "operacional_id": None, "coluna_kanban": "planejado",
         "entrou_em_andamento_em": velho, "travado_automatico": False},
        {"id": "dono", "pontos": 1, "operacional_id": "op-1", "coluna_kanban": "em_andamento",
         "entrou_em_andamento_em": velho, "travado_automatico": False},
    ]})
    monkeypatch.setattr(job, "get_client", lambda: fake)
    job.check_travamento_automatico()
    marcadas = {t["id"]: t["travado_automatico"] for t in fake.tables["tasks"]}
    assert marcadas == {"fila": False, "dono": True}
    assert [r["task_id"] for r in fake.tables["task_travamentos"]] == ["dono"]
