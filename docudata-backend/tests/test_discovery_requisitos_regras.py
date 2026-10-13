import pytest

from services.discovery_requisitos import (
    RegraRequisitoErro, achar_duplicata, normalizar_titulo, pode_editar,
    proximo_codigo, validar_transicao,
)


def test_operacional_pode_revisar():
    validar_transicao("proposto", "em_revisao", "operacional", None)  # não levanta


def test_so_gerente_valida():
    validar_transicao("em_revisao", "validado", "gerente", None)
    with pytest.raises(RegraRequisitoErro) as e:
        validar_transicao("em_revisao", "validado", "operacional", None)
    assert e.value.status == 403


@pytest.mark.parametrize("de", ["proposto", "em_revisao", "validado"])
def test_rejeitar_exige_gerente_e_motivo(de):
    validar_transicao(de, "rejeitado", "gerente", "fora do escopo do cliente")
    with pytest.raises(RegraRequisitoErro) as sem_motivo:
        validar_transicao(de, "rejeitado", "gerente", "   ")
    assert sem_motivo.value.status == 422
    with pytest.raises(RegraRequisitoErro) as sem_cargo:
        validar_transicao(de, "rejeitado", "operacional", "motivo")
    assert sem_cargo.value.status == 403


def test_reabrir_exige_gerente_e_motivo():
    validar_transicao("rejeitado", "proposto", "lider", "cliente voltou atrás")
    with pytest.raises(RegraRequisitoErro) as e:
        validar_transicao("rejeitado", "proposto", "gerente", None)
    assert e.value.status == 422


@pytest.mark.parametrize("de,para", [
    ("proposto", "validado"), ("validado", "em_revisao"), ("rejeitado", "validado"),
    ("proposto", "proposto"), ("em_revisao", "proposto"),
])
def test_transicoes_fora_da_tabela_sao_409(de, para):
    with pytest.raises(RegraRequisitoErro) as e:
        validar_transicao(de, para, "owner", "motivo")
    assert e.value.status == 409


def test_pode_editar():
    assert pode_editar("proposto", "operacional") is True
    assert pode_editar("em_revisao", "operacional") is True
    assert pode_editar("validado", "operacional") is False
    assert pode_editar("rejeitado", "operacional") is False
    assert pode_editar("validado", "gerente") is True


def test_proximo_codigo():
    assert proximo_codigo([]) == "RQ-001"
    assert proximo_codigo(["RQ-001", "RQ-009"]) == "RQ-010"
    assert proximo_codigo(["RQ-002", "lixo", "RQ-1000"]) == "RQ-1001"


def test_normalizar_titulo_ignora_acento_caixa_e_pontuacao():
    assert normalizar_titulo("  Exportação de Relatórios, em PDF! ") == "exportacao de relatorios em pdf"


def test_achar_duplicata():
    existentes = [{"id": "a", "titulo": "Exportar relatório em PDF"}, {"id": "b", "titulo": "Login com SSO"}]
    assert achar_duplicata("Exportar relatorio em PDF", existentes)["id"] == "a"
    assert achar_duplicata("Painel de metas por vendedor", existentes) is None
