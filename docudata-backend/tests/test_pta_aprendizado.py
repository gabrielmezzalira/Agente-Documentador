import services.classificador_aprendizado as ap
from tests.test_classificador_aprendizado import _fake


def _com_projeto(subarea):
    fake = _fake()
    fake.tables["tasks"][0]["project_id"] = "p1"
    fake.tables["projects"] = [{"id": "p1", "subarea": subarea}]
    return fake


def test_conclusao_de_task_pta_vira_exemplo_como_qualquer_outra():
    # O PTA existe para treinar o classificador: suas tasks alimentam os exemplos e os parâmetros.
    fake = _com_projeto("pta")
    ap.registrar_conclusao(fake, "t1")
    assert len(fake.tables["task_aprendizado"]) == 1


def test_conclusao_de_task_de_outra_subarea_continua_virando_exemplo():
    fake = _com_projeto("dados")
    ap.registrar_conclusao(fake, "t1")
    assert len(fake.tables["task_aprendizado"]) == 1


def test_opiniao_do_operacional_em_task_pta_e_gravada():
    fake = _com_projeto("pta")
    ap.registrar_opiniao_operacional(fake, "t1", 3)
    assert fake.tables["task_aprendizado"][0]["opiniao_operacional"] == 3


def test_recalculo_diario_inclui_task_pta(monkeypatch):
    fake = _com_projeto("pta")
    fake.tables["tasks"].append({"id": "t2", "project_id": "p2", "coluna_kanban": "concluida"})
    fake.tables["projects"].append({"id": "p2", "subarea": "dev"})
    fake.tables["tasks"][0]["coluna_kanban"] = "concluida"
    criadas = []
    import services.supabase_client as sc
    monkeypatch.setattr(sc, "get_client", lambda: fake)
    monkeypatch.setattr(ap, "registrar_conclusao", lambda c, t: criadas.append(t))
    monkeypatch.setattr(ap, "recalcular_tudo", lambda c: None)
    ap.recalcular_diario()
    assert sorted(criadas) == ["t1", "t2"]
