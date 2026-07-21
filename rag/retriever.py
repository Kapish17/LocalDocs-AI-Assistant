from pathlib import Path

from langchain_community.vectorstores import FAISS

from rag.embeddings import get_embedding_model


VECTOR_DB_PATH = Path("database/faiss_index")


def load_vector_store():
    """
    Loads the saved FAISS vector database.
    """

    embedding_model = get_embedding_model()

    vector_store = FAISS.load_local(
        folder_path=str(VECTOR_DB_PATH),
        embeddings=embedding_model,
        allow_dangerous_deserialization=True
    )

    return vector_store


def get_retriever(k=4):
    """
    Returns a retriever for semantic search.
    """

    vector_store = load_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={"k": k}
    )

    return retriever