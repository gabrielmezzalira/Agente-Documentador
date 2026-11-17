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


def test_definir_nivel_gerente_travada_409():
    fake = _fake()
    fake.tables["tasks"].append(_task(nivel_travado_em="2026-01-02T00:00:00+00:00"))
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
