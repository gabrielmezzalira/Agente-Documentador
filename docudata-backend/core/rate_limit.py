import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _inteiro_positivo(nome: str, padrao: str) -> int:
    try:
        valor = int(os.environ.get(nome, padrao))
    except ValueError as exc:
        raise RuntimeError(f"{nome} deve ser um inteiro positivo") from exc
    if valor < 1:
        raise RuntimeError(f"{nome} deve ser um inteiro positivo")
    return valor


RATE_LIMIT_PER_MINUTE = _inteiro_positivo("RATE_LIMIT_PER_MINUTE", "20")
GEMINI_RATE_LIMIT = f"{RATE_LIMIT_PER_MINUTE}/minute"

# Autenticação usa limites próprios e bem mais apertados que os de IA: aqui o
# custo de um abuso não é conta de API, é força bruta de senha e criação de
# contas em massa nos endpoints públicos de cadastro.
AUTH_LOGIN_PER_MINUTE = _inteiro_positivo("AUTH_LOGIN_RATE_LIMIT_PER_MINUTE", "5")
AUTH_SIGNUP_PER_HOUR = _inteiro_positivo("AUTH_SIGNUP_RATE_LIMIT_PER_HOUR", "3")
LOGIN_RATE_LIMIT = f"{AUTH_LOGIN_PER_MINUTE}/minute"
SIGNUP_RATE_LIMIT = f"{AUTH_SIGNUP_PER_HOUR}/hour"


def get_client_ip(request: Request) -> str:
    """Identifica o cliente real atrás do proxy do Railway.

    Confiar no primeiro item de `X-Forwarded-For` só é seguro enquanto o
    Railway sobrescrever esse header e o backend não estiver acessível por um
    caminho que contorne o proxy: exposto direto, qualquer cliente forja o
    valor e escapa do limite. Trocar por uma lista de proxies confiáveis é
    assunto da Spec 10.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # O primeiro endereço é o cliente; os seguintes pertencem à cadeia de proxies.
        client_ip = forwarded_for.split(",", 1)[0].strip()
        if client_ip:
            return client_ip
    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip, headers_enabled=True)
