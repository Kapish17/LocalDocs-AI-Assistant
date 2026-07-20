"""
Chunking utilities using LangChain.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

print("✅ Using chunking.py from:", __file__)


def split_documents(documents):
    """
    Splits LangChain Document objects into smaller chunks.

    Args:
        documents (list): List of LangChain Document objects

    Returns:
        list: List of chunked LangChain Document objects
    """

    print("✅ split_documents() called")

    print(f"Received {len(documents)} documents")

    if documents:
        print("First document type:", type(documents[0]))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    chunks = splitter.split_documents(documents)

    print(f"Created {len(chunks)} chunks")

    if chunks:
        print("First chunk type:", type(chunks[0]))

    return chunks