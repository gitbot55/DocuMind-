import { useRef, useState } from "react";
import { deleteDocument, uploadDocuments } from "../api";

export default function Sidebar({ docs, ready, onChanged }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [problems, setProblems] = useState([]);

  async function upload(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length || busy) return;
    if (files.length > 10) {
      setProblems(["You can upload up to 10 files at a time."]);
      return;
    }
    setBusy(true);
    setProblems([]);
    try {
      const results = await uploadDocuments(files);
      setProblems(results.filter((r) => !r.ok).map((r) => `${r.filename}: ${r.error}`));
      await onChanged();
    } catch (err) {
      setProblems([err.message || "Upload failed. Please try again."]);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function remove(doc) {
    if (!window.confirm(`Remove ${doc.filename}? Its pages will no longer be searched.`)) return;
    try {
      await deleteDocument(doc.id);
      await onChanged();
    } catch (err) {
      setProblems([err.message]);
    }
  }

  return (
    <aside className="flex min-h-0 flex-1 flex-col gap-4 border-r border-line bg-surface p-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); upload(e.dataTransfer.files); }}
        className={`rounded-md border-2 border-dashed p-4 text-center text-sm ${dragging ? "border-brand bg-paper" : "border-line"}`}
      >
        <p className="mb-3 text-muted">Drop PDFs here, up to 10 files of 10 MB each.</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          hidden
          onChange={(e) => upload(e.target.files)}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={!ready || busy}
          className="rounded-md bg-brand px-4 py-2 font-medium text-white hover:bg-brand-dark disabled:opacity-50"
        >
          {busy ? "Reading your files..." : "Upload PDFs"}
        </button>
      </div>

      {problems.length > 0 && (
        <ul role="alert" className="space-y-1 rounded-md border border-alert p-3 text-sm text-alert">
          {problems.map((p, i) => <li key={i}>{p}</li>)}
        </ul>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        <h2 className="mb-2 text-sm font-semibold">Your documents ({docs.length})</h2>
        {docs.length === 0 ? (
          <p className="text-sm text-muted">No documents yet. Upload a PDF to start asking questions.</p>
        ) : (
          <ul className="divide-y divide-line">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center gap-2 py-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium" title={d.filename}>{d.filename}</p>
                  <p className="text-xs text-muted">{d.pages} {d.pages === 1 ? "page" : "pages"}, {d.chunk_count} passages</p>
                </div>
                <button
                  onClick={() => remove(d)}
                  className="rounded-md px-2 py-1 text-xs text-alert hover:bg-paper"
                  aria-label={`Remove ${d.filename}`}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
