import { useCallback, useEffect, useState } from "react";
import { getHealth, listDocuments } from "./api";
import Sidebar from "./components/Sidebar.jsx";
import Chat from "./components/Chat.jsx";
import EvalPage from "./components/EvalPage.jsx";

/** Poll /api/health so we can show a friendly message while a sleeping free server wakes up. */
function useServerStatus() {
  const [state, setState] = useState("checking"); // checking | waking | ready | down
  useEffect(() => {
    let stopped = false;
    let timer;
    let failures = 0;
    const slow = setTimeout(() => !stopped && setState((s) => (s === "checking" ? "waking" : s)), 2500);

    async function poll() {
      try {
        const ctrl = new AbortController();
        const abort = setTimeout(() => ctrl.abort(), 8000);
        const health = await getHealth(ctrl.signal);
        clearTimeout(abort);
        if (stopped) return;
        if (health.ready) return setState("ready");
        setState(health.status === "error" ? "down" : "waking");
      } catch {
        failures += 1;
        if (!stopped) setState(failures >= 12 ? "down" : "waking");
      }
      if (!stopped) timer = setTimeout(poll, 3000);
    }
    poll();
    return () => {
      stopped = true;
      clearTimeout(slow);
      clearTimeout(timer);
    };
  }, []);
  return state;
}

const BANNERS = {
  waking: "Waking up the server. Free hosting pauses when idle, so the first load can take up to a minute.",
  down: "The server isn't responding. Check that the backend is running and that VITE_API_URL points to it.",
};

export default function App() {
  const [tab, setTab] = useState("ask");
  const [docs, setDocs] = useState([]);
  const [showDocs, setShowDocs] = useState(false);
  const server = useServerStatus();
  const ready = server === "ready";

  const refreshDocs = useCallback(async () => {
    try {
      setDocs(await listDocuments());
    } catch {
      /* the banner already explains connection problems */
    }
  }, []);

  useEffect(() => {
    if (ready) refreshDocs();
  }, [ready, refreshDocs]);

  const tabClass = (name) =>
    `px-3 py-1.5 text-sm rounded-md ${tab === name ? "bg-brand text-white" : "text-ink hover:bg-paper"}`;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-4 border-b border-line bg-surface px-4 py-2.5">
        <h1 className="font-serif text-xl font-bold tracking-tight">DocuMind</h1>
        <nav className="flex gap-1" aria-label="Sections">
          <button className={tabClass("ask")} onClick={() => setTab("ask")}>Ask</button>
          <button className={tabClass("eval")} onClick={() => setTab("eval")}>Evaluation</button>
        </nav>
        {tab === "ask" && (
          <button
            className="ml-auto rounded-md border border-line px-3 py-1.5 text-sm md:hidden"
            onClick={() => setShowDocs((v) => !v)}
            aria-expanded={showDocs}
          >
            Documents ({docs.length})
          </button>
        )}
      </header>

      {BANNERS[server] && (
        <div role="status" className={`px-4 py-2 text-sm ${server === "down" ? "bg-alert text-white" : "bg-mark text-ink"}`}>
          {BANNERS[server]}
        </div>
      )}

      {tab === "ask" ? (
        <div className="flex min-h-0 flex-1">
          <div className={`${showDocs ? "flex" : "hidden"} w-full flex-col md:flex md:w-80 md:shrink-0`}>
            <Sidebar docs={docs} ready={ready} onChanged={refreshDocs} />
          </div>
          <main className={`${showDocs ? "hidden" : "flex"} min-w-0 flex-1 md:flex`}>
            <Chat ready={ready} docCount={docs.length} />
          </main>
        </div>
      ) : (
        <main className="min-h-0 flex-1 overflow-y-auto">
          <EvalPage ready={ready} />
        </main>
      )}
    </div>
  );
}
