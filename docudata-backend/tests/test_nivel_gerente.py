"""Nível escolhido pelo gerente (spec PTA §3)."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import services.classificador_ciclo as ciclo
from tests.fake_supabase import FakeClient

pytestmark = pytest.mark.classificador_real


def _fake():
    return FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": False},
                    {"id": "s2", "project_id": "p1", "numero": 2, "iniciada": True}],
        "operacionais": [{"id": "op1", "project_id": "p1", "email": "pessoa@citi.org.br"}],
        "funcionalidades": [{"id": "fn-1", "project_id": "p1", "status": "nao_iniciada"}],
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


# --- serviço ---

def test_resultado_manual_tem_o_formato_de_classificacao():
    r = ciclo.resultado_manual(5)
    assert r["status"] == "manual" and r["nivel_final"] == 5
    assert r["faltando"] == [] and r["vetor"] is None and r["ajuste_tempo"] == 0
    assert r["nivel_geral"] is None and r["opiniao_gerente"] is None


def test_gravar_classificacao_manual_nao_registra_modelo():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    ciclo.gravar_classificacao(fake, "t1", ciclo.resultado_manual(3), tipo="criacao", criado_por="g1", texto="")
    linha = fake.tables["task_classificacoes"][0]
    assert linha["status"] == "manual" and linha["modelo"] is None and linha["nivel_final"] == 3
    assert linha["criado_por"] == "g1" and linha["versao_regua"]
    assert fake.tables["tasks"][0]["pontos"] == 3


def test_definir_nivel_gerente_grava_reclassificacao_manual_e_atualiza_pontos():
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("em_revisao", 2))
    ciclo.definir_nivel_gerente(fake, "t1", 5, "g1")
    novas = [c for c in fake.tables["task_classificacoes"] if c["tipo"] == "reclassificacao"]
    assert len(novas) == 1 and novas[0]["status"] == "manual" and novas[0]["criado_por"] == "g1"
    assert fake.tables["tasks"][0]["pontos"] == 5
    assert fake.tables["tasks"][0]["nivel_travado_em"] is None  # planejado: segue destravada


def test_definir_nivel_gerente_em_andamento_trava_em_seguida():
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento"))
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    ciclo.definir_nivel_gerente(fake, "t1", 3, "g1")
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


def test_definir_nivel_gerente_travada_pela_sprint_mas_em_planejado_permite():
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2, nivel_travado_em="2026-01-02T00:00:00+00:00"))
    ciclo.definir_nivel_gerente(fake, "t1", 3, "g1")
    assert fake.tables["tasks"][0]["pontos"] == 3
    assert fake.tables["tasks"][0]["nivel_travado_em"] == "2026-01-02T00:00:00+00:00"


def test_definir_nivel_gerente_travada_409():
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento", nivel_travado_em="2026-01-02T00:00:00+00:00"))
    with pytest.raises(HTTPException) as exc:
        ciclo.definir_nivel_gerente(fake, "t1", 3, "g1")
    assert exc.value.status_code == 409 and exc.value.detail == "Nível já travado: a task começou"
    assert fake.tables["task_classificacoes"] == []


def test_definir_nivel_gerente_concluida_409_e_inexistente_404():
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida"))
    with pytest.raises(HTTPException) as exc:
        ciclo.definir_nivel_gerente(fake, "t1", 3, "g1")
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc2:
        ciclo.definir_nivel_gerente(fake, "nao-existe", 3, "g1")
    assert exc2.value.status_code == 404


def test_travar_nivel_trava_task_manual():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    ciclo.travar_nivel(fake, ["t1"])
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


async def test_reclassificar_task_manual_409():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    with pytest.raises(HTTPException) as exc:
        await ciclo.reclassificar(fake, "t1", "lider-1")
    assert exc.value.status_code == 409
    assert len(fake.tables["task_classificacoes"]) == 1


def test_resolver_revisao_nao_se_aplica_a_task_manual():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    with pytest.raises(HTTPException) as exc:
        ciclo.resolver_revisao(fake, "t1", 2, "motivo", "lider-1")
    assert exc.value.status_code == 409


# --- criação ---

BODY = {"project_id": "p1", "titulo": "Nova", "descricao": "algo claro", "funcionalidade_id": "fn-1"}


@pytest.fixture
def modelo_proibido(monkeypatch):
    async def explode(**kw):
        raise AssertionError("o classificador não pode ser chamado quando o gerente define o nível")

    monkeypatch.setattr(ciclo, "classificar", explode)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")


@pytest.mark.parametrize("cargo", ["gerente", "lider", "owner"])
def test_criar_com_nivel_gerente_nao_chama_ia(monkeypatch, autenticar, modelo_proibido, cargo):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake, cargo).post("/tasks", json={**BODY, "nivel_gerente": 5})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["pontos"] == 5 and body["classificacao_status"] == "manual"
    linhas = fake.tables["task_classificacoes"]
    assert len(linhas) == 1 and linhas[0]["tipo"] == "criacao" and linhas[0]["status"] == "manual"
    assert linhas[0]["nivel_final"] == 5 and linhas[0]["modelo"] is None
    assert fake.tables["tasks"][0]["pontos"] == 5


def test_criar_com_nivel_gerente_ignora_opiniao(monkeypatch, autenticar, modelo_proibido):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json={**BODY, "nivel_gerente": 3, "opiniao_nivel": 5})
    assert resp.status_code == 201 and resp.json()["pontos"] == 3
    assert fake.tables["task_classificacoes"][0]["opiniao_gerente"] is None


def test_criar_com_nivel_gerente_em_sprint_iniciada_trava(monkeypatch, autenticar, modelo_proibido):
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks", json={**BODY, "nivel_gerente": 2, "sprint_id": "s2"})
    assert resp.status_code == 201 and resp.json()["nivel_travado_em"] is not None


def test_criar_com_nivel_gerente_operacional_403(monkeypatch, autenticar, modelo_proibido):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake, "operacional").post("/tasks", json={**BODY, "nivel_gerente": 3})
    assert resp.status_code == 403
    assert fake.tables["tasks"] == []


@pytest.mark.parametrize("invalido", [0, 4, 8, -1])
def test_criar_com_nivel_gerente_fora_da_regua_422(monkeypatch, autenticar, modelo_proibido, invalido):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json={**BODY, "nivel_gerente": invalido})
    assert resp.status_code == 422 and fake.tables["tasks"] == []


def test_criar_sem_nivel_gerente_segue_o_fluxo_da_ia(monkeypatch, autenticar):
    chamadas = []

    async def fake_cls(**kw):
        chamadas.append(kw)
        return {"status": "aplicada", "faltando": [], "sinais": {}, "nivel_sinais": 3, "parecidas": [],
                "nivel_parecidas": None, "nivel_geral": 3, "justificativa_geral": "ia", "nivel_combinado": 3,
                "ajuste_tempo": 0, "nivel_final": 3, "motivo_revisao": None, "parametros": {}, "vetor": None}

    monkeypatch.setattr(ciclo, "classificar", fake_cls)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks", json=BODY)
    assert resp.status_code == 201 and resp.json()["classificacao_status"] == "aplicada" and len(chamadas) == 1


# --- endpoint /nivel-gerente ---

@pytest.mark.parametrize("cargo", ["gerente", "lider", "owner"])
def test_nivel_gerente_troca_o_nivel(monkeypatch, autenticar, cargo):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    resp = _tc(monkeypatch, autenticar, fake, cargo).post("/tasks/t1/nivel-gerente", json={"nivel": 5})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pontos"] == 5 and body["classificacao_status"] == "manual"
    assert fake.tables["tasks"][0]["pontos"] == 5
    ultima = [c for c in fake.tables["task_classificacoes"] if c["tipo"] == "reclassificacao"]
    assert len(ultima) == 1 and ultima[0]["status"] == "manual" and ultima[0]["criado_por"] == "pessoa-teste"


def test_nivel_gerente_operacional_403(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    resp = _tc(monkeypatch, autenticar, fake, "operacional").post("/tasks/t1/nivel-gerente", json={"nivel": 3})
    assert resp.status_code == 403
    assert fake.tables["task_classificacoes"] == []


def test_nivel_gerente_task_travada_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento", nivel_travado_em="2026-01-02T00:00:00+00:00"))
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks/t1/nivel-gerente", json={"nivel": 3})
    assert resp.status_code == 409 and resp.json()["detail"] == "Nível já travado: a task começou"
    assert fake.tables["tasks"][0]["pontos"] == 2


def test_nivel_gerente_task_inexistente_404(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks/nao-existe/nivel-gerente", json={"nivel": 3})
    assert resp.status_code == 404


@pytest.mark.parametrize("invalido", [0, 4, 7])
def test_nivel_gerente_fora_da_regua_422(monkeypatch, autenticar, invalido):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks/t1/nivel-gerente", json={"nivel": invalido})
    assert resp.status_code == 422 and fake.tables["task_classificacoes"] == []


def test_task_manual_comeca_e_trava(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


@pytest.mark.parametrize("campo,valor", [("titulo", "Outro título"), ("descricao", "outra"),
                                         ("checklist", [{"texto": "novo", "done": False}])])
def test_editar_texto_de_task_manual_nao_manda_para_revisao(monkeypatch, autenticar, campo, valor):
    fake = _fake()
    fake.tables["tasks"].append(_task(checklist=[{"texto": "a", "done": False}]))
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={campo: valor})
    assert resp.status_code == 200, resp.text
    assert fake.tables["task_classificacoes"][0]["status"] == "manual"
    assert len(fake.tables["task_classificacoes"]) == 1  # sem reclassificação
    assert fake.tables["tasks"][0]["pontos"] == 2  # PATCH não mexe no nível


def test_reclassificar_task_manual_pela_rota_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    resp = _tc(monkeypatch, autenticar, fake, "lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 409


def test_get_task_traz_status_manual(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    assert _tc(monkeypatch, autenticar, fake).get("/tasks/t1").json()["classificacao_status"] == "manual"


def test_task_manual_concluida_entra_no_aprendizado_fora_do_pta():
    import services.classificador_aprendizado as ap
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida", pontos=3, operacional_id="op1"))
    fake.tables["task_classificacoes"].append(_clas("manual", 3, opiniao_gerente=None))
    fake.tables["task_transicoes"] = [
        {"task_id": "t1", "campo": "coluna_kanban", "de": "planejado", "para": "em_andamento",
         "timestamp": "2026-10-01T08:00:00+00:00", "bloqueio_tipo": None},
        {"task_id": "t1", "campo": "coluna_kanban", "de": "em_andamento", "para": "concluida",
         "timestamp": "2026-10-01T12:00:00+00:00", "bloqueio_tipo": None},
    ]
    fake.tables["classificador_parametros"] = []
    fake.tables["classificador_parametros_hist"] = []
    ap.registrar_conclusao(fake, "t1")
    ex = fake.tables["task_aprendizado"][0]
    assert ex["nivel_sugerido"] == 3
