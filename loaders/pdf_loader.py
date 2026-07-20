from langchain_core.documents import Document
from pypdf import PdfReader


def load_pdf(file_path):
    """
    Reads a PDF file and extracts text.
    """

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return Document(
        page_content=text,
        metadata={
            "source": file_path.name,
            "file_type": "pdf"
        }
    )