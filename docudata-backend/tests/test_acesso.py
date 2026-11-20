import pytest
from fastapi import HTTPException

from services import acesso
from tests.fake_supabase import FakeClient


def _pessoa(cargo, pid="p1", email="x@citi.org.br"):
    return {"id": pid, "email": email, "cargo": cargo}


@pytest.fixture
def real(monkeypatch, acesso_original):
    monkeypatch.setattr("services.acesso._ids_vinculados_gerente", acesso_original)
    monkeypatch.setattr(acesso, "_avisou_tabela_ausente", False)


def test_owner_e_lider_veem_todos(real):
    c = FakeClient({})
    assert acesso.projetos_visiveis(c, _pessoa("owner")) is None
    assert acesso.projetos_visiveis(c, _pessoa("lider")) is None


def test_gerente_vinculado_ve_so_os_seus(real):
    c = FakeClient({"projeto_gerentes": [
        {"project_id": "A", "pessoa_id": "p1"}, {"project_id": "B", "pessoa_id": "p2"}]})
    assert acesso.projetos_visiveis(c, _pessoa("gerente")) == {"A"}
    assert acesso.tem_acesso(c, _pessoa("gerente"), "A")
    assert not acesso.tem_acesso(c, _pessoa("gerente"), "B")


def test_gerente_sem_vinculo_403(real):
    c = FakeClient({"projeto_gerentes": []})
    assert acesso.projetos_visiveis(c, _pessoa("gerente")) == set()
    with pytest.raises(HTTPException) as e:
        acesso.exigir_acesso(c, _pessoa("gerente"), "A")
    assert e.value.status_code == 403 and e.value.detail == acesso.SEM_ACESSO


def test_operacional_por_email(real):
    c = FakeClient({"operacionais": [
        {"project_id": "A", "email": "x@citi.org.br", "ativo": True}, {"project_id": "B", "email": "y@citi.org.br", "ativo": True}]})
    assert acesso.projetos_visiveis(c, _pessoa("operacional")) == {"A"}


class _ClienteSemTabela:
    def __init__(self, erro):
        self._erro = erro

    def table(self, nome):
        erro = self._erro
        class _Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def execute(self): raise erro
        return _Q()


def test_tabela_ausente_vira_none(real):
    c = _ClienteSemTabela(Exception('relation "projeto_gerentes" does not exist 42P01'))
    assert acesso.projetos_visiveis(c, _pessoa("gerente")) is None
    assert acesso.tem_acesso(c, _pessoa("gerente"), "qualquer")


def test_outro_erro_propaga(real):
    c = _ClienteSemTabela(Exception("connection reset"))
    with pytest.raises(Exception, match="connection reset"):
        acesso.projetos_visiveis(c, _pessoa("gerente"))


def test_project_id_de():
    c = FakeClient({
        "tasks": [{"id": "t1", "project_id": "A"}],
        "sprints": [{"id": "s1", "project_id": "B"}],
        "avaliacoes_gerente": [{"id": "av1", "sprint_id": "s1"}],
        "task_sugestoes": [{"id": "su1", "task_id": "t1"}],
    })
    assert acesso.project_id_de(c, "task", "t1") == "A"
    assert acesso.project_id_de(c, "sprint", "s1") == "B"
    assert acesso.project_id_de(c, "avaliacao", "av1") == "B"
    assert acesso.project_id_de(c, "sugestao", "su1") == "A"
    with pytest.raises(HTTPException) as e:
        acesso.project_id_de(c, "task", "nao-existe")
    assert e.value.status_code == 404


def test_exigir_acesso_por(vinculos_gerente):
    c = FakeClient({"tasks": [{"id": "t1", "project_id": "A"}]})
    vinculos_gerente["p1"] = {"A"}
    assert acesso.exigir_acesso_por(c, _pessoa("gerente"), "task", "t1") == "A"
    vinculos_gerente["p1"] = set()
    with pytest.raises(HTTPException):
        acesso.exigir_acesso_por(c, _pessoa("gerente"), "task", "t1")


def test_vincular_gerente_idempotente():
    c = FakeClient({})
    acesso.vincular_gerente(c, "A", "p1", "p0")
    acesso.vincular_gerente(c, "A", "p1", "p0")
    assert len(c.table("projeto_gerentes").select("*").execute().data) == 1


def test_pgrst205_vira_none(real):
    c = _ClienteSemTabela(Exception(
        "Could not find the table 'public.projeto_gerentes' in the schema cache PGRST205"))
    assert acesso.projetos_visiveis(c, _pessoa("gerente")) is None


def test_42p01_de_outra_tabela_propaga(real):
    c = _ClienteSemTabela(Exception('relation "outra" does not exist 42P01'))
    with pytest.raises(Exception, match="outra"):
        acesso.projetos_visiveis(c, _pessoa("gerente"))
