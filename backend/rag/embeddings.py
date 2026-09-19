"""
Embedding model access.

Two interchangeable backends, selected by the EMBEDDING_PROVIDER env var:

- "remote" (the default): calls Hugging Face Inference Providers' hosted
  feature-extraction API for BAAI/bge-small-en-v1.5 (HF_EMBEDDING_MODEL) to
  turn text into vectors. No model weights, PyTorch, or sentence-
  transformers are loaded into THIS process at all — that's what lets the
  backend fit inside Render Free's 512 MB memory limit; running the exact
  same BGE model locally needed close to 1 GB resident once its own eager
  imports were fixed, because torch + sentence-transformers themselves are
  that large regardless of caching.
- "local": the original implementation — loads BAAI/bge-small-en-v1.5
  locally via langchain_huggingface's HuggingFaceEmbeddings (sentence-
  transformers + PyTorch, CPU-only). Kept as an explicit opt-in for local
  development on a machine with plenty of RAM that would rather not depend
  on an external API / HF token — set EMBEDDING_PROVIDER=local. Needs the
  extra sentence-transformers/torch dependencies in backend/requirements.txt
  (not installed in the slim Docker/Render image — see requirements-docker.txt).

Either way, get_embedding_model() returns a process-wide singleton
implementing LangChain's Embeddings interface (embed_documents /
embed_query), so rag/vector_store.py, rag/retriever.py, and FAISS itself
need no changes at all — they only ever call get_embedding_model(), and
every call/session/build reuses the same one instance, so the embedding
dimension used to build a FAISS index and the dimension used to query it
always match (see _RemoteHFEmbeddings._check_dimension for what happens if
that were ever violated mid-process).
"""

import logging
import os
from threading import Lock
from typing import List, Optional

from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

DEFAULT_HF_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Texts are sent to the Hugging Face API in batches of this size rather
# than all at once — keeps a single request small/fast (friendlier to the
# provider's own limits) and means one oversized document doesn't risk a
# single huge, slow, all-or-nothing call.
_REMOTE_BATCH_SIZE = 32


class EmbeddingConfigError(RuntimeError):
    """Raised when the embedding backend is misconfigured (missing
    HF_TOKEN, unknown EMBEDDING_PROVIDER, unavailable model) — a clear,
    actionable error instead of ever silently falling back to fake
    embeddings."""


class EmbeddingServiceError(RuntimeError):
    """Raised when a remote embedding call itself fails at request time
    (Hugging Face API error, timeout, rate/credit exhaustion). Callers
    (core/kb.py, core/rag_engine.py) already propagate exceptions from
    this layer as a clean 5xx to the frontend, exactly like a Gemini
    failure — never substitute a fake/zero vector here."""


class _RemoteHFEmbeddings(Embeddings):
    """Calls Hugging Face Inference Providers' feature-extraction API
    instead of running a model locally. Implements LangChain's Embeddings
    interface so it's a drop-in replacement for HuggingFaceEmbeddings
    everywhere in this codebase (FAISS, retriever, vector_store all only
    ever call embed_documents/embed_query)."""

    def __init__(self, model: str, token: str, timeout: float = 30.0):
        from huggingface_hub import InferenceClient

        self._model = model
        self._client = InferenceClient(model=model, token=token, timeout=timeout)
        self._dimension: Optional[int] = None
        # feature_extraction()'s own thread-safety isn't documented, and
        # concurrent session uploads could call this from multiple FastAPI
        # threads at once — serialize actual network calls rather than
        # risk a race in the underlying HTTP client.
        self._call_lock = Lock()

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

        try:
            with self._call_lock:
                result = self._client.feature_extraction(text=texts, normalize=True)
        except InferenceTimeoutError as e:
            raise EmbeddingServiceError(
                f"Hugging Face embedding request timed out for model '{self._model}'. "
                "The model may be cold-starting on the provider's infrastructure — "
                "retrying shortly usually resolves this."
            ) from e
        except HfHubHTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 401:
                raise EmbeddingConfigError(
                    "Hugging Face rejected HF_TOKEN (401 Unauthorized). Check that "
                    "HF_TOKEN is set and has 'Inference Providers' permission — see "
                    "https://huggingface.co/settings/tokens."
                ) from e
            if status == 404:
                raise EmbeddingConfigError(
                    f"Hugging Face model '{self._model}' was not found, or isn't "
                    "deployed for feature-extraction inference. Check HF_EMBEDDING_MODEL."
                ) from e
            if status == 429:
                raise EmbeddingServiceError(
                    "Hugging Face rate-limited this request or this token's "
                    "inference credits are exhausted (429). Wait and retry, or "
                    "upgrade your Hugging Face plan."
                ) from e
            raise EmbeddingServiceError(
                f"Hugging Face embedding request failed "
                f"({status if status is not None else 'unknown status'}): {e}"
            ) from e
        except EmbeddingConfigError:
            raise
        except Exception as e:
            # Network errors and anything else unanticipated — surfaced
            # clearly rather than swallowed or turned into a fake vector.
            raise EmbeddingServiceError(f"Hugging Face embedding request failed: {e}") from e

        vectors = [[float(x) for x in row] for row in result]
        self._check_dimension(vectors)
        return vectors

    def _check_dimension(self, vectors: List[List[float]]) -> None:
        if not vectors:
            return
        width = len(vectors[0])
        if self._dimension is None:
            self._dimension = width
            logger.info("Remote HF embedding model '%s' dimension: %d", self._model, width)
        elif width != self._dimension:
            # A model/provider swap mid-process would silently corrupt any
            # FAISS index already built at the old dimension — fail loudly
            # instead of writing mismatched vectors into it.
            raise EmbeddingServiceError(
                f"Hugging Face model '{self._model}' returned a {width}-dimension "
                f"vector, but this process already built embeddings at "
                f"{self._dimension} dimensions. Restart the backend after changing "
                "HF_EMBEDDING_MODEL — a running process can't safely mix dimensions."
            )

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors: List[List[float]] = []
        for i in range(0, len(texts), _REMOTE_BATCH_SIZE):
            vectors.extend(self._embed_batch(texts[i : i + _REMOTE_BATCH_SIZE]))
        return vectors

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(list(texts))

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]


def _build_remote_embeddings() -> Embeddings:
    token = os.getenv("HF_TOKEN")
    if not token:
        raise EmbeddingConfigError(
            "EMBEDDING_PROVIDER=remote (the default) requires HF_TOKEN to be set — "
            "a Hugging Face access token with 'Inference Providers' permission. Get "
            "one at https://huggingface.co/settings/tokens, then set it in "
            "backend/.env (local) or as a Render environment variable (production). "
            "Alternatively, set EMBEDDING_PROVIDER=local to use a local embedding "
            "model instead (requires the sentence-transformers/torch dependencies "
            "in backend/requirements.txt, not installed in the Docker/Render image)."
        )
    model = os.getenv("HF_EMBEDDING_MODEL", DEFAULT_HF_EMBEDDING_MODEL)
    timeout = float(os.getenv("HF_EMBEDDING_TIMEOUT", "30"))
    logger.info("Using remote Hugging Face embeddings: model=%s", model)
    return _RemoteHFEmbeddings(model=model, token=token, timeout=timeout)


def _build_local_embeddings() -> Embeddings:
    # Imported here, not at module level, so this (and its heavy
    # transitive imports — sentence-transformers, torch) isn't loaded into
    # memory unless EMBEDDING_PROVIDER=local is explicitly chosen.
    from langchain_huggingface import HuggingFaceEmbeddings

    model = os.getenv("HF_EMBEDDING_MODEL", DEFAULT_HF_EMBEDDING_MODEL)
    logger.info("Using local Hugging Face embeddings: model=%s", model)
    return HuggingFaceEmbeddings(
        model_name=model,
        # Explicit CPU-only inference — Render Free has no GPU, and being
        # explicit avoids any device-probing overhead at load time.
        model_kwargs={"device": "cpu"},
    )


_model: Optional[Embeddings] = None
_model_lock = Lock()


def get_embedding_model() -> Embeddings:
    """
    Returns the shared embedding model (remote or local, per
    EMBEDDING_PROVIDER), creating it once on first use — never at import
    time — and reusing that same instance for every caller/session
    thereafter.
    """
    global _model

    if _model is None:
        with _model_lock:
            # Re-check inside the lock: two near-simultaneous callers could
            # both have seen _model as None before either acquired it.
            if _model is None:
                provider = os.getenv("EMBEDDING_PROVIDER", "remote").strip().lower()
                if provider == "remote":
                    _model = _build_remote_embeddings()
                elif provider == "local":
                    _model = _build_local_embeddings()
                else:
                    raise EmbeddingConfigError(
                        f"Unknown EMBEDDING_PROVIDER '{provider}' — expected "
                        "'remote' or 'local'."
                    )

    return _model
