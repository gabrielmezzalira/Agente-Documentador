import pytest
from pydantic import ValidationError

from models.discovery import (
    NovoRequisito, ReuniaoIngestRequest, RequisitoPatch, SaidaAnalise,
)


def test_ingest_aceita_minimo_e_recusa_tipo_desconhecido():
    ok = ReuniaoIngestRequest(docudata_project_id="p1", fonte_session_id="sessao-123456")
    assert ok.tipo == "outra" and ok.conteudo_estruturado == {} and ok.transcricao is None
    with pytest.raises(ValidationError):
        ReuniaoIngestRequest(docudata_project_id="p1", fonte_session_id="sessao-123456", tipo="almoco")


def test_patch_exige_ao_menos_um_campo():
    with pytest.raises(ValidationError):
        RequisitoPatch()
    assert RequisitoPatch(status="em_revisao").status == "em_revisao"


def test_patch_limpa_criterios_vazios_e_recusa_lista_so_de_vazios():
    p = RequisitoPatch(criterios_aceite=["  Dado A, quando B, então C  ", "  "])
    assert p.criterios_aceite == ["Dado A, quando B, então C"]
    with pytest.raises(ValidationError):
        RequisitoPatch(criterios_aceite=["  ", ""])


def test_saida_do_modelo_tem_listas_vazias_por_padrao():
    s = SaidaAnalise()
    assert s.novos == [] and s.reforcos == [] and s.conflitos == [] and s.ajustes_prioridade == []
    n = NovoRequisito(titulo="Exportar PDF", trecho="queremos exportar em PDF", tipo="funcional")
    assert n.prioridade_sugerida == "should" and n.criterios_aceite == []
