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
