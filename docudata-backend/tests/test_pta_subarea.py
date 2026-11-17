import pytest
from pydantic import ValidationError

from models.schemas import ProjectCreate, ProjectSubareaUpdate


def test_projeto_aceita_subarea_pta():
    assert ProjectCreate(name="PTA 2026", client="CITi", subarea="pta").subarea == "pta"


def test_subarea_invalida_continua_recusada():
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", client="y", subarea="rh")


def test_troca_dados_dev_nao_aceita_pta():
    with pytest.raises(ValidationError):
        ProjectSubareaUpdate(subarea="pta")


def test_github_app_aceita_pta():
    from services.github_app import subarea_github_habilitada
    assert subarea_github_habilitada("pta") is True
