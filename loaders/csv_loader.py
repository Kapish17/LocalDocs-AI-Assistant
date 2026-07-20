from langchain_core.documents import Document
import pandas as pd


def load_csv(file_path):
    """
    Reads a CSV file and converts it to text.
    """

    dataframe = pd.read_csv(file_path)

    text = dataframe.to_string(index=False)

    return Document(
        page_content=text,
        metadata={
            "source": file_path.name,
            "file_type": "csv"
        }
    )