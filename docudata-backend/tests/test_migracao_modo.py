# tests/test_migracao_modo.py (novo)
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, tasks):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto] if projeto else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto, tasks):
        import routers.projects as projects_router
        from main import app
        mock_sb = _mock_client(projeto, tasks)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc
    return _make


def test_preview_migracao_conta_tasks_por_categoria(make_client):
    tasks = [
        {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [{"texto": "a", "done": False}], "bloqueado": False},
        {"id": "t2", "coluna_kanban": "planejado", "operacional_id": None, "titulo": "Y", "pontos": 2, "descricao": None, "checklist": [], "bloqueado": False},
        {"id": "t3", "coluna_kanban": "em_andamento", "operacional_id": "op-b", "titulo": "Z", "pontos": 5, "descricao": "d", "checklist": [], "bloqueado": False},
        {"id": "t4", "coluna_kanban": "concluida", "operacional_id": "op-a", "titulo": "W", "pontos": 4, "descricao": "d", "checklist": [], "bloqueado": False},
        {"id": "t5", "coluna_kanban": "planejado", "operacional_id": "op-c", "titulo": "V", "pontos": 1, "descricao": "d", "checklist": [], "bloqueado": True},
    ]
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True}, tasks=tasks)

    resp = tc.get("/projects/proj-1/migrar-modo/preview?para=PULL")

    assert resp.status_code == 200
    body = resp.json()
    assert body["entrando_na_fila"] == 1  # t1: planejado com responsável, hidratada
    assert body["vira_rascunho"] == 1  # t2: planejado sem descrição/checklist
    assert body["mantem_responsavel"] == 2  # t3: em_andamento; t5: bloqueada (mantém responsável mesmo planejada)
    assert body["sem_alteracao"] == 1  # t4: concluida


def _mock_client_completo(projeto, tasks):
    """Estende _mock_client com update de tasks/sprints/projects e insert de
    migracoes_modo, capturando os payloads em listas (mesmo padrão das
    Tasks 2 e 11) pra assertar o que a rota de aplicação de fato gravou."""
    tasks_update = []
    migracoes_insert = []
    sprints_update = []
    projects_update = []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto] if projeto else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)

            def _update(payload):
                projects_update.append(payload)
                uq = MagicMock()
                uq.eq = MagicMock(return_value=uq)
                uresp = MagicMock()
                uresp.data = [payload]
                uq.execute = MagicMock(return_value=uresp)
                return uq
            tbl.update = MagicMock(side_effect=_update)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)

            def _update(payload):
                tasks_update.append(payload)
                uq = MagicMock()
                uq.eq = MagicMock(return_value=uq)
                uresp = MagicMock()
                uresp.data = [payload]
                uq.execute = MagicMock(return_value=uresp)
                return uq
            tbl.update = MagicMock(side_effect=_update)
        elif name == "sprints":
            def _update(payload):
                sprints_update.append(payload)
                uq = MagicMock()
                uq.eq = MagicMock(return_value=uq)
                uresp = MagicMock()
                uresp.data = [payload]
                uq.execute = MagicMock(return_value=uresp)
                return uq
            tbl.update = MagicMock(side_effect=_update)
        elif name == "migracoes_modo":
            def _insert(payload):
                migracoes_insert.append(payload)
                iq = MagicMock()
                iresp = MagicMock()
                iresp.data = [payload]
                iq.execute = MagicMock(return_value=iresp)
                return iq
            tbl.insert = MagicMock(side_effect=_insert)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_update, migracoes_insert, sprints_update, projects_update


@pytest.fixture
def make_client_completo(monkeypatch, autenticar):
    def _make(projeto, tasks):
        import routers.projects as projects_router
        from main import app
        mock_sb, tasks_update, migracoes_insert, sprints_update, projects_update = _mock_client_completo(projeto, tasks)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc, tasks_update, migracoes_insert, sprints_update, projects_update
    return _make


def test_aplicar_migracao_para_pull_reclassifica_tasks_e_grava_auditoria(make_client_completo, monkeypatch):
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")
    tc, tasks_update, migracoes_insert, sprints_update, projects_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True},
        tasks=[
            {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [{"texto": "a", "done": False}], "bloqueado": False},
            {"id": "t4", "coluna_kanban": "concluida", "operacional_id": "op-a", "titulo": "W", "pontos": 4, "descricao": "d", "checklist": [], "bloqueado": False},
            {"id": "t5", "coluna_kanban": "planejado", "operacional_id": "op-c", "titulo": "V", "pontos": 1, "descricao": "d", "checklist": [], "bloqueado": True},
        ],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    # Só t1 (planejado, não bloqueada) sofre update — t4 (concluída) e t5
    # (bloqueada) nunca disparam client.table("tasks").update(...), então a
    # lista capturada tem exatamente 1 entrada.
    assert len(tasks_update) == 1
    assert tasks_update[0]["operacional_id"] is None
    assert "entrou_na_fila_em" in tasks_update[0]
    assert migracoes_insert[0]["de_modo"] == "ATRIBUICAO"
    assert migracoes_insert[0]["para_modo"] == "PULL"
    assert migracoes_insert[0]["contagem"]["mantem_responsavel"] == 1  # t5, bloqueada
    assert migracoes_insert[0]["contagem"]["sem_alteracao"] == 1  # t4, concluída
    assert sprints_update[0]["hibrida"] is True
    # Fix 1: a rota também precisa persistir projects.modo_trabalho, senão o
    # projeto fica fora de sincronia com as tasks que acabou de reclassificar.
    assert projects_update[0]["modo_trabalho"] == "PULL"


def test_aplicar_migracao_em_andamento_para_pull_mantem_operacional_e_marca_pull_em(make_client_completo, monkeypatch):
    """(a) em_andamento + PULL: mantém operacional_id (responsável) e carimba
    pull_em (não nulo) no payload de update — task não é reclassificada, só
    passa a contar tempo de pull a partir de agora."""
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")
    tc, tasks_update, migracoes_insert, sprints_update, projects_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True},
        tasks=[
            {"id": "t3", "coluna_kanban": "em_andamento", "operacional_id": "op-b", "titulo": "Z", "pontos": 5, "descricao": "d", "checklist": [], "bloqueado": False},
        ],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    assert len(tasks_update) == 1
    # operacional_id não está no payload de update -> permanece inalterado no banco.
    assert "operacional_id" not in tasks_update[0]
    assert tasks_update[0].get("pull_em") is not None
    assert migracoes_insert[0]["contagem"]["mantem_responsavel"] == 1
    assert projects_update[0]["modo_trabalho"] == "PULL"


def test_aplicar_migracao_planejado_para_atribuicao_limpa_campos_de_fila(make_client_completo, monkeypatch):
    """(b) planejado + ATRIBUICAO (reversão): rascunho, motivo_rascunho e
    entrou_na_fila_em precisam ser limpos (False/None) no payload de update
    pra uma task que já estava na fila."""
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")
    tc, tasks_update, migracoes_insert, sprints_update, projects_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": True},
        tasks=[
            {"id": "t2", "coluna_kanban": "planejado", "operacional_id": None, "titulo": "Y", "pontos": 2, "descricao": None, "checklist": [], "bloqueado": False, "rascunho": True, "motivo_rascunho": "sem_descricao", "entrou_na_fila_em": "2026-09-01T00:00:00+00:00"},
        ],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "ATRIBUICAO"})

    assert resp.status_code == 200
    assert len(tasks_update) == 1
    assert tasks_update[0]["rascunho"] is False
    assert tasks_update[0]["motivo_rascunho"] is None
    assert tasks_update[0]["entrou_na_fila_em"] is None
    assert migracoes_insert[0]["de_modo"] == "PULL"
    assert migracoes_insert[0]["para_modo"] == "ATRIBUICAO"
    assert migracoes_insert[0]["contagem"]["sem_alteracao"] == 1
    assert projects_update[0]["modo_trabalho"] == "ATRIBUICAO"


def test_aplicar_migracao_para_pull_forca_wip_por_pessoa_1(make_client_completo, monkeypatch):
    """Fix 1 (revisão final): aplicar_migrar_modo precisa honrar RF-A5 igual
    update_modos já faz — sem isso um projeto migrado para PULL via este
    endpoint ficaria com WIP de atribuição, incoerente com o modo."""
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: None)
    tc, tasks_update, migracoes_insert, sprints_update, projects_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True},
        tasks=[],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    # Segunda escrita em projects (a primeira só grava modo_trabalho) precisa
    # forçar wip_config.por_pessoa = 1.
    assert len(projects_update) == 2
    assert projects_update[0]["modo_trabalho"] == "PULL"
    assert projects_update[1]["wip_config"]["por_pessoa"] == 1


def test_aplicar_migracao_para_atribuicao_nao_mexe_no_wip(make_client_completo, monkeypatch):
    """Fix 1 (revisão final), caso negativo: migrar para ATRIBUICAO não deve
    disparar a escrita extra de wip_config — só entrar em PULL força isso."""
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: None)
    tc, tasks_update, migracoes_insert, sprints_update, projects_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": True},
        tasks=[],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "ATRIBUICAO"})

    assert resp.status_code == 200
    assert len(projects_update) == 1
    assert "wip_config" not in projects_update[0]


def _mock_client_com_historico(projeto, tasks):
    """Fix 3 (revisão final): estende _mock_client_completo capturando
    também os inserts em configuracao_historico, sem alterar o helper
    original (usado por todos os outros testes deste arquivo)."""
    mock_sb, tasks_update, migracoes_insert, sprints_update, projects_update = _mock_client_completo(projeto, tasks)
    historico_insert: list = []
    original_table_side_effect = mock_sb.table.side_effect

    def table_side_effect(name):
        if name == "configuracao_historico":
            tbl = MagicMock()

            def _insert(payload):
                historico_insert.append(payload)
                iq = MagicMock()
                iresp = MagicMock()
                iresp.data = [payload]
                iq.execute = MagicMock(return_value=iresp)
                return iq

            tbl.insert = MagicMock(side_effect=_insert)
            return tbl
        return original_table_side_effect(name)

    mock_sb.table = MagicMock(side_effect=table_side_effect)
    return mock_sb, tasks_update, migracoes_insert, sprints_update, projects_update, historico_insert


@pytest.fixture
def make_client_com_historico(monkeypatch, autenticar):
    def _make(projeto, tasks):
        import routers.projects as projects_router
        from main import app
        mock_sb, tasks_update, migracoes_insert, sprints_update, projects_update, historico_insert = (
            _mock_client_com_historico(projeto, tasks)
        )
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc, historico_insert
    return _make


def test_aplicar_migracao_grava_configuracao_historico_quando_modo_muda(make_client_com_historico, monkeypatch):
    """Fix 3 (revisão final): toda mudança real de modo_trabalho precisa
    gravar em configuracao_historico (o histórico geral que outras telas já
    leem via GET /projects/{id}/modos-historico) — não só em
    migracoes_modo, que é o registro rico específico da migração."""
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: None)
    tc, historico_insert = make_client_com_historico(
        projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True},
        tasks=[],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    assert len(historico_insert) == 1
    assert historico_insert[0]["campo"] == "modo_trabalho"
    assert historico_insert[0]["valor_anterior"] == "ATRIBUICAO"
    assert historico_insert[0]["valor_novo"] == "PULL"
    assert historico_insert[0]["project_id"] == "proj-1"
    assert "usuario_email" in historico_insert[0]


def test_desvincular_planejado_limpa_responsavel_so_de_tasks_planejadas(make_client_completo, monkeypatch):
    tc, tasks_update, _, _, _ = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": False},
        tasks=[
            {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "sprint_id": "sprint-1", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [], "bloqueado": False},
            {"id": "t2", "coluna_kanban": "em_andamento", "operacional_id": "op-b", "sprint_id": "sprint-1", "titulo": "Y", "pontos": 2, "descricao": "d", "checklist": [], "bloqueado": False},
        ],
    )
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")

    resp = tc.post("/projects/proj-1/desvincular-planejado")

    assert resp.status_code == 200
    assert resp.json() == {"desvinculadas": 1}
    assert tasks_update[0]["operacional_id"] is None
