"""Foto de perfil: gerente troca a de qualquer um, cada um troca a própria, o arquivo vira WEBP quadrado."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import services.fotos_perfil as fotos
from main import app
from tests.fake_supabase import FakeClient


def _img(tamanho=(40, 20), formato="PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", tamanho, (30, 120, 200)).save(buf, formato)
    return buf.getvalue()


class _Bucket:
    def __init__(self, arquivos):
        self.arquivos = arquivos

    def upload(self, path, dados, opcoes=None):
        self.arquivos[path] = dados

    def list(self, pasta, opcoes=None):
        return [{"name": p, "updated_at": f"v{len(d)}"} for p, d in sorted(self.arquivos.items())]

    def download(self, path):
        if path not in self.arquivos:
            raise KeyError(path)
        return self.arquivos[path]

    def remove(self, paths):
        for p in paths:
            self.arquivos.pop(p, None)


class _Storage:
    def __init__(self):
        self.arquivos = {}
        self.buckets = []

    def list_buckets(self):
        return [type("B", (), {"name": n})() for n in self.buckets]

    def create_bucket(self, nome, options=None):
        self.buckets.append(nome)

    def from_(self, _nome):
        return _Bucket(self.arquivos)


@pytest.fixture
def api(monkeypatch, autenticar):
    fake = FakeClient({"pessoa": [{"id": "pessoa-teste", "nome": "Gabriel Mezzalira", "cargo": "operacional"}]})
    fake.storage = _Storage()
    monkeypatch.setattr("routers.fotos.get_client", lambda: fake)
    monkeypatch.setattr(fotos, "_bucket_garantido", False)
    c = TestClient(app)
    autenticar(c, "gerente")
    c.fake = fake
    c.como = lambda cargo: autenticar(TestClient(app), cargo)
    return c


def _trocar(c, nome="Maria Souza", dados=None, tipo="image/png"):
    return c.put("/fotos", data={"nome": nome}, files={"arquivo": ("foto.png", dados if dados is not None else _img(), tipo)})


def test_chave_ignora_acento_caixa_e_espaco():
    assert fotos.chave_do_nome("  Ana  Luíza D'Ávila ") == "ana-luiza-d-avila"
    assert fotos.chave_do_nome("") == ""


def test_gerente_troca_foto_e_ela_vira_webp_quadrado(api):
    assert _trocar(api).json() == {"chave": "maria-souza"}
    img = api.get("/fotos/maria-souza")
    assert img.status_code == 200 and img.headers["content-type"] == "image/webp"
    with Image.open(io.BytesIO(img.content)) as saida:
        assert saida.format == "WEBP" and saida.size == (fotos.LADO, fotos.LADO)
    assert list(api.get("/fotos").json()) == ["maria-souza"]
    assert api.fake.storage.buckets == [fotos.BUCKET]


def test_ampliada_mantem_a_foto_inteira_sem_recortar(api):
    _trocar(api, dados=_img((400, 200)))
    grande = api.get("/fotos/maria-souza?tam=completa")
    with Image.open(io.BytesIO(grande.content)) as saida:
        assert saida.size == (400, 200)  # retangular: nada cortado
    assert list(api.get("/fotos").json()) == ["maria-souza"]  # a ampliada não vira "pessoa"
    assert api.delete("/fotos/maria-souza").status_code == 204
    assert api.fake.storage.arquivos == {}


def test_ampliada_de_foto_antiga_cai_na_miniatura(api):
    _trocar(api)
    del api.fake.storage.arquivos["completa/maria-souza.webp"]
    assert api.get("/fotos/maria-souza?tam=completa").status_code == 200


def test_trocar_de_novo_muda_a_versao(api):
    _trocar(api, dados=_img((40, 20)))
    antes = api.fake.storage.arquivos["maria-souza.webp"]
    _trocar(api, dados=_img((300, 300), "JPEG"))
    # trocar substitui o arquivo (miniatura + ampliada), sem acumular cópias
    assert api.fake.storage.arquivos["maria-souza.webp"] != antes
    assert sorted(api.fake.storage.arquivos) == ["completa/maria-souza.webp", "maria-souza.webp"]


def test_arquivo_que_nao_e_imagem_e_recusado(api):
    r = _trocar(api, dados=b"nao sou imagem", tipo="text/plain")
    assert r.status_code == 422 and api.fake.storage.arquivos == {}


def test_operacional_troca_so_a_propria(api):
    op = api.como("operacional")
    assert _trocar(op, nome="Maria Souza").status_code == 403
    assert _trocar(op, nome="gabriel  mezzalira").status_code == 200
    assert op.delete("/fotos/maria-souza").status_code == 403
    assert op.delete("/fotos/gabriel-mezzalira").status_code == 204
    assert api.fake.storage.arquivos == {}


def test_chave_invalida_e_foto_inexistente_dao_404(api):
    assert api.get("/fotos/..%2Fsegredo").status_code == 404
    assert api.get("/fotos/ninguem").status_code == 404


def test_sem_login_nao_ve(api):
    assert TestClient(app).get("/fotos").status_code in (401, 403)
