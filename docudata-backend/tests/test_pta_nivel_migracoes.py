from pathlib import Path

SCHEMA = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")


def _bloco(titulo: str) -> str:
    inicio = SCHEMA.rindex("\n", 0, SCHEMA.index(titulo)) + 1  # começa no início da linha
    return SCHEMA[inicio:]


def test_migracao_subarea_pta_comentada_com_preflight_e_rollback():
    b = _bloco("Migration v11 (2026-11-17): subárea PTA")
    assert "CHECK (subarea IN ('dados','dev','produto','pta'))" in b
    assert "Preflight" in b and "Rollback" in b
    for linha in b.split("Migration v12")[0].splitlines():
        assert not linha.strip() or linha.startswith("--"), linha


def test_migracao_status_manual_comentada_com_preflight_e_rollback():
    b = _bloco("Migration v12 (2026-11-17): status manual")
    assert "'aplicada','em_revisao','provisoria','resolvida','manual'" in b
    assert "Preflight" in b and "Rollback" in b
    for linha in b.splitlines():
        assert not linha.strip() or linha.startswith("--"), linha
