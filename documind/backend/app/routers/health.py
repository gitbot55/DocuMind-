from fastapi import APIRouter

from ..config import get_settings
from ..db import SessionLocal
from ..models import Chunk, Document
from ..services import runtime as rt_module

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    """Cheap status check. Works while the model is still loading (status: starting)."""
    rt = rt_module.maybe_runtime()
    if rt is None:
        status = "error" if rt_module.startup_error else "starting"
        return {"status": status, "ready": False}
    with SessionLocal() as db:
        docs, chunks = db.query(Document).count(), db.query(Chunk).count()
    return {
        "status": "ok",
        "ready": True,
        "documents": docs,
        "chunks": chunks,
        "embedder": rt.embedder.name,
        "llm_configured": bool(get_settings().groq_api_key),
    }
