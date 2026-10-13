from pathlib import Path

SCHEMA = (Path(__file__).resolve().parent.parent / "supabase_schema.sql").read_text(encoding="utf-8")


def _linhas_ativas() -> list[str]:
    return [l for l in SCHEMA.splitlines() if l.strip() and not l.lstrip().startswith("--")]


def test_v8_esta_presente_e_inteiramente_comentada():
    assert "Migration v8: subárea produto" in SCHEMA
    assert "encaminhar_projeto" in SCHEMA
    ativas = "\n".join(_linhas_ativas())
    assert "projeto_encaminhamentos" not in ativas
    assert "encaminhar_projeto" not in ativas
    assert "'produto'" not in ativas


def test_v8_traz_preflight_e_rollback():
    assert "-- Preflight (somente leitura)" in SCHEMA
    assert "-- Rollback (só se NENHUM projeto tiver subarea = 'produto')" in SCHEMA
