"""
Session-scoped document/RAG isolation tests.

Covers the spec's test list A-J:
  A. New session starts with zero documents.
  B. Session A uploads document A.
  C. Session B cannot see document A.
  D. Session B cannot retrieve chunks from document A.
  E. Session A can still query document A.
  F. Refresh/new session produces zero documents.
  G. New session uploads document B.
  H. Query B cannot retrieve A.
  I. Existing document delete behavior still works.
  J. Existing frontend-facing behavior still works (response shapes/status
     codes the React app depends on are unchanged).

Uses the real FastAPI app, real routes, real FAISS, real BM25, real
chunking/splitting — only the embedding model and the Gemini client are
faked (see conftest.py), because this suite is about which folder/index a
request reads and writes (session isolation), not about embedding or LLM
answer quality, and the real ones need network/GPU-class dependencies this
test environment doesn't have.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient


def _client():
    # Imported lazily, inside a fresh cwd (see conftest.py's autouse
    # _isolated_cwd fixture) and after the rag.embeddings / llm.gemini
    # stubs are installed, so core.kb's global DATA_DIR/VECTOR_DB_PATH
    # constants and the per-session paths both land under this test's own
    # tmp_path.
    from api.main import app

    return TestClient(app)


def _upload_txt(client, session_id, filename, text):
    return client.post(
        "/upload",
        headers={"X-Session-Id": session_id},
        files=[("files", (filename, io.BytesIO(text.encode("utf-8")), "text/plain"))],
    )


def _new_session_id():
    return uuid.uuid4().hex


DOC_A_TEXT = "Zebra herds migrate across the savanna every year searching for fresh grass and water."
DOC_B_TEXT = "The rocket's second stage ignited and the spacecraft separated cleanly from the booster."


def test_a_new_session_starts_with_zero_documents():
    client = _client()
    sid = _new_session_id()
    res = client.get("/api/documents", headers={"X-Session-Id": sid})
    assert res.status_code == 200
    assert res.json()["documents"] == []


def test_missing_session_header_is_rejected():
    client = _client()
    res = client.get("/api/documents")
    assert res.status_code == 400


def test_b_session_a_uploads_document_a():
    client = _client()
    sid_a = _new_session_id()
    res = _upload_txt(client, sid_a, "doc_a.txt", DOC_A_TEXT)
    assert res.status_code == 200
    body = res.json()
    assert body["kb_ready"] is True
    assert body["files"][0]["status"] == "indexed"

    listed = client.get("/api/documents", headers={"X-Session-Id": sid_a}).json()["documents"]
    assert [d["document_id"] for d in listed] == ["doc_a.txt"]


def test_c_and_d_session_b_cannot_see_or_retrieve_document_a():
    client = _client()
    sid_a = _new_session_id()
    sid_b = _new_session_id()

    assert _upload_txt(client, sid_a, "doc_a.txt", DOC_A_TEXT).status_code == 200

    # C: session B's document list is empty, even though A has one document.
    listed_b = client.get("/api/documents", headers={"X-Session-Id": sid_b}).json()["documents"]
    assert listed_b == []

    # D: session B has no knowledge base at all yet (never uploaded
    # anything), so querying returns 503 rather than ever touching A's
    # index -- this alone proves B and A don't share a retriever.
    res = client.post(
        "/query",
        headers={"X-Session-Id": sid_b},
        json={"query": "What migrates across the savanna?"},
    )
    assert res.status_code == 503

    # And B genuinely cannot address A's document by id either.
    res_doc = client.post(
        "/query",
        headers={"X-Session-Id": sid_b},
        json={"query": "What migrates across the savanna?", "document_id": "doc_a.txt"},
    )
    assert res_doc.status_code in (503, 404)


def test_e_session_a_can_still_query_document_a():
    client = _client()
    sid_a = _new_session_id()
    assert _upload_txt(client, sid_a, "doc_a.txt", DOC_A_TEXT).status_code == 200

    res = client.post(
        "/query",
        headers={"X-Session-Id": sid_a},
        json={"query": "What migrates across the savanna?"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["retrieved_documents"], "expected at least one retrieved chunk"
    assert all(d["document_id"] == "doc_a.txt" for d in body["retrieved_documents"])
    assert "zebra" in body["retrieved_documents"][0]["content"].lower()


def test_f_and_g_and_h_refresh_starts_new_session_uploads_b_no_leak_from_a():
    client = _client()
    sid_a = _new_session_id()
    assert _upload_txt(client, sid_a, "doc_a.txt", DOC_A_TEXT).status_code == 200

    # F: "refresh" = a brand-new session id (see
    # frontend/src/utils/browserSession.js) -> zero documents, even though
    # A exists.
    sid_new = _new_session_id()
    listed_new = client.get("/api/documents", headers={"X-Session-Id": sid_new}).json()["documents"]
    assert listed_new == []

    # G: upload document B into the new session.
    res = _upload_txt(client, sid_new, "doc_b.txt", DOC_B_TEXT)
    assert res.status_code == 200
    listed_new_after = client.get("/api/documents", headers={"X-Session-Id": sid_new}).json()["documents"]
    assert [d["document_id"] for d in listed_new_after] == ["doc_b.txt"]

    # H: querying the new session never retrieves A's content.
    res_q = client.post(
        "/query",
        headers={"X-Session-Id": sid_new},
        json={"query": "What happened to the rocket?"},
    )
    assert res_q.status_code == 200
    body = res_q.json()
    assert body["retrieved_documents"]
    assert all(d["document_id"] == "doc_b.txt" for d in body["retrieved_documents"])
    assert not any("zebra" in d["content"].lower() for d in body["retrieved_documents"])

    # And A's own session is completely unaffected by any of the above.
    listed_a = client.get("/api/documents", headers={"X-Session-Id": sid_a}).json()["documents"]
    assert [d["document_id"] for d in listed_a] == ["doc_a.txt"]


def test_i_existing_document_delete_behavior_still_works():
    client = _client()
    sid = _new_session_id()
    assert _upload_txt(client, sid, "doc_a.txt", DOC_A_TEXT).status_code == 200

    res = client.delete("/api/documents/doc_a.txt", headers={"X-Session-Id": sid})
    assert res.status_code == 200
    body = res.json()
    assert body["deleted"] is True
    assert body["kb_ready"] is False

    listed = client.get("/api/documents", headers={"X-Session-Id": sid}).json()["documents"]
    assert listed == []

    # Deleting something that doesn't exist still 404s cleanly.
    res_404 = client.delete("/api/documents/does_not_exist.txt", headers={"X-Session-Id": sid})
    assert res_404.status_code == 404


def test_k_stale_document_id_rejected_by_summarize_and_flashcards_in_new_session():
    """Regression test for the refresh bug fixed in
    frontend/src/utils/clearStaleSessionUrl.js: before that fix, a full
    browser refresh landing on /summary/:documentId or
    /flashcards/:documentId (or their session=-query-param export links)
    would fire a request carrying the OLD, now-stale document_id, from a
    document session that no longer exists once BROWSER_SESSION_ID resets.
    The frontend fix stops that request from ever being sent, but the
    backend must independently guarantee it can never resolve a stale
    document_id against another session's files even if such a request
    does arrive.

    sid_new uploads its own document first (doc_b.txt) so it has a real,
    active knowledge base -- a session with no knowledge base at all
    correctly 503s before it ever gets to check the document id (see
    test_c_and_d's equivalent case for /query). This test instead covers
    the case that matters for the refresh bug: a session that legitimately
    has its own document(s) indexed must still never resolve a document
    id belonging to another (e.g. pre-refresh) session -- a clean 404, not
    session A's content silently returned to session B's request.
    """
    client = _client()
    sid_a = _new_session_id()
    assert _upload_txt(client, sid_a, "doc_a.txt", DOC_A_TEXT).status_code == 200

    sid_new = _new_session_id()  # simulates the browser session id after a refresh
    assert _upload_txt(client, sid_new, "doc_b.txt", DOC_B_TEXT).status_code == 200

    res_summary = client.post(
        "/api/documents/doc_a.txt/summarize",
        headers={"X-Session-Id": sid_new},
        json={"detail": "short"},
    )
    assert res_summary.status_code == 404

    res_flash = client.post(
        "/api/documents/doc_a.txt/flashcards",
        headers={"X-Session-Id": sid_new},
        json={"num_cards": 4},
    )
    assert res_flash.status_code == 404

    # Same guarantee for the plain <a href> export endpoints (they accept
    # the session id as a ?session= query param instead of the header,
    # since a download link can't set a custom header -- see
    # frontend/src/services/api.js's summaryExportUrl/flashcardsExportUrl).
    res_export_summary = client.get(
        "/api/documents/doc_a.txt/summary/export",
        params={"session": sid_new},
    )
    assert res_export_summary.status_code == 404

    res_export_flash = client.get(
        "/api/documents/doc_a.txt/flashcards/export",
        params={"session": sid_new},
    )
    assert res_export_flash.status_code == 404

    # And sid_new's own document is completely unaffected.
    res_own = client.post(
        "/api/documents/doc_b.txt/summarize",
        headers={"X-Session-Id": sid_new},
        json={"detail": "short"},
    )
    assert res_own.status_code == 200


def test_j_existing_frontend_facing_behavior_still_works():
    client = _client()

    # /health keeps working with no session header at all (infra/uptime
    # checks, and the very first paint before the frontend's first call).
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {"status", "kb_ready", "llm_ready", "llm_error"}
    assert body["kb_ready"] is False  # no session -> nothing to report ready

    # With a session that has uploaded something, /health (with the header)
    # reflects that session's own readiness.
    sid = _new_session_id()
    assert _upload_txt(client, sid, "doc_a.txt", DOC_A_TEXT).status_code == 200
    res2 = client.get("/health", headers={"X-Session-Id": sid})
    assert res2.json()["kb_ready"] is True

    # Chat conversation sessions (a different, pre-existing concept) are
    # completely unaffected by any of this.
    created = client.post("/api/sessions", json={"title": "test chat"})
    assert created.status_code == 200
    chat_session_id = created.json()["session_id"]
    got = client.get(f"/api/sessions/{chat_session_id}")
    assert got.status_code == 200
    assert got.json()["title"] == "test chat"

    # Document response shape used by the React Documents page is unchanged.
    listed = client.get("/api/documents", headers={"X-Session-Id": sid}).json()["documents"]
    assert set(listed[0].keys()) == {
        "document_id", "filename", "file_type", "size_bytes",
        "uploaded_at", "indexed", "num_chunks", "num_pages",
    }
