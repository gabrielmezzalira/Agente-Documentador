"""Régua única de dificuldade (spec A1 §1)."""
import pytest
from pydantic import ValidationError

from models.schemas import TaskCreate, TaskUpdate
from services.regua import (
    MENSAGEM_NIVEL_INVALIDO,
    NIVEIS,
    ROTULOS,
    ajuste_pontos_reabertura,
    converter_pontos_legado,
)


def test_niveis_da_regua():
    assert NIVEIS == (1, 2, 3, 5)
    assert ROTULOS == {1: "simples", 2: "moderada", 3: "complexa", 5: "muito complexa"}


@pytest.mark.parametrize("antigo,novo", [(1, 1), (2, 2), (3, 3), (4, 3), (5, 5), (8, 5), (13, 5)])
def test_converter_pontos_legado(antigo, novo):
    assert converter_pontos_legado(antigo) == novo


def test_ajuste_reabertura_vazio_quando_ja_esta_na_regua():
    assert ajuste_pontos_reabertura({"pontos": 3}) == {}


def test_ajuste_reabertura_converte_e_guarda_original():
    assert ajuste_pontos_reabertura({"pontos": 8}) == {"pontos": 5, "pontos_legado": 8}


@pytest.mark.parametrize("pontos", [1, 2, 3, 5])
def test_task_create_aceita_niveis(pontos):
    assert TaskCreate(project_id="p", titulo="t", pontos=pontos).pontos == pontos


@pytest.mark.parametrize("pontos", [0, 4, 8])
def test_task_create_rejeita_fora_da_regua(pontos):
    with pytest.raises(ValidationError) as exc:
        TaskCreate(project_id="p", titulo="t", pontos=pontos)
    assert MENSAGEM_NIVEL_INVALIDO in str(exc.value)


def test_task_update_rejeita_fora_da_regua_e_aceita_none():
    assert TaskUpdate().pontos is None
    with pytest.raises(ValidationError) as exc:
        TaskUpdate(pontos=4)
    assert MENSAGEM_NIVEL_INVALIDO in str(exc.value)
