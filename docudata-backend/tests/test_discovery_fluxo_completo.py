"""Fluxo ponta a ponta (mockado): reunião de Discovery -> análise -> revisão -> bifurcação -> contexto no destino."""
import json
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from models.discovery import NovoRequisito, SaidaAnalise
from services import discovery_store as store
from services.discovery_analise import analisar_reuniao
from tests.test_encaminhamento import ClienteComRpc

CHAVE = "chave-servico-fluxo"
SERVICO = {"X-Discovery-Key": CHAVE}
H = {"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]}
SENTINELA = "FRASE-BRUTA-DA-TRANSCRICAO-QUE-NAO-PODE-VAZAR"
SEGREDO = "AIza" + "x" * 35
TRANSCRICAO = f"Marina: precisamos exportar o relatório mensal em PDF. Davi: a diretoria quer assinatura digital. {SENTINELA} chave {SEGREDO}"


def _novo(titulo, trecho, criterios):
    return NovoRequisito(titulo=titulo, tipo="funcional", lente="produto", prioridade_sugerida="must",
                         criterios_aceite=criterios, trecho=trecho)


@pytest.fixture
def fluxo(monkeypatch, autenticar):
    from main import app
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", CHAVE)
    fake = ClienteComRpc({
        "projects": [{"id": "p1", "name": "Cliente X", "client": "X", "subarea": "produto", "description": None,
                      "squad": None, "is_delivered": False, "created_at": "2026-10-12T12:00:00+00:00"}],
        "operacionais": [{"project_id": "p1", "email": "pessoa@citi.org.br", "ativo": True}],
    })
    for alvo in ("routers.discovery_ingest.get_client", "routers.discovery.get_client",
                 "routers.projects.get_client", "services.auth.get_client"):
        monkeypatch.setattr(alvo, lambda: fake)
    monkeypatch.setattr("routers.projects.registrar_auditoria", lambda *a: None)
    # FakeClient não aplica DEFAULT now() do banco; os schemas de resposta exigem esses campos.
    agora = datetime.now(timezone.utc).isoformat()

    def carimbar():
        for tabela, campo in (("discovery_reunioes", "created_at"), ("requisito_evidencias", "created_at"),
                              ("requisito_transicoes", "timestamp")):
            for linha in fake.tables.get(tabela, []):
                linha.setdefault(campo, agora)

    def configurar(saida: SaidaAnalise):
        async def executor(**_):
            return saida

        async def analisar_agora(reuniao_id: str):  # troca só a costura do modelo e da chave
            await analisar_reuniao(fake, reuniao_id, executar=executor, obter_chave=lambda: "k")
            carimbar()

        monkeypatch.setattr("routers.discovery_ingest.analisar_em_segundo_plano", analisar_agora)

    corpo = {"docudata_project_id": "p1", "fonte_session_id": "sessao-0001", "tipo": "contexto_empresa",
             "conteudo_estruturado": {"resumo": "Resumo da empresa X"}, "transcricao": TRANSCRICAO}
    cliente = lambda cargo: autenticar(TestClient(app), cargo)  # noqa: E731
    return fake, TestClient(app), cliente, configurar, corpo, carimbar


def _ingerir_e_listar(fluxo, novos):
    fake, servico, cliente, configurar, corpo, carimbar = fluxo
    configurar(SaidaAnalise(novos=novos))
    assert servico.post("/discovery/reunioes", json=corpo, headers=SERVICO).status_code == 202
    carimbar()
    return store.listar_requisitos(fake, "p1")


def test_do_discovery_ao_destino_com_todo_o_contexto(fluxo):
    fake, servico, cliente, *_ = fluxo
    req = _ingerir_e_listar(fluxo, [
        _novo("Exportar relatório em PDF", "precisamos exportar o relatório mensal em PDF", ["Dado um relatório, quando exporto, então recebo um PDF"]),
        _novo("Assinatura digital", "a diretoria quer assinatura digital", ["Dado um PDF, quando assino, então fica válido"]),
    ])
    assert len(fake.tables["discovery_reunioes"]) == 1 and len(req) == 2
    assert fake.tables["discovery_reunioes"][0]["analise_status"] == "ok"
    assert all(store.contar_evidencias(fake, [r["id"]])[r["id"]] >= 1 for r in req)
    assert SEGREDO not in str(fake.tables)  # redigido já na entrada
    validado, rejeitado = req[0], req[1]

    gerente = cliente("gerente")
    assert gerente.patch(f"/discovery/requisitos/{validado['id']}", json={"status": "em_revisao"}, headers=H).status_code == 200
    assert gerente.patch(f"/discovery/requisitos/{validado['id']}", json={"status": "validado"}, headers=H).status_code == 200
    assert gerente.patch(f"/discovery/requisitos/{rejeitado['id']}",
                         json={"status": "rejeitado", "motivo": "Fora do escopo contratado"}, headers=H).status_code == 200

    resp = gerente.post("/projects/p1/encaminhar", json={"destino": "dados", "promover_validados": True, "motivo": "Discovery concluído"}, headers=H)
    assert resp.status_code == 200 and resp.json()["subarea"] == "dados"
    assert [f["id_funcional"] for f in fake.tables["funcionalidades"]] == [validado["codigo"]]
    por_codigo = {r["codigo"]: r for r in gerente.get("/discovery/projetos/p1/requisitos", headers=H).json()}
    assert por_codigo[validado["codigo"]]["funcionalidade_id"] is not None
    assert por_codigo[rejeitado["codigo"]]["funcionalidade_id"] is None

    # depois da bifurcação, o contexto do cliente segue inteiro, nas duas portas de leitura
    via_servico = servico.get("/discovery/servico/projetos/p1/contexto", headers=SERVICO)
    via_sessao = cliente("operacional").get("/discovery/projetos/p1/contexto", headers=H)
    for resposta in (via_servico, via_sessao):
        assert resposta.status_code == 200
        ctx = resposta.json()
        assert [r["resumo"] for r in ctx["reunioes"]] == ["Resumo da empresa X"]
        status = {r["codigo"]: r for r in ctx["requisitos"]}
        assert status[validado["codigo"]]["status"] == "validado"
        assert status[rejeitado["codigo"]]["status"] == "rejeitado"
        assert status[rejeitado["codigo"]]["motivo_decisao"] == "Fora do escopo contratado"
        texto = json.dumps(ctx, ensure_ascii=False)
        assert SENTINELA not in texto and SEGREDO not in texto


def test_encaminhar_recusado_quando_validado_sem_criterio_de_aceite(fluxo):
    fake, _, cliente, *_ = fluxo
    req = _ingerir_e_listar(fluxo, [_novo("Exportar relatório em PDF", "precisamos exportar o relatório mensal em PDF", [])])
    gerente = cliente("gerente")
    for status in ("em_revisao", "validado"):
        assert gerente.patch(f"/discovery/requisitos/{req[0]['id']}", json={"status": status}, headers=H).status_code == 200
    resp = gerente.post("/projects/p1/encaminhar", json={"destino": "dados", "promover_validados": True, "motivo": "Discovery concluído"}, headers=H)
    assert resp.status_code == 422
    assert fake.tables["projects"][0]["subarea"] == "produto" and fake.chamadas_rpc == []
    assert not fake.tables.get("funcionalidades")


def test_fronteiras_de_autenticacao_do_fluxo(fluxo):
    fake, servico, cliente, _, corpo, _ = fluxo
    assert cliente("gerente").post("/discovery/reunioes", json=corpo, headers=H).status_code in (401, 403)
    assert "discovery_reunioes" not in fake.tables
    sem_sessao = TestClient(servico.app)
    assert sem_sessao.get("/discovery/projetos/p1/contexto", headers=SERVICO).status_code in (401, 403)
    assert sem_sessao.get("/discovery/projetos/p1/requisitos", headers=SERVICO).status_code in (401, 403)
