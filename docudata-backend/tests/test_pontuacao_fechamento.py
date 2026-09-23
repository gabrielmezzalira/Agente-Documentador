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
    cutoff_existente=None,
    sprint=None,
    tasks=None,
    task_transicoes=None,
    task_reaberturas=None,
    task_travamentos=None,
    eventos_tardios=None,
    avaliacoes=None,
    commit_qualidade=None,
    insert_capture=None,
    projeto=None,
    sprint_update_capture=None,
    eventos_insert_capture=None,
    eventos_insert_raises=False,
    operacionais=None,
):
    pontuacao_existente = pontuacao_existente or []
    cutoff_existente = cutoff_existente or []
    tasks = tasks or []
    task_transicoes = task_transicoes or []
    task_reaberturas = task_reaberturas or []
    task_travamentos = task_travamentos or []
    eventos_tardios = eventos_tardios or []
    avaliacoes = avaliacoes or []
    commit_qualidade = commit_qualidade or []
    insert_capture = insert_capture if insert_capture is not None else []
    projeto = projeto or {"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS"}
    sprint_update_capture = sprint_update_capture if sprint_update_capture is not None else []
    eventos_insert_capture = eventos_insert_capture if eventos_insert_capture is not None else []
    operacionais = operacionais or []

    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                # Duas queries diferentes passam por aqui: a checagem de
                # idempotência (.eq("sprint_id", ...)) e a busca de cutoff
                # (.eq("projeto_id", ...).order(...).limit(...)) — distingue
                # pela presença de .order() na chain.
                q = MagicMock()
                state = {"order_called": False}

                def eq_effect(*a, **kw):
                    return q

                def order_effect(*a, **kw):
                    state["order_called"] = True
                    return q

                def limit_effect(*a, **kw):
                    return q

                def execute_effect():
                    resp = MagicMock()
                    resp.data = cutoff_existente if state["order_called"] else pontuacao_existente
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                q.order = MagicMock(side_effect=order_effect)
                q.limit = MagicMock(side_effect=limit_effect)
                q.execute = MagicMock(side_effect=execute_effect)
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

            def update_side_effect(payload):
                sprint_update_capture.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(sprint or {}, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)

        elif name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [projeto]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "pontuacao_eventos":
            def insert_side_effect(payload):
                eventos_insert_capture.extend(payload)
                q = MagicMock()
                if eventos_insert_raises:
                    def execute_effect():
                        raise RuntimeError("falha simulada no insert de pontuacao_eventos")
                    q.execute = MagicMock(side_effect=execute_effect)
                else:
                    resp = MagicMock()
                    resp.data = [dict(row, id=f"evt-{i}") for i, row in enumerate(payload)]
                    q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)

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
                state = {"gt_timestamp": None}

                def in_effect(*a, **kw):
                    return q

                def gt_effect(field, value):
                    state["gt_timestamp"] = value
                    return q

                def execute_effect():
                    resp = MagicMock()
                    data = task_reaberturas
                    if state["gt_timestamp"] is not None:
                        data = [r for r in data if r.get("timestamp", "") > state["gt_timestamp"]]
                    resp.data = data
                    return resp

                q.in_ = MagicMock(side_effect=in_effect)
                q.gt = MagicMock(side_effect=gt_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_travamentos":
            def select_side_effect(cols):
                q = MagicMock()
                state = {"gt_timestamp": None, "dispensado": None, "task_ids": None}

                def in_effect(field, valores):
                    if field == "task_id":
                        state["task_ids"] = set(valores)
                    return q

                def eq_effect(field, value):
                    if field == "dispensado":
                        state["dispensado"] = value
                    return q

                def gt_effect(field, value):
                    state["gt_timestamp"] = value
                    return q

                def execute_effect():
                    resp = MagicMock()
                    data = task_travamentos
                    if state["task_ids"] is not None:
                        data = [r for r in data if r.get("task_id", "task-1") in state["task_ids"]]
                    if state["dispensado"] is not None:
                        data = [r for r in data if r.get("dispensado", False) == state["dispensado"]]
                    if state["gt_timestamp"] is not None:
                        data = [r for r in data if r.get("timestamp", "") > state["gt_timestamp"]]
                    resp.data = data
                    return resp

                q.in_ = MagicMock(side_effect=in_effect)
                q.eq = MagicMock(side_effect=eq_effect)
                q.gt = MagicMock(side_effect=gt_effect)
                q.execute = MagicMock(side_effect=execute_effect)
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

        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        if name == "commit_qualidade":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.gt = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = commit_qualidade
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


def test_golden_fixture_multidimensional_trava_de_regressao(monkeypatch):
    """Sprint de referência com dado fixo cobrindo as 5 dimensões numa
    passada só (entrega, qualidade, autonomia, gerente, bônus). Serve de
    trava de regressão para a spec de Modos de Trabalho e de Avaliação
    (docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md):
    depois que services/pontuacao.py ganhar os campos da Entrega 1, este
    teste tem que continuar passando com os MESMOS valores — prova que
    projeto em ATRIBUICAO + PONTOS_ATRIBUIDOS não muda de comportamento
    (SDD original, risco §11). Escrito e confirmado passando ANTES de
    qualquer mudança em calcular_e_travar_pontuacao."""
    insert_capture = []
    aval = {
        "operacional_id": "op-1",
        "resposta_1": 4, "resposta_2": 4, "resposta_3": 3, "resposta_4": 4,
        "resposta_5": 4, "resposta_6": 5, "resposta_7": 4,
    }
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            {
                "id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida",
                "bloqueado_resolvido_por": "operacional", "bloqueado_resolvido_em": "2026-09-01T00:00:00Z",
            },
            {"id": "task-2", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"},
            {"id": "task-3", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "concluida", "extra": True},
        ],
        task_transicoes=[
            {"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"},
            {"task_id": "task-3", "operacional_id": "op-1", "timestamp": "2026-09-03T00:00:00Z"},
        ],
        task_reaberturas=[{"operacional_id": "op-1"}],
        task_travamentos=[{"task_id": "task-1", "operacional_id": "op-1", "pontos": 5, "dispensado": False, "timestamp": "2026-09-01T12:00:00Z"}],
        avaliacoes=[aval],
        commit_qualidade=[{"operacional_id": "op-1", "nota": 8}, {"operacional_id": "op-1", "nota": 6}],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert len(resultado) == 1
    linha = resultado[0]
    assert linha["operacional_id"] == "op-1"
    assert linha["sprint_id"] == "sprint-1"
    assert linha["projeto_id"] == "proj-1"
    assert linha["gerente_media"] == 3.83
    assert linha["gerente_pergunta6"] == 5
    assert linha["gerente_pergunta3"] == 3
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 8
    assert linha["entrega_pontos_penalizados"] == 5
    assert linha["bonus_pontos_extra"] == 2
    assert linha["qualidade_reaberturas"] == 1
    assert linha["qualidade_tasks_concluidas"] == 2
    assert linha["autonomia_bloqueios_resolvidos_proprio"] == 1
    assert linha["autonomia_bloqueios_totais"] == 1
    assert linha["qualidade_commit_media"] == 7.0
    assert linha["arquetipo"] is None


def test_congela_modo_trabalho_e_avaliacao_da_sprint_no_fechamento():
    sprint_update_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        projeto={"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO"},
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        sprint_update_capture=sprint_update_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    assert sprint_update_capture == [{"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO"}]


def test_entrega_modo_default_pontos_atribuidos_quando_projeto_nao_configurado():
    client = _mock_client(
        sprint=_SPRINT,
        projeto={"modo_trabalho": None, "modo_avaliacao": None},
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_modo"] == "PONTOS_ATRIBUIDOS"


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
    # Média das seis perguntas do questionário; resposta_6 (campo legado, a
    # antiga pergunta de evolução) não entra nessa média.
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


# --- Regressão: carry-over cross-sprint não pode dobrar a contagem (Finding 2) ---

_SPRINT_2 = {"id": "sprint-2", "project_id": "proj-1"}
_CUTOFF = "2026-09-01T12:00:00+00:00"


def test_reabertura_de_sprint_anterior_ja_travada_nao_e_recontada_mas_nova_e_contada(monkeypatch):
    """Task T foi reaberta na sprint-1 (evento já contabilizado quando a
    sprint-1 fechou, travando pontuacao_operacional_sprint com
    finalizado_em=_CUTOFF). T segue sem terminar e é reatribuída pra
    sprint-2 (task.sprint_id vira sprint-2, sem mudar mais nada). Quando
    sprint-2 fecha, _contar_reaberturas não pode encontrar de novo a mesma
    linha antiga de task_reaberturas (timestamp antes do cutoff) — só uma
    reabertura genuinamente nova (timestamp depois do cutoff) deve contar."""
    client = _mock_client(
        cutoff_existente=[{"finalizado_em": _CUTOFF}],
        sprint=_SPRINT_2,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        task_reaberturas=[
            {"operacional_id": "op-1", "timestamp": "2026-08-30T00:00:00+00:00"},  # sprint-1, já contabilizada
            {"operacional_id": "op-1", "timestamp": "2026-09-03T00:00:00+00:00"},  # nova, pós-cutoff
        ],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-2")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["qualidade_reaberturas"] == 1


def test_bloqueio_resolvido_antes_do_cutoff_nao_e_recontado_mas_novo_e_contado(monkeypatch):
    """Mesmo cenário de carry-over, mas para o campo bloqueado_resolvido_em:
    task-1 tem uma resolução de bloqueio antiga (de antes do cutoff, já
    contabilizada quando a sprint-1 fechou) e não deve ser recontada quando
    a sprint-2 (que agora contém task-1) fecha. task-2, com resolução após o
    cutoff, deve ser contada normalmente."""
    client = _mock_client(
        cutoff_existente=[{"finalizado_em": _CUTOFF}],
        sprint=_SPRINT_2,
        tasks=[
            {
                "id": "task-1", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "em_andamento",
                "bloqueado_resolvido_por": "operacional", "bloqueado_resolvido_em": "2026-08-30T00:00:00+00:00",
            },
            {
                "id": "task-2", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "em_andamento",
                "bloqueado_resolvido_por": "operacional", "bloqueado_resolvido_em": "2026-09-03T00:00:00+00:00",
            },
        ],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-2")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["autonomia_bloqueios_totais"] == 1
    assert linha["autonomia_bloqueios_resolvidos_proprio"] == 1


def test_gerente_media_exclui_a_resposta_6(monkeypatch):
    aval = {
        "operacional_id": "op-1",
        "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_6": 0, "resposta_7": 5,
    }
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 1, "coluna_kanban": "em_andamento"}],
        avaliacoes=[aval],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    # resposta_6=0 NÃO derruba a média do gerente — mesmo que alguém ainda
    # mande esse campo legado (via reaproveitar de uma avaliação antiga, por
    # exemplo), ele nunca entrou nessa média e continua não entrando.
    assert linha["gerente_media"] == round((5 + 5 + 5 + 5 + 5 + 5) / 6, 2)
    assert linha["gerente_pergunta6"] == 0


def test_qualidade_commit_media_calculada_no_fechamento(monkeypatch):
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        commit_qualidade=[
            {"operacional_id": "op-1", "nota": 8},
            {"operacional_id": "op-1", "nota": 6},
        ],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["qualidade_commit_media"] == round((8 + 6) / 2, 2)


def test_qualidade_commit_media_null_sem_commit_no_periodo(monkeypatch):
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        commit_qualidade=[],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    assert linha["qualidade_commit_media"] is None


def test_travamento_automatico_penaliza_pontos_de_entrega():
    """Task que ficou parada além do tempo esperado não conta como entrega cheia:
    os pontos dela saem dos concluídos (decisão do Líder, 2026-09-07)."""
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_travamentos=[{"operacional_id": "op-1", "pontos": 8, "dispensado": False, "timestamp": "2026-09-01T00:00:00Z"}],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_pontos_concluidos"] == 8
    assert linha["entrega_pontos_alocados"] == 8
    assert linha["entrega_pontos_penalizados"] == 8


def test_travamento_dispensado_pelo_gerente_nao_penaliza():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_travamentos=[{"operacional_id": "op-1", "pontos": 8, "dispensado": True, "timestamp": "2026-09-01T00:00:00Z"}],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_pontos_penalizados"] == 0


def test_travamento_anterior_ao_cutoff_nao_conta_de_novo():
    """Mesma proteção das reaberturas: travamento já contabilizado num
    fechamento anterior não penaliza a sprint seguinte."""
    client = _mock_client(
        sprint=_SPRINT,
        cutoff_existente=[{"finalizado_em": "2026-09-05T00:00:00Z"}],
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-06T00:00:00Z"}],
        task_travamentos=[
            {"operacional_id": "op-1", "pontos": 5, "dispensado": False, "timestamp": "2026-09-01T00:00:00Z"},
            {"operacional_id": "op-1", "pontos": 5, "dispensado": False, "timestamp": "2026-09-07T00:00:00Z"},
        ],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_pontos_penalizados"] == 5


def test_task_extra_vira_bonus_e_fica_fora_de_entrega():
    """Task extra não consumiu orçamento da sprint, então não pode entrar no
    denominador de Entrega — entrar puniria quem pediu mais trabalho."""
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            {"id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida"},
            {"id": "task-2", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "concluida", "extra": True},
        ],
        task_transicoes=[
            {"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"},
            {"task_id": "task-2", "operacional_id": "op-1", "timestamp": "2026-09-03T00:00:00Z"},
        ],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 5
    assert linha["bonus_pontos_extra"] == 3
    assert linha["qualidade_tasks_concluidas"] == 2


def test_task_extra_nao_concluida_nao_vira_bonus_nem_alocacao():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            {"id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida"},
            {"id": "task-2", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento", "extra": True},
        ],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_pontos_alocados"] == 5
    assert linha["bonus_pontos_extra"] == 0


def test_travamento_de_task_nao_concluida_nao_penaliza():
    """A task nunca entregue já não está nos concluídos; descontar de novo
    puniria as OUTRAS entregas da pessoa."""
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            {"id": "task-1", "operacional_id": "op-1", "pontos": 6, "coluna_kanban": "concluida"},
            {"id": "task-2", "operacional_id": "op-1", "pontos": 4, "coluna_kanban": "em_andamento"},
        ],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_travamentos=[
            {"task_id": "task-2", "operacional_id": "op-1", "pontos": 4, "dispensado": False, "timestamp": "2026-09-01T00:00:00Z"},
        ],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_pontos_penalizados"] == 0


def test_pergunta_3_fica_guardada_para_autonomia():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "em_andamento"}],
        avaliacoes=[_AVALIACAO_OP1],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["gerente_pergunta3"] == _AVALIACAO_OP1["resposta_3"]


def test_extrato_registra_entrega_concluida_e_bonus_extra():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            {"id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida"},
            {"id": "task-2", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "concluida", "extra": True},
        ],
        task_transicoes=[
            {"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"},
            {"task_id": "task-2", "operacional_id": "op-1", "timestamp": "2026-09-03T00:00:00Z"},
        ],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    tipos = {(e["tipo"], e["task_id"], e["pontos"]) for e in eventos_insert_capture}
    assert ("entrega_concluida", "task-1", 5) in tipos
    assert ("bonus_extra", "task-2", 2) in tipos
    for evento in eventos_insert_capture:
        assert evento["sprint_id"] == "sprint-1"
        assert evento["projeto_id"] == "proj-1"
        assert evento["operacional_id"] == "op-1"


def test_extrato_registra_travamento_como_penalidade_negativa():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_travamentos=[{"task_id": "task-1", "operacional_id": "op-1", "pontos": 8, "dispensado": False, "timestamp": "2026-09-01T00:00:00Z"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    penalidades = [e for e in eventos_insert_capture if e["tipo"] == "travamento_penalidade"]
    assert len(penalidades) == 1
    assert penalidades[0]["pontos"] == -8
    assert penalidades[0]["task_id"] == "task-1"


def test_extrato_travamento_dispensado_nao_gera_evento():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_travamentos=[{"task_id": "task-1", "operacional_id": "op-1", "pontos": 8, "dispensado": True, "timestamp": "2026-09-01T00:00:00Z"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    assert not any(e["tipo"] == "travamento_penalidade" for e in eventos_insert_capture)


def test_extrato_registra_reabertura_sem_pontos():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        task_reaberturas=[{"operacional_id": "op-1"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    reaberturas = [e for e in eventos_insert_capture if e["tipo"] == "reabertura"]
    assert len(reaberturas) == 1
    assert reaberturas[0]["pontos"] == 0


def test_falha_no_insert_do_extrato_nao_derruba_o_fechamento():
    """Finding 2 do review final: pontuacao_eventos é best-effort — se o
    insert do ledger falhar, a pontuação já travada (pontuacao_operacional_sprint)
    tem que ser retornada normalmente, sem propagar a exceção."""
    eventos_insert_capture = []
    insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        eventos_insert_capture=eventos_insert_capture,
        eventos_insert_raises=True,
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert len(resultado) == 1
    assert resultado[0]["operacional_id"] == "op-1"
    assert resultado[0]["entrega_pontos_concluidos"] == 5
    # O insert foi tentado (e capturado antes de estourar) — prova que a
    # tentativa aconteceu, não que ela foi pulada.
    assert eventos_insert_capture


def test_extrato_nao_insere_nada_quando_nao_ha_eventos():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    assert eventos_insert_capture == []


def test_vinculado_sem_task_ganha_linha_zerada():
    """O ponto central da correção do bug de PULL: alguém vinculado ao
    projeto, mas sem nenhuma contribuição na sprint (sem task, sem
    avaliação), ainda assim ganha uma linha em pontuacao_operacional_sprint
    com todos os contadores zerados — pra contar no denominador em vez de
    sumir. Ver
    docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
    vinculado_ativo = {
        "id": "op-ocioso", "nome": "Bruno", "email": None, "project_id": "proj-1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    task_de_outra_pessoa = {
        "id": "task-1", "operacional_id": "op-com-task", "pontos": 5,
        "coluna_kanban": "concluida", "extra": False,
        "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None,
    }
    insert_capture = []
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=[task_de_outra_pessoa],
        operacionais=[vinculado_ativo],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linhas_por_operacional = {r["operacional_id"]: r for r in resultado}
    assert "op-ocioso" in linhas_por_operacional
    linha = linhas_por_operacional["op-ocioso"]
    assert linha["entrega_pontos_alocados"] == 0
    assert linha["entrega_pontos_concluidos"] == 0
    assert linha["bonus_pontos_extra"] == 0
    # A pessoa com task continua presente normalmente.
    assert "op-com-task" in linhas_por_operacional


def test_sprint_sem_nenhuma_task_ainda_cria_linhas_zeradas_pra_vinculados():
    """Antes desta Entrega 2, uma sprint com zero tasks retornava [] direto
    (early return). Agora, se houver vinculados, eles ainda ganham linha
    zerada — só retorna [] se não houver NEM task NEM vinculado."""
    vinculado = {
        "id": "op-1", "nome": "Ana", "email": None, "project_id": "proj-1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=[],
        operacionais=[vinculado],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert len(resultado) == 1
    assert resultado[0]["operacional_id"] == "op-1"
    assert resultado[0]["entrega_pontos_alocados"] == 0


def test_sprint_sem_task_e_sem_vinculado_continua_retornando_vazio():
    client = _mock_client(sprint={"id": "sprint-1", "project_id": "proj-1"}, tasks=[], operacionais=[])
    assert calcular_e_travar_pontuacao(client, "sprint-1") == []


def test_formula_pontos_relativo_usa_piso_e_teto_do_projeto():
    """3 vinculados: A concluiu 6 pontos, B concluiu 2, C não concluiu nada.
    denominador_bruto = (6+2+0)/3 = 2.667; piso=1 não altera (2.667 > 1);
    teto=1.5.
    A: bruta = 6/2.667=2.25 -> min(2.25,1.5)=1.5 -> nota=100
    B: bruta = 2/2.667=0.75 -> min(0.75,1.5)=0.75 -> nota=50.0
    C: bruta = 0/2.667=0 -> nota=0
    """
    operacionais = [
        {"id": "op-a", "nome": "A", "email": "a@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None},
        {"id": "op-b", "nome": "B", "email": "b@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None},
        {"id": "op-c", "nome": "C", "email": "c@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None},
    ]
    tasks = [
        {"id": "t1", "operacional_id": "op-a", "pontos": 6, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
        {"id": "t2", "operacional_id": "op-b", "pontos": 2, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
    ]
    capture = []
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=tasks,
        operacionais=operacionais,
        projeto={"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pull_piso_pontos": 1, "pull_teto": 1.5},
        insert_capture=capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    por_op = {r["operacional_id"]: r for r in resultado}
    assert por_op["op-a"]["entrega_nota_relativa"] == 100.0
    assert por_op["op-b"]["entrega_nota_relativa"] == 50.0
    assert por_op["op-c"]["entrega_nota_relativa"] == 0.0
    assert por_op["op-a"]["entrega_pontos_pessoa"] == 6
    assert por_op["op-a"]["entrega_denominador"] == round(8 / 3, 2)


def test_formula_pontos_atribuidos_nao_grava_colunas_relativas():
    tasks = [
        {"id": "t1", "operacional_id": "op-a", "pontos": 6, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
    ]
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=tasks,
        operacionais=[{"id": "op-a", "nome": "A", "email": "a@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None}],
        projeto={"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pull_piso_pontos": 1, "pull_teto": 1.5},
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert resultado[0]["entrega_pontos_pessoa"] is None
    assert resultado[0]["entrega_denominador"] is None
    assert resultado[0]["entrega_nota_relativa"] is None


def test_golden_regression_atribuicao_nao_muda_apos_entrega_3():
    """Mesmo cenário de teste pré-existente do motor de score, sem nenhum
    campo de PONTOS_RELATIVO no projeto — reafirma que a Entrega 3 é
    estritamente aditiva para projetos em ATRIBUICAO."""
    tasks = [
        {"id": "t1", "operacional_id": "op-a", "pontos": 5, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
        {"id": "t2", "operacional_id": "op-a", "pontos": 3, "coluna_kanban": "planejado", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
    ]
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=tasks,
        operacionais=[{"id": "op-a", "nome": "A", "email": "a@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None}],
        projeto={"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pull_piso_pontos": 1, "pull_teto": 1.5},
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = resultado[0]
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 8
    assert linha["entrega_modo"] == "PONTOS_ATRIBUIDOS"
    assert linha["entrega_pontos_pessoa"] is None
    assert linha["entrega_denominador"] is None
    assert linha["entrega_nota_relativa"] is None
