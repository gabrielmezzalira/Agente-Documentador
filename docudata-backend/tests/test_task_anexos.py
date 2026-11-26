"""Imagens anexadas às tasks: gerente anexa e remove, quem tem acesso vê, nada de arquivo que não seja imagem."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import services.task_anexos as anexos
from main import app
from tests.fake_supabase import FakeClient

PID, OUTRO = "proj-1", "proj-2"


def _png(cor=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (6, 6), cor).save(buf, "PNG")
    return buf.getvalue()


class _Bucket:
    def __init__(self, arquivos):
        self.arquivos = arquivos

    def upload(self, path, dados, opcoes=None):
        self.arquivos[path] = dados

    def list(self, pasta):
        prefixo = pasta + "/"
        return [{"name": p[len(prefixo):], "created_at": f"2026-11-25T10:00:{i:02d}Z", "metadata": {"size": len(d)}}
                for i, (p, d) in enumerate(sorted(self.arquivos.items())) if p.startswith(prefixo)]

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
def api(monkeypatch, autenticar, vinculos_gerente):
    fake = FakeClient({
        "tasks": [{"id": "t-in", "project_id": PID}, {"id": "t-out", "project_id": OUTRO}],
        "operacionais": [{"id": "o1", "project_id": PID, "email": "pessoa@citi.org.br", "ativo": True}],
    })
    fake.storage = _Storage()
    monkeypatch.setattr("routers.task_anexos.get_client", lambda: fake)
    monkeypatch.setattr(anexos, "_bucket_garantido", False)
    vinculos_gerente["pessoa-teste"] = {PID}
    c = TestClient(app)
    autenticar(c, "gerente")
    c.fake = fake
    c.como = lambda cargo: autenticar(TestClient(app), cargo)
    return c


def _anexar(c, nome="Tela de login.PNG", dados=None, tipo="image/png", task="t-in"):
    return c.post(f"/tasks/{task}/anexos", files={"arquivo": (nome, dados if dados is not None else _png(), tipo)})


def test_gerente_anexa_lista_e_baixa(api):
    r = _anexar(api)
    assert r.status_code == 201
    nome = r.json()["nome"]
    assert nome.endswith("-tela-de-login.png") and r.json()["url"] == f"/tasks/t-in/anexos/{nome}"
    assert [a["nome"] for a in api.get("/tasks/t-in/anexos").json()] == [nome]
    img = api.get(f"/tasks/t-in/anexos/{nome}")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert img.headers["x-content-type-options"] == "nosniff" and img.content == _png()
    assert f"{PID}/t-in/{nome}" in api.fake.storage.arquivos  # guardado na pasta do projeto e da task


def test_bucket_e_criado_na_primeira_vez_e_privado(api):
    _anexar(api)
    assert api.fake.storage.buckets == [anexos.BUCKET]


def test_operacional_do_projeto_ve_mas_nao_anexa_nem_remove(api):
    nome = _anexar(api).json()["nome"]
    op = api.como("operacional")
    assert [a["nome"] for a in op.get("/tasks/t-in/anexos").json()] == [nome]
    assert op.get(f"/tasks/t-in/anexos/{nome}").status_code == 200
    assert _anexar(op).status_code == 403
    assert op.delete(f"/tasks/t-in/anexos/{nome}").status_code == 403
    assert len(api.fake.storage.arquivos) == 1


def test_projeto_de_fora_nao_acessa(api):
    assert _anexar(api, task="t-out").status_code == 403
    assert api.get("/tasks/t-out/anexos").status_code == 403
    assert api.fake.storage.arquivos == {}


@pytest.mark.parametrize("conteudo,tipo", [
    (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "image/svg+xml"),
    (b"MZ nao sou imagem", "image/png"),  # tipo declarado mente
    (b"", "image/png"),
])
def test_recusa_o_que_nao_e_imagem_valida(api, conteudo, tipo):
    assert _anexar(api, dados=conteudo, tipo=tipo).status_code == 422
    assert api.fake.storage.arquivos == {}


def test_recusa_imagem_acima_do_limite(api, monkeypatch):
    monkeypatch.setattr(anexos, "MAX_BYTES", 10)
    r = _anexar(api)
    assert r.status_code == 422 and "MB" in r.json()["detail"]


def test_limite_de_imagens_por_task(api, monkeypatch):
    monkeypatch.setattr(anexos, "MAX_POR_TASK", 2)
    assert _anexar(api).status_code == 201
    assert _anexar(api, nome="b.png").status_code == 201
    r = _anexar(api, nome="c.png")
    assert r.status_code == 422 and "até 2 imagens" in r.json()["detail"]


def test_gerente_remove(api):
    nome = _anexar(api).json()["nome"]
    assert api.delete(f"/tasks/t-in/anexos/{nome}").status_code == 204
    assert api.get("/tasks/t-in/anexos").json() == []


@pytest.mark.parametrize("nome", ["../t-out/x.png", "a.svg", "A.PNG", "x" * 120 + ".png", ".png"])
def test_nome_invalido_da_404_sem_tocar_no_storage(api, nome):
    assert api.get(f"/tasks/t-in/anexos/{nome}").status_code in (404, 405)
    assert api.delete(f"/tasks/t-in/anexos/{nome}").status_code in (404, 405)


def test_excluir_a_task_leva_as_imagens(api):
    _anexar(api)
    assert len(api.fake.storage.arquivos) == 1
    anexos.remover_todos(api.fake, PID, "t-in")
    assert api.fake.storage.arquivos == {}


def test_resumo_do_nome_original_e_seguro():
    nome = anexos.novo_nome("Relatório Final (v2) — ÇÃO.JPG", "jpg")
    assert anexos.nome_valido(nome) and nome.endswith("-relatorio-final-v2-cao.jpg")
    assert anexos.nome_valido(anexos.novo_nome(None, "png"))
