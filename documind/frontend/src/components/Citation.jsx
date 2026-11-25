/** One source passage: file, page, and a snippet that expands to the full text. */
export default function Citation({ c, open, onToggle }) {
  return (
    <div id={`cite-${c.number}`} className="overflow-hidden rounded-md border border-line bg-surface">
      <button onClick={onToggle} aria-expanded={open} className="flex w-full items-start gap-3 p-3 text-left hover:bg-paper">
        <span className="mt-0.5 shrink-0 rounded bg-brand px-1.5 py-0.5 text-xs font-semibold text-white">{c.number}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{c.filename}, page {c.page}</span>
          {!open && <span className="mt-1 block text-sm text-muted">{c.snippet}</span>}
        </span>
        <span className="shrink-0 text-xs text-muted">{open ? "Hide" : "Show full passage"}</span>
      </button>
      {open && (
        <div className="border-t border-line px-3 pb-3 pt-2">
          <p className="rounded bg-mark/60 p-2 font-serif text-[15px] leading-relaxed">{c.text}</p>
          <p className="mt-2 text-xs text-muted">Match strength {c.score.toFixed(2)}</p>
        </div>
      )}
    </div>
  );
}
