import pandas as pd


def load_csv(file_path):

    dataframe = pd.read_csv(file_path)

    text = dataframe.to_string(index=False)

    return {
        "filename": file_path.name,
        "content": text
    }