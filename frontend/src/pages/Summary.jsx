import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, NotebookText, RefreshCw } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import ErrorBanner from "../components/common/ErrorBanner";
import { SkeletonLines } from "../components/common/LoadingState";
import { useDocuments } from "../hooks/useDocuments";
import { summarizeDocument, summaryExportUrl } from "../services/api";

export default function Summary() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const { documents, loading: docsLoading } = useDocuments();

  const [detail, setDetail] = useState("short");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function generate(currentDetail = detail) {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await summarizeDocument(documentId, currentDetail);
      setSummary(res.summary);
    } catch (err) {
      setError(err.message || "Failed to generate summary.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setSummary(null);
    if (documentId) generate(detail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  function handleDetailChange(next) {
    if (next === detail) return;
    setDetail(next);
    generate(next);
  }

  if (!documentId) {
    return (
      <div>
        <div className="page-heading">
          <div>
            <h1>Summarize a document</h1>
            <p className="subtitle">Pick a document to get a short or detailed AI overview.</p>
          </div>
        </div>
        {docsLoading ? (
          <SkeletonLines count={3} />
        ) : documents.length === 0 ? (
          <EmptyState
            icon={NotebookText}
            title="No documents yet"
            hint="Upload a document from the Documents page first."
          />
        ) : (
          <div className="doc-table">
            {documents.map((d) => (
              <button
                key={d.document_id}
                className="doc-row"
                style={{ cursor: "pointer", textAlign: "left", width: "100%" }}
                onClick={() => navigate(`/summary/${encodeURIComponent(d.document_id)}`)}
              >
                <div className="doc-row-icon">
                  <NotebookText size={18} />
                </div>
                <div className="doc-row-main">
                  <div className="doc-row-name">{d.filename}</div>
                  <div className="doc-row-meta">
                    <span>{d.file_type.toUpperCase()}</span>
                    {d.num_pages ? <span>{d.num_pages} pages</span> : null}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Summary — {documentId}</h1>
          <p className="subtitle">Grounded in this document's own indexed content.</p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div className="detail-toggle">
            <button className={detail === "short" ? "active" : ""} onClick={() => handleDetailChange("short")}>
              Short
            </button>
            <button className={detail === "detailed" ? "active" : ""} onClick={() => handleDetailChange("detailed")}>
              Detailed
            </button>
          </div>
          <button className="icon-btn" title="Regenerate" onClick={() => generate(detail)}>
            <RefreshCw size={15} />
          </button>
          <a className="icon-btn" title="Export as Markdown" href={summaryExportUrl(documentId, detail)} download={`${documentId}-summary.md`}>
            <Download size={15} />
          </a>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={() => generate(detail)} />

      <div className="card">
        {loading ? (
          <SkeletonLines count={6} />
        ) : summary ? (
          <div className="summary-text">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
          </div>
        ) : (
          <EmptyState icon={NotebookText} title="No summary yet" />
        )}
      </div>
    </div>
  );
}
