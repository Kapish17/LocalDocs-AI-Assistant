// Tracks which uploaded documents belong to the CURRENT page load — the
// "session" from the user's perspective, per the product requirement:
// after a real browser refresh/reload, previously uploaded documents must
// stop appearing in the Documents/library UI, while uploads made during
// the current visit keep working and stay visible.
//
// Deliberately a plain in-memory module-scoped Set, NOT sessionStorage or
// localStorage: browser session storage survives a page refresh (that's
// the opposite of what's needed here), while a real reload re-evaluates
// this module from scratch, naturally emptying the set. Client-side route
// navigation (react-router, no full page reload) keeps the same module
// instance, so the list still survives moving between pages in one visit.
//
// This is a UI-only, frontend concern — nothing on disk is touched, the
// FAISS/BM25 index and document-scoped retrieval are unaffected, so a
// still-open tab can keep chatting about a document it uploaded exactly
// as before. document_id === filename (see backend/core/documents.py).
const uploadedThisLoad = new Set();

export function markDocumentUploaded(documentId) {
  if (documentId) uploadedThisLoad.add(documentId);
}

export function isDocumentFromThisLoad(documentId) {
  return uploadedThisLoad.has(documentId);
}
