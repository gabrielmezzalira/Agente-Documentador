"""Confirma que a migração de 'Pendente de aprovação' está presente no
schema. Ver docs/superpowers/specs/2026-09-22-task-pendente-aprovacao-design.md."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def _texto_schema() -> str:
    return _SCHEMA.read_text()


def test_tasks_coluna_kanban_aceita_pendente_aprovacao():
    schema = _texto_schema()
    assert "CHECK (coluna_kanban IN ('planejado','em_andamento','pendente_aprovacao','concluida'))" in schema


def test_tasks_ganha_coluna_requer_aprovacao():
    schema = _texto_schema()
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS requer_aprovacao boolean NOT NULL DEFAULT false;" in schema


def test_tasks_tem_migracao_de_constraint_coluna_kanban():
    schema = _texto_schema()
    assert "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_coluna_kanban_check;" in schema
    assert "ADD CONSTRAINT tasks_coluna_kanban_check" in schema
