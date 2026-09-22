"""Entrega 4 (follow-up): ao migrar um projeto para o modo Pull, operacionais
ativos do projeto e gerentes/líderes recebem um e-mail avisando da mudança.
Mesmo racional de _avisar_gerente_task_concluida (routers/tasks.py) — melhor
esforço, nunca bloqueia a migração. Ver .planning/feature-flow-state.md."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, operacionais=None, gerentes=None):
    operacionais = operacionais if operacionais is not None else []
    gerentes = gerentes if gerentes is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)

            def _update(payload):
                projeto.update(payload)
                uq = MagicMock()
                uq.eq = MagicMock(return_value=uq)
                uresp = MagicMock()
                uresp.data = [projeto]
                uq.execute = MagicMock(return_value=uresp)
                return uq
            tbl.update = MagicMock(side_effect=_update)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = operacionais
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "pessoa":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = gerentes
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
            tbl.insert = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto, operacionais=None, gerentes=None):
        import routers.projects as projects_router
        from main import app
        mock_sb = _mock_client(projeto, operacionais, gerentes)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: None)
        envios = []
        monkeypatch.setattr(
            projects_router, "send_email",
            lambda to, subject, html: envios.append((to, subject, html)),
        )
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc, envios
    return _make


def test_migrar_para_pull_avisa_operacionais_ativos_e_gerentes(make_client):
    tc, envios = make_client(
        projeto={"id": "proj-1", "name": "Projeto X", "modo_trabalho": "ATRIBUICAO"},
        operacionais=[{"email": "op1@citi.com"}, {"email": "op2@citi.com"}],
        gerentes=[{"email": "ger@citi.com"}],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    destinatarios = {to for to, _, _ in envios}
    assert destinatarios == {"op1@citi.com", "op2@citi.com", "ger@citi.com"}
    for _, subject, html in envios:
        assert "Projeto X" in subject
        assert "Pull" in html


def test_migrar_para_pull_nao_duplica_email_se_pessoa_e_operacional_e_gerente(make_client):
    tc, envios = make_client(
        projeto={"id": "proj-1", "name": "Projeto X", "modo_trabalho": "ATRIBUICAO"},
        operacionais=[{"email": "mesma@citi.com"}],
        gerentes=[{"email": "mesma@citi.com"}],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    assert len(envios) == 1


def test_migrar_para_atribuicao_nao_dispara_aviso_de_pull(make_client):
    tc, envios = make_client(
        projeto={"id": "proj-1", "name": "Projeto X", "modo_trabalho": "PULL"},
        operacionais=[{"email": "op1@citi.com"}],
        gerentes=[{"email": "ger@citi.com"}],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "ATRIBUICAO"})

    assert resp.status_code == 200
    assert envios == []


def test_migrar_para_pull_sem_mudanca_real_nao_reenvia_aviso(make_client):
    tc, envios = make_client(
        projeto={"id": "proj-1", "name": "Projeto X", "modo_trabalho": "PULL"},
        operacionais=[{"email": "op1@citi.com"}],
        gerentes=[{"email": "ger@citi.com"}],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    assert envios == []


def test_falha_no_envio_de_email_nao_derruba_a_migracao(make_client, monkeypatch):
    tc, _ = make_client(
        projeto={"id": "proj-1", "name": "Projeto X", "modo_trabalho": "ATRIBUICAO"},
        operacionais=[{"email": "op1@citi.com"}],
        gerentes=[],
    )
    import routers.projects as projects_router

    def _quebra(to, subject, html):
        raise RuntimeError("Resend fora do ar")
    monkeypatch.setattr(projects_router, "send_email", _quebra)

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    assert resp.json()["para_modo"] == "PULL"
