import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def _get_api_key():
    """Looks for the key locally (.env / real env var) first, then falls
    back to Streamlit's secrets manager — which is how the key has to be
    supplied on Streamlit Community Cloud, since .env is gitignored and
    never gets uploaded there."""

    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key

    try:
        import streamlit as st
        api_key = st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        api_key = None

    return api_key


def get_llm():

    api_key = _get_api_key()

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found. Locally: add it to a .env file "
            "(GOOGLE_API_KEY=your-key). On Streamlit Community Cloud: open "
            "your app, go to Manage app -> Settings -> Secrets, and add "
            'GOOGLE_API_KEY = "your-key-here", then save (the app restarts '
            "automatically)."
        )

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=api_key,
        temperature=0.2,
    )

    return llm