"""Acesso por projeto nas rotas de documentos e geração por IA.

Gerente de fora leva 403 antes de qualquer upload, chamada ao Gemini ou
invocação de grafo; gerente vinculado passa pela conferência de acesso.
"""
import io
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app

PID, OUTRO = "proj-1", "proj-2"
PASSOU = 418  # sentinela: o vinculado passou da conferência de acesso


class Fake:
    def __init__(self):
        self.t = {
            "pessoa": [{"id": "pessoa-teste", "nome": "Eu", "email": "pessoa@citi.org.br", "cargo": "gerente"}],
            "projects": [
                {"id": PID, "name": "A", "client": "C", "squad": "s", "subarea": "dados"},
                {"id": OUTRO, "name": "B", "client": "C", "squad": "s", "subarea": "dados"},
            ],
            "generated_docs": [
                {"id": "d-in", "project_id": PID, "doc_type": "planning", "content": "x", "created_at": "2026-01-01"},
                {"id": "d-out", "project_id": OUTRO, "doc_type": "planning", "content": "x", "created_at": "2026-01-01"},
            ],
            "ingestions": [
                {"id": "i-in", "project_id": PID, "sprint_number": 1, "file_name": "a", "file_type": "texto",
                 "extracted_content": {}, "created_at": "2026-01-01"},
                {"id": "i-out", "project_id": OUTRO, "sprint_number": 1, "file_name": "a", "file_type": "texto",
                 "extracted_content": {}, "created_at": "2026-01-01"},
            ],
            "operacionais": [],
        }
        self.writes = []

    def table(self, name):
        return Q(self, name)


class Q:
    def __init__(self, db, name):
        self.db, self.name, self.f, self.op, self.payload = db, name, [], "select", None

    def __getattr__(self, _nome):  # order/limit/range/gte/... são irrelevantes aqui
        return lambda *a, **k: self

    def eq(self, c, v): self.f.append((c, lambda x: x == v)); return self
    def in_(self, c, vs): self.f.append((c, lambda x: x in vs)); return self
    def insert(self, p): self.op, self.payload = "insert", p; return self
    def update(self, p): self.op, self.payload = "update", p; return self
    def delete(self): self.op = "delete"; return self

    def execute(self):
        rows = self.db.t.setdefault(self.name, [])
        match = [r for r in rows if all(fn(r.get(c)) for c, fn in self.f)]
        r = MagicMock()
        if self.op != "select":
            self.db.writes.append((self.name, self.op))
        if self.op == "insert":
            row = {"id": "novo", "created_at": "2026-01-03", **self.payload}
            rows.append(row); r.data = [row]
        elif self.op == "update":
            for m in match: m.update(self.payload)
            r.data = match
        elif self.op == "delete":
            for m in match: rows.remove(m)
            r.data = match
        else:
            r.data = match
        return r


def _gemini_proibido(*a, **k):
    raise HTTPException(status_code=PASSOU, detail="chegou ao Gemini")


class _GrafoProibido:
    def invoke(self, *a, **k):
        raise HTTPException(status_code=PASSOU, detail="chegou ao grafo")

    async def ainvoke(self, *a, **k):
        raise HTTPException(status_code=PASSOU, detail="chegou ao grafo")


@pytest.fixture
def api(monkeypatch, autenticar, vinculos_gerente):
    fake = Fake()
    for mod in ("generate", "export", "ingest", "ingestions", "enrich", "sprint_docs", "composer", "boletins"):
        monkeypatch.setattr(f"routers.{mod}.get_client", lambda: fake)
    monkeypatch.setattr("services.auth.get_client", lambda: fake)
    for mod in ("generate", "ingest", "enrich", "sprint_docs", "composer"):
        if mod != "composer":
            monkeypatch.setattr(f"routers.{mod}.get_gemini_api_key", _gemini_proibido)
    monkeypatch.setattr("routers.composer.get_gemini_api_key", _gemini_proibido)
    for mod, nome in (("generate", "generation_graph"), ("ingest", "extraction_graph"),
                      ("sprint_docs", "generation_graph"), ("sprint_docs", "extraction_graph")):
        monkeypatch.setattr(f"routers.{mod}.{nome}", _GrafoProibido())
    monkeypatch.setattr("routers.export.export_to_gdocs", lambda **k: (_ for _ in ()).throw(
        HTTPException(status_code=PASSOU, detail="chegou ao Google")))
    vinculos_gerente["pessoa-teste"] = {PID}
    c = TestClient(app, raise_server_exceptions=False)
    autenticar(c, "gerente")
    c.fake = fake
    return c


def _pdf():
    return {"arquivo": ("a.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}


# ---- generate ----
def test_generate_de_fora_403_antes_do_grafo(api):
    corpo = {"projeto_id": OUTRO, "tipo_doc": "repasse_semanal", "sprint_numero": 1}
    assert api.post("/generate", json=corpo).status_code == 403
    assert api.post("/generate", json={**corpo, "projeto_id": PID}).status_code == PASSOU


def test_docs_listar_criar_editar_apagar(api):
    assert api.get(f"/docs/{OUTRO}").status_code == 403
    assert api.get(f"/docs/{PID}").status_code == 200
    manual = {"projeto_id": OUTRO, "doc_type": "planning", "content": "x"}
    assert api.post("/docs/manual", json=manual).status_code == 403
    assert api.post("/docs/manual", json={**manual, "projeto_id": PID}).status_code == 201
    assert api.post("/docs/manual/upload", data={"projeto_id": OUTRO, "doc_type": "planning"}, files=_pdf()).status_code == 403
    assert api.patch("/docs/d-out", json={"content": "y"}).status_code == 403
    assert api.delete("/docs/d-out").status_code == 403
    assert not [w for w in api.fake.writes if w != ("generated_docs", "insert")]
    assert any(d["id"] == "d-out" and d["content"] == "x" for d in api.fake.t["generated_docs"])
    assert api.patch("/docs/d-in", json={"content": "y"}).status_code == 200
    assert api.delete("/docs/d-in").status_code == 204


def test_docs_inexistente_404(api):
    assert api.delete("/docs/nao-existe").status_code == 404


# ---- export ----
def test_export_gdocs(api):
    assert api.post("/docs/d-out/export-gdocs").status_code == 403
    assert api.post("/docs/d-in/export-gdocs").status_code == 502  # passou do acesso; o Google falha de propósito


# ---- ingest / ingestions ----
def test_ingest_de_fora_403_antes_de_tudo(api):
    arq = {"arquivo": ("a.txt", io.BytesIO(b"oi"), "text/plain")}
    assert api.post("/ingest", data={"projeto_id": OUTRO, "sprint_numero": "1"}, files=arq).status_code == 403
    arq = {"arquivo": ("a.txt", io.BytesIO(b"oi"), "text/plain")}
    assert api.post("/ingest", data={"projeto_id": PID, "sprint_numero": "1"}, files=arq).status_code == PASSOU


def test_ingestions(api):
    assert api.get(f"/ingestions/{OUTRO}").status_code == 403
    assert api.get(f"/ingestions/{OUTRO}/1").status_code == 403
    assert api.get(f"/ingestions/{PID}").status_code == 200
    assert api.get(f"/ingestions/{PID}/1").status_code == 200
    assert api.patch("/ingestions/i-out", json={"sprint_number": 2}).status_code == 403
    assert api.delete("/ingestions/i-out").status_code == 403
    assert api.fake.writes == []
    assert api.patch("/ingestions/i-in", json={"sprint_number": 2}).status_code == 200
    assert api.delete("/ingestions/i-in").status_code == 204


# ---- enrich ----
def test_enrich_de_fora_403_antes_do_modelo(api):
    assert api.post("/enrich", data={"projeto_id": OUTRO, "doc_type": "planning", "texto": "x"}).status_code == 403
    assert api.post("/enrich", data={"projeto_id": PID, "doc_type": "planning", "texto": "x"}).status_code == PASSOU
    assert api.post("/enrich/planning-correlacoes", data={"projeto_id": OUTRO, "texto": "x"}).status_code == 403
    assert api.post("/enrich/planning-correlacoes", data={"projeto_id": PID, "texto": "x"}).status_code == PASSOU


# ---- sprint_docs ----
_PLANNING = {"sprint_numero": "1", "descricao": "d", "squad": "s", "periodo_inicio": "2026-01-01",
             "periodo_fim": "2026-01-14", "horas_disponiveis": "10", "horas_estimadas": "10",
             "sem_dependencias": "true", "sem_riscos": "true", "sem_carry_over": "true"}
_REVIEW = {"sprint_numero": "1", "observacoes": "o", "percepcao_cliente": "p", "sinal_satisfacao": "ok",
           "squad": "s", "periodo_inicio": "2026-01-01", "periodo_fim": "2026-01-14", "subarea": "dados",
           "percentual_itens_prontos": "1 de 1", "sem_pedidos_fora_escopo": "true", "sem_itens_proxima_sprint": "true"}
_DAILY = {"sprint_numero": "1", "data": "2026-01-02", "feito": "a", "proximo": "b"}
_RETRO = {"sprint_numero": "1"}


@pytest.mark.parametrize("rota,campos", [
    ("planning", _PLANNING), ("review", _REVIEW), ("daily", _DAILY), ("retrospectiva", _RETRO),
])
def test_sprint_docs_forms(api, rota, campos):
    assert api.post(f"/sprint-docs/{rota}", data={**campos, "projeto_id": OUTRO}).status_code == 403
    assert api.fake.writes == []
    assert api.post(f"/sprint-docs/{rota}", data={**campos, "projeto_id": PID}).status_code != 403


def test_sprint_docs_ata(api):
    def anexo():
        return {"anexo": ("a.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}
    assert api.post("/sprint-docs/ata", data={"projeto_id": OUTRO, "sprint_numero": "1"}, files=anexo()).status_code == 403
    assert api.post("/sprint-docs/ata", data={"projeto_id": PID, "sprint_numero": "1"}, files=anexo()).status_code != 403


def test_sprint_docs_planejado_entregue(api):
    q = {"sprint_numero": 1}
    assert api.get("/sprint-docs/review/planejado-entregue", params={**q, "projeto_id": OUTRO}).status_code == 403
    assert api.get("/sprint-docs/review/planejado-entregue", params={**q, "projeto_id": PID}).status_code != 403


# ---- composer ----
def test_composer(api, monkeypatch):
    monkeypatch.setattr("routers.composer.ChatGoogleGenerativeAI", _gemini_proibido)
    assert api.get(f"/composer/rascunho/{OUTRO}/1").status_code == 403
    assert api.patch(f"/composer/rascunho/{OUTRO}/1", json={"step_atual": 1, "dados_json": {}}).status_code == 403
    assert api.post("/composer/confirmar", json={"project_id": OUTRO, "sprint_numero": 1, "markdown": "x"}).status_code == 403
    assert api.post("/composer/gerar", json={"project_id": OUTRO, "sprint_numero": 1}).status_code == 403
    assert api.fake.writes == []
    assert api.get(f"/composer/rascunho/{PID}/1").status_code != 403
    assert api.patch(f"/composer/rascunho/{PID}/1", json={"step_atual": 1, "dados_json": {}}).status_code == 404
    assert api.post("/composer/confirmar", json={"project_id": PID, "sprint_numero": 1, "markdown": "x"}).status_code == 404
    assert api.post("/composer/gerar", json={"project_id": PID, "sprint_numero": 1}).status_code == 404


# ---- boletins ----
def test_boletins_resumo_semanal(api):
    assert api.post("/boletins/resumo_semanal", json={"project_id": OUTRO}).status_code == 403
    assert api.fake.writes == []
    assert api.post("/boletins/resumo_semanal", json={"project_id": PID}).status_code != 403
