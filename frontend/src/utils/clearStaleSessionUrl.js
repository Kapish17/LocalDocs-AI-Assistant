// A full browser refresh reloads whatever URL the tab was on. If that URL
// was a document/chat deep link — /summary/:documentId, /flashcards/:documentId,
// /chat/:sessionId, or /chat?doc=:documentId — React Router would otherwise
// mount that page with the OLD id already sitting in useParams()/
// useSearchParams(), and that page's own effect fetches/queries it
// immediately, before the new session's (empty) document list has even
// loaded. See frontend/src/utils/browserSession.js: BROWSER_SESSION_ID
// already correctly becomes a brand-new id on every real page load — the
// bug is that these three routes don't respect that reset, because the
// stale document_id / chat session_id keeps living in the URL itself
// rather than in the (correctly-reset) session id.
//
// Concretely, per id kind:
//   - /summary/:documentId, /flashcards/:documentId — the backend 404s a
//     document_id that isn't in this fresh session's data_dir (see
//     backend/core/documents.py's find_document_path / api/main.py's
//     _require_document), which is why refreshing on one of these pages
//     surfaced "Document not found" / "No document found with id ..."
//     errors instead of the "pick a document" empty state.
//   - /chat/:sessionId — WORSE: the chat SessionStore
//     (backend/core/sessions.py) is a deliberately global, cross-browser-
//     session store of chat conversations (a separate, pre-existing
//     feature — many chat conversations can exist within one document
//     session, and the list of past conversations is meant to persist for
//     the life of the backend process). So an old chat-session id
//     surviving in the URL across a refresh doesn't 404 — it actually
//     succeeds and silently restores that OLD conversation's messages,
//     which is exactly the "previous session accessed after refresh"
//     symptom.
//   - /chat?doc=:documentId — same root cause as summary/flashcards: a
//     stale document filter would be sent on the next chat question.
//
// The fix rewrites the URL (via history.replaceState, so no extra entry
// is added to browser history) BEFORE React Router ever parses it — see
// main.jsx, which calls this synchronously before mounting <App/>. That
// way the very first route match already sees the id-less base path, so
// Summary/Flashcards/Chat mount in their normal "no document/session yet"
// empty state and never fire a stale request at all.
//
// This module only ever runs once per REAL page load (main.jsx's
// top-level code, like browserSession.js's own module-scope id
// generation, is only (re)evaluated on an actual reload/navigation, never
// during client-side SPA navigation). react-router's own navigate()/
// <Link> calls change the URL via the History API without a real page
// load, so a document/chat URL created by browsing normally within the
// current visit is completely unaffected — this file is never consulted
// again after the initial load.
const STALE_ID_ROUTE_PATTERNS = [
  /^\/summary\/[^/]+\/?$/,
  /^\/flashcards\/[^/]+\/?$/,
  /^\/chat\/[^/]+\/?$/,
];

export function clearStaleSessionUrl(location = window.location) {
  const { pathname, search, hash } = location;

  const matchesStaleIdRoute = STALE_ID_ROUTE_PATTERNS.some((re) => re.test(pathname));
  const hasStaleDocQueryParam = pathname === "/chat" && new URLSearchParams(search).has("doc");

  if (!matchesStaleIdRoute && !hasStaleDocQueryParam) {
    return null;
  }

  // "/summary/report.pdf" -> "/summary", "/chat/abc123" -> "/chat". Any
  // query string is dropped too (covers /chat/:sessionId?doc=... and the
  // bare /chat?doc=... case) since it can only carry more stale ids
  // (document filter) for these three routes.
  const basePath = matchesStaleIdRoute
    ? pathname.split("/").slice(0, 2).join("/") || "/"
    : pathname;

  window.history.replaceState(null, "", basePath + hash);
  return basePath;
}
