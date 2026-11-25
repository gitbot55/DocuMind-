"""Evaluation of retrieval and answer quality on the bundled sample documents.

The evaluator builds its own in-memory index from `sample_docs/` so results do not depend on
what a user has uploaded, and so different chunk sizes can be compared without touching the app.

Metrics:
- Hit Rate@1/@3/@k and MRR: is the expected (file, page) among the retrieved chunks, and how high.
- Refusal accuracy: unanswerable questions that were correctly refused, and answerable ones
  that were wrongly refused (retrieval threshold, plus the LLM's own refusal when enabled).
- LLM-as-judge (needs GROQ_API_KEY): correctness and faithfulness, 1 to 5.
- Average latency per question.
"""
import json
import logging
import re
import time
from pathlib import Path

from ..config import Settings
from ..utils.errors import LLMUnavailable
from .chunking import chunk_pages
from .generator import LLM, REFUSAL, build_messages, finalize
from .ingestion import extract_pages
from .retriever import retrieve
from .vector_store import ChunkRecord, VectorStore

log = logging.getLogger(__name__)

TEST_SET_PATH = Path(__file__).resolve().parents[2] / "eval" / "test_set.json"

JUDGE_PROMPT = """You grade an answer from a document question-answering system.
Return ONLY a JSON object: {"correctness": <1-5>, "faithfulness": <1-5>}.
- correctness: does the answer state the same facts as the expected answer? (5 = same, 1 = wrong or missing)
- faithfulness: is every claim in the answer supported by the context? (5 = fully supported, 1 = invented)"""


def load_test_set(path: Path = TEST_SET_PATH) -> list[dict]:
    return json.loads(Path(path).read_text())


def build_eval_store(settings: Settings, embedder, chunk_words: int, overlap: int) -> VectorStore:
    store = VectorStore(embedder.dim, None, embedder.name)
    next_id = 1
    for doc_id, pdf in enumerate(sorted(Path(settings.sample_docs_dir).glob("*.pdf")), 1):
        pieces = chunk_pages(extract_pages(pdf.read_bytes()), chunk_words, overlap)
        records = [
            ChunkRecord(next_id + i, doc_id, pdf.name, p.page, p.text) for i, p in enumerate(pieces)
        ]
        next_id += len(records)
        store.add(records, embedder.encode([p.text for p in pieces]))
    return store


def _rank_of_expected(hits, item: dict) -> int | None:
    for rank, h in enumerate(hits, 1):
        if h.chunk.filename == item["expected_doc"] and h.chunk.page == item["expected_page"]:
            return rank
    return None


def _judge(llm: LLM, item: dict, context_text: str, answer: str) -> tuple[int, int] | None:
    try:
        out = llm.complete(
            [
                {"role": "system", "content": JUDGE_PROMPT},
                {
                    "role": "user",
                    "content": f"Question: {item['question']}\nExpected answer: {item['expected_answer']}\n"
                    f"Context:\n{context_text}\n\nAnswer to grade: {answer}",
                },
            ],
            max_tokens=60,
            temperature=0.0,
        )
        data = json.loads(re.search(r"\{.*?\}", out, re.S).group(0))
        clamp = lambda v: max(1, min(5, int(v)))  # noqa: E731
        return clamp(data["correctness"]), clamp(data["faithfulness"])
    except (LLMUnavailable, AttributeError, KeyError, ValueError, TypeError):
        return None


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def run_evaluation(
    settings: Settings,
    embedder,
    llm: LLM,
    chunk_words: int | None = None,
    top_k: int | None = None,
    threshold: float | None = None,
    use_llm: bool = True,
    test_set: list[dict] | None = None,
) -> dict:
    chunk_words = chunk_words or settings.chunk_words
    top_k = top_k or settings.top_k
    threshold = settings.threshold_for(embedder.name) if threshold is None else threshold
    overlap = min(settings.chunk_overlap, chunk_words // 2)
    items = test_set if test_set is not None else load_test_set()
    llm_on = bool(use_llm and llm.available)

    store = build_eval_store(settings, embedder, chunk_words, overlap)
    rows, notes = [], []
    if use_llm and not llm.available:
        notes.append("GROQ_API_KEY is not set: answer-quality (judge) scores were skipped. Refusal results use the retrieval threshold only.")

    for item in items:
        t0 = time.perf_counter()
        r = retrieve(item["question"], store, embedder, top_k, threshold)
        row = {
            "question": item["question"],
            "answerable": item["answerable"],
            "best_score": round(r.best_score, 3),
            "rank": _rank_of_expected(r.hits, item) if item["answerable"] else None,
            "refused": not r.passed,
            "answer": None,
            "correctness": None,
            "faithfulness": None,
        }
        if llm_on and r.passed:
            try:
                answer = llm.complete(build_messages(item["question"], r.context, []))
                _, grounded = finalize(answer, r.context)
                row["answer"], row["refused"] = answer, not grounded
            except LLMUnavailable as exc:
                notes.append(f"LLM error on one question: {exc}")
        elif llm_on:
            row["answer"] = REFUSAL
        row["latency_ms"] = int((time.perf_counter() - t0) * 1000)

        if llm_on and item["answerable"] and row["answer"]:
            if row["refused"]:
                row["correctness"] = 1
            else:
                ctx = "\n\n".join(h.chunk.text for h in r.context)
                scores = _judge(llm, item, ctx, row["answer"])
                if scores:
                    row["correctness"], row["faithfulness"] = scores
        rows.append(row)

    ans = [x for x in rows if x["answerable"]]
    unans = [x for x in rows if not x["answerable"]]
    ranks = [x["rank"] for x in ans]
    metrics = {
        "n_answerable": len(ans),
        "n_unanswerable": len(unans),
        "hit_rate_at_1": _avg([1.0 if r_ == 1 else 0.0 for r_ in ranks]),
        "hit_rate_at_3": _avg([1.0 if r_ is not None and r_ <= 3 else 0.0 for r_ in ranks]),
        "hit_rate_at_k": _avg([1.0 if r_ is not None else 0.0 for r_ in ranks]),
        "mrr": _avg([1.0 / r_ if r_ else 0.0 for r_ in ranks]),
        "correct_refusal_rate": _avg([1.0 if x["refused"] else 0.0 for x in unans]),
        "false_refusal_rate": _avg([1.0 if x["refused"] else 0.0 for x in ans]),
        "judge_correctness": _avg([x["correctness"] for x in ans if x["correctness"] is not None]),
        "judge_faithfulness": _avg([x["faithfulness"] for x in ans if x["faithfulness"] is not None]),
        "avg_latency_ms": _avg([x["latency_ms"] for x in rows]),
    }
    return {
        "settings": {
            "chunk_words": chunk_words,
            "chunk_overlap": overlap,
            "top_k": top_k,
            "threshold": threshold,
            "embedder": embedder.name,
            "chunks_indexed": store.count,
            "llm_used": llm_on,
        },
        "metrics": metrics,
        "rows": rows,
        "notes": sorted(set(notes)),
    }


def to_markdown(result: dict) -> str:
    s, m = result["settings"], result["metrics"]
    fmt = lambda v: "n/a" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))  # noqa: E731
    lines = [
        "| Setting | Value |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in s.items()],
        "",
        "| Metric | Value |",
        "|---|---|",
        *[f"| {k} | {fmt(v)} |" for k, v in m.items()],
    ]
    for n in result.get("notes", []):
        lines += ["", f"> {n}"]
    return "\n".join(lines) + "\n"
