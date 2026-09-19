"""
FastAPI backend for LocalDocs AI Assistant.

Wraps the RAG pipeline (core/rag_engine.py, rag/, llm/) behind a small
HTTP API, so the React frontend and the CLI (app.py) share one
implementation instead of separate copies of the retrieval/prompting logic.

Run locally (from the repository root, so data/ and database/ are shared
with the CLI):
    uvicorn backend.api.main:app --reload --port 8000

Or from inside backend/ (its own local data/database, e.g. how the Docker
image runs it):
    uvicorn api.main:app --reload --port 8000

This module is also what the backend Docker image runs in production
(Google Cloud Run) — see backend/Dockerfile.

Document/RAG state is isolated per BROWSER SESSION (see core/sessions.py's
DocumentSessionStore) — every document/RAG endpoint below requires an
X-Session-Id header (frontend: frontend/src/utils/browserSession.js), and
resolves ITS OWN data folder + FAISS index rather than one global one. This
is a separate concept from the existing chat SessionStore (many chat
conversations can exist within one browser session).
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# Makes `from core import kb`, `from rag...`, `from llm...` etc. resolve
# whether this module is imported as `api.main` (cwd = backend/, e.g. the
# Docker image) or as `backend.api.main` (cwd = repo root, local dev) —
# without changing any of the existing unqualified imports throughout
# core/, rag/, llm/, loaders/, utils/.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from fastapi import Depends, FastAPI, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from core import documents as doc_lib
from core import kb
from core import sessions as session_lib
from core.sessions import doc_sessions, is_valid_document_session_id
from core.rag_engine import (
    answer_question,
    friendly_llm_error,
    generate_flashcards,
    summarize_documents,
    try_get_llm,
)
from api.schemas import (
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentSummary,
    Flashcard,
    FlashcardsRequest,
    FlashcardsResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SessionCreateRequest,
    SessionDetail,
    SessionListResponse,
    SessionSummary,
    SourceDocument,
    SummarizeRequest,
    SummarizeResponse,
    UploadedFileResult,
    UploadResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("localdocs.api")

# Process-wide, NOT per-session: the Gemini client uses one API key for the
# whole process, same as before. Document/RAG state (retriever, kb_version)
# used to live here too (state["retriever"], state["kb_version"]) but is
# now per-browser-session — see core.sessions.doc_sessions.
state = {"llm": None, "llm_error": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Document/RAG state is now built lazily, per browser session, on first
    # request (see _ensure_session_kb_and_llm) rather than eagerly from a
    # single global data/database/faiss_index at startup — there is no
    # longer one global knowledge base to build here. Cloud Run's baked-in
    # data/ (see Dockerfile) is still there on disk, but no FastAPI session
    # reads from it automatically; a session's document library always
    # starts empty until that session uploads something, by design (see
    # README "Session-scoped documents"). app.py is unaffected — it still
    # uses core.kb's global-path defaults directly.
    logger.info("Startup: document/RAG state is per-browser-session and built lazily on first use.")

    logger.info("Startup: checking Gemini client...")
    llm, err = try_get_llm()
    state["llm"] = llm
    state["llm_error"] = err
    if err:
        logger.warning("Gemini client not ready at startup: %s", err)

    yield
    # No teardown needed — nothing here holds an external connection open.


app = FastAPI(
    title="LocalDocs AI Assistant API",
    description="RAG over your own documents — the same retrieval/LLM pipeline the CLI (app.py) uses, exposed over HTTP.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow the React frontend's origin(s) to call this API from the
# browser during local dev and in production. Configured via env var
# instead of allow_origins=["*"] so only known frontends can call the API
# with credentials/cookies (not currently used, but this keeps the door
# closed). CORS_ORIGINS takes a comma-separated list and wins if set;
# otherwise falls back to FRONTEND_URL (single origin), then to the
# standard local Vite dev ports.
_cors_origins_env = os.getenv("CORS_ORIGINS")
if _cors_origins_env:
    _allowed_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
else:
    _frontend_url = os.getenv("FRONTEND_URL")
    _allowed_origins = [_frontend_url] if _frontend_url else [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-file upload size limit. Configurable via env var so it can be tuned
# per deployment without a code change; defaults to 25 MB, which comfortably
# covers scanned/OCR PDFs and slide decks while still bounding memory use
# in the /upload handler (files are read fully into memory).
try:
    MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "25"))
except ValueError:
    MAX_UPLOAD_MB = 25.0
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)


# ==============================================================================
# Browser-session resolution
# ==============================================================================
#
# Every document/RAG endpoint requires the frontend's per-page-load id (see
# frontend/src/utils/browserSession.js), sent as the X-Session-Id header.
# The two export endpoints are plain <a href> downloads (can't set custom
# headers), so they also accept it as a `session` query param — the
# frontend appends that for those two links only.


def _resolve_session_id(
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
    session: Optional[str] = Query(default=None),
) -> str:
    sid = x_session_id or session
    if not is_valid_document_session_id(sid):
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid X-Session-Id header. The frontend should send a per-page-load session id on every document/RAG request.",
        )
    return sid


def _resolve_optional_session_id(
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
) -> Optional[str]:
    return x_session_id if is_valid_document_session_id(x_session_id) else None


@app.get("/health", response_model=HealthResponse)
def health(session_id: Optional[str] = Depends(_resolve_optional_session_id)) -> HealthResponse:
    # No header (e.g. an infra/uptime check, or the very first paint before
    # the frontend's first real call) -> kb_ready is simply False, never an
    # error: /health must keep working without a session for Docker/Cloud
    # Run health checks.
    kb_ready = False
    if session_id:
        entry = doc_sessions.peek(session_id)
        kb_ready = bool(entry and entry["retriever"] is not None)
    return HealthResponse(
        status="ok",
        kb_ready=kb_ready,
        llm_ready=state["llm"] is not None,
        llm_error=state["llm_error"],
    )


def _ensure_session_kb_and_llm(session_id: str):
    """Per-session equivalent of the old global _ensure_kb_and_llm: builds
    (if needed) and returns THIS session's retriever, plus the shared LLM
    client. Raises a clear 503 instead of letting a None retriever/llm
    cause a confusing 500 deeper in core.rag_engine."""
    entry = doc_sessions.get_or_create(session_id)
    if entry["retriever"] is None:
        # A knowledge base may have been built since this session's last
        # request (e.g. an upload). Building it can fail (e.g. a transient
        # network error downloading the embedding model), so this must not
        # crash the request with a 500 — fall through to the 503 below.
        try:
            if kb.ensure_knowledge_base(data_dir=entry["data_dir"], vector_db_path=entry["vector_db_path"]):
                entry["retriever"] = kb.load_retriever_if_ready(vector_db_path=entry["vector_db_path"])
        except Exception:
            logger.exception("Failed to build the knowledge base on-demand for session %s.", session_id)
    if entry["retriever"] is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "No knowledge base is available yet. Upload a document to get started."
            ),
        )

    if state["llm"] is None:
        llm, err = try_get_llm()
        state["llm"] = llm
        state["llm_error"] = err
    if state["llm"] is None:
        raise HTTPException(status_code=503, detail=f"Gemini client isn't configured: {state['llm_error']}")

    return entry["retriever"], state["llm"]


def _require_document(document_id: str, data_dir: Path) -> None:
    """404s cleanly if document_id doesn't correspond to an uploaded file in
    THIS session's data_dir, instead of silently returning an
    empty/misleading result for a typo'd, stale, or another session's id."""
    if doc_lib.find_document_path(document_id, data_dir=data_dir) is None:
        raise HTTPException(status_code=404, detail=f"No document found with id '{document_id}'.")


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, browser_session_id: str = Depends(_resolve_session_id)) -> QueryResponse:
    entry = doc_sessions.get_or_create(browser_session_id)
    retriever, llm = _ensure_session_kb_and_llm(browser_session_id)

    if request.document_id:
        _require_document(request.document_id, entry["data_dir"])

    chat_session = None
    if request.session_id:
        chat_session = session_lib.store.get(request.session_id)
        if chat_session is None:
            raise HTTPException(status_code=404, detail=f"No chat session found with id '{request.session_id}'.")

    chat_history = session_lib.store.history_for_prompt(request.session_id) if chat_session else None

    try:
        result = answer_question(
            request.query,
            retriever,
            llm,
            chat_history=chat_history,
            cache_bust=entry["kb_version"],
            document_filter=request.document_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=friendly_llm_error(e))

    if chat_session:
        session_lib.store.add_message(request.session_id, "user", request.query)
        session_lib.store.add_message(
            request.session_id,
            "assistant",
            result["answer"],
            extra={"sources": result["retrieved_documents"], "confidence": result["confidence"]},
        )

    return QueryResponse(
        answer=result["answer"],
        confidence=result["confidence"],
        sources=result["sources"],
        retrieved_documents=[SourceDocument(**d) for d in result["retrieved_documents"]],
        latency_ms=result["latency_ms"],
        session_id=request.session_id,
    )


@app.post("/upload", response_model=UploadResponse)
async def upload(files: list[UploadFile], browser_session_id: str = Depends(_resolve_session_id)) -> UploadResponse:
    """Saves the uploaded files into THIS session's own data folder and
    rebuilds THIS session's own FAISS index from everything currently in
    it (same build_vector_store() pipeline app.py uses — not a second
    implementation, just pointed at a per-session folder). This is a full
    rebuild of this session's index, not an
    incremental add, matching how rag/index_builder.py already works.

    Scanned/image-only PDFs are OCR'd automatically per-page during loading
    (loaders/pdf_loader.py -> core/ocr.py) — no separate OCR pass or
    progress callback needed; a page falls back to OCR only when its native
    text extraction is too short to be usable.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    entry = doc_sessions.get_or_create(browser_session_id)

    results: list[UploadedFileResult] = []
    for f in files:
        try:
            content = await f.read()
            if not content:
                results.append(UploadedFileResult(filename=f.filename, status="failed", detail="Empty file."))
                continue
            if len(content) > MAX_UPLOAD_BYTES:
                results.append(
                    UploadedFileResult(
                        filename=f.filename,
                        status="failed",
                        detail=f"File exceeds the {MAX_UPLOAD_MB:g} MB upload limit.",
                    )
                )
                continue
            kb.save_uploaded_file(f.filename, content, data_dir=entry["data_dir"])
            results.append(UploadedFileResult(filename=f.filename, status="indexed"))
        except ValueError as e:
            results.append(UploadedFileResult(filename=f.filename, status="failed", detail=str(e)))
        except Exception as e:
            logger.exception("Failed to save uploaded file %s", f.filename)
            results.append(UploadedFileResult(filename=f.filename, status="failed", detail=str(e)))

    if any(r.status == "indexed" for r in results):
        # Serializes this session's own rebuilds so two near-simultaneous
        # uploads to the SAME session can't race on the same FAISS folder.
        # Never blocks a different session (each has its own lock).
        with entry["lock"]:
            try:
                kb.rebuild_knowledge_base(data_dir=entry["data_dir"], vector_db_path=entry["vector_db_path"])
                entry["retriever"] = kb.load_retriever_if_ready(vector_db_path=entry["vector_db_path"])
                entry["kb_version"] += 1
            except Exception as e:
                logger.exception("Failed to rebuild the knowledge base after upload.")
                # The files were saved but indexing failed — report that clearly
                # rather than claiming success.
                for r in results:
                    if r.status == "indexed":
                        r.status = "failed"
                        r.detail = f"Saved but indexing failed: {e}"

    return UploadResponse(files=results, kb_ready=entry["retriever"] is not None)


# ==============================================================================
# Document library
# ==============================================================================


@app.get("/api/documents", response_model=DocumentListResponse)
def list_documents(browser_session_id: str = Depends(_resolve_session_id)) -> DocumentListResponse:
    entry = doc_sessions.get_or_create(browser_session_id)
    docs = doc_lib.list_documents(entry["retriever"], data_dir=entry["data_dir"])
    return DocumentListResponse(documents=[DocumentSummary(**d) for d in docs])


@app.delete("/api/documents/{document_id}", response_model=DeleteDocumentResponse)
def delete_document(document_id: str, browser_session_id: str = Depends(_resolve_session_id)) -> DeleteDocumentResponse:
    entry = doc_sessions.get_or_create(browser_session_id)
    _require_document(document_id, entry["data_dir"])
    with entry["lock"]:
        deleted = kb.delete_uploaded_file(document_id, data_dir=entry["data_dir"])
        try:
            kb.rebuild_knowledge_base(data_dir=entry["data_dir"], vector_db_path=entry["vector_db_path"])
            entry["retriever"] = kb.load_retriever_if_ready(vector_db_path=entry["vector_db_path"])
            entry["kb_version"] += 1
        except Exception:
            logger.exception("Failed to rebuild the knowledge base after deleting %s", document_id)
            raise HTTPException(
                status_code=500,
                detail=f"'{document_id}' was deleted but the knowledge base failed to rebuild — try re-uploading.",
            )
    return DeleteDocumentResponse(document_id=document_id, deleted=deleted, kb_ready=entry["retriever"] is not None)


# ==============================================================================
# Summarization & flashcards — reuse the same per-session retriever/index as
# /query, scoped to one document via document_filter (core.rag_engine),
# never a separate ingestion or retrieval path.
# ==============================================================================


@app.post("/api/documents/{document_id}/summarize", response_model=SummarizeResponse)
def summarize_document(
    document_id: str,
    request: SummarizeRequest = SummarizeRequest(),
    browser_session_id: str = Depends(_resolve_session_id),
) -> SummarizeResponse:
    entry = doc_sessions.get_or_create(browser_session_id)
    retriever, llm = _ensure_session_kb_and_llm(browser_session_id)
    _require_document(document_id, entry["data_dir"])
    if not doc_lib.document_exists_in_index(retriever, document_id):
        raise HTTPException(status_code=422, detail=f"'{document_id}' hasn't finished indexing yet — try again shortly.")

    detail = request.detail if request.detail in ("short", "detailed") else "short"
    try:
        summary = summarize_documents(llm, retriever, document_filter=document_id, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=friendly_llm_error(e))

    return SummarizeResponse(document_id=document_id, summary=summary, detail=detail)


@app.post("/api/documents/{document_id}/flashcards", response_model=FlashcardsResponse)
def flashcards_for_document(
    document_id: str,
    request: FlashcardsRequest = FlashcardsRequest(),
    browser_session_id: str = Depends(_resolve_session_id),
) -> FlashcardsResponse:
    entry = doc_sessions.get_or_create(browser_session_id)
    retriever, llm = _ensure_session_kb_and_llm(browser_session_id)
    _require_document(document_id, entry["data_dir"])
    if not doc_lib.document_exists_in_index(retriever, document_id):
        raise HTTPException(status_code=422, detail=f"'{document_id}' hasn't finished indexing yet — try again shortly.")

    try:
        cards = generate_flashcards(llm, retriever, num_cards=request.num_cards, document_filter=document_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=friendly_llm_error(e))

    return FlashcardsResponse(document_id=document_id, flashcards=[Flashcard(**c) for c in cards])


@app.get("/api/documents/{document_id}/summary/export", response_class=PlainTextResponse)
def export_summary(document_id: str, detail: str = "short", browser_session_id: str = Depends(_resolve_session_id)):
    entry = doc_sessions.get_or_create(browser_session_id)
    retriever, llm = _ensure_session_kb_and_llm(browser_session_id)
    _require_document(document_id, entry["data_dir"])
    try:
        summary = summarize_documents(llm, retriever, document_filter=document_id, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=friendly_llm_error(e))
    md = f"# Summary — {document_id}\n\n{summary}\n"
    return PlainTextResponse(md, media_type="text/markdown")


@app.get("/api/documents/{document_id}/flashcards/export", response_class=PlainTextResponse)
def export_flashcards(document_id: str, num_cards: int = 8, browser_session_id: str = Depends(_resolve_session_id)):
    entry = doc_sessions.get_or_create(browser_session_id)
    retriever, llm = _ensure_session_kb_and_llm(browser_session_id)
    _require_document(document_id, entry["data_dir"])
    try:
        cards = generate_flashcards(llm, retriever, num_cards=num_cards, document_filter=document_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=friendly_llm_error(e))
    lines = [f"# Flashcards — {document_id}\n"]
    for i, c in enumerate(cards, start=1):
        lines.append(f"## {i}. {c['question']}\n\n{c['answer']}\n")
    return PlainTextResponse("\n".join(lines), media_type="text/markdown")


# ==============================================================================
# Multi-session chat — in-memory (see core/sessions.py for why: no database
# exists in this project, so this is a documented, scoped limitation, not
# an oversight). Each session's messages are isolated by session_id; /query
# writes into a session only when the caller passes session_id explicitly.
#
# This is the CHAT conversation session concept — unrelated to the
# X-Session-Id browser session above (a single browser session can create
# many of these). Left entirely unchanged by the document/RAG isolation
# work.
# ==============================================================================


@app.post("/api/sessions", response_model=SessionDetail)
def create_session(request: SessionCreateRequest = SessionCreateRequest()) -> SessionDetail:
    session = session_lib.store.create(title=request.title)
    return SessionDetail(**session)


@app.get("/api/sessions", response_model=SessionListResponse)
def list_sessions() -> SessionListResponse:
    sessions = session_lib.store.list()
    return SessionListResponse(
        sessions=[
            SessionSummary(
                session_id=s["session_id"],
                title=s["title"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
                message_count=len(s["messages"]),
            )
            for s in sessions
        ]
    )


@app.get("/api/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str) -> SessionDetail:
    session = session_lib.store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"No chat session found with id '{session_id}'.")
    return SessionDetail(**session)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    if not session_lib.store.delete(session_id):
        raise HTTPException(status_code=404, detail=f"No chat session found with id '{session_id}'.")
    return {"session_id": session_id, "deleted": True}


@app.get("/api/sessions/{session_id}/export", response_class=PlainTextResponse)
def export_session(session_id: str):
    session = session_lib.store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"No chat session found with id '{session_id}'.")

    lines = [f"# {session['title']}\n"]
    for m in session["messages"]:
        speaker = "**You**" if m["role"] == "user" else "**Assistant**"
        lines.append(f"{speaker}: {m['content']}\n")
        sources = m.get("sources")
        if sources:
            unique = sorted({s.get("source", "Unknown") for s in sources})
            lines.append("_Sources: " + ", ".join(unique) + "_\n")
    return PlainTextResponse("\n".join(lines), media_type="text/markdown")
