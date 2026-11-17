"""Frente da task identificada pela IA em segundo plano (F1). Nunca chama o Gemini de verdade."""
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import services.frente as frente
from tests.fake_supabase import FakeClient

pytestmark = pytest.mark.classificador_real

SCHEMA = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")


def _fake(**task_kw):
    task = {"id": "t1", "project_id": "p1", "titulo": "Login", "descricao": "d", "checklist": [],
            "pontos": 2, "coluna_kanban": "planejado", "ordem": 0, "bloqueado": False,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
            "nivel_travado_em": None, "sprint_id": "s1", "frente": None, "frente_definida_por": None}
    task.update(task_kw)
    return FakeClient({
        "projects": [{"id": "p1", "name": "Proj", "subarea": "dev", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": False}],
        "operacionais": [], "tasks": [task], "task_classificacoes": [], "task_aprendizado": [],
    }, defaults={"tasks": {"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00",
                           "updated_at": "2026-01-01T00:00:00+00:00"}})


def _llm_falso(monkeypatch, valor):
    class _Llm:
        def __init__(self, **kw): pass
        def with_structured_output(self, *a, **kw):
            return self
        async def ainvoke(self, msgs):
            return SimpleNamespace(frente=valor)
    monkeypatch.setattr(frente, "ChatGoogleGenerativeAI", _Llm)


KW = dict(titulo="t", descricao=None, checklist=None, projeto_nome="P", subarea="dev")


def test_classificar_devolve_valor_valido(monkeypatch):
    _llm_falso(monkeypatch, "mobile")
    assert asyncio.run(frente.classificar_frente("k", **KW)) == "mobile"


def test_classificar_devolve_none_fora_do_conjunto(monkeypatch):
    _llm_falso(monkeypatch, "blockchain")
    assert asyncio.run(frente.classificar_frente("k", **KW)) is None


def _job(monkeypatch, fake, retorno="dados", erro=None):
    chamadas = []

    async def cls(api_key, **kw):
        chamadas.append(kw)
        if erro:
            raise erro
        return retorno

    monkeypatch.setattr(frente, "get_client", lambda: fake)
    monkeypatch.setattr(frente, "get_gemini_api_key", lambda: "k")
    monkeypatch.setattr(frente, "classificar_frente", cls)
    asyncio.run(frente.atualizar_frente_da_task("t1"))
    return chamadas


def test_job_grava_frente_e_definida_por_ia(monkeypatch):
    fake = _fake()
    chamadas = _job(monkeypatch, fake, "dados")
    t = fake.tables["tasks"][0]
    assert t["frente"] == "dados" and t["frente_definida_por"] == "ia"
    assert chamadas[0]["projeto_nome"] == "Proj" and chamadas[0]["subarea"] == "dev"


def test_job_nao_classifica_task_do_gerente(monkeypatch):
    fake = _fake(frente="ia", frente_definida_por="gerente")
    assert _job(monkeypatch, fake, "dados") == []
    assert fake.tables["tasks"][0]["frente"] == "ia"


def test_job_engole_excecao(monkeypatch):
    fake = _fake()
    _job(monkeypatch, fake, erro=RuntimeError("boom"))
    t = fake.tables["tasks"][0]
    assert t["frente"] is None and t["frente_definida_por"] is None


# --- rotas ---

def _tc(monkeypatch, autenticar, fake, cargo="gerente"):
    import routers.tasks as tasks_router
    import services.classificador_ciclo as ciclo
    from main import app
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)
    agendadas = []

    async def espia(task_id):
        agendadas.append(task_id)

    monkeypatch.setattr(tasks_router, "atualizar_frente_da_task", espia)
    return autenticar(TestClient(app), cargo), agendadas


def test_post_agenda_classificacao_sem_gravar_frente_no_insert(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].clear()
    c, agendadas = _tc(monkeypatch, autenticar, fake)
    resp = c.post("/tasks", json={"project_id": "p1", "titulo": "Nova", "descricao": "x", "nivel_gerente": 3})
    assert resp.status_code == 201, resp.text
    criada = fake.tables["tasks"][0]
    assert agendadas == [criada["id"]]
    assert "frente" not in criada and "frente_definida_por" not in criada


def test_patch_de_titulo_agenda(monkeypatch, autenticar):
    c, agendadas = _tc(monkeypatch, autenticar, _fake())
    assert c.patch("/tasks/t1", json={"titulo": "Outro título"}).status_code == 200
    assert agendadas == ["t1"]


def test_patch_de_coluna_nao_agenda(monkeypatch, autenticar):
    c, agendadas = _tc(monkeypatch, autenticar, _fake())
    assert c.patch("/tasks/t1", json={"coluna_kanban": "em_andamento"}).status_code == 200
    assert agendadas == []


def test_mover_nao_agenda(monkeypatch, autenticar):
    c, agendadas = _tc(monkeypatch, autenticar, _fake())
    assert c.post("/tasks/t1/mover", params={"coluna_destino": "em_andamento"}).status_code == 200
    assert agendadas == []


def test_patch_de_texto_com_frente_do_gerente_nao_agenda(monkeypatch, autenticar):
    c, agendadas = _tc(monkeypatch, autenticar, _fake(frente="ia", frente_definida_por="gerente"))
    assert c.patch("/tasks/t1", json={"titulo": "Outro título"}).status_code == 200
    assert agendadas == []


def test_patch_gerente_define_frente(monkeypatch, autenticar):
    fake = _fake()
    c, agendadas = _tc(monkeypatch, autenticar, fake)
    resp = c.patch("/tasks/t1", json={"frente": "mobile"})
    assert resp.status_code == 200, resp.text
    t = fake.tables["tasks"][0]
    assert t["frente"] == "mobile" and t["frente_definida_por"] == "gerente"
    assert resp.json()["frente"] == "mobile" and agendadas == []


def test_patch_operacional_com_frente_403(monkeypatch, autenticar):
    fake = _fake()
    c, _ = _tc(monkeypatch, autenticar, fake, "operacional")
    assert c.patch("/tasks/t1", json={"frente": "mobile"}).status_code == 403
    assert fake.tables["tasks"][0]["frente"] is None


def test_patch_frente_invalida_422(monkeypatch, autenticar):
    c, _ = _tc(monkeypatch, autenticar, _fake())
    assert c.patch("/tasks/t1", json={"frente": "blockchain"}).status_code == 422


def test_migracao_v13_comentada_com_preflight_e_rollback():
    ini = SCHEMA.rindex("\n", 0, SCHEMA.index("Migration v13 (2026-11-17): frente da task")) + 1
    b = SCHEMA[ini:]
    assert "frente IN ('software','mobile','dados','ia')" in b
    assert "frente_definida_por IN ('ia','gerente')" in b
    assert "Preflight" in b and "Rollback" in b
    for linha in b.splitlines():
        assert not linha.strip() or linha.startswith("--"), linha


def test_job_nao_sobrescreve_frente_gravada_pelo_gerente_durante_a_chamada(monkeypatch):
    """A IA leva segundos: se o gerente grava a frente nesse meio tempo, ela vence."""
    fake = _fake()

    async def cls(api_key, **kw):
        t = fake.tables["tasks"][0]
        t["frente"], t["frente_definida_por"] = "mobile", "gerente"
        return "dados"

    monkeypatch.setattr(frente, "get_client", lambda: fake)
    monkeypatch.setattr(frente, "get_gemini_api_key", lambda: "k")
    monkeypatch.setattr(frente, "classificar_frente", cls)
    asyncio.run(frente.atualizar_frente_da_task("t1"))
    t = fake.tables["tasks"][0]
    assert t["frente"] == "mobile" and t["frente_definida_por"] == "gerente"
