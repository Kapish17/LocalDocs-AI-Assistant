"""
Document-library helpers: listing uploaded documents with per-document
stats (page count, chunk count, indexed status) and locating one document
by id for the delete/summarize/flashcards endpoints.

Kept separate from core/rag_engine.py (which stays focused on retrieval and
generation) and from core/kb.py (file storage / index (re)build) — this
module is the thin layer that combines "what files exist" (kb.py) with
"what's actually indexed for each of them" (rag_engine.get_all_docs) into
the shape the API/React document library needs. No new pipeline is
introduced; it only reads what ingestion/indexing already produced.

There's no database in this project, so document_id is the filename (see
loaders/*.py) and "what documents exist" is simply "what's in data/".
"""

from pathlib import Path
from typing import List, Optional

from core import kb
from core.rag_engine import get_all_docs


def list_documents(retriever, data_dir: Path = kb.DATA_DIR) -> List[dict]:
    """One summary dict per uploaded file, combining filesystem facts
    (size, upload time) with whatever is currently indexed for that
    document (chunk count, highest page number seen). A file can exist but
    not (yet) be indexed — e.g. right after upload if a rebuild failed —
    which is surfaced via `indexed: False` rather than hidden."""
    files = kb.list_uploaded_files(data_dir)

    indexed_chunks = get_all_docs(retriever) if retriever is not None else []
    by_doc: dict = {}
    for chunk in indexed_chunks:
        doc_id = chunk.metadata.get("document_id") or chunk.metadata.get("source")
        by_doc.setdefault(doc_id, []).append(chunk)

    summaries = []
    for f in files:
        doc_id = f.name
        chunks = by_doc.get(doc_id, [])
        pages = [c.metadata.get("page") for c in chunks if c.metadata.get("page") is not None]
        try:
            stat = f.stat()
            size_bytes = stat.st_size
            uploaded_at = stat.st_mtime
        except OSError:
            size_bytes = 0
            uploaded_at = None

        summaries.append(
            {
                "document_id": doc_id,
                "filename": f.name,
                "file_type": f.suffix.lower().lstrip("."),
                "size_bytes": size_bytes,
                "uploaded_at": uploaded_at,
                "indexed": len(chunks) > 0,
                "num_chunks": len(chunks),
                "num_pages": max(pages) if pages else None,
            }
        )
    return summaries


def find_document_path(document_id: str, data_dir: Path = kb.DATA_DIR) -> Optional[Path]:
    """Resolves a document_id to its file on disk, or None if it doesn't
    exist — used to 404 cleanly instead of trusting a client-supplied id."""
    candidate = data_dir / Path(document_id).name
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def document_exists_in_index(retriever, document_id: str) -> bool:
    """True if at least one indexed chunk belongs to this document — used to
    give a clear "not indexed yet" error for summarize/flashcards instead of
    silently returning an empty result."""
    if retriever is None:
        return False
    chunks = get_all_docs(retriever, document_filter=document_id)
    return len(chunks) > 0
