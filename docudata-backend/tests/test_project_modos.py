"""Testes para PATCH /projects/{id}/modos, GET /projects/{id}/modos-historico
e PATCH /projects/{id}/wip-config (Entrega 1 de Modos de Trabalho e de
Avaliação)."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


_PROJETO_BASE = {
    "id": "proj-1", "name": "Projeto Teste", "client": "CITi", "subarea": "dados",
    "description": None, "squad": None, "valor_projeto": None, "valor_por_ponto": None,
    "is_delivered": False, "created_at": "2026-09-01T00:00:00+00:00",
    "data_inicio": None, "data_fim_contratada": None, "tolerancia_desvio_pontos": None,
    "periodo_garantia_dias": None, "gerente_email": None, "arquetipo": "padrao",
    "github_token": None, "github_repo": None,
    "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS",
    "pull_exigir_hidratacao": True, "pull_piso_pontos": 1, "pull_teto": 1.5,
    "wip_config": None,
}


def _mock_client(projeto, historico_insert_capture=None):
    estado = dict(projeto) if projeto is not None else None
    historico_insert_capture = historico_insert_capture if historico_insert_capture is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(estado)] if estado is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                if estado is not None:
                    estado.update(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(estado)] if estado is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "configuracao_historico":
            def insert_side_effect(payload):
                historico_insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id=f"hist-{len(historico_insert_capture)}", criado_em="2026-09-20T00:00:00Z")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, estado


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto=_PROJETO_BASE, historico_insert_capture=None, cargo="gerente"):
        import routers.projects as projects_router
        from main import app
        mock_sb, estado = _mock_client(projeto, historico_insert_capture)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, estado
    return _make


def test_patch_modos_troca_modo_trabalho_e_grava_historico(make_client):
    historico = []
    tc, estado = make_client(historico_insert_capture=historico)

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 200
    assert resp.json()["modo_trabalho"] == "PULL"
    assert historico == [{
        "project_id": "proj-1", "campo": "modo_trabalho",
        "valor_anterior": "ATRIBUICAO", "valor_novo": "PULL",
        "usuario_email": "pessoa@citi.org.br",
    }]


def test_patch_modos_forca_wip_por_pessoa_1_ao_entrar_em_pull(make_client):
    tc, estado = make_client(projeto={**_PROJETO_BASE, "wip_config": {"por_coluna_em_andamento": 8}})

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 200
    assert resp.json()["wip_config"] == {"por_coluna_em_andamento": 8, "por_pessoa": 1}


def test_patch_modos_sem_mudanca_nao_grava_historico(make_client):
    historico = []
    tc, estado = make_client(historico_insert_capture=historico)

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "ATRIBUICAO"})

    assert resp.status_code == 200
    assert historico == []


def test_patch_modos_bloqueia_operacional(make_client):
    tc, estado = make_client(cargo="operacional")

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 403


def test_patch_modos_projeto_inexistente_404(make_client):
    tc, estado = make_client(projeto=None)

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 404


def test_patch_modos_rejeita_valor_fora_do_enum(make_client):
    tc, estado = make_client()

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PARALELO"})

    assert resp.status_code == 422


def test_patch_modos_rejeita_piso_nao_positivo(make_client):
    tc, estado = make_client()

    resp = tc.patch("/projects/proj-1/modos", json={"pull_piso_pontos": 0})

    assert resp.status_code == 422


def test_get_modos_historico_lista_registros(make_client, monkeypatch):
    tc, estado = make_client()
    import routers.projects as projects_router

    registros = [{"id": "h1", "project_id": "proj-1", "campo": "modo_trabalho",
                  "valor_anterior": "ATRIBUICAO", "valor_novo": "PULL",
                  "usuario_email": "g@citi.com", "criado_em": "2026-09-20T00:00:00Z"}]

    mock_sb = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "configuracao_historico":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = registros
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    mock_sb.table = MagicMock(side_effect=table_side_effect)
    monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)

    resp = tc.get("/projects/proj-1/modos-historico")

    assert resp.status_code == 200
    assert resp.json() == registros


def test_patch_wip_config_forca_por_pessoa_1_em_pull(make_client):
    tc, estado = make_client(projeto={**_PROJETO_BASE, "modo_trabalho": "PULL", "wip_config": None})

    resp = tc.patch("/projects/proj-1/wip-config", json={"por_pessoa": 3})

    assert resp.status_code == 200
    assert resp.json()["wip_config"] == {"por_pessoa": 1}


def test_patch_wip_config_edita_livre_em_atribuicao(make_client):
    tc, estado = make_client()

    resp = tc.patch("/projects/proj-1/wip-config", json={"por_pessoa": 3, "por_coluna_em_andamento": 10})

    assert resp.status_code == 200
    assert resp.json()["wip_config"] == {"por_pessoa": 3, "por_coluna_em_andamento": 10}


def test_patch_wip_config_bloqueia_operacional(make_client):
    tc, estado = make_client(cargo="operacional")

    resp = tc.patch("/projects/proj-1/wip-config", json={"por_pessoa": 2})

    assert resp.status_code == 403
