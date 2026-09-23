"""Spec §13: "/aprovar ... dispara pontuação corretamente no fechamento
(teste de integração com calcular_e_travar_pontuacao)".

Teste que faltava (achado #5 da revisão final de branch). O risco concreto:
quem aprova é gerente/líder, quem fez o trabalho é o operacional. Se a
transição gravada por /aprovar não carregasse o `operacional_id` da task,
services/pontuacao.py::_resolver_quem_completou atribuiria os pontos à pessoa
errada (ou a ninguém) no fechamento da sprint.

O teste liga as duas pontas de verdade: roda o endpoint, captura a linha de
task_transicoes que ele grava, e alimenta calcular_e_travar_pontuacao com ela.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.pontuacao import calcular_e_travar_pontuacao
from tests.test_aprovar_task import _mock_client as _mock_tasks_client
from tests.test_pontuacao_fechamento import _mock_client as _mock_pontuacao_client


_TASK = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 5,
    "coluna_kanban": "pendente_aprovacao", "ordem": 0, "sprint_id": "sprint-1",
    # quem fez o trabalho
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": True, "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def aprovar(monkeypatch, autenticar):
    """Executa POST /tasks/task-1/aprovar como gerente e devolve as linhas de
    task_transicoes gravadas."""
    def _aprovar(task=None):
        import routers.tasks as tasks_router
        from main import app
        mock_sb, tasks_update, transicoes_insert = _mock_tasks_client(task or _TASK)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        resp = tc.post("/tasks/task-1/aprovar")
        assert resp.status_code == 200
        return transicoes_insert, tasks_update
    return _aprovar


def test_aprovar_grava_o_operacional_que_fez_o_trabalho_na_transicao(aprovar):
    transicoes_insert, _ = aprovar()

    assert len(transicoes_insert) == 1
    transicao = transicoes_insert[0]
    assert transicao["para"] == "concluida"
    # a pessoa logada é gerente (pessoa@citi.org.br), NÃO op-1 — o snapshot é
    # de quem estava com a task, não de quem clicou em Aprovar
    assert transicao["operacional_id"] == "op-1"


def test_pontuacao_no_fechamento_credita_quem_fez_o_trabalho_nao_quem_aprovou(aprovar):
    transicoes_insert, tasks_update = aprovar()

    # Estado do banco depois da aprovação: task concluída + a transição que o
    # endpoint acabou de gravar (a mesma linha, não uma reconstruída à mão).
    task_concluida = {
        "id": "task-1", "operacional_id": _TASK["operacional_id"], "pontos": _TASK["pontos"],
        "coluna_kanban": tasks_update[-1]["coluna_kanban"],
    }
    transicao = transicoes_insert[0]
    client = _mock_pontuacao_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=[task_concluida],
        task_transicoes=[{
            "task_id": transicao["task_id"],
            "operacional_id": transicao["operacional_id"],
            "timestamp": transicao["timestamp"],
        }],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert task_concluida["coluna_kanban"] == "concluida"
    linhas = {linha["operacional_id"]: linha for linha in resultado}
    assert "op-1" in linhas
    assert linhas["op-1"]["entrega_pontos_concluidos"] == 5
    assert linhas["op-1"]["qualidade_tasks_concluidas"] == 1
    # o gerente que aprovou não vira linha de pontuação por ter aprovado
    assert set(linhas) == {"op-1"}


def test_pontuacao_usa_o_snapshot_da_transicao_mesmo_se_a_task_trocar_de_dono(aprovar):
    """Caso que discrimina de verdade: se a task for reatribuída depois da
    aprovação, o crédito ainda tem que ir pra quem entregou (op-1, gravado por
    /aprovar em task_transicoes) e não pro dono atual (op-2). É o mesmo
    contrato de "transferência só do que falta" já testado em
    tests/test_pontuacao_fechamento.py, aqui exercitado a partir da linha que o
    endpoint realmente grava."""
    transicoes_insert, tasks_update = aprovar()
    transicao = transicoes_insert[0]

    client = _mock_pontuacao_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=[{
            "id": "task-1", "operacional_id": "op-2", "pontos": 5,
            "coluna_kanban": tasks_update[-1]["coluna_kanban"],
        }],
        task_transicoes=[{
            "task_id": transicao["task_id"],
            "operacional_id": transicao["operacional_id"],
            "timestamp": transicao["timestamp"],
        }],
    )

    linhas = {linha["operacional_id"]: linha for linha in calcular_e_travar_pontuacao(client, "sprint-1")}

    assert set(linhas) == {"op-1"}
    assert linhas["op-1"]["entrega_pontos_concluidos"] == 5
