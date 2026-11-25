"""Text embedding backends.

- FastEmbedder: BAAI/bge-small-en-v1.5 via fastembed (CPU, light). Default.
- HashingEmbedder: offline feature-hashing fallback. Lower quality, but needs no model
  download, so tests and first boot never fail.
"""
import logging
import math
import re
import zlib
from functools import lru_cache

import numpy as np

from ..config import get_settings

log = logging.getLogger(__name__)

_STOPWORDS = set(
    "a an and are as at be but by for from has have how i in is it its of on or that the "
    "their there these they this to was we what when where which who will with you your do does "
    "can many much per".split()
)


def _normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vecs / norms).astype("float32")


class HashingEmbedder:
    name = "hashing"
    dim = 1024

    @staticmethod
    def _tokens(text: str) -> list[str]:
        toks = re.findall(r"[a-z0-9]+", text.lower())
        toks = [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in toks]
        return [t for t in toks if t not in _STOPWORDS]

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype="float32")
        for row, text in enumerate(texts):
            toks = self._tokens(text)
            feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
            counts: dict[str, int] = {}
            for f in feats:
                counts[f] = counts.get(f, 0) + 1
            for f, c in counts.items():
                h = zlib.crc32(f.encode())
                sign = 1.0 if (h >> 31) & 1 else -1.0
                out[row, h % self.dim] += sign * (1.0 + math.log(c))
        return _normalize(out)

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        return self.encode(texts)


class FastEmbedder:
    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)
        self.name = f"fastembed:{model_name}"
        self.dim = len(next(iter(self._model.embed(["dimension probe"]))))

    def encode(self, texts: list[str]) -> np.ndarray:
        vecs = np.array(list(self._model.embed(texts, batch_size=32)), dtype="float32")
        return _normalize(vecs)

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        vecs = np.array(list(self._model.query_embed(texts)), dtype="float32")
        return _normalize(vecs)


@lru_cache
def get_embedder():
    """Return the configured embedder (cached), falling back to hashing if the model cannot load."""
    settings = get_settings()
    if settings.embedding_backend == "fastembed":
        try:
            return FastEmbedder(settings.embedding_model)
        except Exception as exc:  # network blocked, model missing, low memory...
            log.error(
                "Could not load fastembed model %s (%s). Falling back to the hashing embedder; "
                "retrieval quality will be lower.",
                settings.embedding_model,
                exc,
            )
    return HashingEmbedder()
