"""Bloco C do Painel (métricas de fluxo): funcionalidade concluída sem a
transição de início ainda conta no total e no throughput."""
from routers.painel import calcular_bloco_c


def test_concluida_sem_transicao_de_inicio_conta_no_throughput():
    funcs = [
        {"id": "f1", "status": "concluida", "created_at": "2026-11-19T10:00:00+00:00"},
        {"id": "f2", "status": "em_andamento", "created_at": "2026-11-19T10:00:00+00:00"},
    ]
    transicoes = [{"funcionalidade_id": "f1", "campo": "status", "para": "concluida", "timestamp": "2026-11-19T12:00:00+00:00"}]

    bloco = calcular_bloco_c(funcs, transicoes)

    assert bloco["total_concluidas"] == 1
    assert bloco["throughput_por_semana"] > 0
    assert bloco["cycle_time_p50_dias"] is None
    assert bloco["wip"] == 1


def test_cycle_time_usa_so_quem_tem_intervalo_completo():
    funcs = [
        {"id": "f1", "status": "concluida", "created_at": "2026-11-01T00:00:00+00:00"},
        {"id": "f2", "status": "concluida", "created_at": "2026-11-01T00:00:00+00:00"},
    ]
    transicoes = [
        {"funcionalidade_id": "f1", "campo": "status", "para": "em_andamento", "timestamp": "2026-11-02T00:00:00+00:00"},
        {"funcionalidade_id": "f1", "campo": "status", "para": "concluida", "timestamp": "2026-11-04T00:00:00+00:00"},
        {"funcionalidade_id": "f2", "campo": "status", "para": "concluida", "timestamp": "2026-11-05T00:00:00+00:00"},
    ]

    bloco = calcular_bloco_c(funcs, transicoes)

    assert bloco["total_concluidas"] == 2
    assert bloco["cycle_time_p50_dias"] == 2.0
