"""
LocalDocs AI Assistant — NotebookLM-style RAG UI
--------------------------------------------------
Pure Streamlit UI layer. Uses only your existing modules:
    rag.retriever.get_retriever()
    rag.prompt.RAG_PROMPT
    llm.gemini.get_llm()

Assumes get_retriever() (re)builds / loads the FAISS index from the
files saved into data/ — call it after uploading to refresh the index.
"""

import time
from pathlib import Path
from datetime import datetime
from app import build_vector_store

import streamlit as st

from rag.retriever import get_retriever
from rag.prompt import RAG_PROMPT
from llm.gemini import get_llm

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = ["pdf", "docx", "pptx", "txt", "csv"]

SAMPLE_QUESTIONS = [
    "Summarize this document in 5 bullet points",
    "What are the key findings or conclusions?",
    "List any numbers, dates, or statistics mentioned",
    "What questions might someone ask about this content?",
]

BUILD_STEPS = [
    (0.15, "Reading uploaded files..."),
    (0.40, "Splitting text into chunks..."),
    (0.65, "Generating embeddings..."),
    (0.85, "Building FAISS vector index..."),
    (1.00, "Knowledge base ready!"),
]

# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="LocalDocs AI Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
_defaults = {
    "chat_history": [],
    "kb_built": False,
    "uploaded_names": [],
    "theme": "dark",
    "total_queries": 0,
    "confidence_scores": [],
    "session_start": datetime.now(),
    "pending_question": None,
}
for key, val in _defaults.items():
    st.session_state.setdefault(key, val)

RETRIEVER_KEY = "_retriever_obj"


# ----------------------------------------------------------------------------
# Theming / CSS
# ----------------------------------------------------------------------------
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
        section[data-testid="stSidebar"] {{
            background: {panel};
            border-right: 1px solid {border};
        }}
        .hero {{
            padding: 1.4rem 1.8rem;
            border-radius: 18px;
            background: linear-gradient(120deg, {accent1}22, {accent2}22);
            border: 1px solid {border};
            margin-bottom: 1.2rem;
        }}
        .hero h1 {{
            font-size: 2rem;
            margin: 0 0 0.2rem 0;
            background: linear-gradient(90deg, {accent1}, {accent2});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
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
        .conf-track {{
            width: 100%; height: 8px; border-radius: 999px;
            background: {border}; overflow: hidden;
        }}
        .conf-fill {{ height: 100%; border-radius: 999px; }}
        .source-chip {{
            background: {card}; border: 1px solid {border};
            border-radius: 10px; padding: 8px 12px; margin-bottom: 6px;
            font-size: 0.85rem;
        }}
        .sim-track {{
            width: 100%; height: 6px; border-radius: 999px;
            background: {border}; overflow: hidden; margin-top: 4px;
        }}
        .sim-fill {{
            height: 100%; border-radius: 999px;
            background: linear-gradient(90deg, {accent2}, {accent1});
        }}
        .status-pill {{
            display: inline-block; padding: 2px 10px;
            border-radius: 999px; font-size: 0.75rem; font-weight: 600;
        }}
        div[data-testid="stChatMessage"] {{
            border-radius: 16px; border: 1px solid {border};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


load_css(st.session_state.theme)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
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


def get_context_and_scores(retriever, question: str, k: int = 4):
    """
    Tries a few retriever/vectorstore APIs to get (doc, similarity_score) pairs.
    Falls back to plain retrieval with estimated descending confidence
    if the underlying vectorstore doesn't expose scores.
    """
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


def build_transcript() -> str:
    lines = [
        "# LocalDocs AI Assistant — Conversation Export",
        f"_Exported {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n",
    ]
    for msg in st.session_state.chat_history:
        role = "You" if msg["role"] == "user" else "AI Assistant"
        lines.append(f"**{role}:** {msg['content']}")
        if msg["role"] == "assistant":
            if msg.get("confidence") is not None:
                lines.append(f"_Confidence: {round(msg['confidence']*100)}%_")
            if msg.get("sources"):
                lines.append("Sources: " + ", ".join(msg["sources"]))
        lines.append("")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Workspace")

    theme_choice = st.radio("Theme", ["dark", "light"], horizontal=True,
                            index=0 if st.session_state.theme == "dark" else 1)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

    st.markdown("---")
    st.markdown("### 📤 Upload Documents")
    uploaded_files = st.file_uploader(
        "Drag & drop files here",
        type=ALLOWED_TYPES,
        accept_multiple_files=True,
        help="Supported: PDF, DOCX, PPTX, TXT, CSV",
    )

    import shutil

    if uploaded_files:
        # Remove old uploaded documents
        shutil.rmtree(DATA_DIR, ignore_errors=True)
        DATA_DIR.mkdir(exist_ok=True)

        st.session_state.uploaded_names = []

        for uf in uploaded_files:
            out_path = DATA_DIR / uf.name

            with open(out_path, "wb") as f:
                f.write(uf.getbuffer())

            st.session_state.uploaded_names.append(uf.name)

    if st.session_state.uploaded_names:
        st.markdown("**Uploaded Files**")
        badge_html = "".join(
            f'<span class="file-badge">✅ {name}</span>' for name in st.session_state.uploaded_names
        )
        st.markdown(badge_html, unsafe_allow_html=True)

    st.markdown("")
    build_disabled = len(st.session_state.uploaded_names) == 0
    if st.button("🏗️ Build Knowledge Base", use_container_width=True,
                disabled=build_disabled, type="primary"):
        progress_bar = st.progress(0, text="Starting...")
        try:
            for frac, msg in BUILD_STEPS:
                progress_bar.progress(frac, text=msg)
                time.sleep(0.35)

            import shutil

            # Remove old FAISS index
            shutil.rmtree("database/faiss_index", ignore_errors=True)

            # Build a new vector database from uploaded files
            build_vector_store()

            # Reload retriever
            st.session_state.pop(RETRIEVER_KEY, None)
            st.session_state[RETRIEVER_KEY] = get_retriever()

            st.session_state.kb_built = True
            st.success(f"Knowledge base built from {len(st.session_state.uploaded_names)} file(s).")
        except Exception as e:
            st.error(f"Failed to build knowledge base: {e}")

    if st.session_state.kb_built:
        st.markdown(
            '<span class="status-pill" style="background:#22c55e30;color:#22c55e;">● Knowledge base ready</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-pill" style="background:#eab30830;color:#eab308;">● Not built yet</span>',
            unsafe_allow_html=True,
        )

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
    st.markdown("### 💾 Export & Reset")

    if st.session_state.chat_history:
        st.download_button(
            "⬇️ Download Conversation",
            data=build_transcript(),
            file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.total_queries = 0
        st.session_state.confidence_scores = []
        st.rerun()


# ----------------------------------------------------------------------------
# Main header
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>📚 LocalDocs AI Assistant</h1>
        <p>Upload your documents, build a knowledge base, and chat with your files —
        with citations, confidence scores, and source similarity.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.kb_built:
    st.info("👈 Upload files and click **Build Knowledge Base** in the sidebar to get started.")

st.markdown("**💡 Try asking:**")
sq_cols = st.columns(len(SAMPLE_QUESTIONS))
for i, sq in enumerate(SAMPLE_QUESTIONS):
    with sq_cols[i]:
        if st.button(sq, key=f"sample_{i}", use_container_width=True, disabled=not st.session_state.kb_built):
            st.session_state.pending_question = sq

st.markdown("")

# ----------------------------------------------------------------------------
# Chat history render
# ----------------------------------------------------------------------------
for msg in st.session_state.chat_history:
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

# ----------------------------------------------------------------------------
# Chat input
# ----------------------------------------------------------------------------
typed_question = st.chat_input(
    "Ask a question about your documents..." if st.session_state.kb_built else "Build a knowledge base first...",
    disabled=not st.session_state.kb_built,
)
if typed_question:
    st.session_state.pending_question = typed_question

# ----------------------------------------------------------------------------
# Process pending question
# ----------------------------------------------------------------------------
if st.session_state.pending_question and st.session_state.kb_built:
    question = st.session_state.pending_question
    st.session_state.pending_question = None

    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.write(question)

    if RETRIEVER_KEY not in st.session_state:
        st.session_state[RETRIEVER_KEY] = get_retriever()
    retriever = st.session_state[RETRIEVER_KEY]
    llm = get_llm()

    with st.chat_message("assistant", avatar="🤖"):
        status = st.empty()
        status.markdown("🔎 _Searching your documents..._")
        docs_scores = get_context_and_scores(retriever, question, k=4)
        time.sleep(0.3)

        status.markdown("🧠 _Thinking..._")
        context = "\n\n".join(doc.page_content for doc, _ in docs_scores)
        prompt = RAG_PROMPT.format(context=context, question=question)

        with st.spinner(""):
            response = llm.invoke(prompt)

        if isinstance(response.content, list):
            answer = "".join(
                block["text"] for block in response.content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            answer = response.content

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

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer,
        "confidence": confidence,
        "source_details": source_details,
        "sources": [s[0] for s in source_details],
    })
    st.session_state.total_queries += 1
    st.session_state.confidence_scores.append(confidence)
    st.rerun()