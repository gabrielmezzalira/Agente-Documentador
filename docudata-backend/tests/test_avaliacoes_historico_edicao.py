"""Tela /avaliacoes: histórico, edição auditada e sincronização do snapshot."""
from fastapi.testclient import TestClient

from services.auth import criar_jwt
from tests.fake_supabase import FakeClient


def _seed(com_snapshot=True):
    return {
        "projects": [
            {"id": "proj-1", "name": "PMO", "modo_trabalho": "ATRIBUICAO"},
            {"id": "proj-2", "name": "Visus", "modo_trabalho": "PULL"},
        ],
        "sprints": [
            {"id": "sp-1", "numero": 1, "project_id": "proj-1"},
            {"id": "sp-2", "numero": 2, "project_id": "proj-1"},
            {"id": "sp-9", "numero": 1, "project_id": "proj-2"},
        ],
        "operacionais": [
            {"id": "op-1", "nome": "Victor Lemos"},
            {"id": "op-2", "nome": "Antonio"},
        ],
        "pessoa": [
            {"id": "pessoa-theo", "nome": "Theo"},
            {"id": "pessoa-ger-1", "nome": "Gabriel"},
        ],
        "avaliacoes_gerente": [
            {"id": "aval-1", "operacional_id": "op-1", "gerente_id": "pessoa-theo", "sprint_id": "sp-1",
             "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5, "resposta_5": 5,
             "resposta_6": None, "resposta_7": 5,
             "criado_em": "2026-09-20T12:00:00+00:00", "editavel_ate": "2026-09-22T12:00:00+00:00"},
            {"id": "aval-2", "operacional_id": "op-2", "gerente_id": "pessoa-theo", "sprint_id": "sp-9",
             "resposta_1": 3, "resposta_2": 3, "resposta_3": 3, "resposta_4": 3, "resposta_5": 3,
             "resposta_6": None, "resposta_7": 3,
             "criado_em": "2026-09-20T12:00:00+00:00", "editavel_ate": "2026-09-22T12:00:00+00:00"},
        ],
        "pontuacao_operacional_sprint": (
            [{"id": "pont-1", "sprint_id": "sp-1", "operacional_id": "op-1",
              "gerente_media": 5.0, "gerente_pergunta3": 5, "gerente_pergunta6": None}]
            if com_snapshot else []
        ),
        "avaliacoes_gerente_edicoes": [],
    }


def _tc(monkeypatch, fake, cargo="gerente"):
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: fake)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-ger-1", "ger@citi.com", cargo))
    return tc


_EDICAO = {
    "resposta_1": 4, "resposta_2": 4, "resposta_3": 5, "resposta_4": 5, "resposta_5": 5, "resposta_7": 5,
    "motivo": "Theo tinha dado 4 em P1 e P2",
}


def test_patch_grava_log_atualiza_e_sincroniza_snapshot(monkeypatch):
    fake = FakeClient(_seed())
    tc = _tc(monkeypatch, fake)

    resp = tc.patch("/avaliacoes/aval-1", json=_EDICAO)

    assert resp.status_code == 200
    body = resp.json()
    assert body["resposta_1"] == 4
    assert body["avaliador_nome"] == "Theo"
    assert body["total_edicoes"] == 1
    assert body["ultima_edicao_por"] == "Gabriel"

    aval = next(a for a in fake.tables["avaliacoes_gerente"] if a["id"] == "aval-1")
    assert aval["resposta_2"] == 4
    assert aval["gerente_id"] == "pessoa-theo"  # avaliador original preservado

    [log] = fake.tables["avaliacoes_gerente_edicoes"]
    assert log["avaliacao_id"] == "aval-1"
    assert log["editor_id"] == "pessoa-ger-1"
    assert log["antes"]["resposta_1"] == 5
    assert log["depois"]["resposta_1"] == 4
    assert log["motivo"] == "Theo tinha dado 4 em P1 e P2"

    [snap] = fake.tables["pontuacao_operacional_sprint"]
    assert snap["gerente_media"] == 4.67


def test_patch_sprint_aberta_nao_cria_snapshot(monkeypatch):
    fake = FakeClient(_seed(com_snapshot=False))
    tc = _tc(monkeypatch, fake)

    resp = tc.patch("/avaliacoes/aval-1", json=_EDICAO)

    assert resp.status_code == 200
    assert fake.tables["pontuacao_operacional_sprint"] == []


def test_patch_motivo_em_branco_422(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))
    resp = tc.patch("/avaliacoes/aval-1", json={**_EDICAO, "motivo": "   "})
    assert resp.status_code == 422


def test_patch_nota_fora_da_escala_422(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))
    resp = tc.patch("/avaliacoes/aval-1", json={**_EDICAO, "resposta_1": 6})
    assert resp.status_code == 422


def test_patch_sem_mudanca_422_e_nao_loga(monkeypatch):
    fake = FakeClient(_seed())
    tc = _tc(monkeypatch, fake)
    sem_mudanca = {**_EDICAO, "resposta_1": 5, "resposta_2": 5}

    resp = tc.patch("/avaliacoes/aval-1", json=sem_mudanca)

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Nenhuma nota alterada."
    assert fake.tables["avaliacoes_gerente_edicoes"] == []


def test_patch_inexistente_404(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))
    resp = tc.patch("/avaliacoes/nao-existe", json=_EDICAO)
    assert resp.status_code == 404


def test_patch_operacional_403(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()), cargo="operacional")
    resp = tc.patch("/avaliacoes/aval-1", json=_EDICAO)
    assert resp.status_code == 403


def test_edicoes_lista_mais_recente_primeiro(monkeypatch):
    fake = FakeClient(_seed())
    tc = _tc(monkeypatch, fake)
    tc.patch("/avaliacoes/aval-1", json=_EDICAO)
    fake.tables["avaliacoes_gerente_edicoes"][0]["criado_em"] = "2026-09-25T10:00:00+00:00"
    tc.patch("/avaliacoes/aval-1", json={**_EDICAO, "resposta_4": 3, "motivo": "segunda correção"})
    fake.tables["avaliacoes_gerente_edicoes"][1]["criado_em"] = "2026-09-25T11:00:00+00:00"

    resp = tc.get("/avaliacoes/aval-1/edicoes")

    assert resp.status_code == 200
    itens = resp.json()
    assert [i["motivo"] for i in itens] == ["segunda correção", "Theo tinha dado 4 em P1 e P2"]
    assert itens[0]["editor_nome"] == "Gabriel"


def test_historico_sem_filtro_traz_tudo_com_nomes(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))

    resp = tc.get("/avaliacoes/historico")

    assert resp.status_code == 200
    itens = resp.json()
    assert [i["id"] for i in itens] == ["aval-1", "aval-2"]  # ordenado por projeto_nome: PMO, Visus
    assert itens[0]["projeto_nome"] == "PMO"
    assert itens[0]["sprint_numero"] == 1
    assert itens[0]["operacional_nome"] == "Victor Lemos"
    assert itens[1]["modo_trabalho"] == "PULL"
    assert itens[0]["total_edicoes"] == 0
    assert itens[0]["ultima_edicao_em"] is None


def test_historico_filtra_por_projeto_e_sprint(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))

    por_projeto = tc.get("/avaliacoes/historico", params={"project_id": "proj-2"}).json()
    por_sprint = tc.get("/avaliacoes/historico", params={"sprint_id": "sp-1"}).json()
    projeto_sem_sprint = tc.get("/avaliacoes/historico", params={"project_id": "proj-x"}).json()

    assert [i["id"] for i in por_projeto] == ["aval-2"]
    assert [i["id"] for i in por_sprint] == ["aval-1"]
    assert projeto_sem_sprint == []


def test_historico_operacional_403(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()), cargo="operacional")
    assert tc.get("/avaliacoes/historico").status_code == 403


def test_post_apos_fechamento_sincroniza_snapshot(monkeypatch):
    seed = _seed()
    seed["avaliacoes_gerente"] = []  # avaliação ainda não existia quando a sprint fechou
    seed["pontuacao_operacional_sprint"][0].update(gerente_media=None, gerente_pergunta3=None)
    fake = FakeClient(seed)
    tc = _tc(monkeypatch, fake)

    resp = tc.post("/avaliacoes", json={
        "operacional_id": "op-1", "sprint_id": "sp-1",
        "resposta_1": 4, "resposta_2": 4, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_7": 5,
    })

    assert resp.status_code == 201
    [snap] = fake.tables["pontuacao_operacional_sprint"]
    assert snap["gerente_media"] == 4.67
    assert snap["gerente_pergunta3"] == 5
