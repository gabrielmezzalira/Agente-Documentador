"""Persistência do aprendizado (spec A2 §4)."""
from fastapi.testclient import TestClient

from services import classificador_aprendizado as ap
from tests.fake_supabase import FakeClient


def _fake():
    return FakeClient({
        "tasks": [{"id": "t1", "pontos": 3, "coluna_kanban": "concluida", "operacional_id": "ana",
                   "pull_em": None, "entrou_em_andamento_em": None, "created_at": "2026-10-01T00:00:00+00:00"}],
        "task_transicoes": [
            {"task_id": "t1", "campo": "coluna_kanban", "de": "planejado", "para": "em_andamento",
             "timestamp": "2026-10-01T08:00:00+00:00", "bloqueio_tipo": None},
            {"task_id": "t1", "campo": "coluna_kanban", "de": "em_andamento", "para": "concluida",
             "timestamp": "2026-10-01T12:00:00+00:00", "bloqueio_tipo": None},
        ],
        "task_classificacoes": [{"id": "c1", "task_id": "t1", "criado_em": "2026-10-01T00:00:00+00:00",
                                  "nivel_final": 3, "criado_por": "g1", "opiniao_gerente": 3,
                                  "sinais": {"partes": {"nota": 1, "evidencia": "x"}}}],
        "task_aprendizado": [], "classificador_parametros": [], "classificador_parametros_hist": [],
    })


def test_registrar_conclusao_grava_exemplo_rotulo_e_parametros():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    ex = fake.tables["task_aprendizado"][0]
    assert (ex["nivel_sugerido"], ex["tempo_limpo_s"], ex["nivel_real"]) == (3, 4 * 3600, 3)
    assert ex["gerente_id"] == "g1" and ex["sinais"] == {"partes": 1}
    params = {(p["tipo"], p["chave"]): p["valor"] for p in fake.tables["classificador_parametros"]}
    assert params[("media_nivel", "3")] == 4 * 3600
    assert len(fake.tables["classificador_parametros_hist"]) >= 1
    assert ap.parametros_vigentes(fake)[("media_nivel", "3")] == 4 * 3600


def test_recalcular_nao_duplica_historico_sem_mudanca():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    n = len(fake.tables["classificador_parametros_hist"])
    ap.recalcular_tudo(fake)
    assert len(fake.tables["classificador_parametros_hist"]) == n


def test_registrar_conclusao_duas_vezes_mantem_um_exemplo():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    ap.registrar_conclusao(fake, "t1")
    assert len(fake.tables["task_aprendizado"]) == 1


def test_sem_classificacao_usa_pontos_convertidos():
    fake = _fake()
    fake.tables["task_classificacoes"] = []
    fake.tables["tasks"][0]["pontos"] = 8
    ap.registrar_conclusao(fake, "t1")
    assert fake.tables["task_aprendizado"][0]["nivel_sugerido"] == 5


def test_sem_inicio_grava_exemplo_com_tempo_nulo():
    fake = _fake()
    fake.tables["task_transicoes"] = fake.tables["task_transicoes"][1:]
    ap.registrar_conclusao(fake, "t1")
    ex = fake.tables["task_aprendizado"][0]
    assert ex["tempo_limpo_s"] is None and ex["nivel_real"] == 3


def test_exclusao_e_reinclusao_recalculam():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    ap.definir_exclusao(fake, "t1", True, "esquecida em andamento", "lider-1")
    assert fake.tables["task_aprendizado"][0]["excluida"] is True
    media = next(p for p in fake.tables["classificador_parametros"]
                 if p["tipo"] == "media_nivel" and p["chave"] == "3")
    assert media["n_amostras"] == 0 and media["valor"] == 4 * 3600
    ap.definir_exclusao(fake, "t1", False, None, "lider-1")
    assert fake.tables["task_aprendizado"][0]["excluida"] is False


def test_opiniao_operacional_grava():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    ap.registrar_opiniao_operacional(fake, "t1", 5)
    assert fake.tables["task_aprendizado"][0]["opiniao_operacional"] == 5


def _rota(monkeypatch, autenticar, registrador):
    import routers.tasks as tasks_router
    from main import app
    from tests.test_regua import _client_task_concluida_legada

    fake = _client_task_concluida_legada()
    fake.tables["tasks"][0].update({"coluna_kanban": "em_andamento", "pontos": 3})
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    monkeypatch.setattr(tasks_router, "check_wip", lambda *a, **k: (True, None))
    monkeypatch.setattr(tasks_router, "on_task_transition", lambda *a, **k: False)
    monkeypatch.setattr(tasks_router, "rotear_evento_pos_fechamento", lambda *a, **k: None)
    monkeypatch.setattr(tasks_router, "registrar_conclusao", registrador)
    return autenticar(TestClient(app))


def test_patch_concluida_chama_registrar_conclusao(monkeypatch, autenticar):
    chamadas = []
    tc = _rota(monkeypatch, autenticar, lambda client, task_id: chamadas.append(task_id))
    resp = tc.patch("/tasks/t1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200, resp.text
    assert chamadas == ["t1"]


def test_falha_no_aprendizado_nao_quebra_o_patch(monkeypatch, autenticar):
    def explode(client, task_id):
        raise RuntimeError("boom")

    tc = _rota(monkeypatch, autenticar, explode)
    resp = tc.patch("/tasks/t1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200, resp.text
