import pytest


def _preparar(monkeypatch):
    import services.google_docs as google_docs

    chamadas = []
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "segredo")

    class FakeCredentials:
        def __init__(self, **kwargs):
            chamadas.append(kwargs)

        def refresh(self, _request):
            return None

    monkeypatch.setattr(google_docs, "OAuthCredentials", FakeCredentials)
    monkeypatch.setattr(google_docs, "Request", lambda: object())
    monkeypatch.setattr(google_docs, "build", lambda service, *_a, **_k: service)
    return google_docs, chamadas


def test_pta_usa_token_proprio_quando_existe(monkeypatch):
    google_docs, chamadas = _preparar(monkeypatch)
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "token-dados")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN_PTA", "token-pta")
    google_docs._get_services("pta")
    assert chamadas[0]["refresh_token"] == "token-pta"


def test_pta_sem_token_proprio_usa_o_de_dados(monkeypatch):
    google_docs, chamadas = _preparar(monkeypatch)
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "token-dados")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN_PTA", "")
    google_docs._get_services("pta")
    assert chamadas[0]["refresh_token"] == "token-dados"


def test_pta_sem_nenhum_token_falha_nomeando_o_de_dados(monkeypatch):
    google_docs, _ = _preparar(monkeypatch)
    monkeypatch.delenv("GOOGLE_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_REFRESH_TOKEN_PTA", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_REFRESH_TOKEN"):
        google_docs._get_services("pta")


def test_template_de_pta_prefere_o_proprio_e_reaproveita_o_de_dados(monkeypatch):
    from services.google_docs import _get_template_id
    for nome in ("GDOCS_TEMPLATE_ID_PLANNING_PTA", "GDOCS_TEMPLATE_ID_PTA",
                 "GDOCS_TEMPLATE_ID_PLANNING", "GDOCS_TEMPLATE_ID"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("GDOCS_TEMPLATE_ID", "modelo-dados")
    assert _get_template_id("planning", "pta") == "modelo-dados"
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PTA", "modelo-pta")
    assert _get_template_id("planning", "pta") == "modelo-pta"
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING_PTA", "planning-pta")
    assert _get_template_id("planning", "pta") == "planning-pta"


def test_pasta_raiz_de_pta_usa_env_propria_e_nunca_cai_em_dados(monkeypatch):
    from services.google_docs import _get_root_folder_id
    monkeypatch.setenv("GDRIVE_FOLDER_ID", "pasta-dados")
    monkeypatch.delenv("GDRIVE_FOLDER_ID_PTA", raising=False)
    with pytest.raises(RuntimeError, match="GDRIVE_FOLDER_ID_PTA"):
        _get_root_folder_id("pta")
    monkeypatch.setenv("GDRIVE_FOLDER_ID_PTA", "pasta-pta")
    assert _get_root_folder_id("pta") == "pasta-pta"
