import json
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import runtime_ready
from ..models import EvalRun
from ..schemas import EvalRequest
from ..services.evaluator import run_evaluation
from ..services.generator import get_llm
from ..services.runtime import Runtime
from ..utils.ratelimit import rate_limit

router = APIRouter(prefix="/api/eval", tags=["eval"])
_lock = threading.Lock()
CLI_RESULT = Path(__file__).resolve().parents[2] / "eval" / "results" / "latest.json"


@router.post("/run", dependencies=[Depends(rate_limit)])
def run(req: EvalRequest | None = None, db: Session = Depends(get_db), rt: Runtime = Depends(runtime_ready)) -> dict:
    """Run the evaluation on the sample documents with optional setting overrides."""
    req = req or EvalRequest()
    if not _lock.acquire(blocking=False):
        raise HTTPException(409, "An evaluation is already running.")
    try:
        result = run_evaluation(
            rt.settings, rt.embedder, get_llm(),
            chunk_words=req.chunk_words, top_k=req.top_k, threshold=req.threshold, use_llm=req.use_llm,
        )
    finally:
        _lock.release()
    db.add(EvalRun(result_json=json.dumps(result)))
    db.commit()
    return result


@router.get("/latest")
def latest(db: Session = Depends(get_db)) -> dict:
    row = db.query(EvalRun).order_by(EvalRun.id.desc()).first()
    if row:
        return {"run": json.loads(row.result_json), "created_at": row.created_at.isoformat()}
    if CLI_RESULT.exists():  # a run made with `python eval/run_eval.py`
        return {"run": json.loads(CLI_RESULT.read_text()), "created_at": None}
    return {"run": None, "created_at": None}
