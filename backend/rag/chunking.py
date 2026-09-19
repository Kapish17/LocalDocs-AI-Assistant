"""
Chunking utilities using LangChain.
"""

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)
logger.debug("Using chunking.py from: %s", __file__)


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
