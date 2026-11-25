import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..deps import runtime_ready
from ..models import Message
from ..schemas import ChatRequest, ChatResponse, MessageOut
from ..services import memory
from ..services.generator import REFUSAL, build_messages, finalize, get_llm
from ..services.retriever import retrieve
from ..services.runtime import Runtime
from ..utils.errors import LLMUnavailable
from ..utils.ratelimit import rate_limit

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


def _prepare(db: Session, req: ChatRequest, rt: Runtime):
    """Check the session, rewrite follow-ups into standalone questions, and retrieve."""
    if not memory.get_session(db, req.session_id):
        raise HTTPException(404, "Chat session not found. Start a new chat.")
    history = memory.load_history(db, req.session_id, rt.settings.history_messages)
    rewritten = memory.rewrite_question(get_llm(), history, req.question)
    retrieval = retrieve(rewritten, rt.store, rt.embedder, rt.settings.top_k,
                         rt.settings.threshold_for(rt.embedder.name))
    return history, rewritten, retrieval


def _save_turn(db: Session, req: ChatRequest, answer: str, citations: list, grounded: bool, rewritten: str | None):
    memory.save_message(db, req.session_id, "user", req.question)
    memory.save_message(
        db, req.session_id, "assistant", answer,
        {"citations": citations, "grounded": grounded, "rewritten_question": rewritten},
    )


@router.post("/new")
def new_chat(db: Session = Depends(get_db)) -> dict:
    return {"session_id": memory.new_session(db)}


@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit)])
def chat(req: ChatRequest, db: Session = Depends(get_db), rt: Runtime = Depends(runtime_ready)) -> ChatResponse:
    start = time.perf_counter()
    history, rewritten, retrieval = _prepare(db, req, rt)
    if not retrieval.passed:  # guard 1: nothing similar enough, so do not call the LLM at all
        answer, citations, grounded = REFUSAL, [], False
    else:
        try:
            answer = get_llm().complete(build_messages(rewritten, retrieval.context, history))
        except LLMUnavailable as exc:
            raise HTTPException(503, str(exc))
        citations, grounded = finalize(answer, retrieval.context)  # guard 2: the model's own refusal
    shown_rewrite = rewritten if rewritten != req.question else None
    _save_turn(db, req, answer, citations, grounded, shown_rewrite)
    return ChatResponse(
        answer=answer, citations=citations, grounded=grounded,
        latency_ms=int((time.perf_counter() - start) * 1000), rewritten_question=shown_rewrite,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream", dependencies=[Depends(rate_limit)])
def chat_stream(req: ChatRequest, rt: Runtime = Depends(runtime_ready)) -> StreamingResponse:
    """Server-Sent Events: `meta`, then `token` events, then `done` (final citations) or `error`."""

    def events():
        start = time.perf_counter()
        with SessionLocal() as db:  # own session: the request-scoped one may be closed mid-stream
            try:
                history, rewritten, retrieval = _prepare(db, req, rt)
            except HTTPException as exc:
                yield _sse("error", {"message": exc.detail})
                return
            shown_rewrite = rewritten if rewritten != req.question else None
            yield _sse("meta", {"rewritten_question": shown_rewrite})
            if not retrieval.passed:
                answer, citations, grounded = REFUSAL, [], False
                yield _sse("token", {"text": answer})
            else:
                parts: list[str] = []
                try:
                    for tok in get_llm().stream(build_messages(rewritten, retrieval.context, history)):
                        parts.append(tok)
                        yield _sse("token", {"text": tok})
                except LLMUnavailable as exc:
                    yield _sse("error", {"message": str(exc)})
                    return
                answer = "".join(parts).strip()
                citations, grounded = finalize(answer, retrieval.context)
            _save_turn(db, req, answer, citations, grounded, shown_rewrite)
            yield _sse("done", {
                "answer": answer, "citations": citations, "grounded": grounded,
                "latency_ms": int((time.perf_counter() - start) * 1000), "rewritten_question": shown_rewrite,
            })

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{session_id}", response_model=list[MessageOut])
def history(session_id: str, db: Session = Depends(get_db)) -> list[MessageOut]:
    if not memory.get_session(db, session_id):
        raise HTTPException(404, "Chat session not found.")
    rows = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id).all()
    return [
        MessageOut(
            role=m.role, content=m.content, citations=m.meta.get("citations", []),
            grounded=m.meta.get("grounded"), created_at=m.created_at,
        )
        for m in rows
    ]
