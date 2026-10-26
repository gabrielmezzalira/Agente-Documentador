"""Tempo limpo de uma task concluída (spec A2 §4.1)."""
from services.classificador_tempo import tempo_limpo

T = "2026-10-0{}T{:02d}:00:00+00:00"


def _t(dia, hora):
    return T.format(dia, hora)


def _col(de, para, ts):
    return {"campo": "coluna_kanban", "de": de, "para": para, "timestamp": ts, "bloqueio_tipo": None}


def _bloq(para, ts, tipo=None):
    return {"campo": "bloqueado", "de": None, "para": str(para), "timestamp": ts, "bloqueio_tipo": tipo}


TASK = {"pull_em": None, "entrou_em_andamento_em": None, "created_at": _t(1, 0)}


def test_simples():
    r = tempo_limpo([_col("planejado", "em_andamento", _t(1, 10)), _col("em_andamento", "concluida", _t(1, 14))], TASK)
    assert r == {"tempo_bruto_s": 4 * 3600, "tempo_limpo_s": 4 * 3600, "reaberta": False, "concluida_em": _t(1, 14)}


def test_desconta_pendente_aprovacao_e_bloqueio_cliente_mas_nao_interno():
    trans = [
        _col("planejado", "em_andamento", _t(1, 8)),
        _bloq(True, _t(1, 9), "cliente"), _bloq(False, _t(1, 11)),      # -2h
        _bloq(True, _t(1, 12), "interno"), _bloq(False, _t(1, 13)),     # conta
        _col("em_andamento", "pendente_aprovacao", _t(1, 14)),
        _col("pendente_aprovacao", "concluida", _t(1, 17)),             # -3h
    ]
    r = tempo_limpo(trans, TASK)
    assert r["tempo_bruto_s"] == 9 * 3600
    assert r["tempo_limpo_s"] == 4 * 3600


def test_bloqueio_antigo_sem_tipo_conta_como_interno():
    trans = [_col("planejado", "em_andamento", _t(1, 8)), _bloq(True, _t(1, 9)), _bloq(False, _t(1, 11)),
             _col("em_andamento", "concluida", _t(1, 12))]
    assert tempo_limpo(trans, TASK)["tempo_limpo_s"] == 4 * 3600


def test_reaberta_soma_trechos_e_marca():
    trans = [
        _col("planejado", "em_andamento", _t(1, 8)), _col("em_andamento", "concluida", _t(1, 10)),
        _col("concluida", "em_andamento", _t(2, 8)), _col("em_andamento", "concluida", _t(2, 9)),
    ]
    r = tempo_limpo(trans, TASK)
    assert r["reaberta"] is True
    assert r["concluida_em"] == _t(2, 9)
    assert r["tempo_bruto_s"] == 25 * 3600
    assert r["tempo_limpo_s"] == 3 * 3600   # o tempo parado em concluida (1·10 → 2·08) não é trabalho


def test_sem_transicao_de_inicio_usa_pull_em():
    task = {**TASK, "pull_em": _t(1, 6)}
    r = tempo_limpo([_col("em_andamento", "concluida", _t(1, 9))], task)
    assert r["tempo_limpo_s"] == 3 * 3600


def test_nao_concluida_devolve_none():
    assert tempo_limpo([_col("planejado", "em_andamento", _t(1, 8))], TASK) is None


# ── PATCH grava o tipo do bloqueio na transição ──────────────────────────────

from tests.test_bloqueio_manual import _BASE_TASK, _make_mock_client, _patch_and_client  # noqa: E402


def _espiar_transicoes(mock_sb):
    gravadas = []
    original = mock_sb.table.side_effect

    def table(nome):
        tbl = original(nome)
        if nome == "task_transicoes":
            insert_orig = tbl.insert.side_effect

            def insert(payload):
                gravadas.append(dict(payload))
                return insert_orig(payload)

            tbl.insert.side_effect = insert
        return tbl

    mock_sb.table.side_effect = table
    return gravadas


def test_patch_bloqueio_de_cliente_grava_tipo_na_transicao(monkeypatch):
    task = dict(_BASE_TASK, bloqueado=False, bloqueado_manual=False)
    mock_sb, _ = _make_mock_client(task)
    gravadas = _espiar_transicoes(mock_sb)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado": True, "bloqueado_manual": True, "bloqueio_tipo": "cliente"})

    assert resp.status_code == 200
    bloqueios = [g for g in gravadas if g["campo"] == "bloqueado"]
    assert bloqueios[-1]["para"] == "True"
    assert bloqueios[-1]["bloqueio_tipo"] == "cliente"


def test_patch_desbloqueio_grava_tipo_que_a_task_tinha(monkeypatch):
    task = dict(_BASE_TASK, bloqueado=True, bloqueado_manual=True, bloqueio_tipo="cliente")
    mock_sb, _ = _make_mock_client(task)
    gravadas = _espiar_transicoes(mock_sb)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado": False, "bloqueado_manual": False})

    assert resp.status_code == 200
    bloqueios = [g for g in gravadas if g["campo"] == "bloqueado"]
    assert bloqueios[-1]["para"] == "False"
    assert bloqueios[-1]["bloqueio_tipo"] == "cliente"
