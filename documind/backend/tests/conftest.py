"""Test setup: temp data dir, offline embedder, no real LLM, synchronous startup."""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="documind-test-")
os.environ["EMBEDDING_BACKEND"] = "hashing"
os.environ["SYNC_STARTUP"] = "true"
os.environ["GROQ_API_KEY"] = ""
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ.pop("SCORE_THRESHOLD", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class FakeLLM:
    """Stands in for Groq: records calls and returns canned text."""

    available = True

    def __init__(self):
        self.calls: list[list[dict]] = []
        self.answer = "Full-time employees get 24 days of paid annual leave per year [1]."
        self.rewrite = "How many annual leave days do part-time employees get?"

    def complete(self, messages, max_tokens=600, temperature=0.1):
        self.calls.append(messages)
        if messages[0]["content"].startswith("Rewrite the user's latest question"):
            return self.rewrite
        return self.answer

    def stream(self, messages, max_tokens=600, temperature=0.1):
        self.calls.append(messages)
        for word in self.answer.split(" "):
            yield word + " "


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr("app.routers.chat.get_llm", lambda: fake)
    return fake


@pytest.fixture(scope="session")
def eval_env(client):  # depends on client so the app (and settings) are initialised
    from app.config import get_settings
    from app.services.embeddings import get_embedder

    return get_settings(), get_embedder()
