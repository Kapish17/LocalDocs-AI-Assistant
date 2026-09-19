import { useRef, useState } from "react";
import { uploadDocuments } from "../services/api";

/**
 * Document upload panel, backed by POST /upload.
 */
export default function UploadPanel({ onUploaded, disabled }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  async function handleFiles(fileList) {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setError(null);
    setResults(null);
    try {
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

  return (
    <div className="upload-panel">
      <label className="upload-label">
        <span className="upload-title">📤 Upload documents</span>
        <span className="upload-hint">PDF, DOCX, PPTX, TXT, CSV, MD</span>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.txt,.csv,.md"
          disabled={disabled || uploading}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>

      {uploading && <p className="upload-status">Indexing documents…</p>}

      {error && <p className="upload-status upload-status--error">⚠️ {error}</p>}

      {results && (
        <ul className="upload-results">
          {results.map((f) => (
            <li key={f.filename} className={f.status === "indexed" ? "ok" : "failed"}>
              {f.status === "indexed" ? "✅" : "❌"} {f.filename}
              {f.detail ? ` — ${f.detail}` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
