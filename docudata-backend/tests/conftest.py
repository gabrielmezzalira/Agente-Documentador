import os

import pytest
from cryptography.fernet import Fernet


os.environ.setdefault("DOCUDATA_APP_SECRET", "chave-de-aplicacao-para-testes")
os.environ.setdefault("ALLOWED_ORIGINS", "https://frontend.test,http://localhost:3000")
os.environ.setdefault("DOCUDATA_SECRETS_KEY", Fernet.generate_key().decode("utf-8"))
os.environ.setdefault("JWT_SECRET", "segredo-jwt-apenas-para-testes-automatizados")


@pytest.fixture
def autenticar():
    """Simula a sessão do navegador sem enfraquecer a autenticação em produção."""
    def _autenticar(client, cargo: str = "gerente"):
        from services.auth import criar_jwt

        token = criar_jwt("pessoa-teste", "pessoa@citi.org.br", cargo)
        client.cookies.set("docudata_session", token)
        return client

    return _autenticar


@pytest.fixture(autouse=True)
def limpar_rate_limiter():
    """Zera a memória do limiter entre testes.

    O limite de login/cadastro é por IP e o TestClient sempre usa o mesmo, então
    sem isso um teste consumia a cota do seguinte. Não desliga o limiter: cada
    teste continua exercitando o caminho real de produção.
    """
    from core.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def classificador_fixo(request, monkeypatch):
    """Os testes antigos criam task sem chamar o modelo: o classificador devolve
    uma classificação 'aplicada' com a opinião do gerente (ou 1). Desligue com
    @pytest.mark.classificador_real nos testes que exercitam o ciclo de verdade."""
    if request.node.get_closest_marker("classificador_real"):
        yield
        return

    import services.classificador_ciclo as ciclo
    from services.regua import NIVEIS

    async def _fake(client, *, titulo, descricao, checklist, opiniao_gerente, gerente_id):
        nivel = opiniao_gerente if opiniao_gerente in NIVEIS else 1
        return {
            "status": "aplicada", "faltando": [], "sinais": None, "nivel_sinais": None,
            "parecidas": [], "nivel_parecidas": None, "nivel_geral": nivel,
            "justificativa_geral": "classificador de teste", "opiniao_gerente": opiniao_gerente,
            "nivel_combinado": nivel, "ajuste_tempo": 0, "nivel_final": nivel,
            "motivo_revisao": None, "parametros": None, "vetor": None,
        }

    monkeypatch.setattr(ciclo, "classificar_para_criacao", _fake)
    yield
