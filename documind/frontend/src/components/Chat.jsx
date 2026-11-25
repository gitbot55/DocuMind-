import { useEffect, useRef, useState } from "react";
import { newSession, streamChat } from "../api";
import Citation from "./Citation.jsx";

const EXAMPLES = [
  "How many days of annual leave do full-time employees get?",
  "How quickly must suspected phishing be reported?",
  "What is the daily meal allowance when travelling?",
];

/** Turn "[1]" markers in an answer into buttons that open the matching source. */
function AnswerText({ text, citations, onCite }) {
  const known = new Set(citations.map((c) => c.number));
  return text.split(/(\[\d+\])/).map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (m && known.has(Number(m[1]))) {
      return (
        <button
          key={i}
          onClick={() => onCite(Number(m[1]))}
          className="mx-0.5 rounded bg-mark px-1 font-sans text-xs font-semibold hover:bg-mark/70"
          aria-label={`Open source ${m[1]}`}
        >
          {m[1]}
        </button>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function Assistant({ m, onToggle }) {
  if (m.error) return <p role="alert" className="text-alert">{m.error}</p>;
  const refused = !m.streaming && m.grounded === false;
  return (
    <div className="space-y-3">
      {m.rewritten && <p className="text-xs text-muted">Searched for: {m.rewritten}</p>}
      <div className={`font-serif text-[17px] leading-relaxed ${refused ? "border-l-4 border-alert pl-3" : ""} ${m.streaming ? "caret" : ""}`}>
        {refused && <p className="mb-1 font-sans text-sm font-semibold text-alert">Not found in your documents</p>}
        <AnswerText text={m.text} citations={m.citations} onCite={(n) => onToggle(n, true)} />
      </div>
      {m.citations.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-semibold">Sources</p>
          {m.citations.map((c) => (
            <Citation key={c.number} c={c} open={m.open === c.number} onToggle={() => onToggle(c.number)} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Chat({ ready, docCount }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (ready && !sessionId) newSession().then((r) => setSessionId(r.session_id)).catch(() => {});
  }, [ready, sessionId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const patchLast = (fn) => setMessages((ms) => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)));

  async function send(text) {
    const question = text.trim();
    if (!question || busy || !sessionId) return;
    setInput("");
    setBusy(true);
    setMessages((ms) => [...ms, { role: "user", text: question }, { role: "assistant", text: "", citations: [], streaming: true }]);
    await streamChat(sessionId, question, {
      onMeta: (meta) => patchLast((a) => ({ ...a, rewritten: meta.rewritten_question })),
      onToken: (t) => patchLast((a) => ({ ...a, text: a.text + t })),
      onDone: (d) =>
        patchLast((a) => ({ ...a, text: d.answer, citations: d.citations, grounded: d.grounded, rewritten: d.rewritten_question, streaming: false })),
      onError: (msg) => {
        if (msg.startsWith("Chat session not found")) {
          newSession().then((r) => setSessionId(r.session_id)).catch(() => {});
          msg = "The server restarted, so this chat was reset. Ask your question again.";
        }
        patchLast((a) => ({ ...a, streaming: false, error: msg }));
      },
    });
    setBusy(false);
  }

  async function startNewChat() {
    setMessages([]);
    try {
      setSessionId((await newSession()).session_id);
    } catch {
      setSessionId(null);
    }
  }

  const toggleCite = (index) => (n, forceOpen) =>
    setMessages((ms) => ms.map((m, i) => (i === index ? { ...m, open: forceOpen || m.open !== n ? n : null } : m)));

  return (
    <section className="flex min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && (
            <div className="space-y-4 pt-6">
              <h2 className="font-serif text-2xl font-bold">Ask your documents</h2>
              <p className="max-w-prose text-muted">
                {docCount === 0
                  ? "Upload a PDF on the left, then ask a question. Every answer shows the file and page it came from."
                  : "Ask a question about your uploaded PDFs. Every answer shows the file and page it came from, and if the answer isn't in the documents, you'll be told."}
              </p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((q) => (
                  <button key={q} onClick={() => send(q)} disabled={!ready || !sessionId}
                    className="rounded-md border border-line bg-surface px-3 py-2 text-left text-sm hover:border-brand disabled:opacity-50">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <p className="max-w-[85%] rounded-md bg-brand px-3 py-2 text-white">{m.text}</p>
              </div>
            ) : (
              <Assistant key={i} m={m} onToggle={toggleCite(i)} />
            )
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-line bg-surface p-3">
        <form
          className="mx-auto flex max-w-3xl items-end gap-2"
          onSubmit={(e) => { e.preventDefault(); send(input); }}
        >
          <label htmlFor="question" className="sr-only">Your question</label>
          <textarea
            id="question"
            value={input}
            rows={1}
            maxLength={2000}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
            placeholder={ready ? "Type your question" : "Waiting for the server..."}
            className="max-h-40 min-h-[42px] flex-1 resize-y rounded-md border border-line bg-paper px-3 py-2"
          />
          <button type="submit" disabled={!ready || busy || !input.trim() || !sessionId}
            className="rounded-md bg-brand px-4 py-2 font-medium text-white hover:bg-brand-dark disabled:opacity-50">
            Ask
          </button>
          <button type="button" onClick={startNewChat} disabled={busy || messages.length === 0}
            className="rounded-md border border-line px-3 py-2 text-sm hover:bg-paper disabled:opacity-50">
            New chat
          </button>
        </form>
      </div>
    </section>
  );
}
