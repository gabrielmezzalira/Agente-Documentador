"""Confirma que a migração da Entrega 1 (Modos de Trabalho e de Avaliação)
está presente no schema. Ver docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md §4."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def _texto_schema() -> str:
    return _SCHEMA.read_text()


def test_projects_ganha_colunas_de_modo():
    schema = _texto_schema()
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_trabalho text NOT NULL DEFAULT 'ATRIBUICAO'" in schema
    assert "CHECK (modo_trabalho IN ('ATRIBUICAO','PULL'))" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_avaliacao text NOT NULL DEFAULT 'PONTOS_ATRIBUIDOS'" in schema
    assert "CHECK (modo_avaliacao IN ('PONTOS_ATRIBUIDOS','PONTOS_RELATIVO'))" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_exigir_hidratacao boolean NOT NULL DEFAULT true;" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_piso_pontos numeric(6,2) NOT NULL DEFAULT 1;" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_teto numeric(4,2) NOT NULL DEFAULT 1.5;" in schema


def test_configuracao_historico_existe():
    schema = _texto_schema()
    assert "CREATE TABLE IF NOT EXISTS configuracao_historico (" in schema
    assert "campo           text NOT NULL CHECK (campo IN ('modo_trabalho','modo_avaliacao'))" in schema


def test_sprints_ganha_colunas_de_modo_e_hibrida():
    schema = _texto_schema()
    assert "ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_trabalho text;" in schema
    assert "ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_avaliacao text;" in schema
    assert "ALTER TABLE sprints ADD COLUMN IF NOT EXISTS hibrida boolean NOT NULL DEFAULT false;" in schema


def test_pontuacao_eventos_existe():
    schema = _texto_schema()
    assert "CREATE TABLE IF NOT EXISTS pontuacao_eventos (" in schema
    assert "'entrega_concluida','travamento_penalidade','devolucao_penalidade','bonus_extra','reabertura'" in schema


def test_pontuacao_operacional_sprint_ganha_coluna_entrega_modo():
    schema = _texto_schema()
    assert "ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_modo text;" in schema
