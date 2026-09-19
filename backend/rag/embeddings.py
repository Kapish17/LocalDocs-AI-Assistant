"""
Embedding model access.

get_embedding_model() is called every time a knowledge base is built or
loaded (rag/vector_store.py's create_vector_store, rag/retriever.py's
load_vector_store) — which happens per browser session, and, on every
single /upload request, TWICE in a row (rebuild_knowledge_base() followed
immediately by load_retriever_if_ready(), see backend/core/kb.py). Without
caching, each of those calls used to construct a brand-new
HuggingFaceEmbeddings instance, which loads the full BAAI/bge-small-en-v1.5
sentence-transformer (and, transitively, torch) from disk into memory from
scratch — multiplying memory usage per request and per session, which is
what was pushing this backend over Render Free's memory limit.

Fixed with a process-wide lazy singleton: the model is loaded at most once
per process, the first time it's actually needed (not at FastAPI import/
startup time — the heavy `langchain_huggingface` import itself is done
inside this function, not at module level, so it isn't pulled in until
then either), and every subsequent call — across every browser session and
every build/load — reuses that same in-memory model instead of loading a
new copy.
"""

from threading import Lock

_model = None
_model_lock = Lock()


def get_embedding_model():
    """
    Returns the shared local HuggingFace embedding model, creating it once
    on first use (never at import time) and reusing that same instance for
    every caller/session thereafter.
    """
    global _model

    if _model is None:
        with _model_lock:
            # Re-check inside the lock: two near-simultaneous callers could
            # both have seen _model as None before either acquired it.
            if _model is None:
                # Imported here, not at module level, so this (and its
                # heavy transitive imports — sentence-transformers, torch)
                # isn't loaded into memory until an embedding model is
                # actually needed, not just because this module was
                # imported (e.g. at FastAPI startup via core.kb).
                from langchain_huggingface import HuggingFaceEmbeddings

                _model = HuggingFaceEmbeddings(
                    model_name="BAAI/bge-small-en-v1.5",
                    # Explicit CPU-only inference — Render Free has no GPU,
                    # and being explicit avoids any device-probing overhead
                    # (e.g. a CUDA availability check) at load time.
                    model_kwargs={"device": "cpu"},
                )

    return _model
