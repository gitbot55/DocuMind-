"""PDF ingestion: validate -> extract pages -> chunk -> embed -> index."""
import io
import logging
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Chunk, Document
from ..utils.errors import IngestionError
from .chunking import chunk_pages
from .vector_store import ChunkRecord, VectorStore

log = logging.getLogger(__name__)

MAX_PAGES = 300


def clean_filename(filename: str) -> str:
    name = Path(filename or "").name.strip()
    return name[:200] or "document.pdf"


def extract_pages(data: bytes) -> list[tuple[int, str]]:
    """Return [(page_number, text)] or raise IngestionError with a user-friendly message."""
    if not data:
        raise IngestionError("The file is empty.")
    if not data.lstrip()[:5] == b"%PDF-":
        raise IngestionError("This file is not a PDF (checked the file content, not just the name).")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            if not reader.decrypt(""):
                raise IngestionError("This PDF is password protected.")
        if len(reader.pages) > MAX_PAGES:
            raise IngestionError(f"This PDF has more than {MAX_PAGES} pages. Please upload a smaller file.")
        pages = [(i + 1, (page.extract_text() or "").strip()) for i, page in enumerate(reader.pages)]
    except IngestionError:
        raise
    except Exception as exc:
        log.warning("PDF parse failed: %s", exc)
        raise IngestionError("Could not read this PDF. The file may be damaged.") from exc
    if not any(len(text.split()) >= 5 for _, text in pages):
        raise IngestionError("No readable text found. Scanned or image-only PDFs are not supported yet.")
    return pages


def ingest_pdf(
    db: Session, store: VectorStore, embedder, filename: str, data: bytes, settings: Settings
) -> Document:
    """Ingest one PDF into the database and the vector index."""
    filename = clean_filename(filename)
    if not filename.lower().endswith(".pdf"):
        raise IngestionError("Only PDF files are accepted.")
    if len(data) > settings.max_upload_bytes:
        raise IngestionError(f"File is larger than {settings.max_upload_mb} MB.")

    pages = extract_pages(data)
    pieces = chunk_pages(pages, settings.chunk_words, settings.chunk_overlap)
    if not pieces:
        raise IngestionError("No usable text could be extracted from this PDF.")

    vectors = embedder.encode([p.text for p in pieces])  # slow part, done before taking the lock

    with store.lock:
        doc = Document(filename=filename, pages=len(pages), chunk_count=len(pieces), status="ready")
        db.add(doc)
        db.flush()
        rows = [Chunk(doc_id=doc.id, filename=filename, page=p.page, text=p.text) for p in pieces]
        db.add_all(rows)
        db.flush()
        records = [ChunkRecord(r.id, doc.id, filename, r.page, r.text) for r in rows]
        try:
            store.add(records, vectors)
            db.commit()
        except Exception:
            store.remove_doc(doc.id)
            db.rollback()
            raise
        store.save()

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    (settings.uploads_dir / f"{doc.id}_{filename}").write_bytes(data)
    log.info("Ingested %s: %d pages, %d chunks", filename, len(pages), len(pieces))
    return doc


def delete_document(db: Session, store: VectorStore, doc: Document, settings: Settings) -> None:
    with store.lock:
        store.remove_doc(doc.id)
        for f in settings.uploads_dir.glob(f"{doc.id}_*"):
            f.unlink(missing_ok=True)
        db.delete(doc)
        db.commit()
        store.save()
