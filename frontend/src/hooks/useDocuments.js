import { useCallback, useEffect, useState } from "react";
import { listDocuments, deleteDocument as apiDeleteDocument } from "../services/api";

/**
 * Shared document-library state — used by the Dashboard, Documents page,
 * and anywhere else that needs to know what's uploaded (e.g. the chat
 * document-picker). One fetch, one source of truth, so the list can't
 * drift out of sync between pages during a session.
 *
 * Session-scoping (a real refresh must show 0 documents, and must never
 * retrieve a previous session's chunks) is enforced by the BACKEND, not
 * here: every request goes out with the X-Session-Id header (see
 * services/api.js and utils/browserSession.js), and the backend resolves
 * an entirely separate data folder + FAISS/BM25 index per session id (see
 * backend/core/sessions.py's DocumentSessionStore). So `listDocuments()`
 * below already returns exactly this session's documents — nothing to
 * filter client-side.
 */
export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err) {
      setError(err.message || "Could not load documents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function removeDocument(documentId) {
    await apiDeleteDocument(documentId);
    await refresh();
  }

  return { documents, loading, error, refresh, removeDocument };
}
