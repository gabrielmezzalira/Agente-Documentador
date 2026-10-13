import pytest


def test_pasta_raiz_de_produto_usa_env_propria(monkeypatch):
    from services.google_docs import _get_root_folder_id
    monkeypatch.setenv("GDRIVE_FOLDER_ID_PRODUTO", "pasta-produto")
    assert _get_root_folder_id("produto") == "pasta-produto"


def test_pasta_raiz_de_produto_nunca_cai_em_dados_nem_dev(monkeypatch):
    from services.google_docs import _get_root_folder_id
    monkeypatch.setenv("GDRIVE_FOLDER_ID", "pasta-dados")
    monkeypatch.setenv("GDRIVE_FOLDER_ID_DEV", "pasta-dev")
    monkeypatch.delenv("GDRIVE_FOLDER_ID_PRODUTO", raising=False)
    with pytest.raises(RuntimeError, match="GDRIVE_FOLDER_ID_PRODUTO"):
        _get_root_folder_id("produto")


def test_template_de_produto_prefere_o_proprio_e_reaproveita_o_de_dados(monkeypatch):
    from services.google_docs import _get_template_id
    for nome in ("GDOCS_TEMPLATE_ID_PLANNING_PRODUTO", "GDOCS_TEMPLATE_ID_PRODUTO",
                 "GDOCS_TEMPLATE_ID_PLANNING", "GDOCS_TEMPLATE_ID"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("GDOCS_TEMPLATE_ID", "modelo-dados")
    assert _get_template_id("planning", "produto") == "modelo-dados"
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PRODUTO", "modelo-produto")
    assert _get_template_id("planning", "produto") == "modelo-produto"
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING_PRODUTO", "planning-produto")
    assert _get_template_id("planning", "produto") == "planning-produto"


def test_autenticacao_google_de_produto_exige_token_proprio(monkeypatch):
    from services.google_docs import _get_services
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "segredo")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "token-dados")
    monkeypatch.delenv("GOOGLE_REFRESH_TOKEN_PRODUTO", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_REFRESH_TOKEN_PRODUTO"):
        _get_services("produto")


def test_github_app_aceita_produto():
    from services.github_app import subarea_github_habilitada
    assert subarea_github_habilitada("produto") is True
