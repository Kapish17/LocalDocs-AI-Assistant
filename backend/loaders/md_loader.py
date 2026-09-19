from langchain_core.documents import Document


def load_md(file_path):
    """
    Reads a Markdown file as plain text. utils/file_scanner.py already lists
    .md as a supported extension, but no loader existed for it — meaning a
    .md upload used to silently vanish (load_document returned None, and
    the caller just skipped it with no error). Markdown needs no special
    parsing for RAG purposes; the raw text (headings, lists, etc. included)
    chunks and embeds fine as-is.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    return Document(
        page_content=text,
        metadata={
            "source": file_path.name,
            "file_type": "md",
            "document_id": file_path.name
        }
    )
