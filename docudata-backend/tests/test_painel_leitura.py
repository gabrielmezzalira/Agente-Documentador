"""Leitura para o Painel do Projeto CITi: chave dedicada e formato das respostas."""
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from main import app
from services import painel_leitura as pl
from tests.fake_supabase import FakeClient

PID = "11111111-1111-4111-8111-111111111111"
SPRINT = "22222222-2222-4222-8222-222222222222"
OP = "33333333-3333-4333-8333-333333333333"
CHAVE = "chave-do-painel-para-testes"


def _tabelas():
    return {
        "projects": [
            {
                "id": PID,
                "name": "Visus",
                "data_inicio": "2026-08-31",
                "data_fim_contratada": "2026-10-09",
                "tolerancia_desvio_pontos": 20,
            }
        ],
        "sprints": [
            {"id": SPRINT, "project_id": PID, "numero": 4, "status_saude": None, "iniciada": True,
             "data_inicio": "2026-09-28", "data_fim": "2026-10-02"},
            {"id": "s-3", "project_id": PID, "numero": 3, "status_saude": "verde", "iniciada": True,
             "data_inicio": "2026-09-21", "data_fim": "2026-09-25"},
        ],
        "tasks": [
            {"id": "t-1", "project_id": PID, "sprint_id": SPRINT, "operacional_id": OP, "titulo": "ETL vendas",
             "pontos": 5, "coluna_kanban": "concluida", "extra": False, "prevista_no_inicio": True,
             "surgiu_na_sprint": False, "checklist": [{"texto": "a", "done": True}],
             "bloqueado_manual": False, "bloqueio_tipo": None, "bloqueado_em": None},
            {"id": "t-2", "project_id": PID, "sprint_id": SPRINT, "operacional_id": None, "titulo": "Acesso ao Data Lake",
             "pontos": 3, "coluna_kanban": "em_andamento", "extra": False, "prevista_no_inicio": True,
             "surgiu_na_sprint": False, "checklist": [{"texto": "a", "done": True}, {"texto": "b", "done": False}],
             "bloqueado_manual": True, "bloqueio_tipo": "cliente", "bloqueado_em": "2026-09-29T12:00:00+00:00"},
        ],
        "task_transicoes": [
            {"id": "x-1", "task_id": "t-1", "campo": "coluna_kanban", "de": "em_andamento", "para": "concluida",
             "timestamp": "2026-09-30T15:00:00+00:00"},
        ],
        "operacionais": [{"id": OP, "project_id": PID, "nome": "Ana", "papel": "Analista", "ativo": True}],
        "funcionalidades": [
            {"id": "f-1", "project_id": PID, "id_funcional": "E1", "titulo": "Mapeamento", "prioridade": "must",
             "status": "concluida", "criterios_aceite": ["Ambientes mapeados"], "sprint_alvo": "3"},
        ],
        "generated_docs": [
            {"id": "d-1", "project_id": PID, "doc_type": "ata_reuniao", "sprint_number": 4,
             "content": "# Reunião de 30 set\nDecidimos X.", "created_at": "2026-09-30T18:00:00+00:00"},
            {"id": "d-2", "project_id": PID, "doc_type": "repasse_semanal", "sprint_number": 4,
             "content": "texto", "created_at": "2026-10-02T18:00:00+00:00"},
        ],
        "commit_qualidade": [
            {"id": "c-1", "projeto_id": PID, "criado_em": "2026-09-29T10:00:00+00:00"},
            {"id": "c-2", "projeto_id": PID, "criado_em": "2026-09-30T10:00:00+00:00"},
            {"id": "c-3", "projeto_id": PID, "criado_em": "2026-10-20T10:00:00+00:00"},
        ],
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOCUDATA_PAINEL_KEY", CHAVE)
    fake = FakeClient(tables=_tabelas())
    monkeypatch.setattr("routers.painel_leitura.get_client", lambda: fake)
    monkeypatch.setattr("routers.painel_leitura.previsto_da_sprint", lambda c, sid: {"previsto": 8})
    return TestClient(app)


H = {"X-Painel-Key": CHAVE}
BASE = f"/integracoes/painel/v1/projetos/{PID}"


class TestChave:
    def test_sem_chave_401(self, client):
        assert client.get(f"{BASE}/kanban").status_code == 401

    def test_chave_errada_401(self, client):
        assert client.get(f"{BASE}/kanban", headers={"X-Painel-Key": "errada"}).status_code == 401

    def test_app_secret_nao_vale(self, client):
        # A chave do hook legado NÃO abre as rotas do painel (cada chave gira separada).
        r = client.get(f"{BASE}/kanban", headers={"X-Docudata-Key": "chave-de-aplicacao-para-testes"})
        assert r.status_code == 401

    def test_variavel_ausente_falha_fechada_503(self, client, monkeypatch):
        monkeypatch.delenv("DOCUDATA_PAINEL_KEY")
        assert client.get(f"{BASE}/kanban", headers=H).status_code == 503

    def test_so_leitura(self, client):
        assert client.post(f"{BASE}/kanban", headers=H).status_code == 405

    def test_projeto_desconhecido_ou_id_invalido_404(self, client):
        base = "/integracoes/painel/v1/projetos"
        assert client.get(f"{base}/44444444-4444-4444-8444-444444444444/kanban", headers=H).status_code == 404
        assert client.get(f"{base}/nao-e-uuid/kanban", headers=H).status_code == 404


class TestRotas:
    def test_kanban(self, client):
        r = client.get(f"{BASE}/kanban", headers=H)
        assert r.status_code == 200
        por_id = {c["id"]: c for c in r.json()}
        assert por_id["t-1"] == {
            "id": "t-1", "titulo": "ETL vendas", "coluna": "Concluída", "colunaTipo": "CONCLUIDO",
            "progresso": 100, "bloqueadoPorCliente": False,
            "concluidaEm": "2026-09-30T15:00:00+00:00", "responsavel": "Ana",
        }
        assert por_id["t-2"]["bloqueadoPorCliente"] is True
        assert por_id["t-2"]["bloqueadaDesde"] == "2026-09-29T12:00:00+00:00"
        assert por_id["t-2"]["progresso"] == 50
        assert "concluidaEm" not in por_id["t-2"]

    def test_indicadores(self, client):
        r = client.get(f"{BASE}/indicadores", headers=H)
        assert r.status_code == 200
        corpo = r.json()
        assert corpo["sprintNumero"] == 4
        assert corpo["spi"] == 0.62  # 5 concluídos / 8 previstos
        assert corpo["desvioPontos"] == -3
        assert corpo["saude"] == "VERMELHO"  # sem saúde manual: deriva do SPI
        assert corpo["inicio"] == "2026-09-28" and corpo["fim"] == "2026-10-02"

    def test_escopo(self, client):
        r = client.get(f"{BASE}/escopo", headers=H)
        assert r.json() == [{
            "id": "f-1", "codigo": "E1", "nome": "Mapeamento", "prioridade": "MUST", "data": "2026-09-25",
            "criterios": [{"texto": "Ambientes mapeados", "atendido": True}],
        }]

    def test_atas_e_documentos_separados(self, client):
        atas = client.get(f"{BASE}/atas", headers=H).json()
        assert [a["id"] for a in atas] == ["d-1"]
        assert atas[0]["titulo"] == "Reunião de 30 set"
        docs = client.get(f"{BASE}/documentos", headers=H).json()
        assert [d["id"] for d in docs] == ["d-2"]
        assert docs[0]["nome"] == "Repasse semanal · sprint 4" and docs[0]["ext"] == "MD"

    def test_pessoas_sem_email(self, client):
        assert client.get(f"{BASE}/pessoas", headers=H).json() == [{"id": OP, "nome": "Ana", "papel": "Analista"}]

    def test_commits_na_janela(self, client):
        r = client.get(f"{BASE}/commits", headers=H, params={"desde": "2026-09-28T00:00:00Z", "ate": "2026-10-02T23:59:59Z"})
        assert r.json() == {"count": 2}

    def test_commits_janela_invertida_422(self, client):
        r = client.get(f"{BASE}/commits", headers=H, params={"desde": "2026-10-02T00:00:00Z", "ate": "2026-09-28T00:00:00Z"})
        assert r.status_code == 422


class TestFuncoesPuras:
    def test_escolher_sprint_prefere_iniciada_de_maior_numero(self):
        sprints = [{"numero": 2, "iniciada": True}, {"numero": 5, "iniciada": False}, {"numero": 3, "iniciada": True}]
        assert pl.escolher_sprint(sprints, None)["numero"] == 3
        assert pl.escolher_sprint(sprints, 5)["numero"] == 5
        assert pl.escolher_sprint(sprints, 9) is None
        assert pl.escolher_sprint([], None) is None

    def test_spi_nulo_sem_previsto(self):
        proj = {"data_inicio": "2026-08-31", "data_fim_contratada": "2026-10-09"}
        r = pl.mapear_indicadores(proj, {"numero": 1}, [], [], 0, date(2026, 9, 1))
        assert r["spi"] is None and r["saude"] is None and r["desvioPontos"] == 0
        assert r["inicio"] == "2026-08-31"  # derivado do contrato: sprint 1 começa no início

    def test_saude_manual_vence_o_spi(self):
        proj = {}
        sprint = {"numero": 2, "status_saude": "amarelo"}
        tasks = [{"pontos": 8, "coluna_kanban": "concluida", "extra": False}]
        assert pl.mapear_indicadores(proj, sprint, tasks, tasks, 8, date(2026, 9, 1))["saude"] == "AMARELO"

    def test_commits_ignora_instante_sem_fuso(self):
        ate = datetime(2026, 10, 2, tzinfo=timezone.utc)
        desde = datetime(2026, 9, 28, tzinfo=timezone.utc)
        assert pl.contar_commits([{"criado_em": "2026-09-30T10:00:00"}], desde, ate) == 0
