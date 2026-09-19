from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS

from rag.embeddings import get_embedding_model


VECTOR_DB_PATH = Path("database/faiss_index")


def load_vector_store(vector_db_path: Optional[Path] = None):
    """
    Loads the saved FAISS vector database.

    vector_db_path defaults to the module-level VECTOR_DB_PATH (unchanged
    behavior for app.py). The FastAPI backend passes a
    per-browser-session path so it loads only that session's own index —
    see backend/core/sessions.py (DocumentSessionStore) and backend/core/kb.py.
    """

    path = vector_db_path or VECTOR_DB_PATH

    embedding_model = get_embedding_model()

    vector_store = FAISS.load_local(
        folder_path=str(path),
        embeddings=embedding_model,
        allow_dangerous_deserialization=True
    )

    return vector_store


def get_retriever(k=4, vector_db_path: Optional[Path] = None):
    """
    Returns a retriever for semantic search.
    """

    vector_store = load_vector_store(vector_db_path=vector_db_path)

    retriever = vector_store.as_retriever(
        search_kwargs={"k": k}
    )

    return retriever
