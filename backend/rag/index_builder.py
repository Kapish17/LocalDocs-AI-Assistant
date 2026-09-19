from pathlib import Path
from typing import Optional

from utils.file_scanner import scan_folder
from loaders.loader_manager import load_document
from rag.chunking import split_documents
from rag.vector_store import create_vector_store


def build_vector_store(data_dir: str = "data", vector_db_path: Optional[Path] = None):
    """
    Scans the data folder, loads documents,
    splits them into chunks, and creates
    a fresh FAISS vector database.

    data_dir/vector_db_path default to the project's global "data" folder
    and rag/vector_store.py's VECTOR_DB_PATH — unchanged behavior for
    app.py / streamlit_app.py. The FastAPI backend passes a per-browser-
    session data_dir/vector_db_path so each session builds its own,
    isolated index from only its own uploaded files — see
    backend/core/sessions.py (DocumentSessionStore) and backend/core/kb.py.
    """

    files = scan_folder(data_dir)

    if not files:
        print("❌ No supported documents found.")
        return

    documents = []

    print("\nLoading documents...\n")

    for file in files:
        try:
            docs_for_file = load_document(file)

            if docs_for_file:
                documents.extend(docs_for_file)
                print(f"✅ Loaded: {file.name} ({len(docs_for_file)} page/section doc(s))")

        except Exception as e:
            print(f"❌ Failed: {file.name}")
            print(e)

    print("\nSplitting documents...\n")

    chunks = split_documents(documents)

    print(f"📄 Documents : {len(documents)}")
    print(f"🧩 Chunks    : {len(chunks)}")

    create_vector_store(chunks, vector_db_path=vector_db_path)
