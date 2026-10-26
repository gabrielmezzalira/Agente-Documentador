import pytest

from services import classificador_busca as b
from tests.fake_supabase import FakeClient


def test_nivel_das_parecidas_ponderado_em_degraus():
    ps = [{"similaridade": 0.9, "nivel_real": 3}, {"similaridade": 0.3, "nivel_real": 1}, {"similaridade": -0.2, "nivel_real": 5}]
    assert b.nivel_das_parecidas(ps) == pytest.approx((0.9 * 2 + 0.3 * 0) / 1.2)
    assert b.nivel_das_parecidas([]) is None
    assert b.nivel_das_parecidas([{"similaridade": 0.0, "nivel_real": 3}]) is None


def test_buscar_parecidas_junta_rpc_e_aprendizado():
    fake = FakeClient({"task_aprendizado": [
        {"task_id": "a", "nivel_real": 3, "tempo_normalizado_s": 100, "outra": "x"},
        {"task_id": "b", "nivel_real": 1, "tempo_normalizado_s": 10},
    ]})
    chamadas = []

    def rpc(p):
        chamadas.append(p)
        return [{"task_id": "b", "similaridade": 0.8}, {"task_id": "z", "similaridade": 0.6}, {"task_id": "a", "similaridade": 0.5}]

    fake.rpcs = {"buscar_tasks_parecidas": rpc}
    r = b.buscar_parecidas(fake, [0.0] * 3, k=2)
    assert [x["task_id"] for x in r] == ["b", "a"]  # "z" sem aprendizado é descartada
    assert r[0] == {"task_id": "b", "similaridade": 0.8, "nivel_real": 1, "tempo_normalizado_s": 10}
    assert isinstance(chamadas[0]["consulta"], str) and chamadas[0]["consulta"].startswith("[")
    assert chamadas[0]["consulta"] == "[0.0,0.0,0.0]" and chamadas[0]["n"] == 2


def test_buscar_parecidas_sem_resultado_da_rpc():
    fake = FakeClient({"task_aprendizado": []})
    fake.rpcs = {"buscar_tasks_parecidas": lambda p: []}
    assert b.buscar_parecidas(fake, [0.1]) == []


def test_salvar_embedding_faz_upsert_com_hash():
    fake = FakeClient({"task_embeddings": []})
    b.salvar_embedding(fake, "t1", "texto", [0.1, 0.2])
    assert fake.tables["task_embeddings"][0]["embedding"] == "[0.1,0.2]"
    b.salvar_embedding(fake, "t1", "texto novo", [0.3, 0.4])
    rows = fake.tables["task_embeddings"]
    assert len(rows) == 1 and rows[0]["hash_texto"] == b.hash_texto("texto novo") and rows[0]["modelo"] == b.EMBED_MODELO
    assert rows[0]["embedding"] == "[0.3,0.4]"


def test_salvar_embedding_pula_escrita_se_hash_igual():
    fake = FakeClient({"task_embeddings": []})
    b.salvar_embedding(fake, "t1", "texto", [0.1, 0.2])
    b.salvar_embedding(fake, "t1", "texto", [9.0, 9.0])
    assert fake.tables["task_embeddings"][0]["embedding"] == "[0.1,0.2]"


async def test_gerar_embedding_valida_dimensao(monkeypatch):
    class Fake:
        def __init__(self, model, google_api_key):
            assert model == b.EMBED_MODELO and google_api_key == "k"

        def embed_query(self, texto, output_dimensionality):
            assert output_dimensionality == b.EMBED_DIM
            return [0.5] * self.n

    monkeypatch.setattr(b, "GoogleGenerativeAIEmbeddings", Fake)
    Fake.n = b.EMBED_DIM
    assert len(await b.gerar_embedding("k", "oi")) == b.EMBED_DIM
    Fake.n = 5
    with pytest.raises(ValueError):
        await b.gerar_embedding("k", "oi")
