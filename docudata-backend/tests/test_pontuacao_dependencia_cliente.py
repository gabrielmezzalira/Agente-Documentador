"""Fechamento da sprint não pode zerar a Entrega de quem não tinha o que
entregar (dependência do cliente / sprint PULL vazia) — design 2026-09-23."""
from services.pontuacao import calcular_e_travar_pontuacao
from tests.test_pontuacao_fechamento import _mock_client

_SPRINT = {"id": "sprint-1", "project_id": "proj-1"}
_PULL = {"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pull_piso_pontos": 1, "pull_teto": 1.5}


def _op(op_id):
    return {"id": op_id, "nome": op_id, "email": None, "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None}


def _task(tid, op, pontos, coluna="em_andamento", **extra):
    base = {
        "id": tid, "operacional_id": op, "pontos": pontos, "coluna_kanban": coluna, "extra": False,
        "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None,
        "bloqueado_manual": False, "bloqueio_tipo": None,
    }
    base.update(extra)
    return base


def _por_op(resultado):
    return {r["operacional_id"]: r for r in resultado}


def test_atribuicao_task_unica_aguardando_cliente_nao_entra_em_alocados():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 5, bloqueado_manual=True, bloqueio_tipo="cliente")],
        operacionais=[_op("op-a")],
    )
    linha = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]
    assert linha["entrega_pontos_alocados"] == 0
    assert linha["entrega_pontos_concluidos"] == 0


def test_atribuicao_bloqueio_interno_continua_contando_em_alocados():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 5, bloqueado_manual=True, bloqueio_tipo="interno")],
        operacionais=[_op("op-a")],
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_pontos_alocados"] == 5


def test_atribuicao_task_de_cliente_concluida_conta_normal():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 5, coluna="concluida", bloqueado_manual=True, bloqueio_tipo="cliente")],
        task_transicoes=[{"task_id": "t1", "operacional_id": "op-a", "timestamp": "2026-09-02T00:00:00Z"}],
        operacionais=[_op("op-a")],
    )
    linha = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 5


def test_atribuicao_mistura_cliente_e_normal_so_tira_a_de_cliente():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            _task("t1", "op-a", 5, bloqueado_manual=True, bloqueio_tipo="cliente"),
            _task("t2", "op-a", 3),
        ],
        operacionais=[_op("op-a")],
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_pontos_alocados"] == 3


def test_pull_sprint_sem_nenhuma_task_fica_sem_dado_pra_todos():
    client = _mock_client(sprint=_SPRINT, tasks=[], operacionais=[_op("op-a"), _op("op-b")], projeto=_PULL)
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-a"]["entrega_nota_relativa"] is None
    assert por_op["op-b"]["entrega_nota_relativa"] is None
    assert por_op["op-a"]["entrega_denominador"] is None


def test_pull_sprint_so_com_task_extra_fica_sem_dado():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", None, 2, extra=True)],
        operacionais=[_op("op-a")],
        projeto=_PULL,
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_nota_relativa"] is None


def test_pull_backlog_com_task_e_ninguem_puxou_continua_zero():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", None, 3, coluna="planejado")],
        operacionais=[_op("op-a")],
        projeto=_PULL,
    )
    assert _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))["op-a"]["entrega_nota_relativa"] == 0.0


def test_pull_quem_nao_puxou_enquanto_outro_puxou_continua_zero():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 4, coluna="concluida")],
        task_transicoes=[{"task_id": "t1", "operacional_id": "op-a", "timestamp": "2026-09-02T00:00:00Z"}],
        operacionais=[_op("op-a"), _op("op-b")],
        projeto=_PULL,
    )
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-b"]["entrega_nota_relativa"] == 0.0
    assert por_op["op-a"]["entrega_nota_relativa"] == 100.0


def test_pull_quem_so_tinha_task_de_cliente_fica_sem_dado_e_sai_da_media():
    """op-a concluiu 4; op-b só tinha task esperando cliente; op-c não puxou.
    Média sem op-b = (4 + 0) / 2 = 2 -> op-a: 4/2=2 -> teto 1.5 -> 100; op-c: 0."""
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            _task("t1", "op-a", 4, coluna="concluida"),
            _task("t2", "op-b", 3, bloqueado_manual=True, bloqueio_tipo="cliente"),
        ],
        task_transicoes=[{"task_id": "t1", "operacional_id": "op-a", "timestamp": "2026-09-02T00:00:00Z"}],
        operacionais=[_op("op-a"), _op("op-b"), _op("op-c")],
        projeto=_PULL,
    )
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-b"]["entrega_nota_relativa"] is None
    assert por_op["op-a"]["entrega_denominador"] == 2.0
    assert por_op["op-a"]["entrega_nota_relativa"] == 100.0
    assert por_op["op-c"]["entrega_nota_relativa"] == 0.0


def test_pull_so_task_de_cliente_na_sprint_fica_sem_dado_pra_todos():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[_task("t1", "op-a", 3, bloqueado_manual=True, bloqueio_tipo="cliente")],
        operacionais=[_op("op-a"), _op("op-b")],
        projeto=_PULL,
    )
    por_op = _por_op(calcular_e_travar_pontuacao(client, "sprint-1"))
    assert por_op["op-a"]["entrega_nota_relativa"] is None
    assert por_op["op-b"]["entrega_nota_relativa"] is None
