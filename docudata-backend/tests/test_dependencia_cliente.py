"""Bloqueio do tipo 'cliente' — dependência do cliente não pode zerar a Entrega
de ninguém (design aprovado 2026-09-23)."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.schemas import TaskUpdate, TaskResponse

SCHEMA = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text()


def test_schema_adiciona_bloqueio_tipo_nao_destrutivo():
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS bloqueio_tipo text" in SCHEMA
    assert "CHECK (bloqueio_tipo IN ('interno','cliente'))" in SCHEMA


def test_task_update_aceita_bloqueio_tipo_valido():
    assert TaskUpdate(bloqueio_tipo="cliente").bloqueio_tipo == "cliente"
    assert TaskUpdate(bloqueio_tipo="interno").bloqueio_tipo == "interno"


def test_task_update_rejeita_bloqueio_tipo_invalido():
    with pytest.raises(ValidationError):
        TaskUpdate(bloqueio_tipo="fornecedor")


def test_task_response_expoe_bloqueio_tipo_opcional():
    assert "bloqueio_tipo" in TaskResponse.model_fields
    assert TaskResponse.model_fields["bloqueio_tipo"].default is None
