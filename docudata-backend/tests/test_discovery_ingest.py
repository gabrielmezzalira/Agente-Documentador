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
    assert len(fake.tables["discovery_reunioes"]) == 1 and len(analises) == 1
    assert len(fake.tables["discovery_transcricoes"]) == 1


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
