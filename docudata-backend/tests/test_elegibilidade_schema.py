# docudata-backend/tests/test_elegibilidade_schema.py
"""Confirma que a migração de elegibilidade temporal da Entrega 2 está
presente no schema. Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.2."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def test_operacionais_ganha_colunas_de_vinculo_temporal():
    schema = _SCHEMA.read_text()
    assert "ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_entrada timestamptz;" in schema
    assert "ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_saida timestamptz;" in schema
    assert "UPDATE operacionais SET data_entrada = created_at WHERE data_entrada IS NULL;" in schema
    assert "ALTER TABLE operacionais ALTER COLUMN data_entrada SET NOT NULL;" in schema
    assert "ALTER TABLE operacionais ALTER COLUMN data_entrada SET DEFAULT now();" in schema
