from app.services.evaluator import build_eval_store, run_evaluation
from app.services.retriever import retrieve


def test_known_question_returns_the_right_chunk(eval_env):
    settings, embedder = eval_env
    store = build_eval_store(settings, embedder, 500, 80)
    r = retrieve("How many days of paid annual leave do full-time employees get?", store, embedder, 5,
                 settings.threshold_for(embedder.name))
    top = r.hits[0].chunk
    assert top.filename == "northwind_employee_handbook.pdf"
    assert top.page == 2
    assert "24 days" in top.text
    assert r.passed


def test_out_of_scope_question_is_refused_by_threshold(eval_env):
    settings, embedder = eval_env
    store = build_eval_store(settings, embedder, 500, 80)
    r = retrieve("What is the airspeed velocity of an unladen swallow?", store, embedder, 5,
                 settings.threshold_for(embedder.name))
    assert not r.passed
    assert r.context == []


def test_evaluation_runs_without_llm_and_finds_right_pages(eval_env):
    settings, embedder = eval_env

    class NoLLM:
        available = False

    result = run_evaluation(settings, embedder, NoLLM(), use_llm=False)
    m = result["metrics"]
    assert m["n_answerable"] >= 20 and m["n_unanswerable"] == 5
    assert m["hit_rate_at_k"] >= 0.9
    assert m["judge_correctness"] is None  # no LLM, so no judge scores
