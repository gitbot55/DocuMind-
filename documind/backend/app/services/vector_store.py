"""FAISS vector store (cosine similarity via normalized vectors + inner product).

FAISS ids are the chunk ids from the database. Chunk text and metadata are kept in memory so
a search returns everything needed for citations without extra queries.
"""
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class ChunkRecord:
    id: int
    doc_id: int
    filename: str
    page: int
    text: str


@dataclass
class Hit:
    chunk: ChunkRecord
    score: float


class VectorStore:
    def __init__(self, dim: int, path: Path | None = None, embedder_name: str = ""):
        self.dim = dim
        self.path = path
        self.embedder_name = embedder_name
        self.lock = threading.RLock()  # also used by callers to serialise writes
        self._index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
        self._meta: dict[int, ChunkRecord] = {}

    @property
    def count(self) -> int:
        return int(self._index.ntotal)

    def add(self, records: list[ChunkRecord], vectors: np.ndarray) -> None:
        if not records:
            return
        ids = np.array([r.id for r in records], dtype="int64")
        with self.lock:
            self._index.add_with_ids(vectors.astype("float32"), ids)
            for r in records:
                self._meta[r.id] = r

    def remove_doc(self, doc_id: int) -> int:
        with self.lock:
            ids = [i for i, r in self._meta.items() if r.doc_id == doc_id]
            if ids:
                self._index.remove_ids(np.array(ids, dtype="int64"))
                for i in ids:
                    del self._meta[i]
            return len(ids)

    def search(self, query_vec: np.ndarray, k: int) -> list[Hit]:
        with self.lock:
            if self.count == 0:
                return []
            q = query_vec.reshape(1, -1).astype("float32")
            scores, ids = self._index.search(q, min(k, self.count))
            return [
                Hit(self._meta[int(i)], float(s))
                for s, i in zip(scores[0], ids[0])
                if int(i) != -1 and int(i) in self._meta
            ]

    # ---- persistence -------------------------------------------------------
    def save(self) -> None:
        if not self.path:
            return
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, str(self.path))
            self.path.with_suffix(".json").write_text(
                json.dumps({"embedder": self.embedder_name, "dim": self.dim})
            )

    @classmethod
    def load(cls, dim: int, path: Path, embedder_name: str, records: list[ChunkRecord]) -> "VectorStore | None":
        """Load a saved index if it matches the embedder and the database; otherwise None."""
        meta_file = path.with_suffix(".json")
        if not (path.exists() and meta_file.exists()):
            return None
        try:
            meta = json.loads(meta_file.read_text())
            index = faiss.read_index(str(path))
        except Exception as exc:
            log.warning("Could not read saved index (%s); it will be rebuilt.", exc)
            return None
        if meta.get("embedder") != embedder_name or index.d != dim or index.ntotal != len(records):
            log.info("Saved index does not match the database or embedder; it will be rebuilt.")
            return None
        store = cls(dim, path, embedder_name)
        store._index = index
        store._meta = {r.id: r for r in records}
        return store
