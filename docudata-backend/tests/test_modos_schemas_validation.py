"""Validação dos schemas Pydantic novos da Entrega 1 (Modos de Trabalho)."""
import pytest
from pydantic import ValidationError

from models.schemas import (
    ModosProjetoUpdate,
    ProjectResponse,
    SprintStatusResponse,
    WipConfigUpdate,
    PontuacaoEventoResponse,
)


def test_project_response_tem_defaults_de_modo():
    resp = ProjectResponse(
        id="p1", name="Projeto", client="CITi", created_at="2026-09-01T00:00:00Z",
    )
    assert resp.modo_trabalho == "ATRIBUICAO"
    assert resp.modo_avaliacao == "PONTOS_ATRIBUIDOS"
    assert resp.pull_exigir_hidratacao is True
    assert resp.pull_piso_pontos == 1
    assert resp.pull_teto == 1.5
    assert resp.wip_config is None


def test_modos_projeto_update_rejeita_modo_trabalho_invalido():
    with pytest.raises(ValidationError):
        ModosProjetoUpdate(modo_trabalho="PARALELO")


def test_modos_projeto_update_rejeita_piso_nao_positivo():
    with pytest.raises(ValidationError):
        ModosProjetoUpdate(pull_piso_pontos=0)


def test_wip_config_update_rejeita_por_pessoa_menor_que_1():
    with pytest.raises(ValidationError):
        WipConfigUpdate(por_pessoa=0)


def test_sprint_status_response_tem_contadores_de_avaliacao_default_zero():
    resp = SprintStatusResponse(
        id="s1", project_id="p1", numero=1,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
    )
    assert resp.avaliados_count == 0
    assert resp.elegiveis_avaliacao_count == 0


def test_pontuacao_evento_response_aceita_tipo_valido():
    ev = PontuacaoEventoResponse(
        id="e1", operacional_id="op-1", sprint_id="s1", projeto_id="p1",
        tipo="entrega_concluida", pontos=5, criado_em="2026-09-01T00:00:00Z",
    )
    assert ev.pontos == 5


def test_pontuacao_evento_response_rejeita_tipo_invalido():
    with pytest.raises(ValidationError):
        PontuacaoEventoResponse(
            id="e1", operacional_id="op-1", sprint_id="s1", projeto_id="p1",
            tipo="tipo_inventado", pontos=5, criado_em="2026-09-01T00:00:00Z",
        )
