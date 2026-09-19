"""
Chunking utilities using LangChain.

_get_recursive_character_text_splitter() below deliberately avoids a plain
`from langchain_text_splitters import RecursiveCharacterTextSplitter`.
langchain_text_splitters' own __init__.py unconditionally imports EVERY
splitter it ships — including SentenceTransformersTokenTextSplitter,
NLTKTextSplitter, and SpacyTextSplitter — which pull in
sentence-transformers/torch/nltk/spacy as a side effect of importing the
PACKAGE at all, even though this project only ever uses
RecursiveCharacterTextSplitter (pure Python, no ML dependency of its own).
Measured impact: a plain top-level import of langchain_text_splitters adds
roughly 800+ MB of resident memory — comparable to loading the embedding
model itself — every single time a document is chunked, which was a large
part of what was pushing this backend over Render Free's memory limit.

The real, unmodified langchain_text_splitters.character module (which only
needs langchain_text_splitters.base, `re`, and `typing` — nothing ML-
related) is imported directly, bypassing the package's own __init__.py, by
registering a lightweight placeholder for the langchain_text_splitters
PACKAGE in sys.modules first. A package's __init__.py only runs once per
process, the first time anything imports that package name; if it's
already present in sys.modules (our placeholder), Python skips straight to
locating and importing the requested submodule instead, so
RecursiveCharacterTextSplitter's actual behavior is completely unchanged —
only which of its sibling splitters get pulled in along with it is
affected. If anything about this ever breaks (e.g. a future
langchain_text_splitters release restructures character.py's own
imports), it falls back to the normal, heavier import so chunking never
silently fails.
"""

import logging
import sys

logger = logging.getLogger(__name__)
logger.debug("Using chunking.py from: %s", __file__)

_RecursiveCharacterTextSplitter = None


def _get_recursive_character_text_splitter():
    global _RecursiveCharacterTextSplitter
    if _RecursiveCharacterTextSplitter is not None:
        return _RecursiveCharacterTextSplitter

    if "langchain_text_splitters" in sys.modules:
        # Something else already fully imported the real package (and
        # already paid its eager-import cost) — just use it normally.
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        _RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
        return _RecursiveCharacterTextSplitter

    try:
        import types
        import importlib.util

        real_spec = importlib.util.find_spec("langchain_text_splitters")
        placeholder = types.ModuleType("langchain_text_splitters")
        placeholder.__path__ = real_spec.submodule_search_locations
        placeholder.__spec__ = real_spec
        sys.modules["langchain_text_splitters"] = placeholder

        from langchain_text_splitters.character import RecursiveCharacterTextSplitter
    except Exception:
        logger.warning(
            "Lightweight RecursiveCharacterTextSplitter import failed — "
            "falling back to the normal langchain_text_splitters import.",
            exc_info=True,
        )
        sys.modules.pop("langchain_text_splitters", None)
        from langchain_text_splitters import RecursiveCharacterTextSplitter

    _RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
    return _RecursiveCharacterTextSplitter


def split_documents(documents):
    """
    Splits LangChain Document objects into smaller chunks.

    Each source Document's metadata (document_id, source, file_type, page,
    ocr) is inherited automatically by every chunk produced from it —
    that's LangChain's own splitter behavior. On top of that, this adds a
    per-chunk chunk_id (stable within one chunking run) so a specific chunk
    can be identified in source attribution independently of its parent
    document/page.

    Args:
        documents (list): List of LangChain Document objects

    Returns:
        list: List of chunked LangChain Document objects
    """

    logger.debug("split_documents() called with %d documents", len(documents))

    RecursiveCharacterTextSplitter = _get_recursive_character_text_splitter()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    chunks = splitter.split_documents(documents)

    # chunk_id is scoped per document_id (falling back to source) so it
    # reads naturally as "chunk 3 of this document" rather than a single
    # index across every document in the whole knowledge base.
    counters = {}
    for chunk in chunks:
        doc_key = chunk.metadata.get("document_id") or chunk.metadata.get("source") or "unknown"
        idx = counters.get(doc_key, 0)
        chunk.metadata["chunk_id"] = f"{doc_key}::chunk_{idx}"
        counters[doc_key] = idx + 1

    logger.debug("Created %d chunks from %d documents", len(chunks), len(documents))

    return chunks
