from loaders.pdf_loader import load_pdf
from loaders.docx_loader import load_docx
from loaders.ppt_loader import load_ppt
from loaders.txt_loader import load_txt
from loaders.csv_loader import load_csv
from loaders.md_loader import load_md


def load_document(file_path):
    """
    Detect -> load -> extract for one file. Always returns a List[Document]
    (never a single Document) so every caller (index_builder, the upload
    endpoint) has one consistent shape to handle, regardless of whether the
    underlying loader is per-page (pdf/pptx) or whole-file (docx/txt/csv).
    Returns None for unsupported extensions, [] if the loader ran but
    produced nothing.
    """

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        result = load_pdf(file_path)

    elif extension == ".docx":
        result = load_docx(file_path)

    elif extension == ".pptx":
        result = load_ppt(file_path)

    elif extension == ".txt":
        result = load_txt(file_path)

    elif extension == ".csv":
        result = load_csv(file_path)

    elif extension == ".md":
        result = load_md(file_path)

    else:
        return None

    if result is None:
        return []
    if isinstance(result, list):
        return result
    return [result]
