"""
Chunking utilities using LangChain.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(documents):
    """
    Splits documents into smaller chunks.

    Args:
        documents (list): List of loaded documents

    Returns:
        list: Chunked documents
    """

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

    chunks = []

    for document in documents:

        text = document["content"]

        filename = document["filename"]

        split_text = splitter.split_text(text)

        for chunk in split_text:

            chunks.append({
                "filename": filename,
                "content": chunk
            })

    return chunks