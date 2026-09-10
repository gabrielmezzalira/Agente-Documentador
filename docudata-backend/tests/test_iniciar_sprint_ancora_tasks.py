"""ALERT-04: iniciar uma sprint (botão "Iniciar próxima sprint", ou
implicitamente ao confirmar a Avaliação Semanal da sprint anterior) ancora o
relógio de travamento automático das tasks que já estavam planejadas nela e
ainda não tinham relógio rodando."""
from unittest.mock import MagicMock

from services.auth import criar_jwt
from services.sprints import iniciar_sprint_e_ancorar_tasks


# ── services.sprints.iniciar_sprint_e_ancorar_tasks (unitário) ────────────

def _make_mock_client(tasks_pendentes):
    client = MagicMock()
    calls = {"sprint_update": [], "tasks_update": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def update_side_effect(payload):
                calls["sprint_update"].append(payload)
                q = MagicMock()
                exec_q = MagicMock()
                exec_q.execute = MagicMock(return_value=MagicMock(data=[dict(payload, id="sprint-1")]))
                q.eq = MagicMock(return_value=exec_q)
                return q

            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.neq = MagicMock(return_value=q)
                q.is_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks_pendentes
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()

                def eq_then_execute(field, value):
                    calls["tasks_update"].append({"id": value, "payload": payload})
                    exec_q = MagicMock()
                    exec_q.execute = MagicMock(return_value=MagicMock(data=[dict(payload, id=value)]))
                    return exec_q

                q.eq = MagicMock(side_effect=eq_then_execute)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def test_iniciar_sprint_marca_iniciada_e_ancora_tasks_pendentes():
    client, calls = _make_mock_client(tasks_pendentes=[{"id": "task-1"}, {"id": "task-2"}])

    iniciar_sprint_e_ancorar_tasks(client, "sprint-1")

    assert calls["sprint_update"][0]["iniciada"] is True
    ids_ancoradas = {u["id"] for u in calls["tasks_update"]}
    assert ids_ancoradas == {"task-1", "task-2"}
    for u in calls["tasks_update"]:
        assert u["payload"]["entrou_em_andamento_em"] is not None


def test_iniciar_sprint_sem_tasks_pendentes_nao_toca_tasks():
    client, calls = _make_mock_client(tasks_pendentes=[])

    iniciar_sprint_e_ancorar_tasks(client, "sprint-1")

    assert calls["sprint_update"][0]["iniciada"] is True
    assert calls["tasks_update"] == []


# ── PATCH /sprints/{id}/iniciar (endpoint) ─────────────────────────────────

def _endpoint_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.sprints as sprints_router
    monkeypatch.setattr(sprints_router, "get_client", lambda: mock_supabase)
    from fastapi.testclient import TestClient
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente"))
    return tc


def test_endpoint_iniciar_sprint_chama_helper_e_retorna_sprint_atualizada(monkeypatch):
    check_resp = MagicMock()
    check_resp.data = [{"id": "sprint-1"}]

    final_resp = MagicMock()
    final_resp.data = [{
        "id": "sprint-1", "numero": 2, "iniciada": True, "project_id": "proj-1",
        "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
    }]

    client = MagicMock()
    calls = {"ancorou": []}
    calls_count = {"n": 0}

    import services.sprints as sprints_service
    monkeypatch.setattr(sprints_service, "iniciar_sprint_e_ancorar_tasks", lambda c, sid: calls["ancorou"].append(sid))
    import routers.sprints as sprints_router
    monkeypatch.setattr(sprints_router, "iniciar_sprint_e_ancorar_tasks", lambda c, sid: calls["ancorou"].append(sid))

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)

                def execute_side_effect():
                    calls_count["n"] += 1
                    return check_resp if calls_count["n"] == 1 else final_resp

                q.execute = MagicMock(side_effect=execute_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    tc = _endpoint_client(monkeypatch, client)

    resp = tc.patch("/sprints/sprint-1/iniciar")

    assert resp.status_code == 200
    assert calls["ancorou"] == ["sprint-1"]
    assert resp.json()["iniciada"] is True


def test_endpoint_iniciar_sprint_inexistente_retorna_404(monkeypatch):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.execute = MagicMock(return_value=MagicMock(data=[]))
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    tc = _endpoint_client(monkeypatch, client)

    resp = tc.patch("/sprints/sprint-x/iniciar")

    assert resp.status_code == 404


# ── Avaliação Semanal confirmada inicia a próxima sprint implicitamente ────

def test_confirmar_avaliacao_semanal_inicia_proxima_sprint_nao_iniciada(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "calcular_e_travar_pontuacao", lambda client, sprint_id: [])

    chamadas = []
    monkeypatch.setattr(
        avaliacoes_router, "iniciar_sprint_e_ancorar_tasks",
        lambda client, sprint_id: chamadas.append(sprint_id),
    )

    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "sprint-2", "iniciada": False}]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                exec_q = MagicMock()
                exec_q.execute = MagicMock(return_value=MagicMock(
                    data=[dict(payload, id="sprint-1", project_id="proj-1", numero=1)]
                ))
                q.eq = MagicMock(return_value=exec_q)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: client)
    monkeypatch.setattr(avaliacoes_router, "listar_pendencias", _fake_listar_pendencias_vazia)

    from fastapi.testclient import TestClient
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente"))

    resp = tc.post("/avaliacoes/sprint-1/confirmar")

    assert resp.status_code == 200
    assert chamadas == ["sprint-2"]


def test_confirmar_avaliacao_semanal_nao_reinicia_proxima_sprint_ja_iniciada(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "calcular_e_travar_pontuacao", lambda client, sprint_id: [])

    chamadas = []
    monkeypatch.setattr(
        avaliacoes_router, "iniciar_sprint_e_ancorar_tasks",
        lambda client, sprint_id: chamadas.append(sprint_id),
    )

    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "sprint-2", "iniciada": True}]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                exec_q = MagicMock()
                exec_q.execute = MagicMock(return_value=MagicMock(
                    data=[dict(payload, id="sprint-1", project_id="proj-1", numero=1)]
                ))
                q.eq = MagicMock(return_value=exec_q)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: client)
    monkeypatch.setattr(avaliacoes_router, "listar_pendencias", _fake_listar_pendencias_vazia)

    from fastapi.testclient import TestClient
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente"))

    resp = tc.post("/avaliacoes/sprint-1/confirmar")

    assert resp.status_code == 200
    assert chamadas == []


async def _fake_listar_pendencias_vazia(sprint_id):
    return []
