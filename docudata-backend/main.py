from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich, funcionalidades, painel, revisao_ingest, composer, aceite_ingest, boletins, sprint_funcionalidades
from services.notification_checker import check_and_send_notifications

logging.basicConfig(level=logging.INFO)

_scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler.add_job(check_and_send_notifications, "interval", hours=1, id="sprint_notifications")
    _scheduler.start()
    yield
    _scheduler.shutdown()


app = FastAPI(title="DocuData API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(sprints.router)
app.include_router(sprint_docs.router)
app.include_router(ingest.router)
app.include_router(generate.router)
app.include_router(ingestions.router)
app.include_router(search.router)
app.include_router(export.router)
app.include_router(commit_ingest.router)
app.include_router(enrich.router)
app.include_router(funcionalidades.router)
app.include_router(painel.router)
app.include_router(revisao_ingest.router)
app.include_router(composer.router)
app.include_router(aceite_ingest.router)
app.include_router(boletins.router)
app.include_router(sprint_funcionalidades.router)


@app.get("/health")
async def health():
    """Health check endpoint — returns ok without hitting Supabase or Gemini."""
    return {"status": "ok"}


@app.post("/notifications/check")
async def trigger_notification_check(background_tasks: BackgroundTasks):
    """Dispara manualmente o check de notificações (uso em testes). Retorna imediatamente."""
    background_tasks.add_task(check_and_send_notifications)
    return {"status": "ok", "message": "Check iniciado em background — veja os logs do Railway para detalhes."}
