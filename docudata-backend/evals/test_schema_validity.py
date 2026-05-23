import pytest
from pydantic import ValidationError
from models.schemas import ConteudoEstruturado

VALID_PAYLOAD = {
    "resumo": "Finalizamos o pipeline de ingestao",
    "tarefas": ["Implementar endpoint", "Revisar schema"],
    "decisoes": ["Usar K-means com k=5"],
    "problemas": ["API do cliente retornou CPF inconsistente"],
    "contexto_cliente": "Cliente do setor financeiro",
    "proximos_passos": ["Validar com o cliente"],
}


def test_valid_payload_constructs():
    obj = ConteudoEstruturado(**VALID_PAYLOAD)
    keys = set(obj.model_dump().keys())
    assert keys == {"resumo", "tarefas", "decisoes", "problemas", "contexto_cliente", "proximos_passos"}


@pytest.mark.parametrize("missing_field", [
    "resumo", "tarefas", "decisoes", "problemas", "contexto_cliente", "proximos_passos"
])
def test_missing_field_raises(missing_field):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != missing_field}
    with pytest.raises(ValidationError):
        ConteudoEstruturado(**payload)


def test_tarefas_wrong_type_raises():
    with pytest.raises(ValidationError):
        ConteudoEstruturado(**{**VALID_PAYLOAD, "tarefas": 123})


def test_resumo_none_raises():
    with pytest.raises(ValidationError):
        ConteudoEstruturado(**{**VALID_PAYLOAD, "resumo": None})


def test_list_fields_are_list_of_str():
    obj = ConteudoEstruturado(**VALID_PAYLOAD)
    for field in ("tarefas", "decisoes", "problemas", "proximos_passos"):
        assert isinstance(getattr(obj, field), list)
        assert all(isinstance(item, str) for item in getattr(obj, field))


def test_str_fields_are_str():
    obj = ConteudoEstruturado(**VALID_PAYLOAD)
    assert isinstance(obj.resumo, str)
    assert isinstance(obj.contexto_cliente, str)
