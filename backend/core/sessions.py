"""
In-memory multi-session chat store.

This project has no database (a scope decision that predates this session
— see README), so sessions live in process memory and reset on backend
restart. That is an explicit, documented limitation, not an oversight: it's
the pragmatic scope for a project this size, while still giving the React
frontend genuine multi-session isolation — separate histories, separate
titles, one session's messages never leaking into another's retrieval or
display — for as long as the process runs.

Thread-safe (a plain dict + lock) because FastAPI can run sync path
operations from a thread pool concurrently.

Also holds DocumentSessionStore (below), added here rather than as a
separate session-storage mechanism elsewhere: it needs exactly the same
thing SessionStore already provides (a thread-safe, process-wide, in-memory
registry keyed by an opaque id), just for a different concept. SessionStore
is per-CHAT-CONVERSATION message history (many can exist per browser visit
— see the sidebar's session list). DocumentSessionStore is per-BROWSER-
SESSION (one page load) document/RAG state: which files were uploaded and
which FAISS/BM25 index to search. They are deliberately kept as two
separate stores/ids rather than merged, because their lifetimes differ
(one browser session can hold many chat conversations).
"""

import re
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


class SessionStore:
    def __init__(self):
        self._lock = Lock()
        self._sessions: Dict[str, dict] = {}

    def create(self, title: Optional[str] = None) -> dict:
        session_id = uuid.uuid4().hex
        now = time.time()
        session = {
            "session_id": session_id,
            "title": title or "New chat",
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[dict]:
        with self._lock:
            return self._sessions.get(session_id)

    def list(self) -> List[dict]:
        with self._lock:
            return sorted(self._sessions.values(), key=lambda s: s["updated_at"], reverse=True)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def add_message(self, session_id: str, role: str, content: str, extra: Optional[dict] = None) -> Optional[dict]:
        """Appends one message to one session only — sessions are separate
        dicts keyed by session_id, so there is no code path by which a
        message written here could end up visible from another session_id."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            message = {"role": role, "content": content, "timestamp": time.time()}
            if extra:
                message.update(extra)
            session["messages"].append(message)
            session["updated_at"] = message["timestamp"]
            if session["title"] == "New chat" and role == "user":
                session["title"] = (content[:60] + "…") if len(content) > 60 else content
            return session

    def rename(self, session_id: str, title: str) -> Optional[dict]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session["title"] = title
            return session

    def history_for_prompt(self, session_id: str) -> List[dict]:
        """Returns this session's messages in the {role, content} shape
        build_conversation_memory() expects — never another session's."""
        session = self.get(session_id)
        if session is None:
            return []
        return [{"role": m["role"], "content": m["content"]} for m in session["messages"]]


# Single process-wide store, mirroring how core/rag_engine.py's BM25 cache
# and the API's `state` dict are also process-wide singletons — consistent
# with this project's no-database, single-process scope.
store = SessionStore()


# ==============================================================================
# Per-browser-session document/RAG isolation
# ==============================================================================

# Frontend-generated ids (see frontend/src/utils/browserSession.js) are
# opaque strings used directly as folder names on disk (see
# DocumentSessionStore._paths_for below), so they're validated up front —
# this is the one place a client-supplied value becomes a filesystem path,
# and this regex is what keeps a hostile id from escaping the sessions
# folder (no "..", "/", or other path-control characters).
_DOCUMENT_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def is_valid_document_session_id(session_id: Optional[str]) -> bool:
    return bool(session_id) and bool(_DOCUMENT_SESSION_ID_RE.match(session_id))


class DocumentSessionStore:
    """In-memory registry of per-browser-session document/RAG state.

    Each entry gets its OWN upload folder and its OWN FAISS index folder
    (data/_sessions/<id>/, database/_sessions/<id>/faiss_index/), built and
    read through core/kb.py's path-parameterized functions — the exact same
    ingestion/chunking/embedding/FAISS/BM25 pipeline the rest of the app
    already uses, just pointed at a different folder per session. Nothing
    about the RAG pipeline itself changes.

    Retrieval isolation for BM25 falls out of this for free: core/rag_engine.py
    caches BM25 indexes keyed by `id(retriever)` (Python object identity).
    Since every session gets its own freshly-loaded retriever object (from
    its own FAISS folder), two sessions can never share a BM25 cache entry —
    no change to rag_engine.py was needed or made.

    Concurrency: a top-level lock guards the registry dict itself (fast:
    just "does this session exist yet"); each session also gets its OWN
    lock, used by the API layer to serialize that session's own
    upload/delete/rebuild operations, so two concurrent uploads to the SAME
    session can't race on the same on-disk FAISS folder. Different sessions
    never block each other.

    Cloud Run limitation (documented, not solved — see README): this is
    process-local memory, exactly like SessionStore above. It's correct for
    a single always-on backend instance, but if Cloud Run ever scales this
    service to multiple concurrent instances with no session affinity, a
    browser session's requests could land on different instances that don't
    share this dict, and each would see that session as brand new. Session
    isolation BETWEEN users/tabs still holds in that scenario (no
    cross-session data leak) — what breaks is continuity: the same
    session's own uploads might not consistently show up. True multi-
    instance safety would need a shared store (e.g. a database or object
    storage keyed by session id), which is intentionally out of scope here
    per the "no database unless absolutely necessary" brief.
    """

    def __init__(self, base_data_dir: Path, base_db_dir: Path):
        self._lock = Lock()
        self._sessions: Dict[str, dict] = {}
        self._base_data_dir = base_data_dir
        self._base_db_dir = base_db_dir

    def _paths_for(self, session_id: str):
        data_dir = self._base_data_dir / session_id
        vector_db_path = self._base_db_dir / session_id / "faiss_index"
        return data_dir, vector_db_path

    def get_or_create(self, session_id: str) -> dict:
        """Returns this session's state dict, creating it (with fresh,
        empty paths and a zero kb_version — i.e. "0 documents") on first
        use. This is what makes a brand-new session_id start at zero
        without any explicit "create session" call from the frontend."""
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                data_dir, vector_db_path = self._paths_for(session_id)
                entry = {
                    "session_id": session_id,
                    "data_dir": data_dir,
                    "vector_db_path": vector_db_path,
                    "retriever": None,
                    "kb_version": 0,
                    "lock": Lock(),
                }
                self._sessions[session_id] = entry
            return entry

    def peek(self, session_id: str) -> Optional[dict]:
        """Like get_or_create, but never creates one — used by /health so a
        session that has never made a real request doesn't get a disk
        folder just from a health poll."""
        with self._lock:
            return self._sessions.get(session_id)


# Base folders kept alongside (as subfolders of) the project's existing
# global data/database folders rather than somewhere new, so the same
# docker-compose volume mounts (./data:/app/data, ./database:/app/database)
# already persist them without any docker-compose.yml change.
doc_sessions = DocumentSessionStore(
    base_data_dir=Path("data") / "_sessions",
    base_db_dir=Path("database") / "_sessions",
)
