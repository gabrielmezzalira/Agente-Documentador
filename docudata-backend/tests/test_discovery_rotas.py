import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from services import discovery_store as store
from tests.fake_supabase import FakeClient

H = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}


@pytest.fixture
def ambiente(monkeypatch, autenticar):
    from main import app
    fake = FakeClient({
        "projects": [{"id": "p1", "subarea": "dados"}, {"id": "p2", "subarea": "dados"}],
        "operacionais": [{"project_id": "p1", "email": "pessoa@citi.org.br", "ativo": True}],
    })
    for alvo in ("routers.discovery.get_client", "services.auth.get_client"):
        monkeypatch.setattr(alvo, lambda: fake)
    agendados: list = []

    async def _tarefa(*args):
        agendados.append(args)

    monkeypatch.setattr("routers.discovery.analisar_em_segundo_plano", _tarefa)
    monkeypatch.setattr("routers.discovery.reconsolidar_em_segundo_plano", _tarefa)

    def _como(cargo):
        return autenticar(TestClient(app), cargo)

    return _como, fake, agendados


def _carimbar(fake):
    """O FakeClient não aplica os DEFAULT now() do banco; o schema de resposta exige esses campos."""
    agora = datetime.now(timezone.utc).isoformat()
    for tabela, campo in (("discovery_reunioes", "created_at"), ("requisito_evidencias", "created_at"),
                          ("requisito_transicoes", "timestamp")):
        for linha in fake.tables.get(tabela, []):
            linha.setdefault(campo, agora)


def _req(fake, status="proposto", criterios=("Dado A, quando B, então C",), codigo="RQ-001"):
    return store.inserir_requisito(fake, {
        "project_id": "p1", "codigo": codigo, "titulo": "Exportar PDF", "tipo": "funcional",
        "prioridade_sugerida": "should", "status": status, "criterios_aceite": list(criterios), "conflito": False,
    })


def test_listar_exige_acesso_ao_projeto(ambiente):
    como, fake, _ = ambiente
    _req(fake)
    assert como("operacional").get("/discovery/projetos/p1/requisitos", headers=H).status_code == 200
    fake.tables["operacionais"].clear()
    assert como("operacional").get("/discovery/projetos/p1/requisitos", headers=H).status_code == 403


def test_listar_filtra_por_status_e_traz_contagem_de_evidencias(ambiente):
    como, fake, _ = ambiente
    r = _req(fake)
    _req(fake, "validado", codigo="RQ-002")
    store.inserir_evidencia(fake, requisito_id=r["id"], reuniao_id="m1", trecho="t", speaker=None, confianca=None)
    corpo = como("gerente").get("/discovery/projetos/p1/requisitos", params={"status": "proposto"}, headers=H).json()
    assert [(q["codigo"], q["n_evidencias"]) for q in corpo] == [("RQ-001", 1)]


def test_operacional_revisa_e_nao_valida(ambiente):
    como, fake, _ = ambiente
    r = _req(fake)
    op = como("operacional")
    ok = op.patch(f"/discovery/requisitos/{r['id']}", json={"status": "em_revisao"}, headers=H)
    assert ok.status_code == 200 and ok.json()["status"] == "em_revisao" and ok.json()["revisado_por"] == "pessoa@citi.org.br"
    assert op.patch(f"/discovery/requisitos/{r['id']}", json={"status": "validado"}, headers=H).status_code == 403


def test_gerente_valida_e_rejeitar_exige_motivo(ambiente):
    como, fake, _ = ambiente
    r = _req(fake, "em_revisao")
    g = como("gerente")
    assert g.patch(f"/discovery/requisitos/{r['id']}", json={"status": "rejeitado"}, headers=H).status_code == 422
    rej = g.patch(f"/discovery/requisitos/{r['id']}", json={"status": "rejeitado", "motivo": "fora do escopo"}, headers=H)
    assert rej.status_code == 200 and rej.json()["motivo_decisao"] == "fora do escopo"
    val = _req(fake, "em_revisao", codigo="RQ-002")
    ok = g.patch(f"/discovery/requisitos/{val['id']}", json={"status": "validado"}, headers=H)
    assert ok.json()["status"] == "validado" and ok.json()["validado_por"] == "pessoa@citi.org.br"


def test_transicao_invalida_retorna_409(ambiente):
    como, fake, _ = ambiente
    r = _req(fake)
    assert como("gerente").patch(f"/discovery/requisitos/{r['id']}", json={"status": "validado"}, headers=H).status_code == 409


def test_operacional_nao_edita_validado_gerente_edita(ambiente):
    como, fake, _ = ambiente
    r = _req(fake, "validado")
    assert como("operacional").patch(f"/discovery/requisitos/{r['id']}", json={"titulo": "Novo título"}, headers=H).status_code == 403
    ok = como("gerente").patch(f"/discovery/requisitos/{r['id']}", json={"titulo": "Novo título"}, headers=H)
    assert ok.status_code == 200 and ok.json()["titulo"] == "Novo título"


def test_detalhe_traz_evidencias_e_transicoes(ambiente):
    como, fake, _ = ambiente
    r = _req(fake)
    store.inserir_evidencia(fake, requisito_id=r["id"], reuniao_id="m1", trecho="queremos pdf", speaker="Ana", confianca=0.9)
    como("operacional").patch(f"/discovery/requisitos/{r['id']}", json={"status": "em_revisao"}, headers=H)
    _carimbar(fake)
    d = como("operacional").get(f"/discovery/requisitos/{r['id']}", headers=H).json()
    assert d["evidencias"][0]["trecho"] == "queremos pdf" and d["transicoes"][-1]["para"] == "em_revisao"


def test_promover_exige_gerente_e_e_idempotente(ambiente):
    como, fake, _ = ambiente
    r = _req(fake, "validado")
    assert como("operacional").post(f"/discovery/requisitos/{r['id']}/promover", headers=H).status_code == 403
    primeira = como("gerente").post(f"/discovery/requisitos/{r['id']}/promover", headers=H)
    segunda = como("gerente").post(f"/discovery/requisitos/{r['id']}/promover", headers=H)
    assert primeira.status_code == 200 and primeira.json()["criada"] is True and segunda.json()["criada"] is False
    assert len(fake.tables["funcionalidades"]) == 1


def test_transcricao_so_para_gerente_e_respeita_expiracao(ambiente):
    como, fake, _ = ambiente
    m = store.inserir_reuniao(fake, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0001", conteudo_estruturado={})
    store.inserir_transcricao(fake, reuniao_id=m["id"], conteudo="texto integral", redigida=False)
    assert como("operacional").get(f"/discovery/reunioes/{m['id']}/transcricao", headers=H).status_code == 403
    ok = como("gerente").get(f"/discovery/reunioes/{m['id']}/transcricao", headers=H)
    assert ok.status_code == 200 and ok.json()["conteudo"] == "texto integral"
    fake.tables["discovery_transcricoes"][0]["expira_em"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert como("gerente").get(f"/discovery/reunioes/{m['id']}/transcricao", headers=H).status_code == 410
    assert como("gerente").get("/discovery/reunioes/nada/transcricao", headers=H).status_code == 404


def test_listagem_de_reunioes_nao_traz_transcricao_nem_conteudo(ambiente):
    como, fake, _ = ambiente
    m = store.inserir_reuniao(fake, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0001", conteudo_estruturado={"resumo": "x"})
    store.inserir_transcricao(fake, reuniao_id=m["id"], conteudo="texto integral", redigida=False)
    _carimbar(fake)
    resp = como("operacional").get("/discovery/projetos/p1/reunioes", headers=H)
    assert resp.status_code == 200 and "texto integral" not in resp.text and "conteudo_estruturado" not in resp.text


def test_reconsolidar_e_reanalisar_exigem_gerente_e_agendam(ambiente):
    como, fake, agendados = ambiente
    m = store.inserir_reuniao(fake, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0001", conteudo_estruturado={})
    assert como("operacional").post("/discovery/projetos/p1/reconsolidar", headers=H).status_code == 403
    assert como("gerente").post("/discovery/projetos/p1/reconsolidar", headers=H).status_code == 202
    assert como("gerente").post(f"/discovery/reunioes/{m['id']}/analisar", headers=H).status_code == 202
    assert agendados == [("p1",), (m["id"],)]
    assert store.buscar_reuniao(fake, m["id"])["analise_status"] == "pendente"


def test_contexto_autenticado_vem_sem_transcricao(ambiente):
    como, fake, _ = ambiente
    m = store.inserir_reuniao(fake, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0001", conteudo_estruturado={"resumo": "r"})
    store.inserir_transcricao(fake, reuniao_id=m["id"], conteudo="SO-NA-TRANSCRICAO", redigida=False)
    resp = como("operacional").get("/discovery/projetos/p1/contexto", headers=H)
    assert resp.status_code == 200 and "SO-NA-TRANSCRICAO" not in resp.text


# ---- autorização por objeto: o id do recurso nunca basta ----
def _req_p2(fake):
    return store.inserir_requisito(fake, {
        "project_id": "p2", "codigo": "RQ-001", "titulo": "Segredo", "tipo": "funcional",
        "prioridade_sugerida": "should", "status": "validado", "criterios_aceite": ["Dado A, quando B, então C"], "conflito": False,
    })


def test_sem_acesso_ao_projeto_b_nao_le_nem_altera_requisitos_por_id(ambiente):
    como, fake, _ = ambiente
    r = _req_p2(fake)
    op = como("operacional")
    assert op.get(f"/discovery/requisitos/{r['id']}", headers=H).status_code == 404
    assert op.patch(f"/discovery/requisitos/{r['id']}", json={"titulo": "Hackeado"}, headers=H).status_code == 404
    assert fake.tables["requisitos"][0]["titulo"] == "Segredo"
    # inexistente e proibido são indistinguíveis (não vaza existência)
    assert op.get("/discovery/requisitos/nao-existe", headers=H).status_code == 404


def test_promover_checa_acesso_do_projeto_do_requisito_antes_de_promover(ambiente, monkeypatch):
    como, fake, _ = ambiente
    r = _req_p2(fake)
    chamadas: list = []
    monkeypatch.setattr("routers.discovery.promover_requisito", lambda *a: chamadas.append(a))
    # operacional é barrado pelo cargo; mesmo um perfil sem acesso nunca chega ao serviço
    assert como("operacional").post(f"/discovery/requisitos/{r['id']}/promover", headers=H).status_code == 403
    assert chamadas == []


def test_sem_acesso_ao_projeto_b_nao_lista_nem_le_contexto(ambiente):
    como, fake, _ = ambiente
    _req_p2(fake)
    op = como("operacional")
    for rota in ("requisitos", "reunioes", "contexto"):
        assert op.get(f"/discovery/projetos/p2/{rota}", headers=H).status_code == 403


def test_reuniao_de_projeto_sem_acesso_vira_404_em_analisar_e_transcricao(ambiente, monkeypatch):
    como, fake, agendados = ambiente
    m = store.inserir_reuniao(fake, project_id="p2", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0002", conteudo_estruturado={})
    store.inserir_transcricao(fake, reuniao_id=m["id"], conteudo="PRIVADO", redigida=False)
    # gerente+ tem acesso global (convenção de require_project_access); para provar o 404 por objeto
    # simulamos um gerente cujo acesso ao projeto é negado.
    from fastapi import HTTPException

    async def _negar(project_id, pessoa):
        raise HTTPException(status_code=403, detail="Você não tem acesso a este projeto")

    monkeypatch.setattr("routers.discovery.require_project_access", _negar)
    g = como("gerente")
    r1 = g.post(f"/discovery/reunioes/{m['id']}/analisar", headers=H)
    r2 = g.get(f"/discovery/reunioes/{m['id']}/transcricao", headers=H)
    assert r1.status_code == 404 and r2.status_code == 404 and "PRIVADO" not in r2.text
    assert agendados == []


def test_gerente_sem_acesso_ao_requisito_nao_promove(ambiente, monkeypatch):
    como, fake, _ = ambiente
    r = _req_p2(fake)
    from fastapi import HTTPException

    async def _negar(project_id, pessoa):
        raise HTTPException(status_code=403, detail="x")

    chamadas: list = []
    monkeypatch.setattr("routers.discovery.require_project_access", _negar)
    monkeypatch.setattr("routers.discovery.promover_requisito", lambda *a: chamadas.append(a))
    assert como("gerente").post(f"/discovery/requisitos/{r['id']}/promover", headers=H).status_code == 404
    assert chamadas == []


def test_reconsolidar_projeto_inexistente_404(ambiente):
    como, _, agendados = ambiente
    assert como("gerente").post("/discovery/projetos/nada/reconsolidar", headers=H).status_code == 404
    assert agendados == []


def test_status_invalido_na_listagem_422(ambiente):
    como, _, _ = ambiente
    assert como("gerente").get("/discovery/projetos/p1/requisitos", params={"status": "xyz"}, headers=H).status_code == 422


def test_transcricao_nao_pode_ser_cacheada(ambiente):
    como, fake, _ = ambiente
    m = store.inserir_reuniao(fake, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0003", conteudo_estruturado={})
    store.inserir_transcricao(fake, reuniao_id=m["id"], conteudo="t", redigida=False)
    resp = como("gerente").get(f"/discovery/reunioes/{m['id']}/transcricao", headers=H)
    assert resp.headers["cache-control"] == "no-store"


def test_edicao_concorrente_com_a_ia_nao_sobrescreve_requisito_ja_validado(ambiente, monkeypatch):
    """O status muda entre a leitura e a escrita: o update condicional impede edição de operacional."""
    como, fake, _ = ambiente
    r = _req(fake)
    original = store.buscar_requisito

    def _desatualizado(client, rid):
        antigo = original(client, rid)
        fake.tables["requisitos"][0]["status"] = "validado"  # outro gerente validou depois da leitura
        return antigo

    monkeypatch.setattr("routers.discovery.store.buscar_requisito", _desatualizado)
    resp = como("operacional").patch(f"/discovery/requisitos/{r['id']}", json={"titulo": "Edição atrasada"}, headers=H)
    assert resp.status_code == 409
    assert fake.tables["requisitos"][0]["titulo"] == "Exportar PDF"


def test_reconsolidar_e_analisar_tem_rate_limit_de_ia():
    from core.rate_limit import limiter

    assert {"routers.discovery.reconsolidar", "routers.discovery.reanalisar"} <= set(limiter._route_limits)


def test_reanalisar_zera_reserva_velha_mas_nao_derruba_analise_em_andamento(ambiente):
    como, fake, agendados = ambiente
    m = store.inserir_reuniao(fake, project_id="p1", tipo="outra", ocorrida_em=None, fonte_session_id="sessao-0001", conteudo_estruturado={})
    linha = fake.tables["discovery_reunioes"][0]
    linha.update(analise_status="falhou", analise_erro="x", analise_iniciada_em=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat())
    assert como("gerente").post(f"/discovery/reunioes/{m['id']}/analisar", headers=H).status_code == 202
    assert linha["analise_status"] == "pendente" and linha["analise_iniciada_em"] is None
    reserva = datetime.now(timezone.utc).isoformat()
    linha["analise_iniciada_em"] = reserva  # análise em andamento
    assert como("gerente").post(f"/discovery/reunioes/{m['id']}/analisar", headers=H).status_code == 202
    assert linha["analise_iniciada_em"] == reserva
