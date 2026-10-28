import pytest

from services.status_funcionalidade import (
    funcionalidade_tem_tasks,
    sincronizar_status,
    status_derivado,
)
from tests.fake_supabase import FakeClient


def t(coluna, extra=False):
    return {"coluna_kanban": coluna, "extra": extra}


@pytest.mark.parametrize("tasks,esperado", [
    ([], None),
    ([t("concluida", extra=True)], None),
    ([t("planejado"), t("planejado")], "nao_iniciada"),
    ([t("planejado"), t("em_andamento")], "em_andamento"),
    ([t("planejado"), t("concluida")], "em_andamento"),
    ([t("pendente_aprovacao")], "em_andamento"),
    ([t("concluida"), t("concluida")], "concluida"),
    ([t("concluida"), t("planejado", extra=True)], "concluida"),
])
def test_status_derivado(tasks, esperado):
    assert status_derivado(tasks) == esperado


def _client(status, colunas, **func_extra):
    return FakeClient({
        "funcionalidades": [{"id": "f1", "status": status, "created_at": "2026-10-01T10:00:00", **func_extra}],
        "tasks": [{"id": f"t{i}", "funcionalidade_id": "f1", "coluna_kanban": c, "extra": False}
                  for i, c in enumerate(colunas)],
        "transicoes_status": [],
    })


def test_muda_status_e_registra_transicao():
    c = _client("nao_iniciada", ["em_andamento"])
    assert sincronizar_status(c, "f1") == "em_andamento"
    assert c.tables["funcionalidades"][0]["status"] == "em_andamento"
    (tr,) = c.tables["transicoes_status"]
    assert (tr["de"], tr["para"], tr["campo"]) == ("nao_iniciada", "em_andamento", "status")


def test_status_igual_nao_escreve():
    c = _client("em_andamento", ["em_andamento"])
    assert sincronizar_status(c, "f1") is None
    assert c.tables["transicoes_status"] == []


def test_em_ajuste_nao_cede_para_em_andamento():
    c = _client("em_ajuste", ["em_andamento"])
    assert sincronizar_status(c, "f1") is None
    assert c.tables["funcionalidades"][0]["status"] == "em_ajuste"
    assert c.tables["transicoes_status"] == []


def test_concluida_aprovada_revoga_ao_voltar():
    c = _client("concluida", ["em_andamento"], aprovada_em="2026-10-10T10:00:00+00:00", aprovada_por="p1")
    assert sincronizar_status(c, "f1") == "em_andamento"
    f = c.tables["funcionalidades"][0]
    assert f["status"] == "em_andamento"
    assert f["aprovada_em"] is None


def test_sem_tasks_nao_escreve():
    c = _client("nao_iniciada", [])
    assert sincronizar_status(c, "f1") is None
    assert c.tables["transicoes_status"] == []
    assert funcionalidade_tem_tasks(c, "f1") is False


def test_id_none():
    assert sincronizar_status(_client("nao_iniciada", ["concluida"]), None) is None


def test_excecao_nao_propaga():
    class Quebrado:
        def table(self, _):
            raise RuntimeError("boom")

    assert sincronizar_status(Quebrado(), "f1") is None


# --- PATCH manual bloqueado com tasks, tem_tasks e backfill (Task 3) ---

from fastapi.testclient import TestClient

_MSG_409 = "O status vem das tasks desta funcionalidade."


def _func(fid, status="nao_iniciada"):
    return {
        "id": fid, "project_id": "p1", "id_funcional": fid.upper(), "titulo": "Login",
        "criterios_aceite": [], "prioridade": "must", "status": status,
        "aprovada_em": None, "aprovada_por": None, "created_at": "2026-01-01T00:00:00+00:00",
    }


def _rota(monkeypatch, autenticar, colunas):
    import routers.funcionalidades as func_router
    from main import app
    fake = FakeClient({
        "pessoa": [],
        "funcionalidades": [_func("f1")],
        "tasks": [{"id": f"t{i}", "funcionalidade_id": "f1", "coluna_kanban": c, "extra": False}
                  for i, c in enumerate(colunas)],
        "transicoes_status": [],
    })
    monkeypatch.setattr(func_router, "get_client", lambda: fake)
    return fake, autenticar(TestClient(app), "gerente")


@pytest.mark.parametrize("novo", ["concluida", "em_ajuste"])
def test_patch_status_com_tasks_409(monkeypatch, autenticar, novo):
    fake, tc = _rota(monkeypatch, autenticar, ["em_andamento"])
    resp = tc.patch("/funcionalidades/f1", json={"status": novo})
    assert resp.status_code == 409
    assert resp.json()["detail"] == _MSG_409
    assert fake.tables["funcionalidades"][0]["status"] == "nao_iniciada"
    assert fake.tables["transicoes_status"] == []


def test_patch_status_sem_tasks_200(monkeypatch, autenticar):
    fake, tc = _rota(monkeypatch, autenticar, [])
    resp = tc.patch("/funcionalidades/f1", json={"status": "concluida"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["funcionalidades"][0]["status"] == "concluida"


def test_patch_titulo_com_tasks_200(monkeypatch, autenticar):
    fake, tc = _rota(monkeypatch, autenticar, ["em_andamento"])
    resp = tc.patch("/funcionalidades/f1", json={"titulo": "x"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["titulo"] == "x"


def test_patch_mesmo_status_com_tasks_200(monkeypatch, autenticar):
    _, tc = _rota(monkeypatch, autenticar, ["em_andamento"])
    resp = tc.patch("/funcionalidades/f1", json={"status": "nao_iniciada", "titulo": "y"})
    assert resp.status_code == 200, resp.text


def test_resposta_traz_tem_tasks(monkeypatch, autenticar):
    fake, tc = _rota(monkeypatch, autenticar, ["em_andamento"])
    fake.tables["funcionalidades"].append(_func("f2"))
    fake.tables["tasks"].append({"id": "tx", "funcionalidade_id": "f2", "coluna_kanban": "concluida", "extra": True})
    por_id = {f["id"]: f for f in tc.get("/funcionalidades?project_id=p1").json()}
    assert por_id["f1"]["tem_tasks"] is True
    assert por_id["f2"]["tem_tasks"] is False  # só task extra não conta
    assert tc.get("/funcionalidades/f1").json()["tem_tasks"] is True


def test_backfill():
    from scripts.status_funcionalidade_backfill import main
    c = FakeClient({
        "funcionalidades": [_func("a"), _func("b"), _func("c")],
        "tasks": [
            {"id": "t1", "funcionalidade_id": "b", "coluna_kanban": "em_andamento", "extra": False},
            {"id": "t2", "funcionalidade_id": "c", "coluna_kanban": "concluida", "extra": False},
        ],
        "transicoes_status": [],
    })
    assert main(dry_run=True, client=c) == {"ajustadas": 2, "total": 3}
    assert c.tables["transicoes_status"] == []
    assert main(dry_run=False, client=c) == {"ajustadas": 2, "total": 3}
    status = {f["id"]: f["status"] for f in c.tables["funcionalidades"]}
    assert status == {"a": "nao_iniciada", "b": "em_andamento", "c": "concluida"}
    assert main(dry_run=False, client=c) == {"ajustadas": 0, "total": 3}
