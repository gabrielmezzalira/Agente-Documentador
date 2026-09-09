from fastapi import APIRouter

from models.schemas import GeminiApiKeyStatus, GeminiApiKeyUpdate
from services.gemini_key import get_gemini_api_key_status, set_gemini_api_key


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/gemini", response_model=GeminiApiKeyStatus)
async def get_gemini_status():
    return get_gemini_api_key_status()


@router.put("/gemini/api-key", response_model=GeminiApiKeyStatus)
async def update_gemini_api_key(data: GeminiApiKeyUpdate):
    return set_gemini_api_key(data.api_key)
