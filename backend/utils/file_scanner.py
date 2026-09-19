"""
Universal File Scanner

Scans a folder and returns all supported document files.
"""

from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".csv",
    ".md",
}


def scan_folder(folder_path):
    """
    Scan a folder and return all supported files.

    Args:
        folder_path (str): Path of folder

    Returns:
        list[Path]: Supported document paths
    """

    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"{folder_path} does not exist.")

    documents = []

    for file in folder.iterdir():

        if file.is_file():

            if file.suffix.lower() in SUPPORTED_EXTENSIONS:
                documents.append(file)

    return documents