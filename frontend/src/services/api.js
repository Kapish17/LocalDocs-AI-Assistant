// All calls to the FastAPI backend go through here — nothing else in the
// app should build a fetch URL or know the API's shape. The backend base
// URL is configured via VITE_API_URL (see .env.example) instead of being
// hardcoded, so the same build can point at localhost, docker-compose, or
// a deployed Cloud Run URL.

import { BROWSER_SESSION_ID } from "../utils/browserSession";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Sent on every request so the backend can keep this page load's uploaded
// documents/FAISS/BM25 state isolated from any other session — see
// utils/browserSession.js and backend/core/sessions.py. Endpoints that
// don't care about it (health check aside, and the chat-session endpoints,
// which are a different, pre-existing concept) simply ignore the header.
const SESSION_HEADERS = { "X-Session-Id": BROWSER_SESSION_ID };

async function parseErrorDetail(response) {
  try {
    const body = await response.json();
    return body.detail || `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

async function getJSON(path) {
  const res = await fetch(`${API_URL}${path}`, { headers: SESSION_HEADERS });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

async function postJSON(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...SESSION_HEADERS },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

async function del(path) {
  const res = await fetch(`${API_URL}${path}`, { method: "DELETE", headers: SESSION_HEADERS });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function getHealth() {
  return getJSON("/health");
}

/**
 * @param {string} query
 * @param {{documentId?: string, sessionId?: string}} [opts]
 */
export async function askQuestion(query, opts = {}) {
  return postJSON("/query", {
    query,
    document_id: opts.documentId || null,
    session_id: opts.sessionId || null,
  });
}

/**
 * @param {FileList | File[]} files
 */
export async function uploadDocuments(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const res = await fetch(`${API_URL}/upload`, { method: "POST", headers: SESSION_HEADERS, body: formData });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

// --- Document library ------------------------------------------------------

export async function listDocuments() {
  const data = await getJSON("/api/documents");
  return data.documents;
}

export async function deleteDocument(documentId) {
  return del(`/api/documents/${encodeURIComponent(documentId)}`);
}

export async function summarizeDocument(documentId, detail = "short") {
  return postJSON(`/api/documents/${encodeURIComponent(documentId)}/summarize`, { detail });
}

export async function getFlashcards(documentId, numCards = 8) {
  return postJSON(`/api/documents/${encodeURIComponent(documentId)}/flashcards`, { num_cards: numCards });
}

// These two are plain <a href> downloads (Summary.jsx / Flashcards.jsx), so
// they can't carry a custom header — the session id goes as a `session`
// query param instead, which the backend accepts as a fallback
// specifically for these two GET export endpoints (see api/main.py's
// _resolve_session_id).
export function summaryExportUrl(documentId, detail = "short") {
  return `${API_URL}/api/documents/${encodeURIComponent(documentId)}/summary/export?detail=${detail}&session=${encodeURIComponent(BROWSER_SESSION_ID)}`;
}

export function flashcardsExportUrl(documentId, numCards = 8) {
  return `${API_URL}/api/documents/${encodeURIComponent(documentId)}/flashcards/export?num_cards=${numCards}&session=${encodeURIComponent(BROWSER_SESSION_ID)}`;
}

// --- Sessions ---------------------------------------------------------------
// Chat conversation sessions — a separate, pre-existing concept from the
// browser/document session above (one browser session can hold many of
// these). Left unchanged; the header is harmless/unused here.

export async function createSession(title) {
  return postJSON("/api/sessions", { title: title || null });
}

export async function listSessions() {
  const data = await getJSON("/api/sessions");
  return data.sessions;
}

export async function getSession(sessionId) {
  return getJSON(`/api/sessions/${encodeURIComponent(sessionId)}`);
}

export async function deleteSession(sessionId) {
  return del(`/api/sessions/${encodeURIComponent(sessionId)}`);
}

export function sessionExportUrl(sessionId) {
  return `${API_URL}/api/sessions/${encodeURIComponent(sessionId)}/export`;
}

export { API_URL };
