// A unique id for THIS page load, sent as the X-Session-Id header on every
// document/RAG request (see services/api.js) so the backend keeps this
// page's uploaded documents, FAISS index, and BM25 index completely
// separate from any other browser tab or previous visit — see
// backend/core/sessions.py (DocumentSessionStore).
//
// Deliberately a plain module-scoped constant, NOT sessionStorage:
// sessionStorage survives a real page refresh, which is the opposite of
// the "a refresh starts a brand-new session" requirement. This value is
// computed once, synchronously, the first time this module is imported —
// a real browser refresh/reload re-evaluates the module from scratch,
// producing a new id, while client-side route navigation (react-router,
// no full page reload) keeps the same module instance and therefore the
// same id for the rest of this visit.
function generateSessionId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for a non-secure-context or older browser (crypto.randomUUID
  // needs a secure context). This id only ever keys an in-memory
  // server-side dict — it isn't a security/auth token — so a weaker
  // fallback here is fine.
  return `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export const BROWSER_SESSION_ID = generateSessionId();
