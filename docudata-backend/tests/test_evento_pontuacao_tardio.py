"""Testes para services/pontuacao.py::rotear_evento_pos_fechamento (Phase 18).

Cobre a Pergunta 3 do brainstorming: reabertura/bloqueio resolvido numa task
cujo sprint de origem já fechou (pontuacao_operacional_sprint travada) é
roteado pra sprint ativa via get_current_sprint_id, através do ledger
eventos_pontuacao_tardios — sem tocar task.sprint_id.
"""
from unittest.mock import MagicMock

from services.pontuacao import rotear_evento_pos_fechamento


def _mock_client(sprint_origem_travada, sprint_ativa_id, sprint_ativa_travada, insert_capture):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "pontuacao_operacional_sprint":
            # Mesmo objeto `q` é reusado nas duas chamadas de rotear_evento_pos_fechamento
            # (checagem da sprint de origem, depois da sprint ativa) — `.eq(...)` grava
            # o valor recebido em `q._last_eq` pra `_resp` saber qual das duas responder.
            def _resp():
                if q._last_eq == "sprint-origem":
                    return MagicMock(data=[{"id": "pont-1"}] if sprint_origem_travada else [])
                return MagicMock(data=[{"id": "pont-2"}] if sprint_ativa_travada else [])

            def _eq_side_effect(field, value):
                q._last_eq = value
                return q

            q = MagicMock()
            q._last_eq = None
            q.eq = MagicMock(side_effect=_eq_side_effect)
            q.execute = MagicMock(side_effect=_resp)
            tbl.select = MagicMock(return_value=q)

        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": sprint_ativa_id, "numero": 2}] if sprint_ativa_id else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "ingestions":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "eventos_pontuacao_tardios":
            def insert_side_effect(payload):
                insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="evento-1")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK = {"id": "task-1", "project_id": "proj-1", "sprint_id": "sprint-origem", "operacional_id": "op-1"}


def test_sprint_origem_nao_travada_nao_faz_nada(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=False, sprint_ativa_id="sprint-ativa", sprint_ativa_travada=False, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "qualidade_reaberturas")

    assert insert_capture == []


def test_sprint_origem_travada_e_ativa_livre_grava_no_ledger(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=True, sprint_ativa_id="sprint-ativa", sprint_ativa_travada=False, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "qualidade_reaberturas")

    assert len(insert_capture) == 1
    assert insert_capture[0]["operacional_id"] == "op-1"
    assert insert_capture[0]["sprint_id_alvo"] == "sprint-ativa"
    assert insert_capture[0]["dimensao"] == "qualidade_reaberturas"
    assert insert_capture[0]["task_id"] == "task-1"


def test_sprint_origem_e_ativa_ambas_travadas_nao_grava_nada(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=True, sprint_ativa_id="sprint-ativa", sprint_ativa_travada=True, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "autonomia_bloqueios_totais")

    assert insert_capture == []


def test_sem_sprint_ativa_nao_grava_nada(monkeypatch):
    insert_capture = []
    client = _mock_client(sprint_origem_travada=True, sprint_ativa_id=None, sprint_ativa_travada=False, insert_capture=insert_capture)

    rotear_evento_pos_fechamento(client, _TASK, "qualidade_reaberturas")

    assert insert_capture == []
