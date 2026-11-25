"""Application settings, loaded from environment variables (and .env)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    allowed_origins: str = "http://localhost:5173"

    top_k: int = 5
    score_threshold: float | None = None  # None = pick a default that suits the embedder
    chunk_words: int = 500
    chunk_overlap: int = 80

    max_upload_mb: int = 10
    max_files_per_upload: int = 10
    rate_limit_per_minute: int = 20
    history_messages: int = 6
    sync_startup: bool = False  # tests set this so the app is ready right after startup

    embedding_backend: str = "fastembed"  # "fastembed" | "hashing"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    data_dir: str = str(BACKEND_DIR / "data")
    sample_docs_dir: str = str(BACKEND_DIR / "sample_docs")

    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    def threshold_for(self, embedder_name: str) -> float:
        """Similarity threshold below which a question is refused without calling the LLM.

        Scores from the offline hashing embedder are much lower than bge-small scores, so each
        gets its own default. Set SCORE_THRESHOLD to override. Tune it with `eval/run_eval.py --sweep`.
        """
        if self.score_threshold is not None:
            return self.score_threshold
        return 0.15 if embedder_name == "hashing" else 0.45

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def uploads_dir(self) -> Path:
        return Path(self.data_dir) / "uploads"

    @property
    def index_dir(self) -> Path:
        return Path(self.data_dir) / "index"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{Path(self.data_dir) / 'app.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
