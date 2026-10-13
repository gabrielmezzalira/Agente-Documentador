import pytest

from services import discovery_store as store
from services.discovery_promocao import promover_requisito, promover_validados_do_projeto
from services.discovery_requisitos import RegraRequisitoErro
from tests.fake_supabase import FakeClient


def _cliente():
    return FakeClient({"projects": [{"id": "p1", "subarea": "produto"}]})


def _req(c, codigo="RQ-001", status="validado", criterios=("Dado A, quando B, então C",)):
    return store.inserir_requisito(c, {
        "project_id": "p1", "codigo": codigo, "titulo": f"Titulo {codigo}", "descricao": "desc", "tipo": "funcional",
        "prioridade_sugerida": "must", "status": status, "criterios_aceite": list(criterios),
    })


def test_promove_validado_e_liga_a_funcionalidade():
    c = _cliente()
    r = _req(c)
    saida = promover_requisito(c, r["id"], "gerente@citi.org.br")
    assert saida["criada"] is True
    fn = c.tables["funcionalidades"][0]
    assert (fn["project_id"], fn["id_funcional"], fn["titulo"], fn["prioridade"]) == ("p1", "RQ-001", "Titulo RQ-001", "must")
    assert fn["criterios_aceite"] == ["Dado A, quando B, então C"]
    assert store.buscar_requisito(c, r["id"])["funcionalidade_id"] == saida["funcionalidade_id"]
    assert store.listar_transicoes(c, r["id"])[-1]["campo"] == "funcionalidade"


def test_promover_duas_vezes_nao_duplica():
    c = _cliente()
    r = _req(c)
    primeira = promover_requisito(c, r["id"], "g@x")
    segunda = promover_requisito(c, r["id"], "g@x")
    assert segunda == {"funcionalidade_id": primeira["funcionalidade_id"], "criada": False}
    assert len(c.tables["funcionalidades"]) == 1


@pytest.mark.parametrize("status", ["proposto", "em_revisao", "rejeitado"])
def test_so_validado_pode_ser_promovido(status):
    c = _cliente()
    r = _req(c, status=status)
    with pytest.raises(RegraRequisitoErro) as e:
        promover_requisito(c, r["id"], "g@x")
    assert e.value.status == 409


def test_exige_criterio_de_aceite():
    c = _cliente()
    r = _req(c, criterios=())
    with pytest.raises(RegraRequisitoErro) as e:
        promover_requisito(c, r["id"], "g@x")
    assert e.value.status == 422


def test_requisito_inexistente_404():
    with pytest.raises(RegraRequisitoErro) as e:
        promover_requisito(_cliente(), "nada", "g@x")
    assert e.value.status == 404


def test_promover_validados_do_projeto_promove_so_os_pendentes():
    c = _cliente()
    ja = _req(c, "RQ-001")
    promover_requisito(c, ja["id"], "g@x")
    _req(c, "RQ-002")
    _req(c, "RQ-003", status="proposto")
    assert promover_validados_do_projeto(c, "p1", "g@x") == 1
    assert len(c.tables["funcionalidades"]) == 2


def test_promover_validados_recusa_tudo_se_algum_nao_tem_criterio():
    c = _cliente()
    _req(c, "RQ-001")
    _req(c, "RQ-002", criterios=())
    with pytest.raises(RegraRequisitoErro) as e:
        promover_validados_do_projeto(c, "p1", "g@x")
    assert e.value.status == 422 and "RQ-002" in e.value.detail
    assert "funcionalidades" not in c.tables


def test_retry_apos_falha_do_vinculo_reaproveita_funcionalidade_existente():
    """Janela de falha: funcionalidade inserida mas o vínculo no requisito não gravou."""
    c = _cliente()
    r = _req(c)
    c.tables["funcionalidades"] = [{"id": "f-orfa", "project_id": "p1", "id_funcional": "RQ-001", "titulo": "Titulo RQ-001"}]
    saida = promover_requisito(c, r["id"], "g@x")
    assert saida == {"funcionalidade_id": "f-orfa", "criada": False}
    assert len(c.tables["funcionalidades"]) == 1
    assert store.buscar_requisito(c, r["id"])["funcionalidade_id"] == "f-orfa"


def test_id_funcional_ocupado_por_outra_funcionalidade_usa_sufixo():
    c = _cliente()
    r = _req(c)
    c.tables["funcionalidades"] = [{"id": "f-manual", "project_id": "p1", "id_funcional": "RQ-001", "titulo": "Outra coisa"}]
    saida = promover_requisito(c, r["id"], "g@x")
    assert saida["criada"] is True and saida["funcionalidade_id"] != "f-manual"
    ids = sorted(f["id_funcional"] for f in c.tables["funcionalidades"])
    assert ids == ["RQ-001", "RQ-001-2"]
