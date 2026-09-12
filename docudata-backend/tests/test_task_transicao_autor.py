"""Testes para o registro de autor em POST /tasks/{id}/mover.

O backend já suportava `autor` em qualquer mudança de coluna_kanban (via
TaskUpdate.autor -> _registrar_task_transicao), mas isso nunca tinha teste —
o gap real estava no frontend, que não mandava o nome da pessoa logada nas
transições comuns de drag-and-drop (só no override de travamento). Este
arquivo fecha a lacuna de cobertura para as transições planejado->em_andamento
e em_andamento->concluida, que são exatamente as que o gerente quer poder
auditar (quem moveu, e quando)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data):
    client = MagicMock()
    task_select_resp = MagicMock()
    task_select_resp.data = [dict(task_data)]

    calls = {"task_transicoes_insert": []}

    def table_side_effect(table_name):
        tbl = MagicMock()

        if table_name == "tasks":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.execute = MagicMock(return_value=task_select_resp)
                return query

            def update_side_effect(updates):
                q = MagicMock()

                def eq_then_execute(field, value):
                    exec_q = MagicMock()
                    merged = dict(task_data, **updates)
                    resp = MagicMock()
                    resp.data = [merged]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_then_execute)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)

        elif table_name == "task_transicoes":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                query.order = MagicMock(return_value=query)
                query.limit = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            def insert_side_effect(payload):
                calls["task_transicoes_insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif table_name == "projects":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"id": "proj-1", "wip_config": {}}]
                query.execute = MagicMock(return_value=resp)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)

        elif table_name == "sprints":
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                resp = MagicMock()
                resp.data = [{"id": "sprint-1", "iniciada": True, "pontos_orcamento": None, "numero": 1}]
                query.execute = MagicMock(return_value=resp)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)

        else:
            def select_side_effect(cols):
                query = MagicMock()
                query.eq = MagicMock(return_value=query)
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
                return query

            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-test-1", "test@citi.com", "gerente"))
    return tc


_BASE_TASK = {
    "id": "task-1",
    "project_id": "proj-1",
    "titulo": "Fazer algo",
    "pontos": 2,
    "coluna_kanban": "planejado",
    "ordem": 0,
    "sprint_id": "sprint-1",
    "operacional_id": None,
    "descricao": None,
    "bloqueado": False,
    "motivo_bloqueio": None,
    "checklist": [],
    "contador_reaberturas": 0,
    "bloqueado_manual": False,
    "bloqueado_em": None,
    "bloqueado_por": None,
    "bloqueado_resolvido_por": None,
    "bloqueado_resolvido_em": None,
    "entrou_em_andamento_em": None,
    "travado_automatico": False,
    "travado_override": False,
    "travado_override_por": None,
    "travado_override_em": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


def test_mover_planejado_para_em_andamento_grava_autor_na_transicao(monkeypatch):
    mock_sb, calls = _make_mock_client(_BASE_TASK)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post(
        "/tasks/task-1/mover",
        params={"coluna_destino": "em_andamento", "autor": "Ana Souza"},
    )

    assert resp.status_code == 200
    insercoes = [i for i in calls["task_transicoes_insert"] if i["campo"] == "coluna_kanban"]
    assert len(insercoes) == 1
    assert insercoes[0]["autor"] == "Ana Souza"
    assert insercoes[0]["de"] == "planejado"
    assert insercoes[0]["para"] == "em_andamento"


def test_mover_em_andamento_para_concluida_grava_autor_na_transicao(monkeypatch):
    task = dict(_BASE_TASK, coluna_kanban="em_andamento", entrou_em_andamento_em="2026-01-01T00:00:00+00:00")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post(
        "/tasks/task-1/mover",
        params={"coluna_destino": "concluida", "autor": "Bruno Lima"},
    )

    assert resp.status_code == 200
    insercoes = [i for i in calls["task_transicoes_insert"] if i["campo"] == "coluna_kanban"]
    assert len(insercoes) == 1
    assert insercoes[0]["autor"] == "Bruno Lima"
    assert insercoes[0]["de"] == "em_andamento"
    assert insercoes[0]["para"] == "concluida"


def test_mover_sem_autor_grava_autor_none(monkeypatch):
    """Documenta o comportamento atual (autor opcional) — o frontend agora
    sempre envia, mas o backend não deve exigir isso."""
    mock_sb, calls = _make_mock_client(_BASE_TASK)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks/task-1/mover", params={"coluna_destino": "em_andamento"})

    assert resp.status_code == 200
    insercoes = [i for i in calls["task_transicoes_insert"] if i["campo"] == "coluna_kanban"]
    assert insercoes[0]["autor"] is None
