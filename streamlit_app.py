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
    - OCR support for scanned PDFs / images
    - Hybrid search (vector + BM25 keyword)
    - Flashcard generation (flip cards)
"""

import time
import json
import uuid
from pathlib import Path
from datetime import datetime

import streamlit as st

from rag.retriever import get_retriever
from rag.prompt import RAG_PROMPT
from llm.gemini import get_llm

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SHARE_DIR = Path("shared_chats")
SHARE_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = ["pdf", "docx", "pptx", "txt", "csv", "png", "jpg", "jpeg"]

SAMPLE_QUESTIONS = [
    "Summarize this document in 5 bullet points",
    "What are the key findings or conclusions?",
    "List any numbers, dates, or statistics mentioned",
    "What questions might someone ask about this content?",
]

BUILD_STEPS = [
    (0.15, "Reading uploaded files..."),
    (0.40, "Running OCR on scanned pages..."),
    (0.60, "Splitting text into chunks..."),
    (0.80, "Generating embeddings..."),
    (0.92, "Building FAISS vector index..."),
    (1.00, "Knowledge base ready!"),
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
    "theme": "dark",
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
# Theming / CSS
# ==============================================================================
def load_css(theme: str):
    if theme == "dark":
        bg, panel, card = "#0b0e14", "#111420", "#161a26"
        text, subtext = "#e8ecf6", "#9aa4bd"
        border = "#242a3d"
        accent1, accent2 = "#7c5cff", "#22d3ee"
    else:
        bg, panel, card = "#f5f6fa", "#ffffff", "#ffffff"
        text, subtext = "#1a1d29", "#5b6172"
        border = "#e4e6ee"
        accent1, accent2 = "#6c5ce7", "#00b4d8"

    st.markdown(
        f"""
        <style>
        .stApp {{ background: {bg}; color: {text}; }}
        section[data-testid="stSidebar"] {{ background: {panel}; border-right: 1px solid {border}; }}
        .hero {{
            padding: 1.4rem 1.8rem; border-radius: 18px;
            background: linear-gradient(120deg, {accent1}22, {accent2}22);
            border: 1px solid {border}; margin-bottom: 1.2rem;
        }}
        .hero h1 {{
            font-size: 2rem; margin: 0 0 0.2rem 0;
            background: linear-gradient(90deg, {accent1}, {accent2});
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;
        }}
        .hero p {{ color: {subtext}; margin: 0; font-size: 0.95rem; }}
        .file-badge {{
            display: inline-flex; align-items: center; gap: 6px;
            background: {card}; border: 1px solid {border};
            padding: 6px 12px; border-radius: 999px;
            font-size: 0.82rem; margin: 3px 4px 3px 0; color: {text};
        }}
        .metric-card {{
            background: {card}; border: 1px solid {border};
            border-radius: 14px; padding: 10px 14px; text-align: center;
        }}
        .conf-wrap {{ margin-top: 6px; margin-bottom: 4px; }}
        .conf-label {{
            font-size: 0.75rem; color: {subtext};
            display: flex; justify-content: space-between; margin-bottom: 3px;
        }}
        .conf-track {{ width: 100%; height: 8px; border-radius: 999px; background: {border}; overflow: hidden; }}
        .conf-fill {{ height: 100%; border-radius: 999px; }}
        .source-chip {{
            background: {card}; border: 1px solid {border};
            border-radius: 10px; padding: 8px 12px; margin-bottom: 6px; font-size: 0.85rem;
        }}
        .sim-track {{ width: 100%; height: 6px; border-radius: 999px; background: {border}; overflow: hidden; margin-top: 4px; }}
        .sim-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, {accent2}, {accent1}); }}
        .status-pill {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
        div[data-testid="stChatMessage"] {{ border-radius: 16px; border: 1px solid {border}; }}

        .chat-list-item {{
            padding: 6px 10px; border-radius: 10px; margin-bottom: 4px;
            font-size: 0.85rem; cursor: pointer;
        }}
        .chat-list-item.active {{ background: {accent1}33; border: 1px solid {accent1}; }}

        .copy-btn {{
            background: linear-gradient(90deg, {accent1}, {accent2});
            color: white; border: none; border-radius: 8px;
            padding: 8px 14px; font-size: 0.85rem; cursor: pointer; width: 100%;
        }}

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


load_css(st.session_state.theme)


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
            📄 <b>{name}</b>
            <div class="sim-track"><div class="sim-fill" style="width:{pct}%;"></div></div>
            <div style="font-size:0.72rem;color:#9aa4bd;margin-top:2px;">Similarity match: {pct}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
# Helpers — OCR
# ==============================================================================
def needs_ocr(pdf_path: Path, min_chars: int = 40) -> bool:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        text = "".join((page.extract_text() or "") for page in reader.pages[:3])
        return len(text.strip()) < min_chars
    except Exception:
        return True


def ocr_extract(file_path: Path) -> str:
    """Runs OCR on a scanned PDF or image and returns extracted text (empty on failure)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    ext = file_path.suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            from pdf2image import convert_from_path
            for img in convert_from_path(str(file_path)):
                text += pytesseract.image_to_string(img) + "\n"
        elif ext in (".png", ".jpg", ".jpeg"):
            text = pytesseract.image_to_string(Image.open(file_path))
    except Exception as e:
        st.warning(f"OCR failed for {file_path.name}: {e}")
    return text.strip()


def run_ocr_pass(file_paths, progress_cb=None) -> int:
    """For scanned PDFs / images, writes a companion .ocr.txt file next to the
    original so your existing ingestion (get_retriever) can pick it up."""
    processed = 0
    candidates = [p for p in file_paths if Path(p).suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg")]
    for i, fp in enumerate(candidates):
        path = Path(fp)
        should_ocr = path.suffix.lower() != ".pdf" or needs_ocr(path)
        if should_ocr:
            text = ocr_extract(path)
            if text:
                out_path = path.with_suffix(path.suffix + ".ocr.txt")
                out_path.write_text(text, encoding="utf-8")
                processed += 1
        if progress_cb:
            progress_cb((i + 1) / max(len(candidates), 1))
    return processed


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
    cards_html = '<div class="flashcard-grid">'
    for q, a in cards:
        cards_html += f"""
        <div class="flashcard">
            <div class="flashcard-inner">
                <div class="flashcard-front">❓ {q}</div>
                <div class="flashcard-back">✅ {a}</div>
            </div>
        </div>
        """
    cards_html += "</div>"
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
    st.markdown("### ⚙️ Workspace")
    theme_choice = st.radio("Theme", ["dark", "light"], horizontal=True,
                             index=0 if st.session_state.theme == "dark" else 1)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

    st.markdown("---")
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
                st.markdown(f'<span class="file-badge">✅ {name}</span>', unsafe_allow_html=True)
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
            st.session_state.uploaded_names = []
            st.session_state.kb_built = False
            st.session_state.summary_text = None
            st.session_state.flashcards = None
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

            for frac, msg in BUILD_STEPS:
                if msg.startswith("Running OCR") and not st.session_state.ocr_enabled:
                    continue
                progress_bar.progress(frac, text=msg)
                if msg.startswith("Running OCR"):
                    run_ocr_pass(file_paths)
                else:
                    time.sleep(0.3)

            # IMPORTANT: if rag/retriever.py's get_retriever() is wrapped in
            # @st.cache_resource, popping it from session_state alone won't help —
            # Streamlit will still hand back the OLD cached FAISS index built from
            # OLD files. Clearing the global resource cache forces a real rebuild.
            st.cache_resource.clear()
            st.session_state.pop(RETRIEVER_KEY, None)
            st.session_state[RETRIEVER_KEY] = get_retriever()
            st.session_state.kb_built = True
            st.session_state["_kb_version"] = st.session_state.get("_kb_version", 0) + 1
            st.session_state.summary_text = None
            st.session_state.flashcards = None
            st.success(f"Knowledge base built from {len(st.session_state.uploaded_names)} file(s).")
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
            retriever = st.session_state.get(RETRIEVER_KEY) or get_retriever()
            st.session_state[RETRIEVER_KEY] = retriever
            st.session_state.summary_text = summarize_documents(get_llm(), retriever)

    if flashcards_clicked:
        with st.spinner("Generating flashcards..."):
            retriever = st.session_state.get(RETRIEVER_KEY) or get_retriever()
            st.session_state[RETRIEVER_KEY] = retriever
            st.session_state.flashcards = generate_flashcards(get_llm(), retriever, num_cards=num_cards)

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
st.markdown(
    """
    <div class="hero">
        <h1>📚 LocalDocs AI Assistant</h1>
        <p>Upload your documents, build a knowledge base, and chat with your files —
        with citations, confidence scores, memory, OCR and hybrid search.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.kb_built:
    st.info("👈 Upload files and click **Build Knowledge Base** in the sidebar to get started.")

if st.session_state.summary_text:
    with st.expander("📋 Document Summary", expanded=True):
        st.markdown(st.session_state.summary_text)

if st.session_state.flashcards:
    with st.expander(f"🃏 Flashcards ({len(st.session_state.flashcards)})", expanded=True):
        render_flashcards(st.session_state.flashcards)

st.markdown("**💡 Try asking:**")
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
    llm = get_llm()

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

        with st.spinner(""):
            response = llm.invoke(prompt)
        answer = extract_answer_text(response)

        status.empty()
        answer_placeholder = st.empty()
        typing_effect(answer_placeholder, answer)

        confidence = sum(s for _, s in docs_scores) / len(docs_scores) if docs_scores else 0.6
        render_confidence_bar(confidence)

        source_details = [(doc.metadata.get("source", "Unknown"), score) for doc, score in docs_scores]
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