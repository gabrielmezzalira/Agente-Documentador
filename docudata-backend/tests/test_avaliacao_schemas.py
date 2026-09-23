"""resposta_6 (a antiga pergunta de evolução) vira opcional nos schemas de
avaliação — o questionário passou a ter 6 perguntas. Ver
docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md."""
import pytest
from pydantic import ValidationError

from models.schemas import AvaliacaoAnteriorResponse, AvaliacaoGerenteCreate, AvaliacaoGerenteResponse


def test_avaliacao_gerente_create_aceita_sem_resposta_6():
    data = AvaliacaoGerenteCreate(
        operacional_id="op-1", sprint_id="sprint-1",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_7=5,
    )
    assert data.resposta_6 is None


def test_avaliacao_gerente_create_ainda_aceita_resposta_6_explicita():
    data = AvaliacaoGerenteCreate(
        operacional_id="op-1", sprint_id="sprint-1",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_6=0, resposta_7=5,
    )
    assert data.resposta_6 == 0


def test_avaliacao_gerente_create_resposta_6_fora_de_0_5_ainda_rejeita():
    with pytest.raises(ValidationError):
        AvaliacaoGerenteCreate(
            operacional_id="op-1", sprint_id="sprint-1",
            resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_6=9, resposta_7=5,
        )


def test_avaliacao_gerente_response_aceita_resposta_6_none():
    resp = AvaliacaoGerenteResponse(
        id="a1", operacional_id="op-1", gerente_id="ger-1", sprint_id="sprint-1",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_7=5,
        criado_em="2026-09-23T00:00:00Z", editavel_ate="2026-09-25T00:00:00Z",
    )
    assert resp.resposta_6 is None


def test_avaliacao_anterior_response_aceita_resposta_6_none():
    resp = AvaliacaoAnteriorResponse(
        avaliacao_id="a1", project_name="Projeto X", criado_em="2026-09-23T00:00:00Z",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_7=5,
    )
    assert resp.resposta_6 is None
