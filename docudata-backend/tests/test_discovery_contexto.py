import json

import pytest
from fastapi.testclient import TestClient

from services import discovery_store as store
from services.discovery_contexto import LIMITE_REQUISITOS, compilar_contexto
from tests.fake_supabase import FakeClient

SEGREDO_DA_TRANSCRICAO = "FRASE-SO-NA-TRANSCRICAO-123"


def _montar():
    c = FakeClient({"projects": [{"id": "p1", "subarea": "dados"}]})
    r = store.inserir_reuniao(c, project_id="p1", tipo="entrevista_tecnica", ocorrida_em=None, fonte_session_id="sessao-0001",
                              conteudo_estruturado={"resumo": "r" * 2000, "decisoes": ["usar API"], "problemas": ["sem API"],
                                                    "red_flags": [{"text": "ERP sem API", "severity": "critical"},
                                                                  {"text": "prazo curto", "severity": "warning"}]})
    store.inserir_transcricao(c, reuniao_id=r["id"], conteudo=SEGREDO_DA_TRANSCRICAO, redigida=False)
    base = {"project_id": "p1", "tipo": "funcional", "prioridade_sugerida": "should", "criterios_aceite": [], "conflito": False}
    store.inserir_requisito(c, base | {"codigo": "RQ-001", "titulo": "Exportar PDF", "status": "validado"})
    store.inserir_requisito(c, base | {"codigo": "RQ-002", "titulo": "App nativo", "status": "rejeitado", "motivo_decisao": "fora do escopo"})
    store.inserir_requisito(c, base | {"codigo": "RQ-003", "titulo": "SSO", "status": "proposto", "conflito": True})
    return c


def test_contexto_nunca_traz_a_transcricao_bruta():
    assert SEGREDO_DA_TRANSCRICAO not in json.dumps(compilar_contexto(_montar(), "p1"), default=str)


def test_contexto_nao_vaza_campos_fora_do_resumo_limitado():
    c = _montar()
    store.inserir_reuniao(c, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0002",
                          conteudo_estruturado={"transcricao_bruta": SEGREDO_DA_TRANSCRICAO, "resumo": "ok"})
    assert SEGREDO_DA_TRANSCRICAO not in json.dumps(compilar_contexto(c, "p1"), default=str)


def test_contexto_inclui_rejeitados_com_motivo_para_nao_re_sugerir():
    ctx = compilar_contexto(_montar(), "p1")
    rejeitado = [q for q in ctx["requisitos"] if q["codigo"] == "RQ-002"][0]
    assert rejeitado["status"] == "rejeitado" and rejeitado["motivo_decisao"] == "fora do escopo"
    assert [q for q in ctx["requisitos"] if q["codigo"] == "RQ-001"][0]["status"] == "validado"


def test_contexto_resume_reunioes_e_lista_conflitos_e_red_flags_criticas():
    ctx = compilar_contexto(_montar(), "p1")
    assert len(ctx["reunioes"][0]["resumo"]) <= 801
    assert ctx["reunioes"][0]["decisoes"] == ["usar API"]
    assert ctx["conflitos_abertos"] == ["RQ-003"]
    assert ctx["red_flags_criticas"] == ["ERP sem API"]


def test_contexto_limita_a_quantidade_de_requisitos():
    c = _montar()
    for i in range(LIMITE_REQUISITOS + 5):
        store.inserir_requisito(c, {"project_id": "p1", "codigo": f"RQ-{i + 10:03d}", "titulo": f"t{i}", "tipo": "funcional",
                                    "prioridade_sugerida": "should", "criterios_aceite": [], "status": "proposto", "conflito": False})
    assert len(compilar_contexto(c, "p1")["requisitos"]) == LIMITE_REQUISITOS


def test_contexto_trunca_textos_longos_e_limita_listas():
    from services.discovery_contexto import LIMITE_LISTA
    c = FakeClient({"projects": [{"id": "p1", "subarea": "dados"}]})
    store.inserir_reuniao(c, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="s-1",
                          conteudo_estruturado={"red_flags": [{"text": "x" * 999, "severity": "critical"}] * (LIMITE_LISTA * 20)})
    store.inserir_requisito(c, {"project_id": "p1", "codigo": "RQ-001", "titulo": "T" * 999, "tipo": "funcional",
                                "prioridade_sugerida": "should", "status": "rejeitado", "motivo_decisao": "M" * 999,
                                "criterios_aceite": ["c" * 999] * 99, "conflito": False})
    ctx = compilar_contexto(c, "p1")
    q = ctx["requisitos"][0]
    assert len(q["titulo"]) <= 200 and len(q["motivo_decisao"]) <= 300
    assert len(q["criterios_aceite"]) <= LIMITE_LISTA and all(len(x) <= 300 for x in q["criterios_aceite"])
    assert len(ctx["red_flags_criticas"]) <= LIMITE_LISTA * 5 and all(len(x) <= 300 for x in ctx["red_flags_criticas"])


def test_rota_de_servico_do_contexto_exige_a_chave(monkeypatch):
    from main import app
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", "chave-teste")
    monkeypatch.setattr("routers.discovery_ingest.get_client", lambda: _montar())
    client = TestClient(app)
    assert client.get("/discovery/servico/projetos/p1/contexto").status_code == 401
    ok = client.get("/discovery/servico/projetos/p1/contexto", headers={"X-Discovery-Key": "chave-teste"})
    assert ok.status_code == 200 and ok.json()["project_id"] == "p1"
    assert client.get("/discovery/servico/projetos/nada/contexto", headers={"X-Discovery-Key": "chave-teste"}).status_code == 404


@pytest.mark.parametrize("campo,valor", [
    ("red_flags", {"a": 1}), ("red_flags", 5), ("red_flags", "texto"),
    ("red_flags", [None, 3, {"severity": "critical"}]),
    ("decisoes", {"a": 1}), ("decisoes", 7), ("problemas", 7), ("resumo", ["x"]),
])
def test_conteudo_malformado_nao_derruba_o_contexto(campo, valor):
    c = _montar()
    store.inserir_reuniao(c, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="ruim",
                          conteudo_estruturado={campo: valor})
    ctx = compilar_contexto(c, "p1")
    assert len(ctx["reunioes"]) == 2
    assert ctx["red_flags_criticas"] == ["ERP sem API"]


def test_corte_de_requisitos_preserva_rejeitados_mesmo_com_codigos_altos():
    c = FakeClient({"projects": [{"id": "p1", "subarea": "dados"}]})
    base = {"project_id": "p1", "titulo": "t", "tipo": "funcional", "prioridade_sugerida": "should",
            "criterios_aceite": [], "conflito": False}
    for i in range(250):
        rej = i >= 240
        store.inserir_requisito(c, base | {"codigo": f"RQ-{i:04d}", "status": "rejeitado" if rej else "proposto",
                                           "motivo_decisao": "x" if rej else None})
    ctx = compilar_contexto(c, "p1")
    assert len(ctx["requisitos"]) == LIMITE_REQUISITOS and ctx["requisitos_truncados"] is True
    assert sum(q["status"] == "rejeitado" for q in ctx["requisitos"]) == 10


def test_conflitos_abertos_calculados_antes_do_corte():
    c = FakeClient({"projects": [{"id": "p1", "subarea": "dados"}]})
    base = {"project_id": "p1", "titulo": "t", "tipo": "funcional", "prioridade_sugerida": "should", "criterios_aceite": []}
    for i in range(LIMITE_REQUISITOS + 20):
        store.inserir_requisito(c, base | {"codigo": f"RQ-{i:04d}", "status": "proposto", "conflito": True})
    assert len(compilar_contexto(c, "p1")["conflitos_abertos"]) == LIMITE_REQUISITOS + 20


def test_teto_de_red_flags_prefere_as_reunioes_mais_recentes():
    from services.discovery_contexto import LIMITE_RED_FLAGS
    c = FakeClient({"projects": [{"id": "p1", "subarea": "dados"}]})
    for n, rotulo in enumerate(["antiga", "nova"]):
        store.inserir_reuniao(c, project_id="p1", tipo="outra", ocorrida_em=f"2026-01-0{n + 1}T00:00:00+00:00",
                              fonte_session_id=f"s{n}", conteudo_estruturado={
                                  "red_flags": [{"text": f"{rotulo}{i}", "severity": "critical"} for i in range(LIMITE_RED_FLAGS)]})
    flags = compilar_contexto(c, "p1")["red_flags_criticas"]
    assert len(flags) == LIMITE_RED_FLAGS and all(f.startswith("nova") for f in flags)


def test_rota_do_contexto_sem_chave_configurada_da_503_e_sem_header_da_401(monkeypatch):
    from main import app
    monkeypatch.setattr("routers.discovery_ingest.get_client", lambda: _montar())
    client = TestClient(app)
    monkeypatch.delenv("DOCUDATA_DISCOVERY_KEY", raising=False)
    assert client.get("/discovery/servico/projetos/p1/contexto", headers={"X-Discovery-Key": "x"}).status_code == 503
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", "chave-teste")
    assert client.get("/discovery/servico/projetos/p1/contexto").status_code == 401


def test_areas_cobertas_aceita_lista_limita_e_ignora_tipo_errado():
    c = FakeClient({"projects": [{"id": "p1", "subarea": "dados"}]})
    lista = [{"area": f"a{i}", "status": "s" * 500, "score": 0.5} for i in range(50)] + ["lixo", {"area": 3}]
    for fonte, areas in (("sessao-0001", lista), ("sessao-0002", "texto"), ("sessao-0003", {"x": "nao-dict", "y": {"score": "alto"}})):
        store.inserir_reuniao(c, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id=fonte,
                              conteudo_estruturado={"areas_cobertas": areas, "contexto_pre_reuniao": 5})
    r = compilar_contexto(c, "p1")["reunioes"]
    assert len(r[0]["areas_cobertas"]) == 20 and len(r[0]["areas_cobertas"][0]["status"]) <= 100
    assert r[1]["areas_cobertas"] == [] and r[1]["resumo"] == ""
    assert r[2]["areas_cobertas"] == [{"area": "y", "status": None, "score": None}]


def test_resumo_vazio_cai_para_contexto_pre_reuniao_com_teto():
    c = FakeClient({"projects": [{"id": "p1", "subarea": "dados"}]})
    store.inserir_reuniao(c, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0001",
                          conteudo_estruturado={"resumo": "  ", "contexto_pre_reuniao": "c" * 2000})
    assert len(compilar_contexto(c, "p1")["reunioes"][0]["resumo"]) == 800
