"""Confirma que a migração de pesos (gerente 50%, evolução removida) e a
coluna resposta_6 opcional estão presentes no schema. Ver
docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def _texto_schema() -> str:
    return _SCHEMA.read_text()


def test_update_pesos_arquetipo_padrao_presente():
    schema = _texto_schema()
    assert "UPDATE pesos_arquetipo SET" in schema
    assert "peso_gerente = 0.50" in schema
    assert "peso_evolucao = 0.00" in schema
    assert "WHERE arquetipo = 'padrao'" in schema


def test_update_pesos_arquetipo_consultoria_presente():
    schema = _texto_schema()
    assert "WHERE arquetipo = 'consultoria_discovery'" in schema


def test_resposta_6_vira_opcional():
    schema = _texto_schema()
    assert "ALTER TABLE avaliacoes_gerente ALTER COLUMN resposta_6 DROP NOT NULL;" in schema
