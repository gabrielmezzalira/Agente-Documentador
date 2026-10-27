"""Script de ponto de partida do classificador (Rodada A2, Task 11)."""
import pytest

from graphs import classificacao_graph as g
from scripts import classificador_ponto_de_partida as sc
from services import classificador_busca as busca
from tests.fake_supabase import FakeClient


def _task(i, col, pontos=3):
    return {"id": i, "titulo": f"Pipeline {i}", "descricao": "Ler o csv do cliente e gravar no banco",
            "checklist": [], "pontos": pontos, "coluna_kanban": col, "operacional_id": "ana",
            "pull_em": None, "entrou_em_andamento_em": None}


def _fake():
    return FakeClient({
        "tasks": [_task("t1", "concluida", 8), _task("t2", "concluida"), _task("t3", "em_andamento")],
        "task_transicoes": [
            {"task_id": "t1", "campo": "coluna_kanban", "de": "planejado", "para": "em_andamento",
             "timestamp": "2026-10-01T08:00:00+00:00", "bloqueio_tipo": None},
            {"task_id": "t1", "campo": "coluna_kanban", "de": "em_andamento", "para": "concluida",
             "timestamp": "2026-10-01T12:00:00+00:00", "bloqueio_tipo": None},
            {"task_id": "t2", "campo": "coluna_kanban", "de": "em_andamento", "para": "concluida",
             "timestamp": "2026-10-02T12:00:00+00:00", "bloqueio_tipo": None},
        ],
    })


@pytest.fixture
def modelo(monkeypatch):
    chamadas = {"emb": 0}

    async def sinais(api_key, msgs):
        return g.SaidaSinais(
            partes=g.NotaSinal(nota=2, evidencia="Ler o csv do cliente"),
            novidade=g.NotaSinal(nota=1, evidencia="gravar no banco"),
            incerteza=g.NotaSinal(nota=0, evidencia="Ler o csv do cliente"),
            dependencia=g.NotaSinal(nota=0, evidencia="Ler o csv do cliente"),
            tamanho=g.NotaSinal(nota=1, evidencia="gravar no banco"),
            risco=g.NotaSinal(nota=0, evidencia="Ler o csv do cliente"),
        )

    async def emb(api_key, texto):
        chamadas["emb"] += 1
        return [0.1] * busca.EMBED_DIM

    monkeypatch.setattr(g, "_invocar_sinais", sinais)
    monkeypatch.setattr(busca, "gerar_embedding", emb)
    return chamadas


async def test_processa_conclui_pula_e_nao_duplica(modelo):
    fake = _fake()
    r = await sc.processar(fake, "k")
    assert (r["processadas"], r["puladas"], r["falhas"]) == (1, 1, 0)
    ex = fake.tables["task_aprendizado"]
    assert len(ex) == 1 and ex[0]["task_id"] == "t1"
    assert ex[0]["nivel_sugerido"] == 5 and ex[0]["gerente_id"] is None and ex[0]["opiniao_operacional"] is None
    assert ex[0]["sinais"]["partes"] == 2 and set(ex[0]["sinais"]) == set(g.SINAIS)
    assert ex[0]["tempo_limpo_s"] == 4 * 3600
    assert len(fake.tables["task_embeddings"]) == 1
    assert fake.tables["classificador_parametros"]  # recalculou

    r2 = await sc.processar(fake, "k")
    assert r2["processadas"] == 0 and r2["reembedadas"] == 0
    assert len(fake.tables["task_aprendizado"]) == 1
    assert modelo["emb"] == 1


async def test_modelo_quebrando_grava_sinais_nulos_e_conta_falha(modelo, monkeypatch):
    async def quebra(api_key, msgs):
        raise RuntimeError("segredo-xyz")

    monkeypatch.setattr(g, "_invocar_sinais", quebra)
    fake = _fake()
    r = await sc.processar(fake, "k")
    assert r["processadas"] == 1 and r["falhas"] == 1
    assert fake.tables["task_aprendizado"][0]["sinais"] is None


async def test_evidencia_invalida_zera_nota(modelo, monkeypatch):
    async def ruim(api_key, msgs):
        return g.SaidaSinais(**{n: g.NotaSinal(nota=2, evidencia="trecho que nao existe") for n in g.SINAIS})

    monkeypatch.setattr(g, "_invocar_sinais", ruim)
    fake = _fake()
    await sc.processar(fake, "k")
    assert set(fake.tables["task_aprendizado"][0]["sinais"].values()) == {0}


async def test_troca_de_modelo_de_embedding_reembeda(modelo, monkeypatch):
    fake = _fake()
    await sc.processar(fake, "k")
    monkeypatch.setattr(busca, "EMBED_MODELO", "models/outro")
    monkeypatch.setattr(sc.busca, "EMBED_MODELO", "models/outro")
    r = await sc.processar(fake, "k")
    assert r["processadas"] == 0 and r["reembedadas"] == 1
    assert fake.tables["task_embeddings"][0]["modelo"] == "models/outro"
    assert len(fake.tables["task_aprendizado"]) == 1


async def test_limite(modelo):
    fake = _fake()
    fake.tables["tasks"].append(_task("t4", "concluida"))
    fake.tables["task_transicoes"].append(
        {"task_id": "t4", "campo": "coluna_kanban", "de": "planejado", "para": "em_andamento",
         "timestamp": "2026-10-03T08:00:00+00:00", "bloqueio_tipo": None})
    fake.tables["task_transicoes"].append(
        {"task_id": "t4", "campo": "coluna_kanban", "de": "em_andamento", "para": "concluida",
         "timestamp": "2026-10-03T10:00:00+00:00", "bloqueio_tipo": None})
    r = await sc.processar(fake, "k", limite=1)
    assert r["processadas"] == 1
