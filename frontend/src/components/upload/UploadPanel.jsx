import { useRef, useState } from "react";
import { UploadCloud, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { uploadDocuments } from "../../services/api";

/**
 * Drag-and-drop document upload. Every state shown here (uploading,
 * per-file indexed/failed) reflects the REAL response from POST /upload —
 * there is no simulated/fake progress animation, because indexing (text
 * extraction, OCR fallback, chunking, embedding, FAISS rebuild) genuinely
 * takes a few seconds and the UI should honestly reflect that.
 */
export default function UploadPanel({ onUploaded, disabled }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);

  async function handleFiles(fileList) {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setError(null);
    setResults(null);
    try {
      // uploadDocuments() sends this page load's X-Session-Id header (see
      // services/api.js), so the backend indexes these files into THIS
      // session's own folder/FAISS index — the refreshed list below
      // (onUploaded -> refresh(), via useDocuments) will already be
      // correctly scoped without any client-side bookkeeping.
      const res = await uploadDocuments(fileList);
      setResults(res.files);
      if (onUploaded) onUploaded(res);
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    if (disabled || uploading) return;
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div>
      <label
        className={`upload-dropzone${dragging ? " dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <UploadCloud size={30} className="upload-dropzone-icon" />
        <div className="upload-dropzone-title">
          {uploading ? "Indexing documents…" : "Drag files here or click to upload"}
        </div>
        <div className="upload-dropzone-hint">PDF, DOCX, PPTX, TXT, CSV, MD</div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.txt,.csv,.md"
          disabled={disabled || uploading}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>

      {uploading && (
        <p className="upload-status">
          <Loader2 size={14} className="spin" /> Extracting text, chunking, and building the search index…
        </p>
      )}

      {error && (
        <p className="upload-status upload-status--error">
          <XCircle size={14} /> {error}
        </p>
      )}

      {results && (
        <ul className="upload-results">
          {results.map((f) => (
            <li key={f.filename} className={f.status === "indexed" ? "ok" : "failed"}>
              {f.status === "indexed" ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
              {f.filename}
              {f.detail ? ` — ${f.detail}` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
