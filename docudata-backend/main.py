from dotenv import load_dotenv
load_dotenv()

import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich, funcionalidades, painel, revisao_ingest, composer, aceite_ingest, boletins, sprint_funcionalidades, operacionais, tasks, metricas, auth, performance, avaliacoes, pontuacao, metodologia, solicitacoes, pessoas
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


app = FastAPI(title="DocuData API", version="1.0.0", lifespan=lifespan)

_frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def _erro_nao_tratado(request: Request, exc: Exception):
    """Sem isso, qualquer exceção não tratada em qualquer rota escapa da
    ExceptionMiddleware do FastAPI e o CORSMiddleware nunca chega a rodar —
    o navegador reporta "bloqueado por CORS" mesmo o servidor estando
    corretamente configurado, escondendo o erro real de quem está debugando
    pelo DevTools. Este handler roda por dentro do stack de middleware, então
    a resposta ainda passa pelo CORSMiddleware normalmente."""
    logging.getLogger("uvicorn.error").exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"Erro interno: {exc}"})


app.include_router(auth.router)
app.include_router(projects.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(sprints.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(sprint_docs.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(ingest.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(generate.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(ingestions.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(search.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(export.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(commit_ingest.router)
app.include_router(enrich.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(funcionalidades.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(painel.router, dependencies=[Depends(require_not_operacional)])
app.include_router(revisao_ingest.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(composer.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(aceite_ingest.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(boletins.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(sprint_funcionalidades.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(operacionais.router, dependencies=[Depends(require_not_operacional)])
app.include_router(tasks.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(metricas.router, dependencies=[Depends(require_not_operacional)])
app.include_router(avaliacoes.router, dependencies=[Depends(require_not_operacional)])
app.include_router(pontuacao.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(performance.router)
app.include_router(metodologia.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(solicitacoes.router, dependencies=[Depends(get_current_pessoa)])
app.include_router(pessoas.router, dependencies=[Depends(get_current_pessoa)])


@app.get("/health")
async def health():
    """Health check endpoint — returns ok without hitting Supabase or Gemini."""
    return {"status": "ok"}


@app.post("/notifications/check")
async def trigger_notification_check(background_tasks: BackgroundTasks):
    """Dispara manualmente o check de notificações (uso em testes). Retorna imediatamente."""
    background_tasks.add_task(check_and_send_notifications)
    return {"status": "ok", "message": "Check iniciado em background — veja os logs do Railway para detalhes."}


@app.post("/tasks/travamento/check")
async def trigger_travamento_check(background_tasks: BackgroundTasks):
    """Dispara manualmente o check de travamento automático (uso em testes). Retorna imediatamente."""
    background_tasks.add_task(check_travamento_automatico)
    return {"status": "ok", "message": "Check de travamento automático iniciado em background — veja os logs do Railway para detalhes."}
