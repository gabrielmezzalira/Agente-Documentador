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
