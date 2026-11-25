"""Top-k retrieval with a similarity threshold (the first hallucination guard)."""
from dataclasses import dataclass

from .vector_store import Hit, VectorStore


@dataclass
class Retrieval:
    hits: list[Hit]  # top-k by score (used for evaluation ranking)
    context: list[Hit]  # hits at or above the threshold (sent to the LLM)
    best_score: float

    @property
    def passed(self) -> bool:
        return bool(self.context)


def retrieve(question: str, store: VectorStore, embedder, top_k: int, threshold: float) -> Retrieval:
    qvec = embedder.encode_queries([question])[0]
    hits = store.search(qvec, top_k)
    best = hits[0].score if hits else 0.0
    context = [h for h in hits if h.score >= threshold]
    return Retrieval(hits=hits, context=context, best_score=best)
