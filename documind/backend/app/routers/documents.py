import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import runtime_ready
from ..models import Document
from ..schemas import DocumentOut, UploadResult
from ..services.ingestion import clean_filename, delete_document, ingest_pdf
from ..services.runtime import Runtime
from ..utils.errors import IngestionError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=list[UploadResult])
def upload(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db), rt: Runtime = Depends(runtime_ready)
) -> list[UploadResult]:
    """Upload up to N PDFs. Each file gets its own result so one bad file does not block the rest."""
    s = rt.settings
    if len(files) > s.max_files_per_upload:
        raise HTTPException(400, f"You can upload at most {s.max_files_per_upload} files at once.")
    results: list[UploadResult] = []
    for f in files:
        name = clean_filename(f.filename or "")
        try:
            data = f.file.read(s.max_upload_bytes + 1)
            doc = ingest_pdf(db, rt.store, rt.embedder, name, data, s)
            results.append(UploadResult(filename=name, ok=True, document=DocumentOut.model_validate(doc)))
        except IngestionError as exc:
            results.append(UploadResult(filename=name, ok=False, error=str(exc)))
        except Exception:
            log.exception("Unexpected error ingesting %s", name)
            results.append(UploadResult(filename=name, ok=False, error="Something went wrong while processing this file."))
    return results


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return db.query(Document).order_by(Document.id).all()


@router.delete("/{doc_id}")
def remove_document(doc_id: int, db: Session = Depends(get_db), rt: Runtime = Depends(runtime_ready)) -> dict:
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    delete_document(db, rt.store, doc, rt.settings)
    return {"deleted": doc_id}
