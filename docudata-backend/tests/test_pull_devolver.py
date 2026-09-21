from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(
    task,
    operacional_da_pessoa=None,
    wip_config=None,
    update_rowcount=1,
    task_travamentos=None,
    pontuacao_eventos_capture=None,
):
    task_travamentos = task_travamentos or []
    pontuacao_eventos_capture = (
        pontuacao_eventos_capture if pontuacao_eventos_capture is not None else []
    )
    client = MagicMock()
    # Tracks calls to `.is_(...)` on the atomic update's query chain — used
    # to assert the code guards the pull with `IS NULL` (via `.is_`), not
    # `.eq("operacional_id", None)` (which serializes to the literal string
    # "None" against postgrest and breaks the `uuid` column comparison).
    is_mock = MagicMock(name="tasks_update_is_")

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [task] if task else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()

                def eq_effect(*a, **kw):
                    return q

                def execute_effect():
                    resp = MagicMock()
                    if update_rowcount == 0:
                        resp.data = []
                    else:
                        resp.data = [dict(task, **payload)]
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                is_mock.return_value = q
                q.is_ = is_mock
                q.execute = MagicMock(side_effect=execute_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [operacional_da_pessoa] if operacional_da_pessoa else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"wip_config": wip_config or {}}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "task_travamentos":
            # Mirrors pontos_travamento_ativo's chain:
            # .select("pontos").eq("task_id", ...).eq("dispensado", False).execute()
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = task_travamentos
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_eventos":
            def insert_side_effect(payload):
                pontuacao_eventos_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="evt-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    client._tasks_update_is_ = is_mock
    client._pontuacao_eventos_capture = pontuacao_eventos_capture
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(
        task,
        operacional_da_pessoa,
        cargo="operacional",
        wip_config=None,
        update_rowcount=1,
        task_travamentos=None,
        pontuacao_eventos_capture=None,
    ):
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(
            task,
            operacional_da_pessoa,
            wip_config,
            update_rowcount,
            task_travamentos=task_travamentos,
            pontuacao_eventos_capture=pontuacao_eventos_capture,
        )
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        # A fixture `autenticar` (tests/conftest.py) sempre autentica como
        # "pessoa@citi.org.br", sem parâmetro de e-mail — por isso o
        # `operacional_da_pessoa` de cada teste usa esse mesmo e-mail (é
        # como o mock resolve "qual operacional é o usuário logado").
        tc = autenticar(TestClient(app), cargo=cargo)
        tc._mock_sb = mock_sb
        return tc
    return _make


def test_puxar_task_disponivel_atribui_a_quem_puxou(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 200
    assert resp.json()["operacional_id"] == "op-a"


def test_puxar_task_ja_puxada_da_409(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"}, update_rowcount=0)

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 409
    # A guarda atômica precisa usar IS NULL (via `.is_`), não `.eq("operacional_id", None)`
    # — este último serializa para a string literal "None" no postgrest e quebra a
    # comparação contra a coluna `uuid`, falhando em produção mesmo no caso sem disputa.
    tc._mock_sb._tasks_update_is_.assert_called_once_with("operacional_id", "null")


def test_puxar_task_rascunho_da_403(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": True, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 403


def test_devolver_task_limpa_responsavel_e_volta_pra_fila(make_client):
    task = {
        "id": "t1", "project_id": "proj-1", "operacional_id": "op-a", "rascunho": False,
        "coluna_kanban": "em_andamento", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
        "travado_automatico": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00",
    }
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/devolver")

    assert resp.status_code == 200
    body = resp.json()
    assert body["operacional_id"] is None
    assert body["coluna_kanban"] == "planejado"


def test_devolver_task_de_outra_pessoa_da_403_para_operacional(make_client):
    task = {
        "id": "t1", "project_id": "proj-1", "operacional_id": "op-b", "rascunho": False,
        "coluna_kanban": "em_andamento", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
        "travado_automatico": False,
    }
    # operacional_da_pessoa resolve pra "op-a" (via e-mail pessoa@citi.org.br),
    # mas a task pertence a "op-b" — RBAC deve barrar.
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/devolver")

    assert resp.status_code == 403


def test_devolver_task_travada_registra_penalidade_no_extrato(make_client):
    """Fix review Task 15 — ramo até então não exercitado: task
    travado_automatico=True, com travamentos ativos somando pontos > 0,
    deve gerar exatamente um evento pontuacao_eventos com tipo
    devolucao_penalidade e pontos negativos (= -soma)."""
    task = {
        "id": "t1", "project_id": "proj-1", "operacional_id": "op-a", "rascunho": False,
        "coluna_kanban": "em_andamento", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
        "travado_automatico": True, "sprint_id": "sprint-1", "ordem": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    tc = make_client(
        task,
        operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"},
        task_travamentos=[
            {"pontos": 2, "dispensado": False},
            {"pontos": 3, "dispensado": False},
        ],
    )

    resp = tc.post("/tasks/t1/devolver")

    assert resp.status_code == 200
    capture = tc._mock_sb._pontuacao_eventos_capture
    assert len(capture) == 1
    evento = capture[0]
    assert evento["tipo"] == "devolucao_penalidade"
    assert evento["pontos"] == -5


def test_devolver_task_travada_sem_pontos_ativos_nao_gera_evento(make_client):
    """Fix review Task 15 — task travado_automatico=True mas sem
    travamentos ativos (soma 0) não deve inserir nenhum evento de
    penalidade — o caso 'travada mas nada ativo' precisa pular o insert."""
    task = {
        "id": "t1", "project_id": "proj-1", "operacional_id": "op-a", "rascunho": False,
        "coluna_kanban": "em_andamento", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
        "travado_automatico": True, "sprint_id": "sprint-1", "ordem": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    tc = make_client(
        task,
        operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"},
        task_travamentos=[],
    )

    resp = tc.post("/tasks/t1/devolver")

    assert resp.status_code == 200
    assert tc._mock_sb._pontuacao_eventos_capture == []


def test_devolver_task_por_gerente_de_task_de_outra_pessoa_permite(make_client):
    """Fix review Task 15 — a cláusula 'OR gerente/líder/owner' do RBAC
    nunca tinha sido exercitada: ambos os testes originais usavam o cargo
    default 'operacional'. Aqui o caller é gerente e a task pertence a
    outro operacional inteiramente — deve ser permitido (200), não 403."""
    task = {
        "id": "t1", "project_id": "proj-1", "operacional_id": "op-b", "rascunho": False,
        "coluna_kanban": "em_andamento", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
        "travado_automatico": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00",
    }
    # operacional_da_pessoa resolveria pra "op-a" (via e-mail
    # pessoa@citi.org.br), mas o cargo "gerente" dispensa essa checagem —
    # não deveria nem precisar bater com o "dono" da task.
    tc = make_client(
        task,
        operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"},
        cargo="gerente",
    )

    resp = tc.post("/tasks/t1/devolver")

    assert resp.status_code == 200
    body = resp.json()
    assert body["operacional_id"] is None
    assert body["coluna_kanban"] == "planejado"
