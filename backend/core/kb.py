"""Shared knowledge-base bootstrap.

Builds the FAISS index from data/ if it doesn't exist yet, and hands back a
retriever. Used by the FastAPI service at startup; the same
build-if-missing behavior app.py's CLI already used, just factored out so
it isn't reimplemented a third time.

Every function here defaults to the project's original global paths
(DATA_DIR / VECTOR_DB_PATH), so app.py — which calls these with no
arguments — behaves exactly as before. The FastAPI backend
now passes an explicit, per-browser-session data_dir/vector_db_path (see
core/sessions.py's DocumentSessionStore and api/main.py) so each browser
session reads and writes its own upload folder and its own FAISS index,
never another session's.
"""

import shutil
from pathlib import Path
from typing import List, Optional

from utils.file_scanner import SUPPORTED_EXTENSIONS, scan_folder
from rag.index_builder import build_vector_store
from rag.retriever import get_retriever

VECTOR_DB_PATH = Path("database/faiss_index")
DATA_DIR = Path("data")


def kb_exists(vector_db_path: Optional[Path] = None) -> bool:
    return (vector_db_path or VECTOR_DB_PATH).exists()


def ensure_knowledge_base(data_dir: Path = DATA_DIR, vector_db_path: Optional[Path] = None) -> bool:
    """Builds the FAISS index from data_dir if it doesn't exist yet and
    data_dir has at least one file. Returns True if a usable index exists
    afterward (either already did, or was just built)."""
    path = vector_db_path or VECTOR_DB_PATH
    if kb_exists(path):
        return True
    if not data_dir.exists() or not any(data_dir.iterdir()):
        return False
    build_vector_store(data_dir=str(data_dir), vector_db_path=path)
    return kb_exists(path)


def load_retriever_if_ready(vector_db_path: Optional[Path] = None):
    """Returns a retriever if the FAISS index exists, else None."""
    path = vector_db_path or VECTOR_DB_PATH
    if not kb_exists(path):
        return None
    return get_retriever(vector_db_path=path)


def save_uploaded_file(filename: str, content: bytes, data_dir: Path = DATA_DIR) -> Path:
    """Writes an uploaded file's bytes into data_dir (creating it if needed)
    so it's picked up by the existing scan_folder()/build_vector_store()
    pipeline exactly like a file placed there manually. Rejects unsupported
    extensions up front instead of letting a silent no-op through
    build_vector_store()."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / Path(filename).name
    dest.write_bytes(content)
    return dest


def list_uploaded_files(data_dir: Path = DATA_DIR) -> List[Path]:
    """Every currently-uploaded, supported file — the document library's
    source of truth. There's no database in this project, so "what
    documents exist" is simply "what's in data/", same as scan_folder()
    already used by the indexing pipeline."""
    if not data_dir.exists():
        return []
    return sorted(scan_folder(str(data_dir)), key=lambda p: p.name.lower())


def delete_uploaded_file(document_id: str, data_dir: Path = DATA_DIR) -> bool:
    """Removes one uploaded file by document_id (== filename). Returns False
    if it didn't exist. Does NOT rebuild the index — callers that want the
    change reflected in retrieval must call rebuild_knowledge_base()
    afterward, same as the upload endpoint already does; kept separate so a
    delete that only touches data/ (e.g. for a dry run) doesn't force a
    rebuild by itself."""
    target = data_dir / Path(document_id).name
    if not target.exists() or not target.is_file():
        return False
    target.unlink()
    return True


def rebuild_knowledge_base(data_dir: Path = DATA_DIR, vector_db_path: Optional[Path] = None) -> bool:
    """Deletes the existing FAISS index (if any) and rebuilds it from
    whatever is currently in data_dir, via the same build_vector_store() the
    CLI (app.py) already uses — no second RAG pipeline. Returns True if a
    usable index exists afterward."""
    path = vector_db_path or VECTOR_DB_PATH
    if path.exists():
        shutil.rmtree(path)
    build_vector_store(data_dir=str(data_dir), vector_db_path=path)
    return kb_exists(path)
