"""Pydantic request/response models."""
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: int
    filename: str
    pages: int
    chunk_count: int
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class UploadResult(BaseModel):
    filename: str
    ok: bool
    error: str | None = None
    document: DocumentOut | None = None


class Citation(BaseModel):
    number: int
    filename: str
    page: int
    snippet: str
    text: str
    score: float


class ChatRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool
    latency_ms: int
    rewritten_question: str | None = None


class MessageOut(BaseModel):
    role: str
    content: str
    citations: list[Citation] = []
    grounded: bool | None = None
    created_at: datetime


class EvalRequest(BaseModel):
    chunk_words: int | None = None
    top_k: int | None = None
    threshold: float | None = None
    use_llm: bool = True
