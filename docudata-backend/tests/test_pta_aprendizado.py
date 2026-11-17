import services.classificador_aprendizado as ap
from tests.test_classificador_aprendizado import _fake


def _com_projeto(subarea):
    fake = _fake()
    fake.tables["tasks"][0]["project_id"] = "p1"
    fake.tables["projects"] = [{"id": "p1", "subarea": subarea}]
    return fake


def test_projeto_e_pta():
    fake = _com_projeto("pta")
    assert ap.projeto_e_pta(fake, "p1") is True
    assert ap.projeto_e_pta(fake, "outro") is False
    assert ap.projeto_e_pta(fake, None) is False


def test_conclusao_de_task_pta_nao_vira_exemplo_nem_calibra():
    fake = _com_projeto("pta")
    ap.registrar_conclusao(fake, "t1")
    assert fake.tables["task_aprendizado"] == []
    assert fake.tables["classificador_parametros"] == []
    assert fake.tables["classificador_parametros_hist"] == []


def test_conclusao_de_task_de_outra_subarea_continua_virando_exemplo():
    fake = _com_projeto("dados")
    ap.registrar_conclusao(fake, "t1")
    assert len(fake.tables["task_aprendizado"]) == 1


def test_opiniao_do_operacional_em_task_pta_e_ignorada_sem_erro():
    # O front abre o diálogo de opinião ao concluir; em PTA a opinião é
    # descartada em silêncio para o candidato não ver erro.
    fake = _com_projeto("pta")
    ap.registrar_opiniao_operacional(fake, "t1", 3)
    assert fake.tables["task_aprendizado"] == []


def test_recalculo_diario_pula_task_pta(monkeypatch):
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
    assert criadas == ["t2"]
