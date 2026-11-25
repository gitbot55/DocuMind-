"""Chat sessions: history storage and follow-up question rewriting."""
import json
import logging
import uuid

from sqlalchemy.orm import Session

from ..models import ChatSession, Message
from ..utils.errors import LLMUnavailable
from .generator import LLM

log = logging.getLogger(__name__)

REWRITE_PROMPT = (
    "Rewrite the user's latest question as a single standalone question that can be understood "
    "without the conversation. Keep names, numbers, and terms. If it is already standalone, "
    "return it unchanged. Output only the question."
)


def new_session(db: Session) -> str:
    session = ChatSession(id=str(uuid.uuid4()))
    db.add(session)
    db.commit()
    return session.id


def get_session(db: Session, session_id: str) -> ChatSession | None:
    return db.get(ChatSession, session_id)


def load_history(db: Session, session_id: str, limit: int) -> list[dict]:
    rows = (
        db.query(Message).filter(Message.session_id == session_id).order_by(Message.id.desc()).limit(limit).all()
    )
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


def save_message(db: Session, session_id: str, role: str, content: str, meta: dict | None = None) -> None:
    db.add(Message(session_id=session_id, role=role, content=content, meta_json=json.dumps(meta or {})))
    db.commit()


def rewrite_question(llm: LLM, history: list[dict], question: str) -> str:
    """Turn a follow-up into a standalone question. Falls back to the original on any failure."""
    if not history:
        return question
    convo = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in history)
    try:
        out = llm.complete(
            [
                {"role": "system", "content": REWRITE_PROMPT},
                {"role": "user", "content": f"Conversation:\n{convo}\n\nLatest question: {question}"},
            ],
            max_tokens=120,
            temperature=0.0,
        )
    except LLMUnavailable:
        return question
    out = out.strip().strip('"')
    return out if 0 < len(out) <= 500 else question
