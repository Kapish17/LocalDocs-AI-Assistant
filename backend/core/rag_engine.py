"""
Core RAG engine.

Retrieval (vector + hybrid BM25), prompting, LLM invocation/retry, and the
summarize/flashcard helpers, kept independent of any UI so the same logic
is used by both the FastAPI service and the CLI (app.py) instead of
maintaining two copies. Nothing here imports fastapi.
"""

import logging
import re
import time
from typing import Callable, List, Optional, Tuple

from rag.prompt import RAG_PROMPT
from llm.gemini import get_llm

# Temporary, fine-grained pipeline tracing for debugging retrieval/answer
# issues (e.g. "why did this chunk win"). Off by default — nothing is
# printed unless this logger's level is explicitly raised to DEBUG (e.g.
# `logging.getLogger("core.rag_engine").setLevel(logging.DEBUG)`), so it's
# safe to leave in place rather than ripping it out after debugging.
logger = logging.getLogger(__name__)

# ==============================================================================
# LLM access
# ==============================================================================


def try_get_llm():
    """Returns (llm, error_message). error_message is None on success.

    Kept separate from any UI concern — callers decide how to surface a
    failure (an HTTP error response, a CLI print, ...)."""
    try:
        return get_llm(), None
    except Exception as e:
        return None, str(e)


# ==============================================================================
# Error classification & friendly messages
# ==============================================================================


def _is_daily_quota_error(e: Exception) -> bool:
    text = str(e).lower().replace(" ", "").replace("_", "")
    return "perday" in text


def _is_model_not_found_error(e: Exception) -> bool:
    text = str(e)
    return "NotFound" in type(e).__name__ or "404" in text or "NOT_FOUND" in text


def friendly_llm_error(e: Exception) -> str:
    """Turns a raw exception from the Gemini call into a short, human
    message. Rate-limit / quota errors are extremely common on the Gemini
    free tier, and there are two very different flavors of them — a
    per-minute burst limit (wait under a minute) vs. the free tier's daily
    request cap (wait until it resets, ~24h) — so they get distinct,
    actionable messages instead of a generic 'something went wrong'."""
    name = type(e).__name__
    text = str(e)
    lower = text.lower()

    if "RateLimit" in name or "429" in text or "resource_exhausted" in lower or "quota" in lower:
        if "perday" in lower.replace(" ", "").replace("_", ""):
            return (
                "Google's Gemini free tier has a daily request cap for this "
                "model, and it's been used up for today — it resets on its own "
                "(usually within 24h). Options right now: wait for the reset, "
                "switch models via GEMINI_MODEL in your .env "
                "(a higher-quota flash-lite model gets ~1,000-1,500 "
                "free requests/day instead of a much smaller preview-model "
                "allowance), or add billing to your Google AI Studio project."
            )
        wait_s = 30
        match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", text)
        if match:
            wait_s = max(int(match.group(1)), 5)
        return (
            f"Google's Gemini API rate-limited this request. Wait about "
            f"{wait_s} seconds and try again — free-tier quota allows only "
            "a handful of requests per minute. Sending fewer/shorter "
            "documents for summaries and flashcards also helps."
        )
    if "PermissionDenied" in name or "API_KEY_INVALID" in text or "403" in text:
        return "Google rejected this API key (invalid, expired, or missing permissions). Double-check the key in your .env."
    if _is_model_not_found_error(e):
        return (
            "Google retired the configured model name and none of the "
            "automatic fallback models worked either. Set GEMINI_MODEL in "
            "your .env to a current model name from "
            "https://ai.google.dev/gemini-api/docs/models."
        )
    return f"The AI model couldn't complete this request ({name}): {text}"


# Tried in order if the configured model gets retired mid-session (Google
# does this periodically — it happened to gemini-2.5-flash-lite in this
# project's own history). "-latest"/"-lite-latest" aliases are preferred
# since Google keeps them pointed at a working model instead of a fixed
# version that can expire.
FALLBACK_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]


def invoke_with_retry(llm, prompt, max_retries: int = 3, on_status: Optional[Callable[[str], None]] = None):
    """Calls llm.invoke(prompt) with two kinds of self-healing:
    - a 429 rate limit gets a short wait (Google's own suggested delay, or a
      short backoff) and a retry, instead of failing on the first transient
      hit, which free-tier Gemini keys run into constantly under normal use.
    - a 404 'model no longer available' (Google retires model names
      periodically) automatically switches to the next known-good model
      name and retries, instead of taking the whole app down.

    `on_status`, if given, is called with a short human-readable string each
    time a retry/fallback kicks in (e.g. to update a UI status line); it is
    never required, so this function works headlessly (API, CLI, tests)."""
    current_llm = llm
    tried_fallbacks = set()
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return current_llm.invoke(prompt)
        except Exception as e:
            last_error = e

            if _is_model_not_found_error(e):
                next_model = next((m for m in FALLBACK_MODELS if m not in tried_fallbacks), None)
                if next_model is None:
                    raise
                tried_fallbacks.add(next_model)
                if on_status is not None:
                    on_status(f"⚙️ That model isn't available — switching to `{next_model}`...")
                try:
                    current_llm = get_llm(model_override=next_model)
                except Exception:
                    raise last_error
                continue

            name = type(e).__name__
            text = str(e)
            lower = text.lower()
            is_rate_limit = "RateLimit" in name or "429" in text or "resource_exhausted" in lower

            if not is_rate_limit or _is_daily_quota_error(e) or attempt == max_retries:
                raise

            match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", text)
            wait_s = int(match.group(1)) if match else (2 ** attempt) * 3
            wait_s = min(max(wait_s, 2), 20)

            if on_status is not None:
                on_status(f"⏳ Rate-limited by Google — retrying in {wait_s}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait_s)
    raise last_error


# ==============================================================================
# Retrieval — vector, BM25/hybrid, and the broad-question special case
# ==============================================================================


def _doc_matches(doc, document_filter: Optional[str]) -> bool:
    if not document_filter:
        return True
    meta = doc.metadata or {}
    return meta.get("document_id") == document_filter or meta.get("source") == document_filter


def get_all_docs(retriever, document_filter: Optional[str] = None):
    """Best-effort pull of every indexed chunk from the FAISS docstore (used by
    hybrid search, summarization and flashcards). Returns [] if unavailable.

    document_filter, when given, restricts the result to chunks belonging to
    one document (matched by document_id, falling back to filename/source
    for chunks that predate document_id) — this is what makes "tell me
    about THIS pdf" actually scope to that PDF instead of the whole
    cross-document index."""
    vectorstore = getattr(retriever, "vectorstore", None)
    if vectorstore is None:
        return []
    try:
        docs = list(vectorstore.docstore._dict.values())
    except Exception:
        return []
    if document_filter:
        docs = [d for d in docs if _doc_matches(d, document_filter)]
    return docs


def vector_search(retriever, question: str, k: int = 4, document_filter: Optional[str] = None):
    """Dense similarity search. When document_filter is set, over-fetches a
    larger candidate pool from FAISS and filters it down to that document —
    FAISS's own metadata-filter kwarg varies across langchain_community
    versions, so this avoids depending on it. If filtering the over-fetched
    pool doesn't surface enough chunks (the document's real content didn't
    make the global top-N), it backfills from that document's own chunks
    directly so a document-specific question is never starved of that
    document's content."""
    fetch_k = max(k * 6, 30) if document_filter else k
    docs_scores = []
    vectorstore = getattr(retriever, "vectorstore", None)
    if vectorstore is not None:
        try:
            results = vectorstore.similarity_search_with_relevance_scores(question, k=fetch_k)
            docs_scores = [(d, float(s)) for d, s in results]
        except Exception:
            try:
                results = vectorstore.similarity_search_with_score(question, k=fetch_k)
                docs_scores = [(d, float(max(0.0, 1.0 - s))) for d, s in results]
            except Exception:
                docs_scores = []
    if not docs_scores:
        docs = retriever.invoke(question)
        docs_scores = [(d, max(0.4, 0.9 - i * 0.12)) for i, d in enumerate(docs)]

    if document_filter:
        filtered = [(d, s) for d, s in docs_scores if _doc_matches(d, document_filter)]
        if len(filtered) < k:
            have = {id(d) for d, _ in filtered}
            for d in get_all_docs(retriever, document_filter):
                if id(d) not in have:
                    filtered.append((d, 0.5))
                    have.add(id(d))
                if len(filtered) >= k:
                    break
        return filtered[:k]

    return docs_scores[:k]


# Process-wide BM25 cache, keyed by (retriever identity, document filter). A
# plain dict works fine here (one process, rebuilt only when cache_bust
# changes), and both the CLI and the API share one cache.
_bm25_cache = {}


def _build_bm25(retriever, cache_bust: int = 0, document_filter: Optional[str] = None):
    """cache_bust changes every time the KB is rebuilt, forcing a fresh index.
    A separate cache entry per document_filter so a document-scoped BM25
    index (built only from that document's own chunks — real per-document
    keyword search, not a global index post-filtered) doesn't collide with
    the whole-corpus one."""
    key = (id(retriever), document_filter)
    cached = _bm25_cache.get(key)
    if cached is not None and cached[0] == cache_bust:
        return cached[1], cached[2]

    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        _bm25_cache[key] = (cache_bust, None, [])
        return None, []

    docs = get_all_docs(retriever, document_filter)
    if not docs:
        _bm25_cache[key] = (cache_bust, None, [])
        return None, []

    corpus = [d.page_content.lower().split() for d in docs]
    bm25 = BM25Okapi(corpus)
    _bm25_cache[key] = (cache_bust, bm25, docs)
    return bm25, docs


def hybrid_search(
    retriever,
    question: str,
    k: int = 4,
    alpha: float = 0.55,
    cache_bust: int = 0,
    document_filter: Optional[str] = None,
):
    """Blends vector similarity (weight=alpha) with BM25 keyword score
    (1-alpha). document_filter restricts both legs to one document's chunks
    (see vector_search / _build_bm25 docstrings)."""
    logger.debug("DOCUMENT FILTER: %r", document_filter)

    vec_results = vector_search(retriever, question, k=max(k * 2, 8), document_filter=document_filter)
    logger.debug(
        "VECTOR RESULTS: %s",
        [(d.metadata.get("source"), round(s, 3)) for d, s in vec_results],
    )

    bm25, all_docs = _build_bm25(retriever, cache_bust, document_filter=document_filter)
    if bm25 is None or not all_docs:
        logger.debug("BM25 RESULTS: unavailable (no index) — falling back to vector-only")
        return vec_results[:k]

    bm25_scores = bm25.get_scores(question.lower().split())
    max_bm = max(bm25_scores) if len(bm25_scores) else 1.0
    doc_id = lambda d: id(d)
    bm25_map = {doc_id(d): (s / max_bm if max_bm > 0 else 0.0) for d, s in zip(all_docs, bm25_scores)}
    logger.debug(
        "BM25 RESULTS: %s",
        sorted(
            [(d.metadata.get("source"), round(bm25_map.get(doc_id(d), 0.0), 3)) for d in all_docs],
            key=lambda x: x[1],
            reverse=True,
        )[:8],
    )

    combined = []
    for doc, vscore in vec_results:
        bscore = bm25_map.get(doc_id(doc), 0.0)
        combined.append((doc, alpha * vscore + (1 - alpha) * bscore))

    combined.sort(key=lambda x: x[1], reverse=True)
    result = combined[:k]
    logger.debug(
        "FINAL HYBRID RESULTS: %s",
        [(d.metadata.get("source"), round(s, 3), d.page_content[:60].replace("\n", " ")) for d, s in result],
    )
    return result


BROAD_QUESTION_KEYWORDS = (
    "summarize", "summary", "summarise", "key finding", "key findings",
    "main point", "main points", "overview", "conclusion", "conclusions",
    "tl;dr", "in summary", "what is this document about",
    "what's this document about", "what is this about",
)

# Catches phrasing like "tell me about this pdf" / "what is this document
# about" / "explain this file" / "describe this doc" that isn't covered by
# the fixed-keyword list above. This is what was originally missing: without
# it, "tell me about this pdf" fell through to ordinary hybrid retrieval,
# where BM25's literal keyword match on the word "pdf" could outrank chunks
# that actually describe the document's real subject matter (see the
# hardened RAG_PROMPT instructions for the second half of that fix).
_BROAD_QUESTION_PATTERN = re.compile(
    r"\b(tell me about|what('?s| is)|explain|describe|summar\w*)\b.{0,15}"
    r"\b(this|the)\b.{0,15}\b(pdf|document|doc|file|paper|report)\b",
    re.IGNORECASE,
)


def is_broad_question(question: str) -> bool:
    """True for meta-questions like 'summarize this', 'key findings', or
    'tell me about this pdf' — these rarely share vocabulary with any single
    chunk, so top-k similarity/BM25 search either retrieves weak matches or
    (worse) latches onto whichever chunk happens to repeat the literal query
    words most, rather than giving a broad overview. Sampling across the
    whole document instead gives a grounded, representative answer."""
    q = question.lower()
    if any(kw in q for kw in BROAD_QUESTION_KEYWORDS):
        return True
    return bool(_BROAD_QUESTION_PATTERN.search(q))


def get_context_and_scores(
    retriever,
    question: str,
    k: int = 4,
    hybrid: bool = True,
    cache_bust: int = 0,
    document_filter: Optional[str] = None,
):
    logger.debug("QUESTION: %r", question)
    logger.debug("is_broad_question: %s", is_broad_question(question))
    if is_broad_question(question):
        docs = get_all_docs(retriever, document_filter)
        if docs:
            max_docs = 16
            if len(docs) <= max_docs:
                sample = docs
            else:
                stride = len(docs) / max_docs
                sample = [docs[int(i * stride)] for i in range(max_docs)]
            return [(d, 0.85) for d in sample]
        if document_filter:
            # A document filter was given but nothing matched it — don't
            # silently fall back to searching every other document.
            return []
    if hybrid:
        return hybrid_search(retriever, question, k=k, cache_bust=cache_bust, document_filter=document_filter)
    return vector_search(retriever, question, k=k, document_filter=document_filter)


# ==============================================================================
# Chat memory & shared text helpers
# ==============================================================================


def build_conversation_memory(history, max_turns: int = 3) -> str:
    recent = history[-(max_turns * 2):]
    lines = []
    for m in recent:
        role = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def dedupe_sources(pairs):
    """Keeps only one entry per unique source filename (highest score wins),
    preserving first-seen order. Fixes the same PDF being listed multiple
    times when the retriever returns several chunks from one file."""
    best_score = {}
    order = []
    for name, score in pairs:
        if name not in best_score:
            order.append(name)
            best_score[name] = score
        else:
            best_score[name] = max(best_score[name], score)
    return [(name, best_score[name]) for name in order]


def extract_answer_text(response) -> str:
    if isinstance(response.content, list):
        return "".join(
            block["text"] for block in response.content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return response.content


# ==============================================================================
# High-level orchestration — one question in, one grounded answer out
# ==============================================================================


def answer_question(
    question: str,
    retriever,
    llm,
    chat_history: Optional[List[dict]] = None,
    hybrid: bool = True,
    k: int = 4,
    cache_bust: int = 0,
    on_status: Optional[Callable[[str], None]] = None,
    document_filter: Optional[str] = None,
) -> dict:
    """Runs the full retrieve -> prompt -> generate pipeline and returns a
    structured result. This is the single implementation used by both the
    CLI chat loop (app.py) and the FastAPI /query endpoint, so retrieval and
    prompting behavior can't drift between the two front ends.

    document_filter: when given (a document_id / filename), retrieval is
    scoped to that document only — used for "tell me about this pdf"-style
    per-document questions so chunks from other uploaded documents can never
    leak into the answer or the shown sources.

    Returns a dict:
        answer: str
        confidence: float (0-1, average retrieval similarity of the
            chunks used — a retrieval-quality signal, not a correctness score)
        sources: list[str]                     (unique source filenames)
        source_details: list[tuple[str, float]] (name, similarity)
        retrieved_documents: list[dict]         (source, content, score)
        latency_ms: int
    """
    t0 = time.perf_counter()

    docs_scores = get_context_and_scores(
        retriever, question, k=k, hybrid=hybrid, cache_bust=cache_bust, document_filter=document_filter
    )

    retrieved_context = "\n\n".join(doc.page_content for doc, _ in docs_scores)
    memory_context = build_conversation_memory(chat_history or [])

    prompt = RAG_PROMPT.format(
        context=retrieved_context or "(no matching document content was retrieved)",
        question=question,
        history=memory_context or "(none)",
    )
    logger.debug("CONTEXT SENT TO GEMINI:\n%s", retrieved_context[:2000])

    response = invoke_with_retry(llm, prompt, on_status=on_status)
    answer = extract_answer_text(response)
    logger.debug("GEMINI RESPONSE: %s", answer[:500])

    confidence = sum(s for _, s in docs_scores) / len(docs_scores) if docs_scores else 0.6
    source_details = dedupe_sources(
        [(doc.metadata.get("source", "Unknown"), score) for doc, score in docs_scores]
    )
    retrieved_documents = [
        {
            "source": doc.metadata.get("source", "Unknown"),
            "document_id": doc.metadata.get("document_id", doc.metadata.get("source", "Unknown")),
            "page": doc.metadata.get("page"),
            "chunk_id": doc.metadata.get("chunk_id"),
            "content": doc.page_content,
            "score": float(score),
        }
        for doc, score in docs_scores
    ]

    latency_ms = int((time.perf_counter() - t0) * 1000)

    return {
        "answer": answer,
        "confidence": confidence,
        "sources": [s[0] for s in source_details],
        "source_details": source_details,
        "retrieved_documents": retrieved_documents,
        "latency_ms": latency_ms,
    }


# ==============================================================================
# Summarization & flashcards
# ==============================================================================


def summarize_documents(
    llm,
    retriever,
    max_chars: int = 12000,
    document_filter: Optional[str] = None,
    detail: str = "short",
) -> str:
    """Reuses the same indexed chunks retrieval/hybrid-search/answer_question
    already reads (get_all_docs) — no separate document-loading path.

    For documents whose combined text fits in one prompt, this is a single
    Gemini call. For longer documents it does real hierarchical (map-reduce)
    summarization — summarize each max_chars-sized segment, then combine
    those partial summaries into one final summary — rather than silently
    truncating the document to its first max_chars characters, which would
    drop real content and bias the summary toward whatever came first.
    """
    docs = get_all_docs(retriever, document_filter=document_filter)
    if not docs:
        if document_filter:
            return f"⚠️ No indexed content found for document '{document_filter}'."
        return "⚠️ No indexed documents found — build the knowledge base first."

    combined = "\n\n".join(d.page_content for d in docs)
    style = (
        "Use clear section headers and concise bullet points covering key themes, "
        "facts, and conclusions. Keep it brief — a short, scannable overview."
        if detail != "detailed"
        else
        "Write a thorough, well-organized summary with section headers, covering "
        "key themes, structure, important facts/details, and conclusions."
    )

    if len(combined) <= max_chars:
        prompt = (
            f"Summarize the following document content for someone who hasn't read it. {style}\n\n"
            f"CONTENT:\n{combined}"
        )
        response = invoke_with_retry(llm, prompt)
        return extract_answer_text(response)

    logger.debug("Long document (%d chars) — using hierarchical summarization", len(combined))
    segments = [combined[i : i + max_chars] for i in range(0, len(combined), max_chars)]
    partial_summaries = []
    for i, segment in enumerate(segments):
        seg_prompt = (
            f"Summarize part {i + 1} of {len(segments)} of a longer document. Capture the key "
            "facts and points concisely — this will be combined with summaries of the other parts.\n\n"
            f"CONTENT:\n{segment}"
        )
        response = invoke_with_retry(llm, seg_prompt)
        partial_summaries.append(extract_answer_text(response))

    combine_prompt = (
        "The following are summaries of consecutive parts of one document, in order. "
        f"Combine them into a single coherent summary of the whole document. {style}\n\n"
        + "\n\n".join(f"Part {i + 1} summary:\n{s}" for i, s in enumerate(partial_summaries))
    )
    response = invoke_with_retry(llm, combine_prompt)
    return extract_answer_text(response)


def generate_flashcards(llm, retriever, num_cards: int = 8, max_chars: int = 12000, document_filter: Optional[str] = None):
    """Grounded in the document's own indexed chunks (get_all_docs) — same
    ingestion/retrieval infrastructure as Q&A and summarization, no separate
    pipeline. Returns a list of {question, answer, source} dicts; source is
    the document's filename plus a page number when every chunk used came
    from a single page (best-effort — a card that draws on content spanning
    multiple pages is attributed to the document as a whole rather than
    guessing a page)."""
    docs = get_all_docs(retriever, document_filter=document_filter)
    if not docs:
        return []

    combined = "\n\n".join(d.page_content for d in docs)[:max_chars]
    pages = {d.metadata.get("page") for d in docs if d.metadata.get("page") is not None}
    single_page = next(iter(pages)) if len(pages) == 1 else None
    filename = docs[0].metadata.get("document_id") or docs[0].metadata.get("source", "Unknown")

    prompt = (
        f"Create exactly {num_cards} study flashcards grounded ONLY in the content below — "
        "do not invent facts that aren't supported by it. "
        "Strictly use this format with no extra commentary:\n"
        "Q: <question>\nA: <answer>\n\n"
        f"CONTENT:\n{combined}"
    )
    response = invoke_with_retry(llm, prompt)
    text = extract_answer_text(response)

    cards, q = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Q:"):
            q = line[2:].strip()
        elif line.startswith("A:") and q:
            cards.append(
                {
                    "question": q,
                    "answer": line[2:].strip(),
                    "source": {"filename": filename, "page": single_page},
                }
            )
            q = None
    return cards
