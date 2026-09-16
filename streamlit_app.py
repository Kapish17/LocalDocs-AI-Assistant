"""
LocalDocs AI Assistant — NotebookLM-style RAG UI (v3)
--------------------------------------------------------
Uses only your existing modules:
    rag.retriever.get_retriever()
    rag.prompt.RAG_PROMPT
    llm.gemini.get_llm()

New in this version:
    - Multiple chats ("+ New Chat")
    - Share conversation (generates a copy-able link)
    - Chat memory (recent turns are fed back into the prompt)
    - Document summarization
    - OCR support for scanned PDFs / images (EasyOCR — pure Python, no
      external Tesseract binary/install required)
    - Hybrid search (vector + BM25 keyword)
    - Flashcard generation (flip cards)
"""

import re
import time
import json
import uuid
import html
import functools
from pathlib import Path
from datetime import datetime

import streamlit as st

import shutil
from rag.retriever import get_retriever
from rag.index_builder import build_vector_store
from rag.prompt import RAG_PROMPT
from llm.gemini import get_llm

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
FAISS_INDEX_DIR = Path("database/faiss_index")
SHARE_DIR = Path("shared_chats")
SHARE_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = ["pdf", "docx", "pptx", "txt", "csv", "png", "jpg", "jpeg"]

SAMPLE_QUESTIONS = [
    "Summarize this document in 5 bullet points",
    "What are the key findings or conclusions?",
    "List any numbers, dates, or statistics mentioned",
    "What questions might someone ask about this content?",
]

# ==============================================================================
# Page config
# ==============================================================================
st.set_page_config(
    page_title="LocalDocs AI Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# Session state
# ==============================================================================
_defaults = {
    "chats": {},
    "current_chat_id": None,
    "kb_built": False,
    "uploaded_names": [],
    "total_queries": 0,
    "confidence_scores": [],
    "session_start": datetime.now(),
    "pending_question": None,
    "hybrid_search": True,
    "ocr_enabled": True,
    "summary_text": None,
    "flashcards": None,
}
for key, val in _defaults.items():
    st.session_state.setdefault(key, val)

RETRIEVER_KEY = "_retriever_obj"
BM25_KEY = "_bm25_index"


def new_chat(name: str = None) -> str:
    chat_id = uuid.uuid4().hex[:8]
    st.session_state.chats[chat_id] = {
        "name": name or f"Chat {len(st.session_state.chats) + 1}",
        "history": [],
        "created": datetime.now(),
    }
    st.session_state.current_chat_id = chat_id
    return chat_id


if not st.session_state.chats:
    new_chat("Chat 1")

if st.session_state.current_chat_id not in st.session_state.chats:
    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]


def current_chat():
    return st.session_state.chats[st.session_state.current_chat_id]


# ==============================================================================
# Shared (read-only) view — checked before anything else renders
# ==============================================================================
query_params = st.query_params
if "share" in query_params:
    share_id = query_params["share"]
    shared_path = SHARE_DIR / f"{share_id}.json"

    st.markdown("## 🔗 Shared Conversation")
    if shared_path.exists():
        with open(shared_path) as f:
            shared_data = json.load(f)
        st.caption(f"Shared on {shared_data.get('shared_at', 'unknown date')} · read-only")
        for msg in shared_data.get("history", []):
            role = "🧑 You" if msg["role"] == "user" else "🤖 Assistant"
            st.markdown(f"**{role}:** {msg['content']}")
            if msg.get("sources"):
                st.caption("Sources: " + ", ".join(msg["sources"]))
            st.markdown("---")
    else:
        st.error("This shared link is invalid or has expired.")

    st.info("This is a read-only shared view. Remove the `?share=` parameter from the URL to use the full app.")
    st.stop()


# ==============================================================================
# Theming / CSS — single default theme (dark), no toggle
# ==============================================================================
def load_css():
    bg, panel, card = "#0b0e14", "#10131e", "#161a26"
    card2 = "#1a1f30"
    text, subtext = "#e8ecf6", "#9aa4bd"
    border = "#242a3d"
    accent1, accent2 = "#7c5cff", "#22d3ee"

    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <style>
        html, body, .stApp {{ font-family: 'Inter', -apple-system, sans-serif; }}
        h1, h2, h3, .hero h1 {{ font-family: 'Sora', sans-serif; }}

        .stApp {{
            background:
                radial-gradient(1100px 500px at 12% -8%, {accent1}1c, transparent 60%),
                radial-gradient(900px 500px at 100% 0%, {accent2}14, transparent 55%),
                {bg};
            color: {text};
        }}
        section[data-testid="stSidebar"] {{
            background: {panel};
            border-right: 1px solid {border};
        }}
        section[data-testid="stSidebar"] h3 {{
            font-family: 'Sora', sans-serif; font-size: 0.95rem;
            letter-spacing: 0.02em; margin-top: 0.4rem;
        }}

        /* ---------- Hero ---------- */
        .hero {{
            padding: 1.5rem 1.9rem; border-radius: 20px;
            background: linear-gradient(120deg, {accent1}26, {accent2}1c);
            border: 1px solid {border}; margin-bottom: 1.3rem;
            box-shadow: 0 10px 30px -12px rgba(0,0,0,0.5);
            animation: fadeSlideIn 0.5s ease both;
        }}
        .hero-row {{ display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }}
        .hero h1 {{
            font-size: 2.1rem; margin: 0 0 0.3rem 0;
            background: linear-gradient(90deg, {accent1}, {accent2});
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;
        }}
        .hero p {{ color: {subtext}; margin: 0; font-size: 0.95rem; max-width: 620px; }}
        .hero-status {{
            white-space: nowrap; font-size: 0.8rem; font-weight: 600; color: {text};
            background: {card}cc; border: 1px solid {border};
            padding: 7px 14px; border-radius: 999px;
        }}

        .section-label {{
            font-size: 0.85rem; font-weight: 600; color: {subtext};
            margin: 0.6rem 0 0.5rem 0; letter-spacing: 0.02em;
        }}

        /* ---------- Empty state ---------- */
        .empty-state {{
            text-align: center; padding: 2.6rem 1.5rem; border-radius: 18px;
            background: {card}; border: 1px dashed {border}; margin-bottom: 1.1rem;
            animation: fadeSlideIn 0.5s ease both;
        }}
        .empty-state-icon {{ font-size: 2.4rem; margin-bottom: 0.6rem; }}
        .empty-state-title {{ font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.15rem; margin-bottom: 0.4rem; }}
        .empty-state-text {{ color: {subtext}; font-size: 0.88rem; max-width: 480px; margin: 0 auto; line-height: 1.55; }}

        /* ---------- Setup / error card ---------- */
        .setup-card {{
            display: flex; gap: 14px; align-items: flex-start;
            background: linear-gradient(120deg, #f59e0b1c, {card});
            border: 1px solid #f59e0b55; border-radius: 16px;
            padding: 16px 18px; margin: 0.6rem 0 1rem 0;
        }}
        .setup-card-icon {{ font-size: 1.6rem; line-height: 1; }}
        .setup-card-body b {{ font-family: 'Sora', sans-serif; font-size: 1rem; }}
        .setup-card-body p {{ color: {subtext}; font-size: 0.85rem; margin: 6px 0 0 0; line-height: 1.55; }}
        .setup-card-hint code {{
            background: {card2}; border: 1px solid {border}; border-radius: 5px;
            padding: 1px 6px; font-size: 0.8rem; color: {accent2};
        }}

        .file-badge {{
            display: inline-flex; align-items: center; gap: 6px;
            background: {card}; border: 1px solid {border};
            padding: 6px 12px; border-radius: 999px;
            font-size: 0.82rem; margin: 3px 4px 3px 0; color: {text};
            transition: border-color 0.15s ease;
        }}
        .file-badge:hover {{ border-color: {accent1}80; }}

        .metric-card {{
            background: linear-gradient(160deg, {card2}, {card});
            border: 1px solid {border};
            border-radius: 14px; padding: 12px 14px; text-align: center;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}
        .metric-card:hover {{ transform: translateY(-2px); border-color: {accent1}70; }}
        .metric-card b {{ font-size: 1.15rem; font-family: 'Sora', sans-serif; }}

        .conf-wrap {{ margin-top: 6px; margin-bottom: 4px; }}
        .conf-label {{
            font-size: 0.75rem; color: {subtext};
            display: flex; justify-content: space-between; margin-bottom: 3px;
        }}
        .conf-track {{ width: 100%; height: 8px; border-radius: 999px; background: {border}; overflow: hidden; }}
        .conf-fill {{ height: 100%; border-radius: 999px; transition: width 0.4s ease; }}
        .source-chip {{
            background: {card}; border: 1px solid {border};
            border-radius: 10px; padding: 8px 12px; margin-bottom: 6px; font-size: 0.85rem;
            transition: border-color 0.15s ease;
        }}
        .source-chip:hover {{ border-color: {accent2}70; }}
        .sim-track {{ width: 100%; height: 6px; border-radius: 999px; background: {border}; overflow: hidden; margin-top: 4px; }}
        .sim-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, {accent2}, {accent1}); }}
        .status-pill {{ display: inline-block; padding: 3px 12px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}

        div[data-testid="stChatMessage"] {{
            border-radius: 16px; border: 1px solid {border};
            background: {card}; animation: fadeSlideIn 0.35s ease both;
        }}

        /* ---------- Buttons & inputs ---------- */
        .stButton > button {{
            border-radius: 10px !important; border: 1px solid {border} !important;
            transition: transform 0.12s ease, border-color 0.12s ease !important;
        }}
        .stButton > button:hover {{ transform: translateY(-1px); border-color: {accent1}90 !important; }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(90deg, {accent1}, {accent2}) !important;
            border: none !important; font-weight: 600 !important;
        }}
        div[data-testid="stChatInput"] {{
            border-radius: 14px !important;
        }}
        section[data-testid="stFileUploaderDropzone"] {{
            border-radius: 12px !important;
        }}

        ::-webkit-scrollbar {{ width: 9px; height: 9px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {border}; border-radius: 999px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: {accent1}80; }}

        @keyframes fadeSlideIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .chat-list-item {{
            padding: 6px 10px; border-radius: 10px; margin-bottom: 4px;
            font-size: 0.85rem; cursor: pointer;
        }}
        .chat-list-item.active {{ background: {accent1}33; border: 1px solid {accent1}; }}

        .copy-btn {{
            background: linear-gradient(90deg, {accent1}, {accent2});
            color: white; border: none; border-radius: 8px;
            padding: 8px 14px; font-size: 0.85rem; cursor: pointer; width: 100%;
            transition: opacity 0.15s ease;
        }}
        .copy-btn:hover {{ opacity: 0.88; }}

        .flashcard-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 16px; margin-top: 10px;
        }}
        .flashcard {{ width: 100%; height: 170px; perspective: 1200px; }}
        .flashcard-inner {{
            position: relative; width: 100%; height: 100%;
            transition: transform 0.6s; transform-style: preserve-3d;
        }}
        .flashcard:hover .flashcard-inner {{ transform: rotateY(180deg); }}
        .flashcard-front, .flashcard-back {{
            position: absolute; width: 100%; height: 100%; backface-visibility: hidden;
            border-radius: 14px; padding: 16px; display: flex; align-items: center;
            justify-content: center; text-align: center; font-size: 0.88rem;
            border: 1px solid {border}; overflow: auto;
        }}
        .flashcard-front {{
            background: linear-gradient(135deg, {accent1}, {accent2}); color: white; font-weight: 600;
        }}
        .flashcard-back {{ background: {card}; color: {text}; transform: rotateY(180deg); }}
        .flashcard-hint {{ font-size: 0.7rem; color: {subtext}; margin-top: 4px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


load_css()


# ==============================================================================
# Helpers — retrieval
# ==============================================================================
def confidence_color(score: float) -> str:
    if score >= 0.75:
        return "#22c55e"
    if score >= 0.5:
        return "#eab308"
    return "#ef4444"


def render_confidence_bar(score: float):
    pct = max(0, min(100, round(score * 100)))
    color = confidence_color(score)
    st.markdown(
        f"""
        <div class="conf-wrap">
            <div class="conf-label"><span>Confidence</span><span>{pct}%</span></div>
            <div class="conf-track"><div class="conf-fill" style="width:{pct}%;background:{color};"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source(name: str, similarity: float):
    pct = max(0, min(100, round(similarity * 100)))
    st.markdown(
        f"""
        <div class="source-chip">
            📄 <b>{html.escape(name)}</b>
            <div class="sim-track"><div class="sim-fill" style="width:{pct}%;"></div></div>
            <div style="font-size:0.72rem;color:#9aa4bd;margin-top:2px;">Similarity match: {pct}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def typing_effect(placeholder, full_text: str, speed: float = 0.012):
    shown = ""
    for word in full_text.split(" "):
        shown += word + " "
        placeholder.markdown(shown + "▌")
        time.sleep(speed)
    placeholder.markdown(shown)


def extract_answer_text(response) -> str:
    if isinstance(response.content, list):
        return "".join(
            block["text"] for block in response.content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return response.content


def render_setup_card(message: str):
    """A friendly, actionable card shown instead of a crash when the Gemini
    API key is missing/invalid, so the app degrades gracefully instead of
    throwing an unhandled traceback at the user."""
    st.markdown(
        f"""
        <div class="setup-card">
            <div class="setup-card-icon">🔑</div>
            <div class="setup-card-body">
                <b>Gemini API key isn't set up yet</b>
                <p>{html.escape(message)}</p>
                <p class="setup-card-hint">
                    Local dev: add <code>GOOGLE_API_KEY=...</code> to a <code>.env</code> file.<br>
                    Streamlit Cloud: <i>Manage app → Settings → Secrets</i> →
                    add <code>GOOGLE_API_KEY = "your-key-here"</code>.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_get_llm(show_error: bool = True):
    """Wraps llm.gemini.get_llm() so a missing/invalid API key renders a
    clear setup card instead of an unhandled ValueError crashing the app."""
    try:
        return get_llm()
    except Exception as e:
        if show_error:
            render_setup_card(str(e))
        return None


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
                "switch to a model with a higher free quota by setting "
                "GEMINI_MODEL in your .env / Streamlit secrets (e.g. "
                "gemini-2.5-flash-lite, which gets ~1,500 free requests/day "
                "instead of a much smaller preview-model allowance), or add "
                "billing to your Google AI Studio project."
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
        return "Google rejected this API key (invalid, expired, or missing permissions). Double-check the key in your .env / Streamlit secrets."
    return f"The AI model couldn't complete this request ({name}): {text}"


def render_tool_error(message: str, icon: str = "⏳"):
    """A friendly card for runtime AI-call failures (rate limits, quota,
    transient API errors) that aren't a missing-key setup problem."""
    st.markdown(
        f"""
        <div class="setup-card">
            <div class="setup-card-icon">{icon}</div>
            <div class="setup-card-body">
                <b>Couldn't complete that request</b>
                <p>{html.escape(message)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_all_docs(retriever):
    """Best-effort pull of every indexed chunk from the FAISS docstore (used by
    hybrid search, summarization and flashcards). Returns [] if unavailable."""
    vectorstore = getattr(retriever, "vectorstore", None)
    if vectorstore is None:
        return []
    try:
        return list(vectorstore.docstore._dict.values())
    except Exception:
        return []


def vector_search(retriever, question: str, k: int = 4):
    docs_scores = []
    vectorstore = getattr(retriever, "vectorstore", None)
    if vectorstore is not None:
        try:
            results = vectorstore.similarity_search_with_relevance_scores(question, k=k)
            docs_scores = [(d, float(s)) for d, s in results]
        except Exception:
            try:
                results = vectorstore.similarity_search_with_score(question, k=k)
                docs_scores = [(d, float(max(0.0, 1.0 - s))) for d, s in results]
            except Exception:
                docs_scores = []
    if not docs_scores:
        docs = retriever.invoke(question)
        docs_scores = [(d, max(0.4, 0.9 - i * 0.12)) for i, d in enumerate(docs)]
    return docs_scores


@st.cache_resource(show_spinner=False)
def _build_bm25(_retriever, cache_bust: int):
    """cache_bust changes every time the KB is rebuilt, forcing a fresh index."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return None, []
    docs = get_all_docs(_retriever)
    if not docs:
        return None, []
    corpus = [d.page_content.lower().split() for d in docs]
    return BM25Okapi(corpus), docs


def hybrid_search(retriever, question: str, k: int = 4, alpha: float = 0.55):
    """Blends vector similarity (weight=alpha) with BM25 keyword score (1-alpha)."""
    vec_results = vector_search(retriever, question, k=max(k * 2, 8))

    bm25, all_docs = _build_bm25(retriever, st.session_state.get("_kb_version", 0))
    if bm25 is None or not all_docs:
        return vec_results[:k]

    bm25_scores = bm25.get_scores(question.lower().split())
    max_bm = max(bm25_scores) if len(bm25_scores) else 1.0
    doc_id = lambda d: id(d)
    bm25_map = {doc_id(d): (s / max_bm if max_bm > 0 else 0.0) for d, s in zip(all_docs, bm25_scores)}

    combined = []
    for doc, vscore in vec_results:
        bscore = bm25_map.get(doc_id(doc), 0.0)
        combined.append((doc, alpha * vscore + (1 - alpha) * bscore))

    combined.sort(key=lambda x: x[1], reverse=True)
    return combined[:k]


def get_context_and_scores(retriever, question: str, k: int = 4):
    if st.session_state.hybrid_search:
        return hybrid_search(retriever, question, k=k)
    return vector_search(retriever, question, k=k)


# ==============================================================================
# Helpers — chat memory
# ==============================================================================
def build_conversation_memory(history, max_turns: int = 3) -> str:
    recent = history[-(max_turns * 2):]
    lines = []
    for m in recent:
        role = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


# ==============================================================================
# Helpers — OCR (EasyOCR — pure Python, no external Tesseract binary needed)
# ==============================================================================
def needs_ocr(pdf_path: Path, min_chars: int = 40) -> bool:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        text = "".join((page.extract_text() or "") for page in reader.pages[:3])
        return len(text.strip()) < min_chars
    except Exception:
        return True


@st.cache_resource(show_spinner=False)
def _get_easyocr_reader():
    """Loads the EasyOCR model once per process and reuses it — model init
    takes a few seconds, so we don't want to redo it per file/page. Uses
    st.cache_resource (rather than functools.lru_cache) so it plays nicely
    with Streamlit's rerun model."""
    import easyocr
    return easyocr.Reader(["en"], gpu=False)  # set gpu=True if you have a CUDA GPU + torch-cuda


def ocr_extract(file_path: Path) -> str:
    """Runs OCR on a scanned PDF or image and returns extracted text (empty on
    failure). Uses EasyOCR — a pure-Python OCR engine with no external binary
    dependency, unlike Tesseract which requires a separate system install.
    PDFs are rasterized with PyMuPDF (fitz), which has no dependency on the
    external 'poppler' binary either."""
    try:
        reader = _get_easyocr_reader()
        from PIL import Image
        import numpy as np
    except ImportError:
        print("[ocr] easyocr/Pillow/numpy not installed — skipping OCR. Run: pip install easyocr")
        return ""
    except Exception as e:
        print(f"[ocr] Failed to load EasyOCR model: {e}")
        st.warning(f"OCR engine failed to load: {e}")
        return ""

    ext = file_path.suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            try:
                import fitz  # PyMuPDF
            except ImportError:
                print("[ocr] PyMuPDF not installed — skipping OCR for PDF. Run: pip install pymupdf")
                st.warning("OCR for scanned PDFs needs PyMuPDF — run `pip install pymupdf` and rebuild.")
                return ""

            doc = fitz.open(str(file_path))
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                result = reader.readtext(np.array(img), detail=0, paragraph=True)
                text += "\n".join(result) + "\n"
            doc.close()
        elif ext in (".png", ".jpg", ".jpeg"):
            img = Image.open(file_path).convert("RGB")
            result = reader.readtext(np.array(img), detail=0, paragraph=True)
            text = "\n".join(result)
    except Exception as e:
        st.warning(f"OCR failed for {file_path.name}: {e}")
        print(f"[ocr] Failed for {file_path.name}: {e}")
    return text.strip()


def run_ocr_pass(file_paths, progress_cb=None) -> int:
    """For scanned PDFs / images, writes a companion .ocr.txt file next to the
    original so your existing ingestion (scan_folder) can pick it up.

    Only runs OCR when actually needed:
        - Skips any file that already has a valid, non-empty .ocr.txt from a
        previous run (so re-building the KB doesn't re-OCR everything).
        - For PDFs, only OCRs if the PDF has no extractable native text
        (needs_ocr() check) — text-based PDFs are never OCR'd.
        - Images always need OCR the first time (no native text), but are
        still skipped on repeat builds thanks to the .ocr.txt check above.
    """
    processed = 0
    candidates = [p for p in file_paths if Path(p).suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg")]
    total = len(candidates)

    for i, fp in enumerate(candidates):
        path = Path(fp)
        ocr_companion = path.with_suffix(path.suffix + ".ocr.txt")

        # Already OCR'd previously — skip re-running it.
        already_ocred = False
        if ocr_companion.exists():
            try:
                already_ocred = len(ocr_companion.read_text(encoding="utf-8").strip()) >= 10
            except Exception:
                already_ocred = False

        if already_ocred:
            if progress_cb:
                progress_cb((i + 1) / max(total, 1))
            continue

        # For PDFs, only OCR if there's no usable native text extraction.
        should_ocr = path.suffix.lower() != ".pdf" or needs_ocr(path)
        if should_ocr:
            text = ocr_extract(path)
            if text:
                ocr_companion.write_text(text, encoding="utf-8")
                processed += 1

        if progress_cb:
            progress_cb((i + 1) / max(total, 1))

    return processed


def has_extractable_text(file_path: Path, min_chars: int = 10) -> bool:
    """Checks whether a file has any real extractable text — either from its
    normal content or a successful OCR pass (.ocr.txt companion). Scanned PDFs
    that failed OCR will fail this check, which is what lets
    rebuild_knowledge_base() quarantine them before they reach
    build_vector_store() and cause an 'IndexError: list index out of range'
    (or similar) from an empty document/chunk list downstream."""
    ocr_companion = file_path.with_suffix(file_path.suffix + ".ocr.txt")
    if ocr_companion.exists():
        try:
            if len(ocr_companion.read_text(encoding="utf-8").strip()) >= min_chars:
                return True
        except Exception:
            pass

    ext = file_path.suffix.lower()

    if ext in (".png", ".jpg", ".jpeg"):
        # Images have no "native" text — only the OCR companion counts, checked above.
        return False

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            text = "".join((p.extract_text() or "") for p in reader.pages)
            return len(text.strip()) >= min_chars
        except Exception:
            return False

    # docx / txt / csv / pptx — assume they carry text; the real loaders will
    # surface any genuine problem later with a clearer error.
    return True


# ==============================================================================
# Knowledge base rebuild (fixes: stale FAISS index, orphan files, cache-only reload)
# ==============================================================================
def sync_data_folder():
    """data/ can accumulate files from past sessions/uploads that are no longer
    tracked in uploaded_names. scan_folder('data') would still pick those up
    and re-embed them. This deletes anything in data/ that isn't in the current
    tracked file list (including orphaned .ocr.txt companions)."""
    if not DATA_DIR.exists():
        return
    keep = set(st.session_state.uploaded_names)
    for f in DATA_DIR.iterdir():
        if not f.is_file():
            continue
        base_name = f.name[:-8] if f.name.endswith(".ocr.txt") else f.name
        if base_name not in keep:
            f.unlink()


def rebuild_knowledge_base(progress_cb=None):
    """A real rebuild — delete the old FAISS index, run build_vector_store() to
    re-embed only what's currently in data/, then force a fresh (uncached)
    retriever load. Files with zero extractable text (e.g. a scanned PDF where
    OCR failed) are temporarily moved out of data/ so build_vector_store()
    doesn't choke on an empty document. Returns (retriever, skipped_filenames).
    """
    if progress_cb:
        progress_cb(0.1, "Syncing data folder...")
    sync_data_folder()

    if progress_cb:
        progress_cb(0.25, "Deleting old FAISS index...")
    if FAISS_INDEX_DIR.exists():
        shutil.rmtree(FAISS_INDEX_DIR)

    if progress_cb:
        progress_cb(0.4, "Checking for unreadable files...")
    quarantined = []  # list of (original_path, quarantine_path)
    for name in st.session_state.uploaded_names:
        fp = DATA_DIR / name
        if fp.exists() and not has_extractable_text(fp):
            q_path = fp.with_suffix(fp.suffix + ".skipped")
            fp.rename(q_path)
            quarantined.append((fp, q_path))
            print(f"[build] Quarantined '{name}' — no extractable text found.")

    if progress_cb:
        progress_cb(0.55, "Rebuilding vector store from data/...")
    try:
        build_vector_store()
    finally:
        for original, q_path in quarantined:
            if q_path.exists():
                q_path.rename(original)

    if progress_cb:
        progress_cb(0.9, "Reloading retriever...")
    st.cache_resource.clear()
    st.session_state.pop(RETRIEVER_KEY, None)
    retriever = get_retriever()

    if progress_cb:
        progress_cb(1.0, "Knowledge base ready!")

    skipped_names = [original.name for original, _ in quarantined]
    return retriever, skipped_names


# ==============================================================================
# Helpers — summarization & flashcards
# ==============================================================================
def summarize_documents(llm, retriever, max_chars: int = 12000) -> str:
    docs = get_all_docs(retriever)
    if not docs:
        return "⚠️ No indexed documents found — build the knowledge base first."
    combined = "\n\n".join(d.page_content for d in docs)[:max_chars]
    prompt = (
        "Summarize the following document content for someone who hasn't read it. "
        "Use clear section headers and concise bullet points covering key themes, "
        "facts, and conclusions.\n\nCONTENT:\n" + combined
    )
    response = llm.invoke(prompt)
    return extract_answer_text(response)


def generate_flashcards(llm, retriever, num_cards: int = 8, max_chars: int = 12000):
    docs = get_all_docs(retriever)
    if not docs:
        return []
    combined = "\n\n".join(d.page_content for d in docs)[:max_chars]
    prompt = (
        f"Create exactly {num_cards} study flashcards from the content below. "
        "Strictly use this format with no extra commentary:\n"
        "Q: <question>\nA: <answer>\n\n"
        f"CONTENT:\n{combined}"
    )
    response = llm.invoke(prompt)
    text = extract_answer_text(response)

    cards, q = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Q:"):
            q = line[2:].strip()
        elif line.startswith("A:") and q:
            cards.append((q, line[2:].strip()))
            q = None
    return cards


def render_flashcards(cards):
    """Builds the flip-card grid as ONE unbroken HTML line (no blank lines,
    no leading indentation). Blank lines / 4+-space-indented lines between
    cards were causing Streamlit's markdown renderer to close the HTML block
    after card 1, so every card after that showed up as literal HTML text."""
    card_blocks = []
    for q, a in cards:
        safe_q = html.escape(str(q)).replace("\n", " ")
        safe_a = html.escape(str(a)).replace("\n", " ")
        card_blocks.append(
            '<div class="flashcard"><div class="flashcard-inner">'
            f'<div class="flashcard-front">❓ {safe_q}</div>'
            f'<div class="flashcard-back">✅ {safe_a}</div>'
            '</div></div>'
        )
    cards_html = '<div class="flashcard-grid">' + "".join(card_blocks) + "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
    st.markdown('<div class="flashcard-hint">Hover a card to flip it.</div>', unsafe_allow_html=True)


# ==============================================================================
# Helpers — transcript / share
# ==============================================================================
def build_transcript(history) -> str:
    lines = ["# LocalDocs AI Assistant — Conversation Export",
              f"_Exported {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n"]
    for msg in history:
        role = "You" if msg["role"] == "user" else "AI Assistant"
        lines.append(f"**{role}:** {msg['content']}")
        if msg["role"] == "assistant":
            if msg.get("confidence") is not None:
                lines.append(f"_Confidence: {round(msg['confidence']*100)}%_")
            if msg.get("sources"):
                lines.append("Sources: " + ", ".join(msg["sources"]))
        lines.append("")
    return "\n".join(lines)


def share_current_chat() -> str:
    chat = current_chat()
    share_id = uuid.uuid4().hex[:10]
    payload = {
        "name": chat["name"],
        "history": chat["history"],
        "shared_at": datetime.now().isoformat(),
    }
    with open(SHARE_DIR / f"{share_id}.json", "w") as f:
        json.dump(payload, f, default=str)
    return share_id


# ==============================================================================
# Sidebar
# ==============================================================================
with st.sidebar:
    st.markdown("### 💬 Chats")
    if st.button("➕ New Chat", use_container_width=True):
        new_chat()
        st.rerun()

    for cid, chat in st.session_state.chats.items():
        active = cid == st.session_state.current_chat_id
        col_a, col_b = st.columns([5, 1])
        with col_a:
            if st.button(("🟣 " if active else "💬 ") + chat["name"], key=f"switch_{cid}",
                         use_container_width=True):
                st.session_state.current_chat_id = cid
                st.rerun()
        with col_b:
            if len(st.session_state.chats) > 1 and st.button("✕", key=f"del_{cid}"):
                del st.session_state.chats[cid]
                if st.session_state.current_chat_id == cid:
                    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
                st.rerun()

    st.markdown("---")
    st.markdown("### 📤 Upload Documents")
    uploaded_files = st.file_uploader(
        "Drag & drop files here", type=ALLOWED_TYPES, accept_multiple_files=True,
        help="Supported: PDF, DOCX, PPTX, TXT, CSV, PNG, JPG",
    )
    if uploaded_files:
        newly_added = False
        for uf in uploaded_files:
            out_path = DATA_DIR / uf.name
            with open(out_path, "wb") as f:
                f.write(uf.getbuffer())
            if uf.name not in st.session_state.uploaded_names:
                st.session_state.uploaded_names.append(uf.name)
                newly_added = True
        if newly_added:
            # Files changed — the old knowledge base no longer reflects what's on disk.
            st.session_state.kb_built = False
            st.session_state.summary_text = None
            st.session_state.flashcards = None

    if st.session_state.uploaded_names:
        st.markdown("**Uploaded Files**")
        for name in list(st.session_state.uploaded_names):
            fcol1, fcol2 = st.columns([5, 1])
            with fcol1:
                st.markdown(f'<span class="file-badge">✅ {html.escape(name)}</span>', unsafe_allow_html=True)
            with fcol2:
                if st.button("✕", key=f"rmfile_{name}", help=f"Remove {name}"):
                    st.session_state.uploaded_names.remove(name)
                    for suffix in ("", ".ocr.txt"):
                        p = DATA_DIR / (name + suffix)
                        if p.exists():
                            p.unlink()
                    st.session_state.kb_built = False
                    st.session_state.summary_text = None
                    st.session_state.flashcards = None
                    st.rerun()

        if st.button("🧹 Clear All Files", use_container_width=True):
            for name in st.session_state.uploaded_names:
                for suffix in ("", ".ocr.txt"):
                    p = DATA_DIR / (name + suffix)
                    if p.exists():
                        p.unlink()
            if FAISS_INDEX_DIR.exists():
                shutil.rmtree(FAISS_INDEX_DIR)
            st.session_state.uploaded_names = []
            st.session_state.kb_built = False
            st.session_state.summary_text = None
            st.session_state.flashcards = None
            st.cache_resource.clear()
            st.session_state.pop(RETRIEVER_KEY, None)
            st.rerun()

    if not st.session_state.kb_built and st.session_state.uploaded_names:
        st.warning("⚠️ Files changed since the last build — click **Build Knowledge Base** to refresh answers.")

    st.session_state.ocr_enabled = st.checkbox("🔍 Enable OCR for scanned PDFs/images",
                                                value=st.session_state.ocr_enabled)
    st.session_state.hybrid_search = st.checkbox("🧬 Hybrid Search (vector + keyword)",
                                                  value=st.session_state.hybrid_search)

    st.markdown("")
    build_disabled = len(st.session_state.uploaded_names) == 0
    if st.button("🏗️ Build Knowledge Base", use_container_width=True,
                 disabled=build_disabled, type="primary"):
        progress_bar = st.progress(0, text="Starting...")
        try:
            file_paths = [str(DATA_DIR / n) for n in st.session_state.uploaded_names]

            if st.session_state.ocr_enabled:
                progress_bar.progress(0.08, text="Running OCR on scanned pages...")
                run_ocr_pass(file_paths)

            def _cb(fraction, message):
                # OCR already used up to ~10%; scale the rest of the rebuild into 10-100%
                progress_bar.progress(0.1 + fraction * 0.9, text=message)

            new_retriever, skipped_files = rebuild_knowledge_base(progress_cb=_cb)
            st.session_state[RETRIEVER_KEY] = new_retriever
            st.session_state.kb_built = True
            st.session_state["_kb_version"] = st.session_state.get("_kb_version", 0) + 1
            st.session_state.summary_text = None
            st.session_state.flashcards = None

            built_count = len(st.session_state.uploaded_names) - len(skipped_files)
            st.success(f"Knowledge base rebuilt from {built_count} file(s) "
                       f"(old index deleted, data/ synced).")

            if skipped_files:
                st.warning(
                    "⚠️ Skipped file(s) with no extractable text (likely scanned/image-only "
                    "PDFs where OCR didn't run or failed): " + ", ".join(skipped_files) +
                    ". They're still in your file list — install `pymupdf` + `easyocr` "
                    "(`pip install pymupdf easyocr`), make sure OCR is enabled, and rebuild."
                )
        except Exception as e:
            st.error(f"Failed to build knowledge base: {e}")

    if st.session_state.kb_built:
        st.markdown('<span class="status-pill" style="background:#22c55e30;color:#22c55e;">'
                     '● Knowledge base ready</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill" style="background:#eab30830;color:#eab308;">'
                     '● Not built yet</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🧠 Document Tools")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        summarize_clicked = st.button("📝 Summarize", use_container_width=True,
                                       disabled=not st.session_state.kb_built)
    with tcol2:
        flashcards_clicked = st.button("🃏 Flashcards", use_container_width=True,
                                        disabled=not st.session_state.kb_built)
    num_cards = st.slider("Number of flashcards", 4, 20, 8)

    if summarize_clicked:
        with st.spinner("Summarizing documents..."):
            llm = safe_get_llm(show_error=False)
            if llm is None:
                st.session_state.summary_text = None
                st.session_state["_llm_error"] = True
                st.session_state["_tool_error"] = None
            else:
                st.session_state["_llm_error"] = False
                try:
                    retriever = st.session_state.get(RETRIEVER_KEY) or get_retriever()
                    st.session_state[RETRIEVER_KEY] = retriever
                    st.session_state.summary_text = summarize_documents(llm, retriever)
                    st.session_state["_tool_error"] = None
                except Exception as e:
                    st.session_state.summary_text = None
                    st.session_state["_tool_error"] = friendly_llm_error(e)

    if flashcards_clicked:
        with st.spinner("Generating flashcards..."):
            llm = safe_get_llm(show_error=False)
            if llm is None:
                st.session_state.flashcards = None
                st.session_state["_llm_error"] = True
                st.session_state["_tool_error"] = None
            else:
                st.session_state["_llm_error"] = False
                try:
                    retriever = st.session_state.get(RETRIEVER_KEY) or get_retriever()
                    st.session_state[RETRIEVER_KEY] = retriever
                    st.session_state.flashcards = generate_flashcards(llm, retriever, num_cards=num_cards)
                    st.session_state["_tool_error"] = None
                except Exception as e:
                    st.session_state.flashcards = None
                    st.session_state["_tool_error"] = friendly_llm_error(e)

    st.markdown("---")
    st.markdown("### 📊 Session Analytics")
    elapsed = datetime.now() - st.session_state.session_start
    mins, secs = int(elapsed.total_seconds() // 60), int(elapsed.total_seconds() % 60)
    avg_conf = (
        round(sum(st.session_state.confidence_scores) / len(st.session_state.confidence_scores) * 100)
        if st.session_state.confidence_scores else 0
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="metric-card"><b>{len(st.session_state.uploaded_names)}</b><br>'
                     f'<span style="font-size:0.75rem;">Files</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><b>{st.session_state.total_queries}</b><br>'
                     f'<span style="font-size:0.75rem;">Queries</span></div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f'<div class="metric-card"><b>{avg_conf}%</b><br>'
                     f'<span style="font-size:0.75rem;">Avg Confidence</span></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><b>{mins}m {secs}s</b><br>'
                     f'<span style="font-size:0.75rem;">Session Time</span></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 💾 Export & Share")

    chat = current_chat()
    if chat["history"]:
        st.download_button(
            "⬇️ Download Conversation",
            data=build_transcript(chat["history"]),
            file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

        if st.button("🔗 Share Conversation", use_container_width=True):
            share_id = share_current_chat()
            st.query_params["share_generated"] = share_id
            st.session_state["_last_share_id"] = share_id

        if st.session_state.get("_last_share_id"):
            sid = st.session_state["_last_share_id"]
            st.text_input("Share link param (append to your app URL):", value=f"?share={sid}",
                          key="share_link_display")
            st.markdown(
                f"""
                <button class="copy-btn" onclick="navigator.clipboard.writeText(
                    window.location.origin + window.location.pathname + '?share={sid}'
                ); this.innerText='✅ Copied!'">📋 Copy Link</button>
                """,
                unsafe_allow_html=True,
            )

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        chat["history"] = []
        st.session_state.total_queries = 0
        st.session_state.confidence_scores = []
        st.rerun()


# ==============================================================================
# Main header
# ==============================================================================
_status_dot = "🟢" if st.session_state.kb_built else "🟡"
_status_text = "Knowledge base ready" if st.session_state.kb_built else "Waiting for documents"
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-row">
            <div>
                <h1>📚 LocalDocs AI Assistant</h1>
                <p>Upload your documents, build a knowledge base, and chat with your files —
                with citations, confidence scores, memory, OCR and hybrid search.</p>
            </div>
            <div class="hero-status">{_status_dot} {_status_text}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.get("_llm_error"):
    render_setup_card("The AI model couldn't be reached, so this tool has no answer to show.")

if st.session_state.get("_tool_error"):
    render_tool_error(st.session_state["_tool_error"])

if not st.session_state.kb_built:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">🗂️</div>
            <div class="empty-state-title">Let's build your knowledge base</div>
            <div class="empty-state-text">
                Drop PDFs, DOCX, PPTX, TXT, CSV or images into the sidebar, then hit
                <b>Build Knowledge Base</b>. Once it's ready you can chat, summarize
                and generate flashcards from your own documents.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if st.session_state.summary_text:
    with st.expander("📋 Document Summary", expanded=True):
        st.markdown(st.session_state.summary_text)

if st.session_state.flashcards:
    with st.expander(f"🃏 Flashcards ({len(st.session_state.flashcards)})", expanded=True):
        render_flashcards(st.session_state.flashcards)

if st.session_state.kb_built:
    st.markdown('<div class="section-label">💡 Try asking</div>', unsafe_allow_html=True)
    sq_cols = st.columns(len(SAMPLE_QUESTIONS))
    for i, sq in enumerate(SAMPLE_QUESTIONS):
        with sq_cols[i]:
            if st.button(sq, key=f"sample_{i}", use_container_width=True, disabled=not st.session_state.kb_built):
                st.session_state.pending_question = sq

st.markdown("")

# ==============================================================================
# Chat render
# ==============================================================================
chat = current_chat()

for msg in chat["history"]:
    with st.chat_message("user" if msg["role"] == "user" else "assistant",
                          avatar="🧑" if msg["role"] == "user" else "🤖"):
        st.write(msg["content"])
        if msg["role"] == "assistant":
            if msg.get("confidence") is not None:
                render_confidence_bar(msg["confidence"])
            if msg.get("source_details"):
                with st.expander(f"📄 Sources ({len(msg['source_details'])})"):
                    for name, sim in msg["source_details"]:
                        render_source(name, sim)

typed_question = st.chat_input(
    "Ask a question about your documents..." if st.session_state.kb_built else "Build a knowledge base first...",
    disabled=not st.session_state.kb_built,
)
if typed_question:
    st.session_state.pending_question = typed_question

# ==============================================================================
# Process pending question
# ==============================================================================
if st.session_state.pending_question and st.session_state.kb_built:
    question = st.session_state.pending_question
    st.session_state.pending_question = None

    chat["history"].append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.write(question)

    if RETRIEVER_KEY not in st.session_state:
        st.session_state[RETRIEVER_KEY] = get_retriever()
    retriever = st.session_state[RETRIEVER_KEY]
    llm = safe_get_llm(show_error=False)

    if llm is None:
        with st.chat_message("assistant", avatar="🤖"):
            render_setup_card(
                "Your question was received, but there's no configured Gemini "
                "API key to answer it with."
            )
        chat["history"].append({
            "role": "assistant",
            "content": "⚠️ I can't answer yet — the Gemini API key isn't configured. "
                       "See the setup card above for how to add it.",
            "confidence": None,
            "source_details": None,
            "sources": [],
        })
        st.stop()

    with st.chat_message("assistant", avatar="🤖"):
        status = st.empty()
        status.markdown("🔎 _Searching your documents (hybrid)..._" if st.session_state.hybrid_search
                         else "🔎 _Searching your documents..._")
        docs_scores = get_context_and_scores(retriever, question, k=4)
        time.sleep(0.2)

        status.markdown("🧠 _Thinking..._")
        retrieved_context = "\n\n".join(doc.page_content for doc, _ in docs_scores)
        memory_context = build_conversation_memory(chat["history"][:-1])

        full_context = retrieved_context
        if memory_context:
            full_context = f"Previous conversation:\n{memory_context}\n\nRetrieved context:\n{retrieved_context}"

        prompt = RAG_PROMPT.format(context=full_context, question=question)

        try:
            with st.spinner(""):
                response = llm.invoke(prompt)
            answer = extract_answer_text(response)
        except Exception as e:
            status.empty()
            err_msg = friendly_llm_error(e)
            render_tool_error(err_msg)
            chat["history"].append({
                "role": "assistant",
                "content": f"⚠️ {err_msg}",
                "confidence": None,
                "source_details": None,
                "sources": [],
            })
            st.stop()

        status.empty()
        answer_placeholder = st.empty()
        typing_effect(answer_placeholder, answer)

        confidence = sum(s for _, s in docs_scores) / len(docs_scores) if docs_scores else 0.6
        render_confidence_bar(confidence)

        source_details = dedupe_sources(
            [(doc.metadata.get("source", "Unknown"), score) for doc, score in docs_scores]
        )
        if source_details:
            with st.expander(f"📄 Sources ({len(source_details)})"):
                for name, sim in source_details:
                    render_source(name, sim)

    chat["history"].append({
        "role": "assistant",
        "content": answer,
        "confidence": confidence,
        "source_details": source_details,
        "sources": [s[0] for s in source_details],
    })
    st.session_state.total_queries += 1
    st.session_state.confidence_scores.append(confidence)
    st.rerun()