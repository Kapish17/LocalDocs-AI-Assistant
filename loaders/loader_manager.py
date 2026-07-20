from loaders.pdf_loader import load_pdf
from loaders.docx_loader import load_docx
from loaders.ppt_loader import load_ppt
from loaders.txt_loader import load_txt
from loaders.csv_loader import load_csv


def load_document(file_path):

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return load_pdf(file_path)

    elif extension == ".docx":
        return load_docx(file_path)

    elif extension == ".pptx":
        return load_ppt(file_path)

    elif extension == ".txt":
        return load_txt(file_path)

    elif extension == ".csv":
        return load_csv(file_path)

    return None