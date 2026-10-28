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


def test_em_ajuste_cede_para_o_derivado():
    c = _client("em_ajuste", ["em_andamento"])
    assert sincronizar_status(c, "f1") == "em_andamento"
    assert c.tables["funcionalidades"][0]["status"] == "em_andamento"
    assert [(t["de"], t["para"]) for t in c.tables["transicoes_status"]] == [("em_ajuste", "em_andamento")]


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


@pytest.mark.parametrize("novo", ["concluida", "em_andamento", "em_ajuste"])
def test_patch_status_com_tasks_409(monkeypatch, autenticar, novo):
    fake, tc = _rota(monkeypatch, autenticar, ["em_andamento"])
    resp = tc.patch("/funcionalidades/f1", json={"status": novo})
    assert resp.status_code == 409
    assert resp.json()["detail"] == _MSG_409
    assert fake.tables["funcionalidades"][0]["status"] == "nao_iniciada"
    assert fake.tables["transicoes_status"] == []


def test_patch_sair_de_em_ajuste_com_tasks_409(monkeypatch, autenticar):
    fake, tc = _rota(monkeypatch, autenticar, ["em_andamento"])
    fake.tables["funcionalidades"][0]["status"] = "em_ajuste"
    resp = tc.patch("/funcionalidades/f1", json={"status": "em_andamento"})
    assert resp.status_code == 409
    assert fake.tables["funcionalidades"][0]["status"] == "em_ajuste"


def test_patch_em_ajuste_sem_tasks_200(monkeypatch, autenticar):
    fake, tc = _rota(monkeypatch, autenticar, [])
    resp = tc.patch("/funcionalidades/f1", json={"status": "em_ajuste"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["funcionalidades"][0]["status"] == "em_ajuste"


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
    assert main(dry_run=True, client=c) == {"ajustadas": 2, "total": 3, "aprovacoes_revogadas": 0}
    assert c.tables["transicoes_status"] == []
    assert main(dry_run=False, client=c) == {"ajustadas": 2, "total": 3, "aprovacoes_revogadas": 0}
    assert all(t["autor"] == "backfill" and t["duracao_fase_anterior_segundos"] is None
               for t in c.tables["transicoes_status"] if t["campo"] == "status")
    status = {f["id"]: f["status"] for f in c.tables["funcionalidades"]}
    assert status == {"a": "nao_iniciada", "b": "em_andamento", "c": "concluida"}
    assert main(dry_run=False, client=c) == {"ajustadas": 0, "total": 3, "aprovacoes_revogadas": 0}


def test_backfill_em_ajuste_com_tasks_segue_o_derivado():
    from scripts.status_funcionalidade_backfill import main
    def montar():
        return FakeClient({
            "funcionalidades": [_func("a", status="em_ajuste")],
            "tasks": [{"id": "t1", "funcionalidade_id": "a", "coluna_kanban": "em_andamento", "extra": False}],
            "transicoes_status": [],
        })
    assert main(dry_run=True, client=montar())["ajustadas"] == 1
    c = montar()
    assert main(dry_run=False, client=c)["ajustadas"] == 1
    assert c.tables["funcionalidades"][0]["status"] == "em_andamento"


def test_backfill_conta_aprovacoes_revogadas(capsys):
    from scripts.status_funcionalidade_backfill import main
    def montar():
        f = _func("a", status="concluida")
        f["aprovada_em"] = "2026-10-10T10:00:00+00:00"
        return FakeClient({
            "funcionalidades": [f, _func("b", status="concluida")],
            "tasks": [{"id": "t1", "funcionalidade_id": "a", "coluna_kanban": "em_andamento", "extra": False},
                      {"id": "t2", "funcionalidade_id": "b", "coluna_kanban": "em_andamento", "extra": False}],
            "transicoes_status": [],
        })
    assert main(dry_run=True, client=montar())["aprovacoes_revogadas"] == 1
    c = montar()
    assert main(dry_run=False, client=c) == {"ajustadas": 2, "total": 2, "aprovacoes_revogadas": 1}
    assert c.tables["funcionalidades"][0]["aprovada_em"] is None
    assert "aprovações revogadas" in capsys.readouterr().out


def test_sincronizar_nao_grava_transicao_se_o_update_nao_pegou(monkeypatch):
    import services.status_funcionalidade as sf
    c = _client("nao_iniciada", ["em_andamento"])
    original = sf.tasks_da_funcionalidade

    def corrida(client, fid):
        client.tables["funcionalidades"][0]["status"] = "em_andamento"  # outra escrita venceu
        return original(client, fid)

    monkeypatch.setattr(sf, "tasks_da_funcionalidade", corrida)
    assert sincronizar_status(c, "f1") is None
    assert c.tables["transicoes_status"] == []


def test_com_tem_tasks_em_lote():
    from services.aprovacao_funcionalidade import com_tem_tasks
    c = FakeClient({"tasks": [
        {"id": "t1", "funcionalidade_id": "a", "extra": False},
        {"id": "t2", "funcionalidade_id": "b", "extra": True},
    ]})
    out = com_tem_tasks(c, [{"id": "a"}, {"id": "b"}, {"id": "c"}])
    assert [f["tem_tasks"] for f in out] == [True, False, False]


def test_nomes_dos_aprovadores_nao_traz_tem_tasks():
    from services.aprovacao_funcionalidade import nomes_dos_aprovadores
    c = FakeClient({"pessoa": [], "tasks": []})
    assert "tem_tasks" not in nomes_dos_aprovadores(c, [{"id": "a"}])[0]
