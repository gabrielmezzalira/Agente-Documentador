"""Rotas de acompanhamento do classificador (só líder/owner)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import routers.classificador as rota
import services.classificador_aprendizado as aprendizado
from services.classificador_estatistica import metricas_acuracia
from tests.fake_supabase import FakeClient

pytestmark = pytest.mark.classificador_real


def _dias(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def _ex(task_id, sug, real, gerente="g1", concluida=None, **kw):
    concluida = concluida or _dias(3)
    base = {"task_id": task_id, "nivel_sugerido": sug, "nivel_real": real, "nivel_pelo_tempo": real,
            "tempo_limpo_s": 3600, "tempo_normalizado_s": 3600.0, "alerta": False, "excluida": False,
            "gerente_id": gerente, "operacional_id": "op1", "opiniao_operacional": None,
            "classificacao_id": None, "concluida_em": concluida, "sinais": None}
    base.update(kw)
    return base


def _fake():
    return FakeClient({
        "task_aprendizado": [
            _ex("t1", 2, 2, classificacao_id="c2", opiniao_operacional=2),
            _ex("t2", 1, 3, alerta=True, tempo_normalizado_s=9000.0),
            _ex("t3", 3, 3, gerente="g2", concluida=_dias(200)),
        ],
        "tasks": [{"id": f"t{i}", "titulo": f"Task {i}", "project_id": "p1"} for i in (1, 2, 3)],
        "projects": [{"id": "p1", "name": "Projeto"}],
        "pessoa": [{"id": "g1", "nome": "Gerente Um"}, {"id": "g2", "nome": "Gerente Dois"}],
        "operacionais": [{"id": "op1", "nome": "Operacional Um"}],
        "classificador_parametros": [
            {"tipo": "media_nivel", "chave": "2", "valor": 3000, "n_amostras": 1},
            {"tipo": "ritmo_pessoa", "chave": "op1", "valor": 1.1, "n_amostras": 3},
            {"tipo": "peso_sinal", "chave": "partes", "valor": 0.4, "n_amostras": 12},
            {"tipo": "vies_gerente", "chave": "g1", "valor": 0.5, "n_amostras": 2},
            {"tipo": "peso_opiniao_gerente", "chave": "g1", "valor": 0.3, "n_amostras": 1},
            {"tipo": "peso_opiniao_operacional", "chave": "op1", "valor": 0.2, "n_amostras": 1},
        ],
        "classificador_parametros_hist": [
            {"tipo": "media_nivel", "chave": "2", "valor": 2500, "n_amostras": 1, "criado_em": "2026-10-19T10:00:00+00:00"},
            {"tipo": "media_nivel", "chave": "2", "valor": 3000, "n_amostras": 1, "criado_em": "2026-10-21T10:00:00+00:00"},
            {"tipo": "peso_sinal", "chave": "partes", "valor": 0.4, "n_amostras": 12, "criado_em": "2026-10-21T11:00:00+00:00"},
            {"tipo": "ritmo_pessoa", "chave": "op1", "valor": 1.1, "n_amostras": 3, "criado_em": "2026-10-21T11:00:00+00:00"},
        ],
        "task_classificacoes": [
            {"id": "c1", "task_id": "t1", "status": "em_revisao", "nivel_final": 2, "criado_em": "2026-10-01T00:00:00+00:00"},
            {"id": "c2", "task_id": "t1", "status": "aplicada", "nivel_final": 2, "opiniao_gerente": 2, "criado_em": "2026-10-02T00:00:00+00:00"},
            {"id": "c3", "task_id": "t2", "status": "em_revisao", "nivel_final": 3, "motivo_revisao": "divergência",
             "criado_em": "2026-10-03T00:00:00+00:00", "parecidas": [{"task_id": "t3", "similaridade": 0.9}]},
            {"id": "c4", "task_id": "t3", "status": "provisoria", "nivel_final": 1, "criado_em": "2026-10-04T00:00:00+00:00"},
        ],
    })


def _tc(monkeypatch, autenticar, cargo="lider"):
    from main import app
    fake = _fake()
    monkeypatch.setattr(rota, "get_client", lambda: fake)
    return autenticar(TestClient(app), cargo), fake


ROTAS = [("get", "/classificador/resumo"), ("get", "/classificador/revisao"),
         ("get", "/classificador/tasks/t2"), ("patch", "/classificador/aprendizado/t2")]


@pytest.mark.parametrize("metodo,url", ROTAS)
def test_gerente_recebe_403(monkeypatch, autenticar, metodo, url):
    tc, _ = _tc(monkeypatch, autenticar, "gerente")
    r = getattr(tc, metodo)(url, **({"json": {"excluida": False}} if metodo == "patch" else {}))
    assert r.status_code == 403


@pytest.mark.parametrize("metodo,url", ROTAS)
def test_lider_acessa(monkeypatch, autenticar, metodo, url):
    tc, _ = _tc(monkeypatch, autenticar)
    monkeypatch.setattr(rota, "definir_exclusao", lambda *a, **k: {"task_id": "t2"})
    r = getattr(tc, metodo)(url, **({"json": {"excluida": False}} if metodo == "patch" else {}))
    assert r.status_code == 200


def test_resumo_acuracia_alerta_e_filtro(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar)
    corpo = tc.get("/classificador/resumo").json()
    esperado = metricas_acuracia([(2, 2), (1, 3), (3, 3)])
    assert corpo["acuracia"]["n"] == 3
    assert corpo["acuracia"]["exata"] == esperado["exata"]
    assert corpo["acuracia"]["erro_medio_degraus"] == esperado["erro_medio_degraus"]
    assert [a["task_id"] for a in corpo["alertas"]] == ["t2"]
    assert corpo["alertas"][0]["operacional"] == "Operacional Um"
    assert corpo["alertas"][0]["projeto"] == "Projeto"
    assert {g["id"] for g in corpo["gerentes"]} == {"g1", "g2"}
    assert corpo["ritmos"] == [{"pessoa_id": "op1", "nome": "Operacional Um", "ritmo": 1.1, "n": 3}]
    # último valor da semana de 2026-10-19
    assert corpo["evolucao_medias"] == [{"semana": "2026-10-19", "nivel": 2, "media_s": 3000.0}]
    nivel2 = next(m for m in corpo["medias"] if m["nivel"] == 2)
    assert nivel2["media_sem_excluidas_s"] == 3000 and nivel2["n"] == 1

    assert corpo["opinioes"]["gerentes"] == [{"pessoa_id": "g1", "nome": "Gerente Um", "peso": 0.3, "acuracia": 1.0, "n": 1}]
    assert corpo["opinioes"]["operacionais"] == [{"pessoa_id": "op1", "nome": "Operacional Um", "peso": 0.2, "acuracia": 1.0, "n": 1}]
    assert corpo["vies_gerentes"] == [{"gerente_id": "g1", "nome": "Gerente Um", "vies": 0.5, "n": 2}]
    assert corpo["pesos_sinais"] == [{"sinal": "partes", "peso": 0.4}]
    assert corpo["evolucao_pesos"] == [{"data": "2026-10-21", "sinal": "partes", "peso": 0.4}]
    por_mes = {m["mes"]: m for m in corpo["evolucao_acuracia"]}
    assert por_mes[_dias(3)[:7]]["n"] == 2
    assert por_mes[_dias(200)[:7]]["mais_menos_um"] == 1.0
    assert sum(m["n"] for m in corpo["evolucao_acuracia"]) == 3

    filtrado = tc.get("/classificador/resumo?gerente_id=g1").json()
    assert filtrado["acuracia"]["n"] == 2
    assert tc.get("/classificador/resumo?periodo=30").json()["acuracia"]["n"] == 2
    assert tc.get("/classificador/resumo?periodo=7").status_code == 422


def test_resumo_media_inclui_excluidas(monkeypatch, autenticar):
    tc, fake = _tc(monkeypatch, autenticar)
    fake.tables["task_aprendizado"][0].update(excluida=True, motivo_exclusao="ruído", tempo_normalizado_s=1000.0)
    corpo = tc.get("/classificador/resumo").json()
    nivel2 = next(m for m in corpo["medias"] if m["nivel"] == 2)
    assert (nivel2["n"], nivel2["n_total"], nivel2["media_s"]) == (0, 1, 1000.0)
    assert corpo["excluidas"][0]["motivo_exclusao"] == "ruído"
    assert "excluida_em" in corpo["excluidas"][0]


def test_patch_exclui_com_motivo_e_exige_motivo(monkeypatch, autenticar):
    tc, fake = _tc(monkeypatch, autenticar)
    monkeypatch.setattr(aprendizado, "get_client", lambda: fake, raising=False)
    assert tc.patch("/classificador/aprendizado/t2", json={"excluida": True}).status_code == 422
    assert tc.patch("/classificador/aprendizado/t2", json={"excluida": True, "motivo": "  "}).status_code == 422
    r = tc.patch("/classificador/aprendizado/t2", json={"excluida": True, "motivo": "task atípica"})
    assert r.status_code == 200
    assert r.json()["excluida"] is True and r.json()["motivo_exclusao"] == "task atípica"
    r = tc.patch("/classificador/aprendizado/t2", json={"excluida": False})
    assert r.json()["excluida"] is False
    assert tc.patch("/classificador/aprendizado/nao-existe", json={"excluida": False}).status_code == 404


def test_revisao_lista_so_atuais_em_revisao_ou_provisoria(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar)
    itens = tc.get("/classificador/revisao").json()
    assert {i["task_id"] for i in itens} == {"t2", "t3"}  # t1 tem em_revisao antiga, atual aplicada
    t2 = next(i for i in itens if i["task_id"] == "t2")
    assert t2["titulo"] == "Task 2" and t2["projeto"] == "Projeto" and t2["motivo_revisao"] == "divergência"


def test_detalhe_traz_parecidas_com_titulo(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar)
    corpo = tc.get("/classificador/tasks/t2").json()
    assert corpo["classificacao"]["parecidas"][0]["titulo"] == "Task 3"
    assert corpo["aprendizado"]["task_id"] == "t2"
    assert tc.get("/classificador/tasks/sem-clas").status_code == 404


def test_resumo_banco_vazio(monkeypatch, autenticar):
    from main import app
    fake = FakeClient()
    monkeypatch.setattr(rota, "get_client", lambda: fake)
    corpo = autenticar(TestClient(app), "lider").get("/classificador/resumo").json()
    assert corpo["acuracia"]["n"] == 0 and corpo["acuracia"]["exata"] == 0
    assert all(m["n"] == 0 and m["media_s"] == 0 for m in corpo["medias"])
    for chave in ("alertas", "excluidas", "evolucao_medias", "evolucao_acuracia", "pesos_sinais",
                  "evolucao_pesos", "vies_gerentes", "ritmos", "gerentes"):
        assert corpo[chave] == []
    assert corpo["opinioes"] == {"gerentes": [], "operacionais": []}


def test_alerta_sem_nivel_real_e_ignorado(monkeypatch, autenticar):
    tc, fake = _tc(monkeypatch, autenticar)
    fake.tables["task_aprendizado"].append(_ex("t4", 2, None, alerta=True))
    assert [a["task_id"] for a in tc.get("/classificador/resumo").json()["alertas"]] == ["t2"]


def test_ler_tudo_percorre_varias_paginas():
    from services.supabase_paginacao import ler_tudo
    fake = FakeClient({"t": [{"id": f"{i:02d}"} for i in range(5)]})
    linhas = ler_tudo(lambda: fake.table("t").select("id").order("id"), lote=2)
    assert [l["id"] for l in linhas] == ["00", "01", "02", "03", "04"]
    assert ler_tudo(lambda: fake.table("t").select("id").order("id"), lote=5) == linhas
