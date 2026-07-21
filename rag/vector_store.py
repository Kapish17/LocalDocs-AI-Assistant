from pathlib import Path

from langchain_community.vectorstores import FAISS

from rag.embeddings import get_embedding_model


# Folder where FAISS index will be saved
VECTOR_DB_PATH = Path("database/faiss_index")


def create_vector_store(chunks):
    """
    Creates a FAISS vector database from document chunks.
    """

    print("\nCreating embeddings...")

    embedding_model = get_embedding_model()

    print("Building FAISS vector store...")

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embedding_model
    )

    VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)

    vector_store.save_local(str(VECTOR_DB_PATH))

    print("✅ Vector database created successfully!")

    return vector_store