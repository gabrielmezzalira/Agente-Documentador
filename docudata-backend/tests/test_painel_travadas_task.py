from datetime import datetime, timedelta, timezone

from routers.painel import calcular_bloco_b, ultimo_movimento_das_tasks
from tests.fake_supabase import FakeClient

AGORA = datetime.now(timezone.utc)


def _iso(dias):
    return (AGORA - timedelta(days=dias)).isoformat()


def _func(fid="f1"):
    return {"id": fid, "titulo": "Login", "status": "em_andamento", "created_at": _iso(40)}


def _trans_status(dias, fid="f1"):
    return {"funcionalidade_id": fid, "campo": "status", "timestamp": _iso(dias)}


def test_task_movida_ontem_nao_trava():
    b = calcular_bloco_b([_func()], [_trans_status(20)], None, {"f1": AGORA - timedelta(days=1)})
    assert b["travadas"] == []


def test_sem_movimento_de_task_ha_10_dias_trava():
    b = calcular_bloco_b([_func()], [_trans_status(20)], None, {"f1": AGORA - timedelta(days=10)})
    assert [t["id"] for t in b["travadas"]] == ["f1"]
    assert b["travadas"][0]["dias"] == 10


def test_sem_transicao_de_task_cai_na_ultima_transicao_de_status():
    b = calcular_bloco_b([_func()], [_trans_status(10)], None, {})
    assert b["travadas"][0]["dias"] == 10
    assert calcular_bloco_b([_func()], [_trans_status(2)], None)["travadas"] == []


def test_ultimo_movimento_das_tasks_em_lote():
    c = FakeClient({
        "tasks": [
            {"id": "t1", "funcionalidade_id": "f1"},
            {"id": "t2", "funcionalidade_id": "f1"},
            {"id": "t3", "funcionalidade_id": "f2"},
        ],
        "task_transicoes": [
            {"id": "a", "task_id": "t1", "timestamp": _iso(9)},
            {"id": "b", "task_id": "t2", "timestamp": _iso(1)},
            {"id": "c", "task_id": "t3", "timestamp": _iso(15)},
        ],
    })
    out = ultimo_movimento_das_tasks(c, ["f1", "f2", "f3"])
    assert set(out) == {"f1", "f2"}
    assert (AGORA - out["f1"]).days == 1
    assert (AGORA - out["f2"]).days == 15
