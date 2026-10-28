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
