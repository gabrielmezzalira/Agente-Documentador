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


class _Espiao:
    """Conta escritas (insert/update/upsert/delete) por tabela, repassando ao FakeClient."""

    def __init__(self, fake):
        self._fake = fake
        self.tables = fake.tables
        self.escritas: dict[str, int] = {}

    def table(self, name):
        tabela = self._fake.table(name)
        espiao = self

        class _T:
            def __getattr__(self, attr):
                alvo = getattr(tabela, attr)
                if attr in ("insert", "update", "upsert", "delete"):
                    def contado(*a, **k):
                        espiao.escritas[name] = espiao.escritas.get(name, 0) + 1
                        return alvo(*a, **k)
                    return contado
                return alvo

        return _T()


def test_recalcular_sem_mudanca_nao_escreve_em_task_aprendizado():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    esp = _Espiao(fake)
    ap.recalcular_tudo(esp)
    assert esp.escritas.get("task_aprendizado", 0) == 0
    assert esp.escritas.get("classificador_parametros", 0) == 0


def test_so_linhas_com_rotulo_alterado_sao_escritas_e_so_colunas_de_rotulo():
    fake = _fake()
    for i in (2, 3):
        fake.tables["tasks"].append({**fake.tables["tasks"][0], "id": f"t{i}"})
        for t in [x for x in fake.tables["task_transicoes"] if x["task_id"] == "t1"]:
            fake.tables["task_transicoes"].append({**t, "task_id": f"t{i}"})
        ap.registrar_conclusao(fake, f"t{i}")
    ap.registrar_conclusao(fake, "t1")
    por_id = {l["task_id"]: l for l in fake.tables["task_aprendizado"]}
    por_id["t2"]["nivel_real"] = 99  # só t2 fica desatualizada
    por_id["t3"]["excluida"] = True  # mudança "concorrente" que não pode ser revertida
    por_id["t3"]["opiniao_operacional"] = 5
    payloads = []

    class _Capta(_Espiao):
        def table(self, name):
            t = super().table(name)
            if name != "task_aprendizado":
                return t

            class _T:
                def __getattr__(_, attr):
                    alvo = getattr(t, attr)
                    if attr in ("update", "upsert"):
                        def f(payload, *a, **k):
                            payloads.append(payload)
                            return alvo(payload, *a, **k)
                        return f
                    return alvo
            return _T()

    ap.recalcular_tudo(_Capta(fake))
    assert len(payloads) == 1
    assert set(payloads[0]) <= {"ritmo_usado", "tempo_normalizado_s", "nivel_pelo_tempo", "nivel_real",
                                "alerta", "atualizado_em"}
    assert por_id["t2"]["nivel_real"] != 99
    assert por_id["t3"]["excluida"] is True and por_id["t3"]["opiniao_operacional"] == 5


def test_mais_de_100_classificacoes_funciona():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    for i in range(150):
        fake.tables["task_classificacoes"].append({"id": f"x{i}", "task_id": f"y{i}", "nivel_final": 1})
        fake.tables["task_aprendizado"].append({
            "task_id": f"y{i}", "classificacao_id": f"x{i}", "nivel_sugerido": 1, "operacional_id": None,
            "gerente_id": None, "sinais": None, "tempo_limpo_s": None, "excluida": False,
            "opiniao_operacional": None, "concluida_em": f"2026-10-02T00:{i % 60:02d}:00+00:00"})
    tamanhos = []

    class _Q:
        def __init__(self, q):
            self._q = q

        def __getattr__(self, attr):
            alvo = getattr(self._q, attr)
            if attr == "in_":
                def f(col, vals):
                    tamanhos.append(len(vals))
                    return _Q(alvo(col, vals))
                return f
            if attr == "eq":
                return lambda *a, **k: _Q(alvo(*a, **k))
            return alvo

    class _Cli:
        tables = fake.tables

        def table(self, name):
            t = fake.table(name)
            return type("T", (), {"__getattr__": lambda _, a: (lambda *x, **k: _Q(getattr(t, a)(*x, **k)))
                                  if a == "select" else getattr(t, a)})()

    ap.recalcular_tudo(_Cli())
    assert tamanhos and max(tamanhos) <= 100 and sum(tamanhos) >= 151
    assert all(l.get("nivel_real") == 1 for l in fake.tables["task_aprendizado"] if l["task_id"].startswith("y"))


def test_reconclusao_preserva_exclusao_e_opiniao():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    ap.registrar_opiniao_operacional(fake, "t1", 5)
    ap.definir_exclusao(fake, "t1", True, "motivo", "lider-1")
    ap.registrar_conclusao(fake, "t1")
    ex = fake.tables["task_aprendizado"][0]
    assert ex["excluida"] is True and ex["opiniao_operacional"] == 5 and ex["motivo_exclusao"] == "motivo"


def test_parametro_que_muda_grava_historico():
    fake = _fake()
    ap.registrar_conclusao(fake, "t1")
    antes = len([h for h in fake.tables["classificador_parametros_hist"]
                 if (h["tipo"], h["chave"]) == ("media_nivel", "3")])
    fake.tables["task_transicoes"][1]["timestamp"] = "2026-10-01T10:00:00+00:00"  # 2h em vez de 4h
    ap.registrar_conclusao(fake, "t1")
    hist = [h for h in fake.tables["classificador_parametros_hist"]
            if (h["tipo"], h["chave"]) == ("media_nivel", "3")]
    assert len(hist) == antes + 1 and hist[-1]["valor"] == 2 * 3600


def test_aprovar_chama_registrar_conclusao(monkeypatch, autenticar):
    import routers.tasks as tasks_router
    from main import app
    from tests.test_aprovar_task import _TASK_PENDENTE, _mock_client

    mock_sb, _, _ = _mock_client(_TASK_PENDENTE)
    chamadas = []
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
    monkeypatch.setattr(tasks_router, "registrar_conclusao", lambda c, tid: chamadas.append(tid))
    tc = autenticar(TestClient(app), cargo="gerente")
    assert tc.post("/tasks/task-1/aprovar").status_code == 200
    assert chamadas == ["task-1"]
