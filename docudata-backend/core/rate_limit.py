import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _rate_limit_por_minuto() -> int:
    try:
        valor = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "20"))
    except ValueError as exc:
        raise RuntimeError("RATE_LIMIT_PER_MINUTE deve ser um inteiro positivo") from exc
    if valor < 1:
        raise RuntimeError("RATE_LIMIT_PER_MINUTE deve ser um inteiro positivo")
    return valor


RATE_LIMIT_PER_MINUTE = _rate_limit_por_minuto()
GEMINI_RATE_LIMIT = f"{RATE_LIMIT_PER_MINUTE}/minute"


def get_client_ip(request: Request) -> str:
    """Identifica o cliente real atrás do proxy do Railway."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # O primeiro endereço é o cliente; os seguintes pertencem à cadeia de proxies.
        client_ip = forwarded_for.split(",", 1)[0].strip()
        if client_ip:
            return client_ip
    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip, headers_enabled=True)
