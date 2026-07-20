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

    return {
        "filename": file_path.name,
        "content": text
    }