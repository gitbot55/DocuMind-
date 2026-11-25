const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function readError(res) {
  let detail = `Something went wrong (error ${res.status}).`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    /* keep the default message */
  }
  return detail;
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, options);
  if (!res.ok) {
    const err = new Error(await readError(res));
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const getHealth = (signal) => request("/api/health", { signal });
export const listDocuments = () => request("/api/documents");
export const deleteDocument = (id) => request(`/api/documents/${id}`, { method: "DELETE" });
export const newSession = () => request("/api/chat/new", { method: "POST" });
export const getLatestEval = () => request("/api/eval/latest");

export function uploadDocuments(files) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  return request("/api/documents/upload", { method: "POST", body: form });
}

export function runEval(useLlm) {
  return request("/api/eval/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ use_llm: useLlm }),
  });
}

/** Ask a question and stream the answer (Server-Sent Events over fetch). */
export async function streamChat(sessionId, question, { onMeta, onToken, onDone, onError }) {
  let res;
  try {
    res = await fetch(`${BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question }),
    });
  } catch {
    onError("Can't reach the server. Check your connection and try again.");
    return;
  }
  if (!res.ok) {
    onError(await readError(res));
    return;
  }

  let finished = false;
  const handle = (block) => {
    let event = "message";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7).trim();
      else if (line.startsWith("data: ")) data += line.slice(6);
    }
    if (!data) return;
    const payload = JSON.parse(data);
    if (event === "meta") onMeta(payload);
    else if (event === "token") onToken(payload.text);
    else if (event === "done") {
      finished = true;
      onDone(payload);
    } else if (event === "error") {
      finished = true;
      onError(payload.message);
    }
  };

  try {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        handle(buffer.slice(0, idx));
        buffer = buffer.slice(idx + 2);
      }
    }
  } catch {
    /* handled below */
  }
  if (!finished) onError("The answer was cut off. Please ask again.");
}
