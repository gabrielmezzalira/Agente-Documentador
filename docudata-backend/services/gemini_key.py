"""Armazenamento seguro da chave Gemini global da aplicação."""

import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

from services.supabase_client import get_client


_SETTING_KEY = "gemini_api_key"


class GeminiApiKeyNotConfigured(Exception):
    """Nenhuma chave Gemini global foi cadastrada."""


class GeminiApiKeyStorageError(Exception):
    """A configuração global não pôde ser lida ou gravada com segurança."""


class GeminiApiKeyInvalid(Exception):
    """A nova chave Gemini não contém um valor válido."""


def _fernet() -> Fernet:
    secrets_key = os.environ.get("DOCUDATA_SECRETS_KEY", "")
    if not secrets_key:
        raise GeminiApiKeyStorageError("Configuração segura indisponível")
    try:
        return Fernet(secrets_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise GeminiApiKeyStorageError("Configuração segura inválida") from exc


def get_gemini_api_key() -> str:
    """Retorna a chave global descriptografada, sem cache ou fallback por projeto."""
    try:
        response = (
            get_client()
            .table("app_settings")
            .select("encrypted_value")
            .eq("key", _SETTING_KEY)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise GeminiApiKeyStorageError("Não foi possível ler a configuração segura") from exc

    if not response.data:
        raise GeminiApiKeyNotConfigured

    encrypted_value = response.data[0].get("encrypted_value")
    if not encrypted_value:
        raise GeminiApiKeyStorageError("Configuração segura inválida")
    try:
        api_key = _fernet().decrypt(encrypted_value.encode("utf-8")).decode("utf-8").strip()
    except (InvalidToken, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise GeminiApiKeyStorageError("Configuração segura inválida") from exc
    if not api_key:
        raise GeminiApiKeyStorageError("Configuração segura inválida")
    return api_key


def set_gemini_api_key(api_key: str) -> dict:
    """Criptografa e substitui atomicamente a chave global; nunca retorna o segredo."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise GeminiApiKeyInvalid("A chave Gemini não pode estar vazia")

    normalized = api_key.strip()
    encrypted_value = _fernet().encrypt(normalized.encode("utf-8")).decode("utf-8")
    updated_at = datetime.now(timezone.utc).isoformat()
    safe_status = {
        "configured": True,
        "key_hint": f"••••••••{normalized[-4:]}",
        "updated_at": updated_at,
    }
    payload = {
        "key": _SETTING_KEY,
        "encrypted_value": encrypted_value,
        "display_hint": safe_status["key_hint"],
        "updated_at": updated_at,
    }
    try:
        get_client().table("app_settings").upsert(payload, on_conflict="key").execute()
    except Exception as exc:
        raise GeminiApiKeyStorageError("Não foi possível salvar a configuração segura") from exc
    return safe_status


def get_gemini_api_key_status() -> dict:
    """Retorna somente metadados seguros da configuração global."""
    try:
        response = (
            get_client()
            .table("app_settings")
            .select("display_hint, updated_at")
            .eq("key", _SETTING_KEY)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise GeminiApiKeyStorageError("Não foi possível ler a configuração segura") from exc

    if not response.data:
        return {"configured": False, "key_hint": None, "updated_at": None}
    row = response.data[0]
    return {
        "configured": True,
        "key_hint": row.get("display_hint"),
        "updated_at": row.get("updated_at"),
    }
