from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import projects, ingest, generate, ingestions, search, sprints, sprint_docs

app = FastAPI(title="DocuData API", version="1.0.0")

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


@app.get("/health")
async def health():
    """Health check endpoint — returns ok without hitting Supabase or Gemini."""
    return {"status": "ok"}
