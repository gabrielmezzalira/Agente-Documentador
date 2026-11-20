"""Propostas de melhoria (PTA): o operacional propõe, o PM decide e a aprovada
vira task de inovação com bônus de pontuação no fechamento."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.performance import BONUS_EXTRA_POR_PONTO, BONUS_EXTRA_TETO, BONUS_INOVACAO_FATOR, _bonus_extra
from services.pontuacao import calcular_e_travar_pontuacao
from tests.fake_supabase import FakeClient
from tests.test_pontuacao_fechamento import _mock_client

SCHEMA = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")
DETAIL_NAO_PTA = "Propostas de melhoria só existem em projetos PTA."
EMAIL = "pessoa@citi.org.br"  # e-mail do JWT da fixture `autenticar`


def _fake(subarea="pta", modo="ATRIBUICAO", sou_da_equipe=True, iniciada=True):
    ops = [{"id": "op-2", "project_id": "p1", "nome": "Outra", "email": "outra@citi.org.br", "ativo": True}]
    if sou_da_equipe:
        ops.append({"id": "op-1", "project_id": "p1", "nome": "Eu", "email": EMAIL, "ativo": True})
    return FakeClient(
        {
            "projects": [{"id": "p1", "name": "Proj", "subarea": subarea, "modo_trabalho": modo}],
            "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": iniciada}],
            "operacionais": ops,
            "tasks": [],
            "task_classificacoes": [],
            "propostas_melhoria": [],
            "ingestions": [],
        },
        defaults={"propostas_melhoria": {"status": "pendente", "motivo": None, "decidido_por": None,
                                         "decidido_em": None, "task_id": None, "sprint_id": None,
                                         "criado_em": "2026-11-18T10:00:00+00:00"},
                  "tasks": {"bloqueado": False, "created_at": "2026-11-18T10:00:00+00:00",
                            "updated_at": "2026-11-18T10:00:00+00:00"}},
    )


def _api(monkeypatch, autenticar, fake, cargo="operacional"):
    import routers.propostas as router
    from main import app
    import services.auth as auth
    monkeypatch.setattr(router, "get_client", lambda: fake)
    monkeypatch.setattr(auth, "get_client", lambda: fake)  # require_project_access (operacional)
    return autenticar(TestClient(app), cargo=cargo)


CORPO = {"titulo": "Automatizar o relatório", "valor_cliente": "Economiza 3h por semana", "esforco": 3}


def _proposta(fake, **kw):
    row = {"id": "pr1", "project_id": "p1", "operacional_id": "op-1", "titulo": "Automatizar",
           "valor_cliente": "Valor X", "esforco": 3}
    row.update(kw)
    fake.tables["propostas_melhoria"].append(_com_defaults(row))
    return row


def _com_defaults(row):
    return {"status": "pendente", "motivo": None, "decidido_por": None, "decidido_em": None,
            "task_id": None, "sprint_id": None, "criado_em": "2026-11-18T10:00:00+00:00", **row}


# 1. criação ---------------------------------------------------------------

def test_operacional_cria_proposta(monkeypatch, autenticar):
    fake = _fake()
    r = _api(monkeypatch, autenticar, fake).post("/projects/p1/propostas", json=CORPO)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pendente"
    assert r.json()["operacional_id"] == "op-1"
    assert fake.tables["propostas_melhoria"][0]["esforco"] == 3


def test_projeto_nao_pta_422(monkeypatch, autenticar):
    r = _api(monkeypatch, autenticar, _fake(subarea="dados")).post("/projects/p1/propostas", json=CORPO)
    assert r.status_code == 422
    assert r.json()["detail"] == DETAIL_NAO_PTA


@pytest.mark.parametrize("campos", [{"esforco": 4}, {"titulo": "ab"}, {"valor_cliente": ""}])
def test_proposta_invalida_422(monkeypatch, autenticar, campos):
    r = _api(monkeypatch, autenticar, _fake()).post("/projects/p1/propostas", json={**CORPO, **campos})
    assert r.status_code == 422


def test_pessoa_fora_da_equipe_403(monkeypatch, autenticar):
    r = _api(monkeypatch, autenticar, _fake(sou_da_equipe=False)).post("/projects/p1/propostas", json=CORPO)
    assert r.status_code == 403


# 2. gerente não propõe ------------------------------------------------------

def test_gerente_nao_cria_proposta_403(monkeypatch, autenticar):
    r = _api(monkeypatch, autenticar, _fake(), cargo="gerente").post("/projects/p1/propostas", json=CORPO)
    assert r.status_code == 403


# 3. listagem ----------------------------------------------------------------

def test_listagem_gerente_ve_todas_e_operacional_so_as_proprias(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["propostas_melhoria"] += [
        _com_defaults({"id": "a", "project_id": "p1", "operacional_id": "op-1", "titulo": "A", "valor_cliente": "v",
                       "esforco": 1, "status": "recusada", "criado_em": "2026-11-18T09:00:00+00:00"}),
        _com_defaults({"id": "b", "project_id": "p1", "operacional_id": "op-2", "titulo": "B", "valor_cliente": "v",
                       "esforco": 2, "status": "aprovada", "criado_em": "2026-11-18T12:00:00+00:00"}),
        _com_defaults({"id": "c", "project_id": "p1", "operacional_id": "op-2", "titulo": "C", "valor_cliente": "v",
                       "esforco": 2, "status": "pendente", "criado_em": "2026-11-18T08:00:00+00:00"}),
        _com_defaults({"id": "d", "project_id": "p1", "operacional_id": "op-1", "titulo": "D", "valor_cliente": "v",
                       "esforco": 2, "status": "adiada", "criado_em": "2026-11-18T07:00:00+00:00"}),
    ]
    ger = _api(monkeypatch, autenticar, fake, cargo="gerente").get("/projects/p1/propostas")
    assert ger.status_code == 200
    assert [p["id"] for p in ger.json()] == ["c", "d", "b", "a"]
    assert ger.json()[0]["operacional_nome"] == "Outra"
    op = _api(monkeypatch, autenticar, fake).get("/projects/p1/propostas")
    assert sorted(p["id"] for p in op.json()) == ["a", "d"]


def test_listagem_em_projeto_nao_pta_422(monkeypatch, autenticar):
    r = _api(monkeypatch, autenticar, _fake(subarea="dev"), cargo="gerente").get("/projects/p1/propostas")
    assert r.status_code == 422 and r.json()["detail"] == DETAIL_NAO_PTA


# 4/5. aprovação -------------------------------------------------------------

def test_aprovar_em_atribuicao_cria_task_de_inovacao(monkeypatch, autenticar):
    fake = _fake()
    _proposta(fake)
    r = _api(monkeypatch, autenticar, fake, cargo="gerente").post("/propostas/pr1/decisao", json={"acao": "aprovar"})
    assert r.status_code == 200, r.text
    task = fake.tables["tasks"][0]
    assert task["extra"] is True and task["inovacao"] is True
    assert task["pontos"] == 3 and task["operacional_id"] == "op-1" and task["sprint_id"] == "s1"
    assert task["coluna_kanban"] == "planejado"
    assert task["descricao"] == "Valor para o cliente: Valor X"
    assert fake.tables["task_classificacoes"][0]["status"] == "manual"
    prop = fake.tables["propostas_melhoria"][0]
    assert prop["status"] == "aprovada" and prop["task_id"] == task["id"] and prop["sprint_id"] == "s1"
    assert prop["decidido_por"] == "pessoa-teste" and prop["decidido_em"]
    assert r.json()["task_id"] == task["id"]


def test_aprovar_em_pull_deixa_task_sem_dono(monkeypatch, autenticar):
    fake = _fake(modo="PULL")
    _proposta(fake)
    r = _api(monkeypatch, autenticar, fake, cargo="lider").post("/propostas/pr1/decisao", json={"acao": "aprovar"})
    assert r.status_code == 200, r.text
    assert fake.tables["tasks"][0].get("operacional_id") is None


# 6. recusa, adiamento, 409 --------------------------------------------------

def test_recusar_sem_motivo_422_e_com_motivo_grava(monkeypatch, autenticar):
    fake = _fake()
    _proposta(fake)
    c = _api(monkeypatch, autenticar, fake, cargo="gerente")
    assert c.post("/propostas/pr1/decisao", json={"acao": "recusar"}).status_code == 422
    assert c.post("/propostas/pr1/decisao", json={"acao": "recusar", "motivo": "  "}).status_code == 422
    r = c.post("/propostas/pr1/decisao", json={"acao": "recusar", "motivo": "Fora do escopo"})
    assert r.status_code == 200
    assert fake.tables["propostas_melhoria"][0]["status"] == "recusada"
    assert fake.tables["propostas_melhoria"][0]["motivo"] == "Fora do escopo"
    assert fake.tables["tasks"] == []


@pytest.mark.parametrize("status", ["recusada", "aprovada"])
def test_decidir_de_novo_409(monkeypatch, autenticar, status):
    fake = _fake()
    _proposta(fake, status=status)
    r = _api(monkeypatch, autenticar, fake, cargo="gerente").post("/propostas/pr1/decisao", json={"acao": "adiar"})
    assert r.status_code == 409


def test_adiada_pode_ser_aprovada_depois(monkeypatch, autenticar):
    fake = _fake()
    _proposta(fake)
    c = _api(monkeypatch, autenticar, fake, cargo="gerente")
    assert c.post("/propostas/pr1/decisao", json={"acao": "adiar"}).status_code == 200
    assert fake.tables["propostas_melhoria"][0]["status"] == "adiada"
    assert c.post("/propostas/pr1/decisao", json={"acao": "aprovar"}).status_code == 200
    assert fake.tables["propostas_melhoria"][0]["status"] == "aprovada"


def test_decisao_em_projeto_nao_pta_422(monkeypatch, autenticar):
    fake = _fake(subarea="dados")
    _proposta(fake)
    r = _api(monkeypatch, autenticar, fake, cargo="gerente").post("/propostas/pr1/decisao", json={"acao": "aprovar"})
    assert r.status_code == 422 and r.json()["detail"] == DETAIL_NAO_PTA


def test_proposta_inexistente_404(monkeypatch, autenticar):
    r = _api(monkeypatch, autenticar, _fake(), cargo="gerente").post("/propostas/x/decisao", json={"acao": "adiar"})
    assert r.status_code == 404


def test_decisao_concorrente_409_e_nao_deixa_task_orfa(monkeypatch, autenticar):
    """Outra decisão vence entre a checagem de status e o update final."""
    import routers.propostas as router
    fake = _fake()
    _proposta(fake)
    original = router._aprovar

    def aprovar_e_perde_a_corrida(*a, **kw):
        resultado = original(*a, **kw)
        fake.tables["propostas_melhoria"][0]["status"] = "recusada"
        return resultado

    monkeypatch.setattr(router, "_aprovar", aprovar_e_perde_a_corrida)
    r = _api(monkeypatch, autenticar, fake, cargo="gerente").post("/propostas/pr1/decisao", json={"acao": "aprovar"})
    assert r.status_code == 409
    assert fake.tables["tasks"] == []
    assert fake.tables["propostas_melhoria"][0]["status"] == "recusada"
    assert fake.tables["propostas_melhoria"][0]["task_id"] is None


# 7. operacional não decide --------------------------------------------------

def test_operacional_nao_decide_403(monkeypatch, autenticar):
    fake = _fake()
    _proposta(fake)
    r = _api(monkeypatch, autenticar, fake).post("/propostas/pr1/decisao", json={"acao": "aprovar"})
    assert r.status_code == 403


# 8. fechamento --------------------------------------------------------------

_SPRINT = {"id": "sprint-1", "project_id": "proj-1"}


def _op(op_id):
    return {"id": op_id, "nome": op_id, "email": None, "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None}


def _com_propostas(client, propostas=None, erro=False):
    original = client.table.side_effect

    def table(name):
        if name != "propostas_melhoria":
            return original(name)
        from unittest.mock import MagicMock
        tbl = MagicMock()
        q = MagicMock()
        q.eq.return_value = q
        if erro:
            q.execute.side_effect = RuntimeError('relation "propostas_melhoria" does not exist')
        else:
            q.execute.return_value = MagicMock(data=propostas or [])
        tbl.select.return_value = q
        return tbl

    client.table.side_effect = table
    return client


def test_fechamento_soma_bonus_de_inovacao_e_grava_eventos():
    insert, eventos = [], []
    client = _mock_client(sprint=_SPRINT, operacionais=[_op("op-a")], insert_capture=insert,
                          eventos_insert_capture=eventos)
    _com_propostas(client, [
        {"id": "pr1", "operacional_id": "op-a", "esforco": 3, "task_id": "t1"},
        {"id": "pr2", "operacional_id": "op-a", "esforco": 2, "task_id": "t2"},
    ])
    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]
    assert linha["bonus_pontos_inovacao"] == 5
    ev = [e for e in eventos if e["tipo"] == "bonus_inovacao"]
    assert sorted(e["pontos"] for e in ev) == [2, 3]
    assert all(e["descricao"] == "Proposta de melhoria aprovada" for e in ev)


def test_pessoa_so_com_inovacao_ganha_linha():
    client = _mock_client(sprint=_SPRINT, operacionais=[])
    _com_propostas(client, [{"id": "pr1", "operacional_id": "op-z", "esforco": 5, "task_id": "t1"}])
    # sem tasks nem vinculados o fechamento retorna cedo; com uma task de outra pessoa a linha existe
    client = _mock_client(
        sprint=_SPRINT, operacionais=[],
        tasks=[{"id": "t9", "operacional_id": "op-a", "pontos": 1, "coluna_kanban": "planejado", "extra": False,
                "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None,
                "bloqueado_manual": False, "bloqueio_tipo": None}],
    )
    _com_propostas(client, [{"id": "pr1", "operacional_id": "op-z", "esforco": 5, "task_id": "t1"}])
    por_op = {r["operacional_id"]: r for r in calcular_e_travar_pontuacao(client, "sprint-1")}
    assert por_op["op-z"]["bonus_pontos_inovacao"] == 5


def test_task_de_inovacao_concluida_nao_gera_bonus_extra():
    eventos = []
    client = _mock_client(
        sprint=_SPRINT, operacionais=[_op("op-a")], eventos_insert_capture=eventos,
        tasks=[{"id": "t1", "operacional_id": "op-a", "pontos": 3, "coluna_kanban": "concluida", "extra": True,
                "inovacao": True, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None,
                "bloqueado_manual": False, "bloqueio_tipo": None}],
        task_transicoes=[{"task_id": "t1", "operacional_id": "op-a", "timestamp": "2026-09-02T00:00:00Z"}],
    )
    _com_propostas(client, [])
    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]
    assert linha["bonus_pontos_extra"] == 0
    assert "bonus_pontos_inovacao" not in linha
    assert not [e for e in eventos if e["tipo"] == "bonus_extra"]


def test_falha_ao_ler_propostas_nao_quebra_o_fechamento():
    insert = []
    client = _mock_client(sprint=_SPRINT, operacionais=[_op("op-a")], insert_capture=insert)
    _com_propostas(client, erro=True)
    linhas = calcular_e_travar_pontuacao(client, "sprint-1")
    assert len(linhas) == 1
    assert "bonus_pontos_inovacao" not in insert[0][0]


# 9. performance -------------------------------------------------------------

def test_bonus_extra_conta_inovacao_com_fator():
    assert BONUS_INOVACAO_FATOR == 0.5
    assert _bonus_extra([{"bonus_pontos_extra": 0, "bonus_pontos_inovacao": 4}]) == 4 * 0.5 * BONUS_EXTRA_POR_PONTO


def test_bonus_extra_teto_vale_para_a_soma():
    assert _bonus_extra([{"bonus_pontos_extra": 4, "bonus_pontos_inovacao": 10}]) == BONUS_EXTRA_TETO


# 10. reabertura -------------------------------------------------------------

def test_reabrir_apaga_bonus_inovacao(monkeypatch, autenticar):
    import routers.avaliacoes as router
    from main import app
    fake = FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "avaliacao_completa_em": "2026-11-01T10:00:00+00:00"}],
        "pontuacao_operacional_sprint": [], "eventos_pontuacao_tardios": [],
        "pontuacao_eventos": [{"id": "e1", "sprint_id": "s1", "tipo": "bonus_inovacao", "pontos": 3}],
    })
    monkeypatch.setattr(router, "get_client", lambda: fake)
    assert autenticar(TestClient(app), cargo="lider").delete("/avaliacoes/s1/confirmar").status_code == 200
    assert fake.tables["pontuacao_eventos"] == []


# 11. schema -----------------------------------------------------------------

def test_migracao_v14_comentada_com_preflight_e_rollback():
    ini = SCHEMA.rindex("\n", 0, SCHEMA.index("Migration v14 (2026-11-18): propostas de melhoria (PTA)")) + 1
    b = SCHEMA[ini:]
    for trecho in ("propostas_melhoria", "inovacao boolean NOT NULL DEFAULT false",
                   "bonus_pontos_inovacao int NOT NULL DEFAULT 0", "bonus_inovacao",
                   "esforco IN (1,2,3,5)", "'pendente','aprovada','recusada','adiada'", "Preflight", "Rollback"):
        assert trecho in b, trecho
    for linha in b.splitlines():
        assert not linha.strip() or linha.startswith("--"), linha
