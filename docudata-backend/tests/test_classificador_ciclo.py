"""Ciclo de vida do nível da task (spec A2 §5)."""
import pytest
from fastapi.testclient import TestClient

import services.classificador_ciclo as ciclo
from tests.fake_supabase import FakeClient

pytestmark = pytest.mark.classificador_real


def _resultado(nivel=3, status="aplicada", faltando=None):
    return {"status": status, "faltando": faltando or [], "sinais": {}, "nivel_sinais": nivel, "parecidas": [],
            "nivel_parecidas": None, "nivel_geral": nivel, "justificativa_geral": "porque sim",
            "nivel_combinado": nivel, "ajuste_tempo": 0, "nivel_final": nivel, "motivo_revisao": None,
            "parametros": {}, "vetor": [0.1, 0.2]}


@pytest.fixture
def classificar_ok(monkeypatch):
    async def fake(**kw):
        return _resultado()

    monkeypatch.setattr(ciclo, "classificar", fake)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    monkeypatch.setattr(ciclo, "salvar_embedding", lambda *a, **k: None)


def _fake(**tasks_extra):
    return FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": False},
                    {"id": "s2", "project_id": "p1", "numero": 2, "iniciada": True}],
        "operacionais": [{"id": "op1", "project_id": "p1", "email": "pessoa@citi.org.br"}],
        "tasks": [], "task_classificacoes": [], "task_aprendizado": [],
    }, defaults={"tasks": {"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00",
                           "updated_at": "2026-01-01T00:00:00+00:00"}})


def _task(**kw):
    base = {"id": "t1", "project_id": "p1", "titulo": "Login", "descricao": "d", "checklist": [],
            "pontos": 2, "coluna_kanban": "planejado", "ordem": 0, "bloqueado": False,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
            "nivel_travado_em": None, "sprint_id": "s1"}
    base.update(kw)
    return base


def _clas(status="aplicada", nivel=3, task_id="t1", criado_em="2026-01-01T00:00:00+00:00", **kw):
    return {"id": f"c-{status}-{criado_em}", "task_id": task_id, "tipo": "criacao", "criado_por": "pessoa-teste",
            "criado_em": criado_em, "status": status, "nivel_final": nivel, **kw}


def _tc(monkeypatch, autenticar, fake, cargo="gerente"):
    import routers.tasks as tasks_router
    from main import app
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)
    return autenticar(TestClient(app), cargo)


BODY = {"project_id": "p1", "titulo": "Nova", "descricao": "algo claro"}


def test_criar_com_classificacao_aplicada(monkeypatch, autenticar, classificar_ok):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json={**BODY, "pontos": 5})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["pontos"] == 3 and body["classificacao_status"] == "aplicada"
    assert body["justificativa_nivel"] == "porque sim"
    assert fake.tables["tasks"][0]["pontos"] == 3
    linhas = fake.tables["task_classificacoes"]
    assert len(linhas) == 1 and linhas[0]["tipo"] == "criacao" and linhas[0]["criado_por"] == "pessoa-teste"
    assert linhas[0]["nivel_final"] == 3 and "vetor" not in linhas[0] and "faltando" not in linhas[0]


def test_criar_com_faltando_devolve_422_sem_criar(monkeypatch, autenticar):
    async def fake_cls(**kw):
        return _resultado(status="faltando", faltando=["descricao"])

    monkeypatch.setattr(ciclo, "classificar", fake_cls)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json=BODY)
    assert resp.status_code == 422
    assert resp.json()["detail"] == {"faltando": ["descricao"]}
    assert fake.tables["tasks"] == [] and fake.tables["task_classificacoes"] == []


@pytest.mark.parametrize("opiniao,esperado", [(None, 2), (5, 5)])
def test_criar_com_modelo_falhando_fica_provisoria(monkeypatch, autenticar, opiniao, esperado):
    async def quebra(**kw):
        raise RuntimeError("segredo-do-modelo")

    monkeypatch.setattr(ciclo, "classificar", quebra)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json={**BODY, "opiniao_nivel": opiniao})
    assert resp.status_code == 201, resp.text
    assert resp.json()["pontos"] == esperado and resp.json()["classificacao_status"] == "provisoria"
    assert fake.tables["task_classificacoes"][0]["status"] == "provisoria"


def test_criar_sem_chave_fica_provisoria(monkeypatch, autenticar):
    from services.gemini_key import GeminiApiKeyNotConfigured

    def sem_chave():
        raise GeminiApiKeyNotConfigured()

    monkeypatch.setattr(ciclo, "get_gemini_api_key", sem_chave)
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks", json=BODY)
    assert resp.status_code == 201 and resp.json()["classificacao_status"] == "provisoria"


def test_criar_em_sprint_iniciada_trava(monkeypatch, autenticar, classificar_ok):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json={**BODY, "sprint_id": "s2"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["nivel_travado_em"] is not None


def test_criar_provisoria_em_sprint_iniciada_nao_trava(monkeypatch, autenticar):
    async def quebra(**kw):
        raise RuntimeError("x")

    monkeypatch.setattr(ciclo, "classificar", quebra)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks", json={**BODY, "sprint_id": "s2"})
    assert resp.status_code == 201 and resp.json()["nivel_travado_em"] is None


async def test_reclassificar_provisorias_troca_o_nivel(monkeypatch, classificar_ok):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)
    await ciclo.reclassificar_provisorias()
    assert fake.tables["tasks"][0]["pontos"] == 3
    novas = [c for c in fake.tables["task_classificacoes"] if c["tipo"] == "reclassificacao"]
    assert len(novas) == 1 and novas[0]["status"] == "aplicada"


async def test_reclassificar_provisorias_mantem_se_modelo_segue_fora(monkeypatch):
    async def quebra(**kw):
        raise RuntimeError("x")

    monkeypatch.setattr(ciclo, "classificar", quebra)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)
    await ciclo.reclassificar_provisorias()
    assert fake.tables["tasks"][0]["pontos"] == 2 and len(fake.tables["task_classificacoes"]) == 1


def test_travar_nivel_nao_trava_provisoria_e_trava_aplicada():
    fake = _fake()
    fake.tables["tasks"] += [_task(id="t1"), _task(id="t2"), _task(id="t3")]
    fake.tables["task_classificacoes"] += [_clas("provisoria", task_id="t1"), _clas("aplicada", task_id="t2")]
    ciclo.travar_nivel(fake, ["t1", "t2", "t3"])
    travadas = {t["id"]: t["nivel_travado_em"] for t in fake.tables["tasks"]}
    assert travadas["t1"] is None and travadas["t2"] is not None and travadas["t3"] is not None  # t3 = legada


def test_reclassificar_task_travada_409(monkeypatch, autenticar, classificar_ok):
    fake = _fake()
    fake.tables["tasks"].append(_task(nivel_travado_em="2026-01-02T00:00:00+00:00"))
    resp = _tc(monkeypatch, autenticar, fake, cargo="lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 409


def test_reclassificar_gerente_403(monkeypatch, autenticar, classificar_ok):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    assert _tc(monkeypatch, autenticar, fake, cargo="gerente").post("/tasks/t1/reclassificar").status_code == 403


def test_reclassificar_lider_grava_e_atualiza_pontos(monkeypatch, autenticar, classificar_ok):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("em_revisao", 2))
    resp = _tc(monkeypatch, autenticar, fake, cargo="lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 200, resp.text
    assert resp.json()["nivel_final"] == 3 and fake.tables["tasks"][0]["pontos"] == 3
    assert fake.tables["tasks"][0]["nivel_travado_em"] is None  # planejado: segue destravada


def test_reclassificar_em_andamento_trava_em_seguida(monkeypatch, autenticar, classificar_ok):
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento"))
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    resp = _tc(monkeypatch, autenticar, fake, cargo="lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


def test_revisao_nivel_resolve_e_grava_motivo(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("em_revisao", 2))
    resp = _tc(monkeypatch, autenticar, fake, cargo="lider").post(
        "/tasks/t1/revisao-nivel", json={"nivel": 5, "motivo": "mexe em dados de produção"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["pontos"] == 5
    nova = max(fake.tables["task_classificacoes"], key=lambda c: c["criado_em"])
    assert nova["status"] == "resolvida" and nova["tipo"] == "reclassificacao"
    assert nova["nivel_final"] == 5 and nova["motivo_revisao"] == "mexe em dados de produção"
    assert nova["resolvido_por"] == "pessoa-teste" and nova["resolvido_em"]


def test_revisao_nivel_sem_revisao_pendente_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    resp = _tc(monkeypatch, autenticar, fake, cargo="lider").post(
        "/tasks/t1/revisao-nivel", json={"nivel": 5, "motivo": "porque sim"})
    assert resp.status_code == 409


def test_revisao_nivel_valida_regua_e_motivo(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    c = _tc(monkeypatch, autenticar, fake, cargo="lider")
    assert c.post("/tasks/t1/revisao-nivel", json={"nivel": 4, "motivo": "abc"}).status_code == 422
    assert c.post("/tasks/t1/revisao-nivel", json={"nivel": 3, "motivo": "ab"}).status_code == 422


def test_patch_ignora_pontos_do_cliente(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"pontos": 5, "titulo": "Outro"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["pontos"] == 2 and fake.tables["tasks"][0]["titulo"] == "Outro"


def test_patch_para_em_andamento_trava_nivel(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["nivel_travado_em"] is not None
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


def test_patch_reabertura_continua_convertendo_pontos_legados(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=8, coluna_kanban="concluida", sprint_id="s1"))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["pontos"] in (1, 2, 3, 5)
    assert fake.tables["tasks"][0]["pontos_legado"] == 8


def test_iniciar_sprint_trava_tasks_aplicadas():
    from services.sprints import iniciar_sprint_e_ancorar_tasks

    fake = _fake()
    fake.tables["tasks"] += [_task(id="t1"), _task(id="t2")]
    fake.tables["task_classificacoes"] += [_clas("aplicada", task_id="t1"), _clas("provisoria", task_id="t2")]
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    travadas = {t["id"]: t["nivel_travado_em"] for t in fake.tables["tasks"]}
    assert travadas["t1"] is not None and travadas["t2"] is None


def test_puxar_trava_nivel(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["projects"][0]["modo_trabalho"] = "PULL"
    fake.tables["tasks"].append(_task(operacional_id=None))
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    monkeypatch.setattr("routers.tasks.check_wip", lambda *a, **k: (True, ""))
    resp = _tc(monkeypatch, autenticar, fake, cargo="operacional").post("/tasks/t1/puxar")
    assert resp.status_code == 200, resp.text
    assert resp.json()["nivel_travado_em"] is not None


def test_opiniao_nivel_em_task_nao_concluida_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento", operacional_id="op1"))
    resp = _tc(monkeypatch, autenticar, fake, cargo="operacional").post("/tasks/t1/opiniao-nivel", json={"nivel": 3})
    assert resp.status_code == 409


def test_opiniao_nivel_concluida_grava(monkeypatch, autenticar):
    chamadas = []
    monkeypatch.setattr("routers.tasks.registrar_opiniao_operacional", lambda c, t, n: chamadas.append((t, n)))
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida", operacional_id="op1"))
    resp = _tc(monkeypatch, autenticar, fake, cargo="operacional").post("/tasks/t1/opiniao-nivel", json={"nivel": 3})
    assert resp.status_code == 204, resp.text
    assert chamadas == [("t1", 3)]


def test_opiniao_nivel_de_outro_operacional_403(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida", operacional_id="outro"))
    resp = _tc(monkeypatch, autenticar, fake, cargo="operacional").post("/tasks/t1/opiniao-nivel", json={"nivel": 3})
    assert resp.status_code == 403


def test_opiniao_nivel_valida_regua(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida", operacional_id="op1"))
    resp = _tc(monkeypatch, autenticar, fake, cargo="operacional").post("/tasks/t1/opiniao-nivel", json={"nivel": 4})
    assert resp.status_code == 422


def test_recalcular_diario_cria_exemplo_faltante(monkeypatch):
    import services.classificador_aprendizado as ap

    fake = _fake()
    fake.tables["tasks"] += [_task(id="t1", coluna_kanban="concluida"), _task(id="t2", coluna_kanban="concluida")]
    fake.tables["task_aprendizado"].append({"task_id": "t2"})
    criadas, recalc = [], []
    import services.supabase_client as sc
    monkeypatch.setattr(sc, "get_client", lambda: fake)
    monkeypatch.setattr(ap, "registrar_conclusao", lambda c, t: criadas.append(t))
    monkeypatch.setattr(ap, "recalcular_tudo", lambda c: recalc.append(1))
    ap.recalcular_diario()
    assert criadas == ["t1"] and recalc == [1]


# --- rodada de correção 1 ---

def _durante(monkeypatch, fake, acao):
    async def cls(**kw):
        acao()
        return _resultado()

    monkeypatch.setattr(ciclo, "classificar", cls)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    monkeypatch.setattr(ciclo, "salvar_embedding", lambda *a, **k: None)
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)


async def test_job_task_vai_para_em_andamento_durante_a_chamada_e_trava(monkeypatch):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    _durante(monkeypatch, fake, lambda: fake.tables["tasks"][0].update(coluna_kanban="em_andamento"))
    await ciclo.reclassificar_provisorias()
    t = fake.tables["tasks"][0]
    assert t["pontos"] == 3 and t["nivel_travado_em"] is not None
    assert fake.tables["task_classificacoes"][-1]["status"] == "aplicada"


async def test_job_task_travada_durante_a_chamada_nao_grava(monkeypatch):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    _durante(monkeypatch, fake, lambda: fake.tables["tasks"][0].update(nivel_travado_em="2026-01-02T00:00:00+00:00"))
    await ciclo.reclassificar_provisorias()
    assert fake.tables["tasks"][0]["pontos"] == 2 and len(fake.tables["task_classificacoes"]) == 1


async def test_job_outra_classificacao_durante_a_chamada_nao_grava(monkeypatch):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    _durante(monkeypatch, fake, lambda: fake.tables["task_classificacoes"].append(
        _clas("resolvida", 5, criado_em="2026-01-01T00:05:00+00:00")))
    await ciclo.reclassificar_provisorias()
    assert fake.tables["tasks"][0]["pontos"] == 2 and len(fake.tables["task_classificacoes"]) == 2


def test_rota_reclassificar_trava_ou_muda_durante_a_chamada_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("em_revisao", 2))
    _durante(monkeypatch, fake, lambda: fake.tables["tasks"][0].update(nivel_travado_em="2026-01-02T00:00:00+00:00"))
    resp = _tc(monkeypatch, autenticar, fake, cargo="lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 409 and len(fake.tables["task_classificacoes"]) == 1

    fake2 = _fake()
    fake2.tables["tasks"].append(_task())
    fake2.tables["task_classificacoes"].append(_clas("em_revisao", 2))
    _durante(monkeypatch, fake2, lambda: fake2.tables["task_classificacoes"].append(
        _clas("resolvida", 5, criado_em="2026-01-01T00:05:00+00:00")))
    resp = _tc(monkeypatch, autenticar, fake2, cargo="lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 409 and fake2.tables["tasks"][0]["pontos"] == 2


def test_rota_reclassificar_503_e_422(monkeypatch, autenticar):
    async def quebra(**kw):
        raise RuntimeError("x")

    monkeypatch.setattr(ciclo, "classificar", quebra)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    fake = _fake()
    fake.tables["tasks"].append(_task())
    assert _tc(monkeypatch, autenticar, fake, cargo="lider").post("/tasks/t1/reclassificar").status_code == 503

    async def falta(**kw):
        return _resultado(status="faltando", faltando=["descricao"])

    monkeypatch.setattr(ciclo, "classificar", falta)
    resp = _tc(monkeypatch, autenticar, fake, cargo="lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 422 and resp.json()["detail"] == {"faltando": ["descricao"]}


async def test_job_faltando_manda_provisoria_para_revisao(monkeypatch):
    async def falta(**kw):
        return _resultado(status="faltando", faltando=["descricao"])

    monkeypatch.setattr(ciclo, "classificar", falta)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)
    await ciclo.reclassificar_provisorias()
    c = fake.tables["task_classificacoes"][0]
    assert c["status"] == "em_revisao" and c["motivo_revisao"] == "texto insuficiente para classificar"


def test_opiniao_nivel_gerente_ok(monkeypatch, autenticar):
    chamadas = []
    monkeypatch.setattr("routers.tasks.registrar_opiniao_operacional", lambda c, t, n: chamadas.append((t, n)))
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida", operacional_id="op1"))
    resp = _tc(monkeypatch, autenticar, fake, cargo="gerente").post("/tasks/t1/opiniao-nivel", json={"nivel": 2})
    assert resp.status_code == 204 and chamadas == [("t1", 2)]


@pytest.mark.parametrize("campo,valor", [("titulo", "Outro título"), ("descricao", "outra"),
                                         ("checklist", [{"texto": "novo", "done": False}])])
def test_editar_texto_manda_aplicada_para_revisao(monkeypatch, autenticar, campo, valor):
    fake = _fake()
    fake.tables["tasks"].append(_task(checklist=[{"texto": "a", "done": False}]))
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={campo: valor})
    assert resp.status_code == 200, resp.text
    c = fake.tables["task_classificacoes"][0]
    assert c["status"] == "em_revisao" and c["motivo_revisao"] == "texto editado após a classificação"


def test_editar_texto_em_task_travada_ou_so_done_nao_mexe(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(nivel_travado_em="2026-01-02T00:00:00+00:00"))
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    assert _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"titulo": "Novo"}).status_code == 200
    assert fake.tables["task_classificacoes"][0]["status"] == "aplicada"

    fake2 = _fake()
    fake2.tables["tasks"].append(_task(checklist=[{"texto": "a", "done": False}]))
    fake2.tables["task_classificacoes"].append(_clas("resolvida", 2))
    resp = _tc(monkeypatch, autenticar, fake2).patch("/tasks/t1", json={"checklist": [{"texto": "a", "done": True}]})
    assert resp.status_code == 200
    assert fake2.tables["task_classificacoes"][0]["status"] == "resolvida"


@pytest.mark.parametrize("destino", ["pendente_aprovacao", "concluida"])
def test_sair_de_planejado_direto_para_fim_trava(monkeypatch, autenticar, destino):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"coluna_kanban": destino})
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


async def test_job_trava_apos_sucesso_se_task_em_andamento(monkeypatch, classificar_ok):
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento"))
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)
    await ciclo.reclassificar_provisorias()
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None and fake.tables["tasks"][0]["pontos"] == 3
