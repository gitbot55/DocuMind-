import io
import json

from pypdf import PdfWriter

from app.services.generator import REFUSAL

LEAVE_Q = "How many days of paid annual leave do full-time employees get?"


def _new_session(client) -> str:
    return client.post("/api/chat/new").json()["session_id"]


def _make_pdf(text: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in text.split("\n"):
        c.drawString(50, y, line)
        y -= 18
    c.save()
    return buf.getvalue()


def test_health_reports_ready_and_seeded_documents(client):
    body = client.get("/api/health").json()
    assert body["ready"] is True and body["status"] == "ok"
    assert body["documents"] == 2 and body["embedder"] == "hashing"


def test_upload_rejects_non_pdf_fake_pdf_and_scanned_pdf(client):
    blank = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(blank)
    files = [
        ("files", ("notes.txt", b"hello", "text/plain")),
        ("files", ("fake.pdf", b"this is not a pdf at all", "application/pdf")),
        ("files", ("scan.pdf", blank.getvalue(), "application/pdf")),
    ]
    results = client.post("/api/documents/upload", files=files).json()
    assert [r["ok"] for r in results] == [False, False, False]
    assert "Only PDF" in results[0]["error"]
    assert "not a PDF" in results[1]["error"]
    assert "No readable text" in results[2]["error"]
    assert len(client.get("/api/documents").json()) == 2


def test_upload_rejects_oversized_file(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    pdf = _make_pdf("A small but valid policy document with several words in it.")
    r = client.post("/api/documents/upload", files=[("files", ("big.pdf", pdf, "application/pdf"))]).json()
    assert r[0]["ok"] is False and "larger than" in r[0]["error"]


def test_upload_then_answerable_then_delete(client):
    from app.services.runtime import get_runtime

    text = "Zebra care policy\n1.1 Feeding. Zebras at the sanctuary are fed twice daily, at 6am and 6pm, by trained staff only."
    up = client.post("/api/documents/upload", files=[("files", ("zebra.pdf", _make_pdf(text), "application/pdf"))]).json()
    assert up[0]["ok"] is True
    doc_id = up[0]["document"]["id"]
    store = get_runtime().store
    assert len(client.get("/api/documents").json()) == 3
    before = store.count

    # the new document is searchable
    from app.services.retriever import retrieve

    rt = get_runtime()
    hits = retrieve("How often are zebras fed?", rt.store, rt.embedder, 3, 0.0).hits
    assert hits[0].chunk.filename == "zebra.pdf"

    assert client.delete(f"/api/documents/{doc_id}").status_code == 200
    assert len(client.get("/api/documents").json()) == 2
    assert store.count < before
    assert client.delete(f"/api/documents/{doc_id}").status_code == 404


def test_chat_returns_grounded_answer_with_citations(client, fake_llm):
    sid = _new_session(client)
    body = client.post("/api/chat", json={"session_id": sid, "question": LEAVE_Q}).json()
    assert body["grounded"] is True
    assert "[1]" in body["answer"]
    cit = body["citations"][0]
    assert cit["filename"] == "northwind_employee_handbook.pdf" and cit["page"] == 2
    assert "24 days" in cit["text"]
    assert len(fake_llm.calls) == 1  # one generation call, no rewrite on the first turn


def test_out_of_scope_question_is_refused_without_calling_the_llm(client, fake_llm):
    sid = _new_session(client)
    body = client.post("/api/chat", json={"session_id": sid, "question": "What is the airspeed velocity of an unladen swallow?"}).json()
    assert body["grounded"] is False
    assert body["answer"] == REFUSAL
    assert body["citations"] == []
    assert fake_llm.calls == []


def test_llm_refusal_has_no_citations(client, fake_llm):
    fake_llm.answer = REFUSAL
    sid = _new_session(client)
    body = client.post("/api/chat", json={"session_id": sid, "question": LEAVE_Q}).json()
    assert body["grounded"] is False and body["citations"] == []


def test_follow_up_is_rewritten_and_history_is_saved(client, fake_llm):
    sid = _new_session(client)
    client.post("/api/chat", json={"session_id": sid, "question": LEAVE_Q})
    second = client.post("/api/chat", json={"session_id": sid, "question": "What about part-time staff?"}).json()
    assert second["rewritten_question"] == fake_llm.rewrite
    assert any(c[0]["content"].startswith("Rewrite") for c in fake_llm.calls)
    msgs = client.get(f"/api/chat/{sid}").json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]


def test_streaming_sends_meta_tokens_and_done(client, fake_llm):
    sid = _new_session(client)
    with client.stream("POST", "/api/chat/stream", json={"session_id": sid, "question": LEAVE_Q}) as r:
        raw = "".join(r.iter_text())
    events = [blk.split("\n")[0].removeprefix("event: ") for blk in raw.strip().split("\n\n")]
    assert events[0] == "meta" and events[-1] == "done" and "token" in events
    done = json.loads(raw.strip().split("\n\n")[-1].split("data: ", 1)[1])
    assert done["grounded"] is True and done["citations"][0]["page"] == 2


def test_unknown_session_returns_404(client, fake_llm):
    r = client.post("/api/chat", json={"session_id": "does-not-exist", "question": LEAVE_Q})
    assert r.status_code == 404
    assert client.get("/api/chat/does-not-exist").status_code == 404


def test_missing_api_key_gives_clear_503(client):
    sid = _new_session(client)  # real get_llm(), no key configured
    r = client.post("/api/chat", json={"session_id": sid, "question": LEAVE_Q})
    assert r.status_code == 503 and "GROQ_API_KEY" in r.json()["detail"]


def test_rate_limit_returns_429(client, fake_llm, monkeypatch):
    from app.config import get_settings
    from app.utils import ratelimit

    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 2)
    ratelimit._hits.clear()
    sid = _new_session(client)
    codes = [client.post("/api/chat", json={"session_id": sid, "question": LEAVE_Q}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    ratelimit._hits.clear()


def test_eval_endpoint_runs_without_llm(client):
    r = client.post("/api/eval/run", json={"use_llm": False})
    assert r.status_code == 200 and r.json()["metrics"]["hit_rate_at_k"] >= 0.9
    latest = client.get("/api/eval/latest").json()
    assert latest["run"]["settings"]["llm_used"] is False
