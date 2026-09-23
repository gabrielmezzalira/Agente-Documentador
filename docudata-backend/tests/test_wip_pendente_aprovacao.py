"""Spec §13: "WIP: task em pendente_aprovacao não conta pro limite por pessoa
nem por coluna (check_wip)".

Teste que faltava (achado #5 da revisão final de branch). O comportamento cai
naturalmente do fato de check_wip contar só `coluna_kanban == "em_andamento"`,
mas nada travava isso: bastaria alguém somar pendente_aprovacao à contagem
"pra não perder de vista o trabalho em voo" pra o operacional ficar bloqueado
esperando o gerente aprovar — trabalho que ele já entregou.
"""
from unittest.mock import MagicMock

from services.wip_check import check_wip


def _mock_client(wip_config, tasks):
    """Mock que respeita os filtros .eq() usados por check_wip — sem isso o
    teste não distinguiria 'não conta pendente_aprovacao' de 'não filtra
    nada'."""
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"wip_config": wip_config}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                filtros: dict = {}

                def eq_effect(field, value):
                    filtros[field] = value
                    return q

                def execute_effect():
                    resp = MagicMock()
                    resp.data = [
                        t for t in tasks
                        if all(t.get(campo) == valor for campo, valor in filtros.items())
                    ]
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_task_em_pendente_aprovacao_nao_conta_no_wip_por_coluna():
    tasks = [
        {"id": "t1", "project_id": "proj-1", "operacional_id": "op-1", "coluna_kanban": "pendente_aprovacao"},
        {"id": "t2", "project_id": "proj-1", "operacional_id": "op-2", "coluna_kanban": "pendente_aprovacao"},
    ]
    client = _mock_client({"por_coluna_em_andamento": 1}, tasks)

    ok, motivo = check_wip(client, "proj-1", "op-1", "em_andamento")

    assert ok is True
    assert motivo is None


def test_task_em_pendente_aprovacao_nao_conta_no_wip_por_pessoa():
    tasks = [
        {"id": "t1", "project_id": "proj-1", "operacional_id": "op-1", "coluna_kanban": "pendente_aprovacao"},
    ]
    client = _mock_client({"por_pessoa": 1}, tasks)

    ok, motivo = check_wip(client, "proj-1", "op-1", "em_andamento")

    assert ok is True
    assert motivo is None


def test_task_em_andamento_ainda_conta_no_wip_por_pessoa():
    """Trava de contraste: o mock filtra de verdade — o teste acima não passa
    só porque nada é contado."""
    tasks = [
        {"id": "t1", "project_id": "proj-1", "operacional_id": "op-1", "coluna_kanban": "em_andamento"},
    ]
    client = _mock_client({"por_pessoa": 1}, tasks)

    ok, motivo = check_wip(client, "proj-1", "op-1", "em_andamento")

    assert ok is False
    assert "por pessoa" in motivo


def test_mover_para_pendente_aprovacao_nao_dispara_wip():
    """O destino pendente_aprovacao também não é limitado: check_wip só age
    quando o destino é em_andamento."""
    tasks = [
        {"id": "t1", "project_id": "proj-1", "operacional_id": "op-1", "coluna_kanban": "em_andamento"},
        {"id": "t2", "project_id": "proj-1", "operacional_id": "op-1", "coluna_kanban": "em_andamento"},
    ]
    client = _mock_client({"por_pessoa": 1, "por_coluna_em_andamento": 1}, tasks)

    ok, motivo = check_wip(client, "proj-1", "op-1", "pendente_aprovacao")

    assert ok is True
    assert motivo is None
