import pytest
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient

CHAVE = "chave-servico-de-teste"
H = {"X-Discovery-Key": CHAVE}
CHAVE_GOOGLE = "AIza" + "x" * 35


@pytest.fixture
def servico(monkeypatch):
    from main import app
    monkeypatch.setenv("DOCUDATA_DISCOVERY_KEY", CHAVE)
    fake = FakeClient({"projects": [{"id": "p1", "subarea": "produto"}]})
    analises: list[str] = []

    async def registrar(reuniao_id: str):
        analises.append(reuniao_id)

    monkeypatch.setattr("routers.discovery_ingest.get_client", lambda: fake)
    monkeypatch.setattr("routers.discovery_ingest.analisar_em_segundo_plano", registrar)
    return TestClient(app), fake, analises


def _corpo(**extra):
    base = {"docudata_project_id": "p1", "fonte_session_id": "sessao-0001", "tipo": "contexto_empresa",
            "conteudo_estruturado": {"resumo": "r"}, "transcricao": "Marina: precisamos exportar PDF"}
    return base | extra


def test_cria_reuniao_grava_transcricao_e_dispara_analise(servico):
    client, fake, analises = servico
    resp = client.post("/discovery/reunioes", json=_corpo(), headers=H)
    assert resp.status_code == 202
    corpo = resp.json()
    assert corpo["analise_status"] == "pendente" and corpo["duplicada"] is False
    assert len(fake.tables["discovery_reunioes"]) == 1
    assert fake.tables["discovery_transcricoes"][0]["conteudo"] == "Marina: precisamos exportar PDF"
    assert analises == [corpo["id"]]


def test_reenvio_da_mesma_sessao_e_idempotente(servico):
    client, fake, analises = servico
    primeira = client.post("/discovery/reunioes", json=_corpo(), headers=H).json()
    resp = client.post("/discovery/reunioes", json=_corpo(), headers=H)
    assert resp.status_code == 200
    assert resp.json()["id"] == primeira["id"] and resp.json()["duplicada"] is True
    assert len(fake.tables["discovery_reunioes"]) == 1
    assert len(fake.tables["discovery_transcricoes"]) == 1  # não regrava a transcrição
    assert len(analises) == 2  # reunião ainda pendente: o reenvio reagenda (análise é idempotente)


def test_segredos_sao_redigidos_antes_de_gravar(servico):
    client, fake, _ = servico
    client.post("/discovery/reunioes", json=_corpo(
        transcricao=f"use a chave {CHAVE_GOOGLE}", conteudo_estruturado={"resumo": f"chave {CHAVE_GOOGLE}"}), headers=H)
    assert CHAVE_GOOGLE not in str(fake.tables)
    assert fake.tables["discovery_transcricoes"][0]["redigida"] is True


def test_projeto_inexistente_retorna_404(servico):
    client, fake, analises = servico
    assert client.post("/discovery/reunioes", json=_corpo(docudata_project_id="nada"), headers=H).status_code == 404
    assert "discovery_reunioes" not in fake.tables and analises == []


def test_transcricao_acima_de_2mb_retorna_413_sem_gravar(servico):
    client, fake, _ = servico
    grande = "a" * (2 * 1024 * 1024 + 1)
    assert client.post("/discovery/reunioes", json=_corpo(transcricao=grande), headers=H).status_code == 413
    assert "discovery_reunioes" not in fake.tables


def test_413_vem_antes_da_redacao(servico, monkeypatch):
    client, _, _ = servico

    def nao_deve_rodar(_):
        raise AssertionError("redação executada antes do limite de tamanho")

    monkeypatch.setattr("routers.discovery_ingest.redigir_segredos", nao_deve_rodar)
    grande = "a" * (2 * 1024 * 1024 + 1)
    assert client.post("/discovery/reunioes", json=_corpo(transcricao=grande), headers=H).status_code == 413


def test_corrida_na_restricao_unica_devolve_a_existente(servico, monkeypatch):
    client, fake, analises = servico
    primeira = client.post("/discovery/reunioes", json=_corpo(), headers=H).json()
    analises.clear()
    from services import discovery_store as store

    # Simula o reenvio concorrente: a checagem prévia não enxerga a linha, mas o INSERT bate no UNIQUE.
    chamadas = {"n": 0}
    real = store.buscar_reuniao_por_fonte

    def cega_na_primeira(client_, fonte):
        chamadas["n"] += 1
        return None if chamadas["n"] == 1 else real(client_, fonte)

    def insert_viola_unique(*a, **k):
        raise RuntimeError("duplicate key value violates unique constraint")

    monkeypatch.setattr(store, "buscar_reuniao_por_fonte", cega_na_primeira)
    monkeypatch.setattr(store, "inserir_reuniao", insert_viola_unique)
    resp = client.post("/discovery/reunioes", json=_corpo(), headers=H)
    assert resp.status_code == 200
    assert resp.json()["id"] == primeira["id"] and resp.json()["duplicada"] is True
    assert analises == []


def test_falha_de_insert_sem_duplicata_retorna_500_generico(servico, monkeypatch):
    client, _, _ = servico
    from services import discovery_store as store

    def quebra(*a, **k):
        raise RuntimeError("segredo-interno " + CHAVE_GOOGLE)

    monkeypatch.setattr(store, "inserir_reuniao", quebra)
    resp = client.post("/discovery/reunioes", json=_corpo(), headers=H)
    assert resp.status_code == 500
    assert CHAVE_GOOGLE not in resp.text and "segredo-interno" not in resp.text


def test_mesma_sessao_de_outro_projeto_retorna_409(servico):
    client, fake, analises = servico
    fake.tables["projects"].append({"id": "p2", "subarea": "produto"})
    client.post("/discovery/reunioes", json=_corpo(), headers=H)
    resp = client.post("/discovery/reunioes", json=_corpo(docudata_project_id="p2"), headers=H)
    assert resp.status_code == 409
    assert len(fake.tables["discovery_reunioes"]) == 1 and len(analises) == 1


def test_sem_chave_401_chave_errada_401_sem_configuracao_503(servico, monkeypatch):
    client, _, _ = servico
    assert client.post("/discovery/reunioes", json=_corpo()).status_code == 401
    assert client.post("/discovery/reunioes", json=_corpo(), headers={"X-Discovery-Key": "errada"}).status_code == 401
    monkeypatch.delenv("DOCUDATA_DISCOVERY_KEY")
    assert client.post("/discovery/reunioes", json=_corpo(), headers=H).status_code == 503


def test_segredo_da_aplicacao_nao_substitui_a_chave_de_servico(servico, monkeypatch):
    client, _, _ = servico
    monkeypatch.setenv("DOCUDATA_APP_SECRET", "segredo-da-app")
    for cabecalho in ({"X-App-Secret": "segredo-da-app"}, {"X-Discovery-Key": "segredo-da-app"},
                      {"Authorization": "Bearer segredo-da-app"}):
        assert client.post("/discovery/reunioes", json=_corpo(), headers=cabecalho).status_code == 401


def test_cookie_de_pessoa_nao_substitui_a_chave_de_servico(servico, autenticar):
    client, _, _ = servico
    autenticar(client, "owner")
    assert client.post("/discovery/reunioes", json=_corpo()).status_code == 401


def test_existe_transcricao_no_store():
    from services import discovery_store as store
    fake = FakeClient({})
    assert store.existe_transcricao(fake, "r1") is False
    store.inserir_transcricao(fake, reuniao_id="r1", conteudo="x", redigida=False)
    assert store.existe_transcricao(fake, "r1") is True


def test_falha_ao_gravar_transcricao_e_reenvio_retoma(servico, monkeypatch):
    _, fake, analises = servico
    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    from services import discovery_store as store
    real = store.inserir_transcricao
    chamadas = {"n": 0}

    def falha_na_primeira(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("timeout-interno " + CHAVE_GOOGLE)
        return real(*a, **k)

    monkeypatch.setattr(store, "inserir_transcricao", falha_na_primeira)
    corpo = _corpo(transcricao=f"chave {CHAVE_GOOGLE}")
    erro = client.post("/discovery/reunioes", json=corpo, headers=H)
    assert erro.status_code == 500 and "timeout-interno" not in erro.text and CHAVE_GOOGLE not in erro.text
    assert analises == [] and "discovery_transcricoes" not in fake.tables

    resp = client.post("/discovery/reunioes", json=corpo, headers=H)
    assert resp.status_code == 200 and resp.json()["duplicada"] is True
    assert len(fake.tables["discovery_transcricoes"]) == 1
    assert fake.tables["discovery_transcricoes"][0]["redigida"] is True
    assert CHAVE_GOOGLE not in str(fake.tables)
    assert analises == [resp.json()["id"]]


@pytest.mark.parametrize("status", ["ok", "falhou"])
def test_reenvio_de_reuniao_ja_analisada_nao_grava_nem_agenda(servico, status):
    client, fake, analises = servico
    primeira = client.post("/discovery/reunioes", json=_corpo(), headers=H).json()
    fake.tables["discovery_reunioes"][0]["analise_status"] = status
    fake.tables["discovery_transcricoes"].clear()
    analises.clear()
    resp = client.post("/discovery/reunioes", json=_corpo(), headers=H)
    assert resp.status_code == 200 and resp.json()["id"] == primeira["id"]
    assert fake.tables["discovery_transcricoes"] == [] and analises == []


def test_reenvio_pendente_com_transcricao_existente_so_reagenda(servico):
    client, fake, analises = servico
    primeira = client.post("/discovery/reunioes", json=_corpo(), headers=H).json()
    analises.clear()  # simula crash entre o insert da transcrição e o add_task
    client.post("/discovery/reunioes", json=_corpo(), headers=H)
    assert len(fake.tables["discovery_transcricoes"]) == 1
    assert analises == [primeira["id"]]


def test_reenvio_pendente_sem_transcricao_no_corpo_reagenda_sem_inventar(servico):
    client, fake, analises = servico
    primeira = client.post("/discovery/reunioes", json=_corpo(transcricao=None), headers=H).json()
    analises.clear()
    resp = client.post("/discovery/reunioes", json=_corpo(transcricao=None), headers=H)
    assert resp.status_code == 200 and resp.json()["duplicada"] is True
    assert "discovery_transcricoes" not in fake.tables and analises == [primeira["id"]]


def test_reenvio_com_transcricao_gigante_continua_413(servico):
    client, fake, analises = servico
    client.post("/discovery/reunioes", json=_corpo(), headers=H)
    analises.clear()
    grande = "a" * (2 * 1024 * 1024 + 1)
    assert client.post("/discovery/reunioes", json=_corpo(transcricao=grande), headers=H).status_code == 413
    assert analises == []


# ---- contrato com o Agente Diagnóstico (formato literal de montar_pacote, discovery_export.py) ----
SENTINELA = "FRASE-SO-NA-TRANSCRICAO-777"


def _pacote_do_agente() -> dict:
    return {
        "docudata_project_id": "p1",
        "fonte_session_id": "sessao-agente-01",
        "tipo": "outra",
        "ocorrida_em": "2026-10-01T14:00:00+00:00",
        "conteudo_estruturado": {
            "origem": "agente_diagnostico",
            "contexto_pre_reuniao": "Cliente de logística quer painel de entregas atrasadas.",
            "areas_cobertas": {
                "negocio": {"status": "covered", "score": 0.8, "notes": "dor clara"},
                "eng_dados": {"status": "partial", "score": 0.4, "notes": "ERP sem API"},
            },
            "red_flags": [{"text": "ERP sem API", "severity": "critical", "evidence": "x", "lens": "dados"}],
            "perguntas": [{"text": "Quantas fontes?", "block": "eng_dados", "lens": "dados", "status": "used"}],
            "transcricao_truncada": False,
        },
        "transcricao": f"Marina: {SENTINELA}",
    }


def test_contexto_de_reuniao_do_agente_tem_resumo_e_areas_sem_transcricao(servico):
    import json

    from services.discovery_contexto import compilar_contexto
    client, fake, _ = servico
    assert client.post("/discovery/reunioes", json=_pacote_do_agente(), headers=H).status_code == 202
    ctx = compilar_contexto(fake, "p1")
    reuniao = ctx["reunioes"][0]
    assert reuniao["resumo"] == "Cliente de logística quer painel de entregas atrasadas."
    areas = {a["area"]: a for a in reuniao["areas_cobertas"]}
    assert areas["eng_dados"] == {"area": "eng_dados", "status": "partial", "score": 0.4}
    assert ctx["red_flags_criticas"] == ["ERP sem API"]
    assert SENTINELA not in json.dumps(ctx, default=str)
