import os
import secrets

from fastapi import Header, HTTPException


APP_SECRET = os.environ.get("DOCUDATA_APP_SECRET")
if not APP_SECRET:
    raise RuntimeError(
        "DOCUDATA_APP_SECRET deve estar definida para iniciar o backend com segurança"
    )


def require_app_key(
    x_docudata_key: str | None = Header(default=None, alias="X-Docudata-Key"),
) -> None:
    """Exige a chave compartilhada em todas as rotas protegidas."""
    if not x_docudata_key or not secrets.compare_digest(x_docudata_key, APP_SECRET):
        raise HTTPException(
            status_code=401,
            detail="Chave de aplicação ausente ou inválida",
        )


def require_discovery_key(
    x_discovery_key: str | None = Header(default=None, alias="X-Discovery-Key"),
) -> None:
    """Chave de serviço dedicada do Agente Diagnóstico (Spec 12).

    Lida a cada requisição (e não no import) para a variável ausente nunca derrubar o
    backend: sem ela, as rotas de serviço do Discovery falham fechadas com 503. Não
    reusa DOCUDATA_APP_SECRET: a chave do hook legado e a do Agente giram separadas.
    """
    esperada = os.environ.get("DOCUDATA_DISCOVERY_KEY", "")
    if not esperada:
        raise HTTPException(status_code=503, detail="Integração de Discovery não configurada")
    # Compara em bytes: compare_digest com str não-ASCII levantaria TypeError (500).
    if not x_discovery_key or not secrets.compare_digest(
        x_discovery_key.encode("utf-8"), esperada.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Chave de serviço ausente ou inválida")
