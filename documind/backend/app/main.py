"""DocuMind API entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import chat, documents, eval as eval_router, health
from .services.runtime import init_runtime, start_in_background
from .utils.logging import setup_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if settings.sync_startup:
        init_runtime()
    else:
        start_in_background()  # model loading can be slow on free hosting; /api/health reports "starting"
    yield


app = FastAPI(title="DocuMind", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
for r in (health.router, documents.router, chat.router, eval_router.router):
    app.include_router(r)

@app.get("/")
async def root():
    return {
        "message": "Welcome to DocuMind API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    } 
