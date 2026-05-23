import pytest
from langgraph.graph import END
from graphs.extraction_graph import _roteador


@pytest.mark.parametrize("valido,tentativas,expected", [
    (True,  0, "salvar"),
    (False, 0, "extrair_conteudo"),
    (False, 1, "extrair_conteudo"),
    (False, 2, END),
])
def test_roteador_routing(valido, tentativas, expected):
    assert _roteador({"valido": valido, "tentativas": tentativas}) == expected


@pytest.mark.parametrize("tentativas", [2, 3, 10])
def test_roteador_terminates_at_max_retries(tentativas):
    result = _roteador({"valido": False, "tentativas": tentativas})
    assert result == END
    assert result != "extrair_conteudo"
