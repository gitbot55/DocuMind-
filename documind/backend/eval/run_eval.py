"""Run the DocuMind evaluation from the command line (run from backend/).

    python eval/run_eval.py                  # settings from .env; uses Groq if GROQ_API_KEY is set
    python eval/run_eval.py --no-llm         # retrieval + threshold refusal only (no API calls)
    python eval/run_eval.py --sweep          # compare chunk sizes and thresholds (retrieval only)
    python eval/run_eval.py --chunk-words 200 --top-k 3 --threshold 0.5

Results are saved to eval/results/ (latest.json, latest.md, sweep.md).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.services.embeddings import get_embedder  # noqa: E402
from app.services.evaluator import run_evaluation, to_markdown  # noqa: E402
from app.services.generator import get_llm  # noqa: E402

RESULTS = ROOT / "eval" / "results"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chunk-words", type=int)
    ap.add_argument("--top-k", type=int)
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--no-llm", action="store_true", help="skip all LLM calls")
    ap.add_argument("--sweep", action="store_true", help="compare settings, retrieval only")
    ap.add_argument("--thresholds", default="0.35,0.45,0.55", help="comma list used by --sweep")
    args = ap.parse_args()

    settings, embedder, llm = get_settings(), get_embedder(), get_llm()
    RESULTS.mkdir(parents=True, exist_ok=True)

    if args.sweep:
        rows = ["| chunk_words | top_k | threshold | hit@1 | hit@3 | MRR | correct refusals | false refusals |", "|---|---|---|---|---|---|---|---|"]
        for cw in (100, 200, 500):
            for th in [float(t) for t in args.thresholds.split(",")]:
                m = run_evaluation(settings, embedder, llm, cw, args.top_k, th, use_llm=False)["metrics"]
                f = lambda v: "n/a" if v is None else f"{v:.2f}"  # noqa: E731
                rows.append(f"| {cw} | {args.top_k or settings.top_k} | {th} | {f(m['hit_rate_at_1'])} | {f(m['hit_rate_at_3'])} | {f(m['mrr'])} | {f(m['correct_refusal_rate'])} | {f(m['false_refusal_rate'])} |")
        text = f"Embedder: {embedder.name}\n\n" + "\n".join(rows) + "\n"
        (RESULTS / "sweep.md").write_text(text)
        print(text)
        return

    result = run_evaluation(settings, embedder, llm, args.chunk_words, args.top_k, args.threshold, use_llm=not args.no_llm)
    (RESULTS / "latest.json").write_text(json.dumps(result, indent=2))
    (RESULTS / "latest.md").write_text(to_markdown(result))
    print(to_markdown(result))
    misses = [r["question"] for r in result["rows"] if r["answerable"] and r["rank"] != 1]
    if misses:
        print("Answerable questions where the right page was not ranked first:")
        for q in misses:
            print(" -", q)


if __name__ == "__main__":
    main()
