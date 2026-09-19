import { useNavigate } from "react-router-dom";
import { FileStack, MessageSquare, NotebookText, Layers, FileText } from "lucide-react";
import UploadPanel from "../components/upload/UploadPanel";
import EmptyState from "../components/common/EmptyState";
import ErrorBanner from "../components/common/ErrorBanner";
import { useDocuments } from "../hooks/useDocuments";
import { useSessions } from "../hooks/useSessions";

const FEATURES = [
  {
    to: "/chat",
    icon: MessageSquare,
    title: "Chat with your documents",
    desc: "Ask questions and get grounded, cited answers.",
  },
  {
    to: "/summary",
    icon: NotebookText,
    title: "Summarize a document",
    desc: "Get a short or detailed AI-generated overview.",
  },
  {
    to: "/flashcards",
    icon: Layers,
    title: "Generate flashcards",
    desc: "Turn a document into study Q&A cards.",
  },
  {
    to: "/documents",
    icon: FileStack,
    title: "Manage your library",
    desc: "View, search, and remove uploaded documents.",
  },
];

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  return kb < 1024 ? `${kb.toFixed(0)} KB` : `${(kb / 1024).toFixed(1)} MB`;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { documents, loading, error, refresh } = useDocuments();
  const { sessions } = useSessions();

  const indexedCount = documents.filter((d) => d.indexed).length;
  const totalChunks = documents.reduce((sum, d) => sum + (d.num_chunks || 0), 0);
  const recent = [...documents]
    .sort((a, b) => (b.uploaded_at || 0) - (a.uploaded_at || 0))
    .slice(0, 5);

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Dashboard</h1>
          <p className="subtitle">Your document library and AI tools, at a glance.</p>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-card-label">Documents</div>
          <div className="stat-card-value">{documents.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Indexed</div>
          <div className="stat-card-value">{indexedCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Chunks in index</div>
          <div className="stat-card-value">{totalChunks}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Chat sessions</div>
          <div className="stat-card-value">{sessions.length}</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="section-title">Upload a document</div>
        <UploadPanel onUploaded={refresh} />
      </div>

      <div className="section-title">Quick actions</div>
      <div className="feature-grid">
        {FEATURES.map(({ to, icon: Icon, title, desc }) => (
          <button key={to} className="feature-card" onClick={() => navigate(to)}>
            <span className="feature-card-icon">
              <Icon size={18} />
            </span>
            <span className="feature-card-title">{title}</span>
            <p className="feature-card-desc">{desc}</p>
          </button>
        ))}
      </div>

      <div className="section-title">Recent documents</div>
      <ErrorBanner message={error} onRetry={refresh} />
      {!loading && recent.length === 0 && !error && (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          hint="Upload a PDF, DOCX, PPTX, TXT, CSV, or Markdown file above to get started."
        />
      )}
      {recent.length > 0 && (
        <div className="recent-list">
          {recent.map((d) => (
            <div key={d.document_id} className="recent-item">
              <FileText size={16} className="recent-item-icon" />
              <span className="recent-item-name">{d.filename}</span>
              <span className="recent-item-meta">
                {d.file_type.toUpperCase()} · {formatBytes(d.size_bytes)}
                {d.num_pages ? ` · ${d.num_pages} pages` : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
