from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def test_bloco_rodada_b1_tem_as_tabelas_da_meta():
    sql = _SCHEMA.read_text(encoding="utf-8")
    assert "-- Rodada B1" in sql
    bloco = sql.split("-- Rodada B1", 1)[1]
    for trecho in (
        "CREATE TABLE IF NOT EXISTS sprint_meta_funcionalidades",
        "PRIMARY KEY (sprint_id, funcionalidade_id)",
        "CREATE TABLE IF NOT EXISTS sprint_meta_eventos",
        "CHECK (acao IN ('incluiu','retirou'))",
        "idx_sprint_meta_eventos_sprint",
    ):
        assert trecho in bloco, trecho
