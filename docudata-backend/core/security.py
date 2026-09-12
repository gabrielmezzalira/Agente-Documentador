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
