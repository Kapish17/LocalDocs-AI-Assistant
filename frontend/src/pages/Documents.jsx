import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  FileType2,
  MessageSquare,
  NotebookText,
  Layers,
  Trash2,
  FileStack,
} from "lucide-react";
import UploadPanel from "../components/upload/UploadPanel";
import EmptyState from "../components/common/EmptyState";
import ErrorBanner from "../components/common/ErrorBanner";
import { LoadingRow } from "../components/common/LoadingState";
import { useDocuments } from "../hooks/useDocuments";

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  return kb < 1024 ? `${kb.toFixed(0)} KB` : `${(kb / 1024).toFixed(1)} MB`;
}

function formatDate(unixSeconds) {
  if (!unixSeconds) return "";
  return new Date(unixSeconds * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function Documents() {
  const navigate = useNavigate();
  const { documents, loading, error, refresh, removeDocument } = useDocuments();
  const [search, setSearch] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  const filtered = documents.filter((d) => d.filename.toLowerCase().includes(search.toLowerCase()));

  async function handleDelete(documentId) {
    setDeletingId(documentId);
    try {
      await removeDocument(documentId);
    } catch (err) {
      alert(err.message || "Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Documents</h1>
          <p className="subtitle">Everything you've uploaded, and what's currently indexed for search.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <UploadPanel onUploaded={refresh} />
      </div>

      <div className="doc-toolbar">
        <div className="doc-search">
          <Search size={15} />
          <input
            placeholder="Search documents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search documents"
          />
        </div>
      </div>

      <ErrorBanner message={error} onRetry={refresh} />
      {loading && <LoadingRow label="Loading documents…" />}

      {!loading && filtered.length === 0 && !error && (
        <EmptyState
          icon={documents.length === 0 ? FileStack : Search}
          title={documents.length === 0 ? "No documents yet" : "No matches"}
          hint={
            documents.length === 0
              ? "Upload a document above to start building your knowledge base."
              : "Try a different search term."
          }
        />
      )}

      <div className="doc-table">
        {filtered.map((d) => (
          <div className="doc-row" key={d.document_id}>
            <div className="doc-row-icon">
              <FileType2 size={18} />
            </div>
            <div className="doc-row-main">
              <div className="doc-row-name" title={d.filename}>
                {d.filename}
              </div>
              <div className="doc-row-meta">
                <span>{d.file_type.toUpperCase()}</span>
                <span>{formatBytes(d.size_bytes)}</span>
                {d.num_pages ? <span>{d.num_pages} pages</span> : null}
                <span>{d.num_chunks} chunks</span>
                {d.uploaded_at ? <span>{formatDate(d.uploaded_at)}</span> : null}
                <span className={`doc-badge ${d.indexed ? "doc-badge--indexed" : "doc-badge--pending"}`}>
                  {d.indexed ? "Indexed" : "Pending"}
                </span>
              </div>
            </div>
            <div className="doc-row-actions">
              <button
                className="icon-btn"
                title="Chat with this document"
                onClick={() => navigate(`/chat?doc=${encodeURIComponent(d.document_id)}`)}
              >
                <MessageSquare size={15} />
              </button>
              <button
                className="icon-btn"
                title="Summarize"
                onClick={() => navigate(`/summary/${encodeURIComponent(d.document_id)}`)}
              >
                <NotebookText size={15} />
              </button>
              <button
                className="icon-btn"
                title="Flashcards"
                onClick={() => navigate(`/flashcards/${encodeURIComponent(d.document_id)}`)}
              >
                <Layers size={15} />
              </button>
              <button
                className="icon-btn"
                title="Delete"
                disabled={deletingId === d.document_id}
                onClick={() => {
                  if (confirm(`Delete "${d.filename}"? This removes it from the knowledge base.`)) {
                    handleDelete(d.document_id);
                  }
                }}
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
