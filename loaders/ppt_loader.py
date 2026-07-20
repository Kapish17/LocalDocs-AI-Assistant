from pptx import Presentation


def load_ppt(file_path):

    presentation = Presentation(file_path)

    text = ""

    for slide in presentation.slides:

        for shape in slide.shapes:

            if hasattr(shape, "text"):
                text += shape.text + "\n"

    return {
        "filename": file_path.name,
        "content": text
    }