"""Testes para services/pontuacao.py::calcular_e_travar_pontuacao (Phase 18).

Cobre: cálculo básico de entrega/qualidade/autonomia/gerente, idempotência
(chamar duas vezes não duplica nem recalcula), e a mecânica de reatribuição
mid-sprint decidida no brainstorming ("transferência só do que falta": pontos
concluídos ficam com quem entregou, via snapshot em task_transicoes;
pontos ainda alocados seguem o operacional atual).
"""
from unittest.mock import MagicMock

from services.pontuacao import calcular_e_travar_pontuacao


def _mock_client(
    pontuacao_existente=None,
    sprint=None,
    tasks=None,
    task_transicoes=None,
    task_reaberturas=None,
    eventos_tardios=None,
    avaliacoes=None,
    insert_capture=None,
):
    pontuacao_existente = pontuacao_existente or []
    tasks = tasks or []
    task_transicoes = task_transicoes or []
    task_reaberturas = task_reaberturas or []
    eventos_tardios = eventos_tardios or []
    avaliacoes = avaliacoes or []
    insert_capture = insert_capture if insert_capture is not None else []

    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao_existente
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(row, id=f"pont-{i}") for i, row in enumerate(payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [sprint] if sprint else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = task_transicoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_reaberturas":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = task_reaberturas
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "eventos_pontuacao_tardios":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = eventos_tardios
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = avaliacoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_SPRINT = {"id": "sprint-1", "project_id": "proj-1"}
_AVALIACAO_OP1 = {
    "operacional_id": "op-1",
    "resposta_1": 5, "resposta_2": 4, "resposta_3": 3, "resposta_4": 4, "resposta_5": 5,
    "resposta_6": 2, "resposta_7": 3,
}


def test_calcula_entrega_qualidade_autonomia_gerente_para_task_simples(monkeypatch):
    insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{
            "id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida",
            "bloqueado_resolvido_por": "operacional", "bloqueado_resolvido_em": "2026-09-01T00:00:00Z",
        }],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_reaberturas=[{"operacional_id": "op-1"}],
        avaliacoes=[_AVALIACAO_OP1],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert len(resultado) == 1
    linha = resultado[0]
    assert linha["operacional_id"] == "op-1"
    assert linha["projeto_id"] == "proj-1"
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 5
    assert linha["qualidade_tasks_concluidas"] == 1
    assert linha["qualidade_reaberturas"] == 1
    assert linha["autonomia_bloqueios_totais"] == 1
    assert linha["autonomia_bloqueios_resolvidos_proprio"] == 1
    assert linha["gerente_media"] == round((5 + 4 + 3 + 4 + 5 + 3) / 6, 2)
    assert linha["gerente_pergunta6"] == 2
    assert linha["arquetipo"] is None
    assert len(insert_capture) == 1


def test_idempotente_nao_recalcula_se_ja_existir_linha(monkeypatch):
    existente = [{"id": "pont-1", "operacional_id": "op-1", "sprint_id": "sprint-1"}]
    client = _mock_client(pontuacao_existente=existente, sprint=_SPRINT)

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert resultado == existente
    # Não deve nem consultar "tasks" — a checagem de idempotência é a primeira coisa que roda.
    client.table.assert_any_call("pontuacao_operacional_sprint")


def test_reatribuicao_mid_sprint_pontos_concluidos_ficam_com_quem_entregou(monkeypatch):
    """Task foi concluída pelo op-A e só depois reatribuída pro op-B — os pontos
    concluídos ficam com op-A (quem entregou), não com op-B (quem está com a
    task agora)."""
    insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-B", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-A", "timestamp": "2026-09-01T00:00:00Z"}],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    por_operacional = {linha["operacional_id"]: linha for linha in resultado}
    assert por_operacional["op-A"]["entrega_pontos_concluidos"] == 8
    assert por_operacional["op-A"]["entrega_pontos_alocados"] == 8
    assert "op-B" not in por_operacional


def test_reatribuicao_mid_sprint_task_ainda_aberta_fica_com_operacional_atual(monkeypatch):
    """Task ainda não concluída, reatribuída de op-A pra op-B — os pontos
    alocados (ainda não entregues) seguem o operacional atual (op-B)."""
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-B", "pontos": 3, "coluna_kanban": "em_andamento"}],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    por_operacional = {linha["operacional_id"]: linha for linha in resultado}
    assert por_operacional["op-B"]["entrega_pontos_alocados"] == 3
    assert por_operacional["op-B"]["entrega_pontos_concluidos"] == 0
    assert "op-A" not in por_operacional


def test_eventos_tardios_somam_na_contagem_normal(monkeypatch):
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "em_andamento"}],
        eventos_tardios=[
            {"operacional_id": "op-1", "dimensao": "qualidade_reaberturas"},
            {"operacional_id": "op-1", "dimensao": "autonomia_bloqueios_totais"},
            {"operacional_id": "op-1", "dimensao": "autonomia_bloqueios_resolvidos_proprio"},
        ],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["qualidade_reaberturas"] == 1
    assert linha["autonomia_bloqueios_totais"] == 1
    assert linha["autonomia_bloqueios_resolvidos_proprio"] == 1


def test_sprint_inexistente_retorna_lista_vazia(monkeypatch):
    client = _mock_client(sprint=None)
    assert calcular_e_travar_pontuacao(client, "sprint-inexistente") == []


def test_sprint_sem_nenhuma_task_retorna_lista_vazia(monkeypatch):
    client = _mock_client(sprint=_SPRINT, tasks=[])
    assert calcular_e_travar_pontuacao(client, "sprint-1") == []
