import { useCallback, useEffect, useState } from "react";
import { getLatestEval, runEval } from "../api";

const pct = (v) => (v == null ? null : `${Math.round(v * 100)}%`);
const num = (v) => (v == null ? null : v.toFixed(2));
const ms = (v) => (v == null ? null : `${Math.round(v)} ms`);

function metricRows(m, k) {
  return [
    ["Right page ranked first", pct(m.hit_rate_at_1), "Hit rate at 1"],
    ["Right page in the top 3", pct(m.hit_rate_at_3), "Hit rate at 3"],
    [`Right page in the top ${k}`, pct(m.hit_rate_at_k), `Hit rate at ${k}`],
    ["Ranking quality", num(m.mrr), "Mean reciprocal rank, 1.00 is perfect"],
    ["Out-of-scope questions refused", pct(m.correct_refusal_rate), "Higher is better"],
    ["In-scope questions wrongly refused", pct(m.false_refusal_rate), "Lower is better"],
    ["Answer correctness", m.judge_correctness == null ? null : `${num(m.judge_correctness)} / 5`, "Scored by an AI judge"],
    ["Answer faithfulness", m.judge_faithfulness == null ? null : `${num(m.judge_faithfulness)} / 5`, "Are all claims supported by the sources"],
    ["Average time per question", ms(m.avg_latency_ms), ""],
  ];
}

export default function EvalPage({ ready }) {
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [skipAi, setSkipAi] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setRun((await getLatestEval()).run);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  async function start() {
    setRunning(true);
    setError("");
    try {
      setRun(await runEval(!skipAi));
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4 py-8">
      <div className="space-y-2">
        <h2 className="font-serif text-2xl font-bold">How well does it work?</h2>
        <p className="max-w-prose text-muted">
          This runs a fixed set of questions against the sample documents and checks whether the right page is found,
          whether out-of-scope questions are refused, and (with an API key) whether the answers are correct.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <button onClick={start} disabled={!ready || running}
          className="rounded-md bg-brand px-4 py-2 font-medium text-white hover:bg-brand-dark disabled:opacity-50">
          {running ? "Running..." : "Run evaluation"}
        </button>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={skipAi} onChange={(e) => setSkipAi(e.target.checked)} />
          Skip AI scoring (no API calls)
        </label>
        {running && <span className="text-sm text-muted">This can take a minute with AI scoring.</span>}
      </div>

      {error && <p role="alert" className="text-alert">{error}</p>}

      {!loading && !run && !error && (
        <p className="rounded-md border border-line bg-surface p-4 text-muted">
          No evaluation has been run yet. Run it to see how retrieval and answers perform on the sample documents.
        </p>
      )}

      {run && (
        <>
          <p className="text-sm text-muted">
            {run.metrics.n_answerable} answerable and {run.metrics.n_unanswerable} unanswerable questions, chunks of{" "}
            {run.settings.chunk_words} words, top {run.settings.top_k}, threshold {run.settings.threshold},
            embedder {run.settings.embedder}.
          </p>
          {run.notes.map((n) => (
            <p key={n} className="rounded-md bg-mark/60 p-3 text-sm">{n}</p>
          ))}
          <div className="overflow-x-auto rounded-md border border-line bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line">
                <tr><th className="p-3 font-semibold">Measure</th><th className="p-3 font-semibold">Result</th><th className="p-3 font-semibold">What it means</th></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {metricRows(run.metrics, run.settings.top_k).map(([label, value, hint]) => (
                  <tr key={label}>
                    <td className="p-3">{label}</td>
                    <td className="p-3 font-semibold">{value ?? <span className="font-normal text-muted">Not measured</span>}</td>
                    <td className="p-3 text-muted">{hint}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <details className="rounded-md border border-line bg-surface">
            <summary className="cursor-pointer p-3 text-sm font-medium">Show all {run.rows.length} questions</summary>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-y border-line">
                  <tr><th className="p-3">Question</th><th className="p-3">Right page rank</th><th className="p-3">Match</th><th className="p-3">Refused</th></tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {run.rows.map((r) => (
                    <tr key={r.question}>
                      <td className="p-3">{r.question}</td>
                      <td className="p-3">{r.answerable ? (r.rank ?? "Missed") : "Not applicable"}</td>
                      <td className="p-3">{r.best_score.toFixed(2)}</td>
                      <td className="p-3">{r.refused ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
