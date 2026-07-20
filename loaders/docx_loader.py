import docx


def load_docx(file_path):

    document = docx.Document(file_path)

    text = ""

    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"

    return {
        "filename": file_path.name,
        "content": text
    }