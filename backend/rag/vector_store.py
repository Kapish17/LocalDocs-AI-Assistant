from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS

from rag.embeddings import get_embedding_model


# Folder where FAISS index will be saved
VECTOR_DB_PATH = Path("database/faiss_index")


def create_vector_store(chunks, vector_db_path: Optional[Path] = None):
    """
    Creates a FAISS vector database from document chunks.

    vector_db_path defaults to the module-level VECTOR_DB_PATH (unchanged
    behavior for app.py, which calls this with no path).
    The FastAPI backend passes a per-browser-session path here so each
    session's vectors are written to their own folder — see
    backend/core/sessions.py (DocumentSessionStore) and backend/core/kb.py.
    """

    path = vector_db_path or VECTOR_DB_PATH

    print("\nCreating embeddings...")

    embedding_model = get_embedding_model()

    print("Building FAISS vector store...")

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embedding_model
    )

    path.mkdir(parents=True, exist_ok=True)

    vector_store.save_local(str(path))

    print("✅ Vector database created successfully!")

    return vector_store
