"""Process-wide objects (embedder + vector store) and startup bootstrap."""
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings, get_settings
from ..db import SessionLocal, init_db
from ..models import Chunk, Document
from ..utils.errors import IngestionError
from .embeddings import get_embedder
from .ingestion import ingest_pdf
from .vector_store import ChunkRecord, VectorStore

log = logging.getLogger(__name__)


@dataclass
class Runtime:
    settings: Settings
    embedder: object
    store: VectorStore


_runtime: Runtime | None = None


def get_runtime() -> Runtime:
    if _runtime is None:
        raise RuntimeError("Runtime not initialised; call init_runtime() at startup.")
    return _runtime


def init_runtime() -> Runtime:
    """Create tables, load (or rebuild) the FAISS index, and seed the demo documents if empty."""
    global _runtime
    settings = get_settings()
    init_db()
    embedder = get_embedder()
    index_path = settings.index_dir / "faiss.index"

    with SessionLocal() as db:
        rows = db.query(Chunk).all()
        records = [ChunkRecord(r.id, r.doc_id, r.filename, r.page, r.text) for r in rows]
        store = VectorStore.load(embedder.dim, index_path, embedder.name, records)
        if store is None:
            store = VectorStore(embedder.dim, index_path, embedder.name)
            if records:
                log.info("Rebuilding index from %d stored chunks", len(records))
                for i in range(0, len(records), 64):
                    batch = records[i : i + 64]
                    store.add(batch, embedder.encode([r.text for r in batch]))
                store.save()

        if db.query(Document).count() == 0:
            _seed_samples(db, store, embedder, settings)

    _runtime = Runtime(settings, embedder, store)
    log.info("Runtime ready: embedder=%s, chunks=%d", embedder.name, store.count)
    return _runtime


def _seed_samples(db, store, embedder, settings: Settings) -> None:
    for pdf in sorted(Path(settings.sample_docs_dir).glob("*.pdf")):
        try:
            ingest_pdf(db, store, embedder, pdf.name, pdf.read_bytes(), settings)
        except IngestionError as exc:
            log.warning("Skipped sample doc %s: %s", pdf.name, exc)


startup_error: str | None = None


def maybe_runtime() -> Runtime | None:
    """The runtime if startup has finished, else None."""
    return _runtime


def start_in_background() -> None:
    """Run init_runtime() in a thread so the server can answer /api/health while the model loads."""

    def _run() -> None:
        global startup_error
        try:
            init_runtime()
        except Exception as exc:  # keep the server up and report the problem via /api/health
            log.exception("Startup failed")
            startup_error = str(exc)

    threading.Thread(target=_run, daemon=True, name="documind-startup").start()
