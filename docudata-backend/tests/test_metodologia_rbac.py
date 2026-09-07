"""GET /metodologia/{slug} — documento interno restrito a Líder e Gerente.

O conteúdo é a camada oculta do sistema de performance (pesos, fórmulas, notas
cruas), então o gate `require_not_operacional` é parte do contrato, não detalhe
de implementação.
"""
from fastapi.testclient import TestClient

from services.auth import criar_jwt

_SECRET = "test-secret-nao-usar-em-producao"


def test_sem_cookie_retorna_401():
    from main import app
    tc = TestClient(app)

    resp = tc.get("/metodologia/performance")

    assert resp.status_code == 401


def test_operacional_bloqueado_na_metodologia_completa(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    resp = tc.get("/metodologia/performance", cookies={"docudata_session": token})

    assert resp.status_code == 403


def test_operacional_le_os_documentos_publicos(monkeypatch):
    """Guia do sistema e versão pública do acompanhamento são para todo mundo."""
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-op-1", "op@citi.com", "operacional")

    for slug in ("guia", "acompanhamento"):
        resp = tc.get(f"/metodologia/{slug}", cookies={"docudata_session": token})
        assert resp.status_code == 200, slug
        assert resp.json()["restrito"] is False
        assert len(resp.json()["conteudo"]) > 500


def test_listagem_esconde_o_documento_restrito_do_operacional(monkeypatch):
    """Não adianta listar o que a pessoa não vai conseguir abrir."""
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)

    op = tc.get("/metodologia", cookies={"docudata_session": criar_jwt("op", "op@citi.com", "operacional")})
    ger = tc.get("/metodologia", cookies={"docudata_session": criar_jwt("g", "g@citi.com", "gerente")})

    slugs_op = {d["slug"] for d in op.json()}
    slugs_ger = {d["slug"] for d in ger.json()}
    assert "performance" not in slugs_op
    assert slugs_op == {"guia", "acompanhamento"}
    assert "performance" in slugs_ger


def test_documento_publico_nao_expoe_a_camada_oculta():
    """Dizer que os pesos não são divulgados é o ponto do documento; o que ele não
    pode ter é o número de nenhum peso, nem a mecânica do cálculo."""
    import re
    from pathlib import Path
    conteudo = (Path(__file__).resolve().parent.parent / "docs" / "acompanhamento-publico.md").read_text()

    percentuais = re.findall(r"\d+\s*%", conteudo)
    assert percentuais == [], f"documento público expõe percentuais: {percentuais}"

    baixo = conteudo.lower()
    for proibido in ("score", "sub-score", "dividido pelo", "multiplicado", "0,35", "0.35"):
        assert proibido not in baixo, f"documento público menciona '{proibido}'"


def test_gerente_recebe_o_documento(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-ger-1", "ger@citi.com", "gerente")

    resp = tc.get("/metodologia/performance", cookies={"docudata_session": token})

    assert resp.status_code == 200
    body = resp.json()
    assert body["titulo"] == "Sistema de Acompanhamento de Performance"
    assert "Avaliação do Gerente" in body["conteudo"]


def test_lider_recebe_o_documento(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-lid-1", "lider@citi.com", "lider")

    resp = tc.get("/metodologia/performance", cookies={"docudata_session": token})

    assert resp.status_code == 200
    assert len(resp.json()["conteudo"]) > 1000


def test_slug_desconhecido_404(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    from main import app
    tc = TestClient(app)
    token = criar_jwt("pessoa-lid-1", "lider@citi.com", "lider")

    resp = tc.get("/metodologia/inexistente", cookies={"docudata_session": token})

    assert resp.status_code == 404
