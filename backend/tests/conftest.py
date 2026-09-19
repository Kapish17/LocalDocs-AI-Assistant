"""
Test-only stubs so this suite can run without the real embedding model or
Gemini client (both need network access / GPU-class dependencies this test
environment doesn't have, and aren't what this suite is testing anyway —
it's testing SESSION ISOLATION, i.e. which folder/FAISS index a request
reads and writes, not embedding quality or Gemini output quality).

Both stubs are installed into sys.modules BEFORE anything imports
rag.vector_store / rag.retriever / core.rag_engine, which each do
`from rag.embeddings import get_embedding_model` / `from llm.gemini import
get_llm` at their own module import time — this is the standard way to
swap a dependency for real code that does a top-level `from X import Y`,
without touching any of that real code.

The embedding stub is a deterministic bag-of-words vectorizer (not random)
so FAISS's own similarity math is exercised for real — just without a
multi-hundred-MB model download. Combined with the real, unmodified
BM25/hybrid_search/chunking/FAISS code, this reproduces the real retrieval
pipeline closely enough to prove session isolation, which is what these
tests check.
"""

import sys
import types
import hashlib
from pathlib import Path

import pytest

# So `import api.main` / `from core import ...` etc. resolve the same way
# api/main.py itself makes them resolve (backend/ on sys.path), regardless
# of which directory `pytest` is invoked from.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_EMBED_DIM = 64


def _fake_embed(text: str):
    """A small, deterministic, non-random vector: every word contributes to
    a few fixed dimensions (via a stable hash), so texts sharing words end
    up with more similar vectors than texts that don't — enough signal for
    FAISS similarity search to behave sensibly in tests without a real
    model."""
    vec = [0.0] * _EMBED_DIM
    for word in text.lower().split():
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        vec[h % _EMBED_DIM] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


from langchain_core.embeddings import Embeddings


class FakeEmbeddings(Embeddings):
    """Subclasses langchain_core's real Embeddings ABC (not just duck-typed)
    so FAISS/langchain_community treat it as a first-class embeddings
    object rather than falling back to a degraded "bare callable" code
    path — a bare object without this base class produced spurious
    "embedding_function is expected to be an Embeddings object" warnings
    and broken query-time retrieval when this was tried without it."""

    def embed_documents(self, texts):
        return [_fake_embed(t) for t in texts]

    def embed_query(self, text):
        return _fake_embed(text)


class FakeLLMResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """Echoes back which source chunks it was given, so tests can assert on
    retrieval (what made it into the prompt) without caring about real
    Gemini output quality."""

    def invoke(self, prompt):
        return FakeLLMResponse(content=f"FAKE ANSWER based on: {prompt[:2000]}")


def _install_module_stub(name: str, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class EmbeddingConfigError(RuntimeError):
    """Placeholder standing in for rag.embeddings.EmbeddingConfigError so
    core.rag_engine's `from rag.embeddings import EmbeddingConfigError,
    EmbeddingServiceError` succeeds against this stub module. Not raised by
    anything in this test suite (FakeEmbeddings never fails) — it only
    needs to exist as an importable, isinstance()-able class."""


class EmbeddingServiceError(RuntimeError):
    """Placeholder standing in for rag.embeddings.EmbeddingServiceError —
    see EmbeddingConfigError above."""


_install_module_stub(
    "rag.embeddings",
    get_embedding_model=lambda: FakeEmbeddings(),
    EmbeddingConfigError=EmbeddingConfigError,
    EmbeddingServiceError=EmbeddingServiceError,
)
_install_module_stub("llm.gemini", get_llm=lambda model_override=None: FakeLLM())


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """Every test runs with cwd pointed at a fresh temp directory, so
    test-created sessions never touch the real project's data/ or
    database/ folders, and tests never see each other's leftover files."""
    monkeypatch.chdir(tmp_path)
