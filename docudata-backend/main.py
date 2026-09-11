from dotenv import load_dotenv
load_dotenv()

import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.observability import (
    MENSAGEM_ERRO_INTERNO,
    REQUEST_ID_HEADER,
    encerrar_contexto_requisicao,
    iniciar_contexto_requisicao,
    normalizar_request_id,
    registrar_excecao,
    registrar_resposta,
)
from core.rate_limit import limiter
from core.security import require_app_key
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich, funcionalidades, painel, revisao_ingest, composer, aceite_ingest, boletins, sprint_funcionalidades, operacionais, tasks, metricas, auth, performance, avaliacoes, pontuacao, metodologia, solicitacoes, pessoas, settings, github_integration
from services.gemini_key import (
    GeminiApiKeyInvalid,
    GeminiApiKeyNotConfigured,
    GeminiApiKeyStorageError,
)
from services.notification_checker import check_and_send_notifications
from services.travamento_checker import check_travamento_automatico
from services.auth import get_current_pessoa, require_not_operacional

logging.basicConfig(level=logging.INFO)

_scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler.add_job(check_and_send_notifications, "interval", hours=1, id="sprint_notifications")
    _scheduler.add_job(check_travamento_automatico, "interval", hours=24, id="task_travamento_check")
    _scheduler.start()
    yield
    _scheduler.shutdown()


def _flag_habilitada(nome: str, padrao: str) -> bool:
    return os.environ.get(nome, padrao).strip().lower() in {"1", "true", "yes", "on"}


# Local fica ligada para o time explorar a API; produção deve subir com
# API_DOCS_ENABLED=false para não publicar o mapa completo de rotas e schemas.
API_DOCS_ENABLED = _flag_habilitada("API_DOCS_ENABLED", "true")

app = FastAPI(
    title="DocuData API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if API_DOCS_ENABLED else None,
    redoc_url="/redoc" if API_DOCS_ENABLED else None,
    openapi_url="/openapi.json" if API_DOCS_ENABLED else None,
)
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

_frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allowed_origins = {
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}
allowed_origins.add(_frontend_url.rstrip("/"))
if "*" in allowed_origins:
    raise RuntimeError("ALLOWED_ORIGINS não pode conter '*'")

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
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

    # Streams sem Content-Length seguem sem bloqueio; leitura em chunks fica fora desta implementação.
    return await call_next(request)


@app.middleware("http")
async def correlacionar_requisicao(request: Request, call_next):
    """Atribui (ou reaproveita) o `X-Request-ID` e devolve no response."""
    request_id = normalizar_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.scope.setdefault("state", {})["request_id"] = request_id
    token = iniciar_contexto_requisicao(request_id, request.method, request.url.path)
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        registrar_resposta(request_id, request.method, request.url.path, response.status_code)
        return response
    finally:
        encerrar_contexto_requisicao(token)


@app.exception_handler(Exception)
async def _erro_nao_tratado(request: Request, exc: Exception):
    """Sem isso, qualquer exceção não tratada em qualquer rota escapa da
    ExceptionMiddleware do FastAPI e o navegador reporta "bloqueado por CORS"
    mesmo o servidor estando configurado corretamente, escondendo o erro real
    de quem está debugando pelo DevTools.

    O corpo devolve apenas mensagem genérica + `request_id`: interpolar a
    exceção aqui já vazou nome de tabela, URL interna e trecho de payload para
    o navegador. O detalhe real fica no log, correlacionado pelo mesmo id."""
    request_id = registrar_excecao(request, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": MENSAGEM_ERRO_INTERNO, "request_id": request_id},
        headers={REQUEST_ID_HEADER: request_id},
    )


app_key = [Depends(require_app_key)]
authenticated = [Depends(get_current_pessoa)]
restricted = [Depends(require_not_operacional)]

app.include_router(auth.router)
app.include_router(projects.router, dependencies=authenticated)
app.include_router(sprints.router, dependencies=authenticated)
app.include_router(sprint_docs.router, dependencies=authenticated)
app.include_router(ingest.router, dependencies=authenticated)
app.include_router(generate.router, dependencies=authenticated)
app.include_router(ingestions.router, dependencies=authenticated)
app.include_router(search.router, dependencies=authenticated)
app.include_router(export.router, dependencies=authenticated)
# O hook legado autentica pela chave da aplicação e não possui cookie de usuário.
app.include_router(commit_ingest.router, dependencies=app_key)
app.include_router(enrich.router, dependencies=authenticated)
app.include_router(funcionalidades.router, dependencies=authenticated)
app.include_router(painel.router, dependencies=restricted)
app.include_router(revisao_ingest.router, dependencies=app_key)
app.include_router(composer.router, dependencies=authenticated)
app.include_router(aceite_ingest.service_router, dependencies=app_key)
app.include_router(aceite_ingest.router, dependencies=authenticated)
app.include_router(boletins.router, dependencies=authenticated)
app.include_router(sprint_funcionalidades.router, dependencies=authenticated)
app.include_router(operacionais.router, dependencies=restricted)
app.include_router(tasks.router, dependencies=authenticated)
app.include_router(metricas.router, dependencies=restricted)
app.include_router(avaliacoes.router, dependencies=restricted)
app.include_router(pontuacao.router, dependencies=authenticated)
app.include_router(performance.router)
app.include_router(metodologia.router, dependencies=authenticated)
app.include_router(solicitacoes.router, dependencies=authenticated)
app.include_router(pessoas.router, dependencies=authenticated)
app.include_router(settings.router, dependencies=restricted)
app.include_router(github_integration.router, dependencies=restricted)

# O GitHub usa state assinado ou HMAC do corpo bruto, sem credenciais do navegador.
app.include_router(github_integration.public_router)


@app.get("/health")
async def health():
    """Health check endpoint — returns ok without hitting Supabase or Gemini."""
    return {"status": "ok"}


@app.post("/notifications/check", dependencies=restricted)
async def trigger_notification_check(background_tasks: BackgroundTasks):
    """Dispara manualmente o check de notificações (uso em testes). Retorna imediatamente."""
    background_tasks.add_task(check_and_send_notifications)
    return {"status": "ok", "message": "Check iniciado em background — veja os logs do Railway para detalhes."}


@app.post("/tasks/travamento/check", dependencies=restricted)
async def trigger_travamento_check(background_tasks: BackgroundTasks):
    """Dispara manualmente o check de travamento automático (uso em testes). Retorna imediatamente."""
    background_tasks.add_task(check_travamento_automatico)
    return {"status": "ok", "message": "Check de travamento automático iniciado em background — veja os logs do Railway para detalhes."}
