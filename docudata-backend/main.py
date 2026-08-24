from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.security import require_app_key
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs, export, commit_ingest, enrich

app = FastAPI(title="DocuData API", version="1.0.0")

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


@app.get("/health")
async def health():
    """Health check endpoint — returns ok without hitting Supabase or Gemini."""
    return {"status": "ok"}
