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


def test_v9_esta_presente_e_inteiramente_comentada():
    assert "Migration v9: Discovery" in SCHEMA
    ativas = "\n".join(_linhas_ativas())
    for nome in ("discovery_reunioes", "discovery_transcricoes", "requisito_evidencias", "requisito_transicoes"):
        assert nome in SCHEMA
        assert nome not in ativas
    assert "CREATE TABLE IF NOT EXISTS requisitos" in SCHEMA
    assert "CREATE TABLE IF NOT EXISTS requisitos" not in ativas


def test_v9_garante_idempotencia_por_sessao():
    assert "uq_discovery_reunioes_fonte" in SCHEMA
    assert "WHERE fonte_session_id IS NOT NULL" in SCHEMA
