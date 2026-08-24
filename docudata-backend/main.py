from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.rate_limit import limiter
from core.security import require_app_key
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich, settings
from services.gemini_key import (
    GeminiApiKeyInvalid,
    GeminiApiKeyNotConfigured,
    GeminiApiKeyStorageError,
)

app = FastAPI(title="DocuData API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(GeminiApiKeyNotConfigured)
async def gemini_key_not_configured_handler(request: Request, exc: GeminiApiKeyNotConfigured):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "A chave Gemini da aplicação ainda não está configurada. Configure-a em Configurações antes de usar recursos de IA."
        },
    )


@app.exception_handler(GeminiApiKeyInvalid)
async def gemini_key_invalid_handler(request: Request, exc: GeminiApiKeyInvalid):
    return JSONResponse(status_code=422, content={"detail": "A chave Gemini não pode estar vazia."})


@app.exception_handler(GeminiApiKeyStorageError)
async def gemini_key_storage_handler(request: Request, exc: GeminiApiKeyStorageError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Não foi possível acessar a configuração segura do Gemini."},
    )

try:
    max_upload_mb = int(os.environ.get("MAX_UPLOAD_MB", "20"))
except ValueError as exc:
    raise RuntimeError("MAX_UPLOAD_MB deve ser um inteiro positivo") from exc
if max_upload_mb < 1:
    raise RuntimeError("MAX_UPLOAD_MB deve ser um inteiro positivo")
max_upload_bytes = max_upload_mb * 1024 * 1024

allowed_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if "*" in allowed_origins:
    raise RuntimeError("ALLOWED_ORIGINS não pode conter '*'")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_oversized_request(request: Request, call_next):
    content_length = request.headers.get("Content-Length")
    if content_length:
        try:
            request_size = int(content_length)
        except ValueError:
            request_size = None
        if request_size is not None and request_size > max_upload_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Upload excede o limite de {max_upload_mb} MB"},
            )

    # Streams sem Content-Length seguem sem bloqueio; leitura em chunks fica fora desta spec.
    return await call_next(request)

protected = [Depends(require_app_key)]

app.include_router(projects.router, dependencies=protected)
app.include_router(sprints.router, dependencies=protected)
app.include_router(sprint_docs.router, dependencies=protected)
app.include_router(ingest.router, dependencies=protected)
app.include_router(generate.router, dependencies=protected)
app.include_router(ingestions.router, dependencies=protected)
app.include_router(search.router, dependencies=protected)
app.include_router(export.router, dependencies=protected)
app.include_router(commit_ingest.router, dependencies=protected)
app.include_router(enrich.router, dependencies=protected)
app.include_router(settings.router, dependencies=protected)


@app.get("/health")
async def health():
    """Health check endpoint — returns ok without hitting Supabase or Gemini."""
    return {"status": "ok"}
