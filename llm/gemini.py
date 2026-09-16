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


# "gemini-flash-latest" (the full-size alias) can resolve to a brand-new
# preview model with a tiny free quota (20 req/day, as happened here).
# Pinning to one exact version like "gemini-2.5-flash-lite" is *also*
# fragile — Google periodically retires specific model versions outright
# (a 404 NOT_FOUND, also hit here). "gemini-flash-lite-latest" is an alias
# Google keeps pointing at whatever its current lite model is, so it
# survives both kinds of change without a code edit.
DEFAULT_MODEL = "gemini-flash-lite-latest"


def _get_model_name():
    model_name = os.getenv("GEMINI_MODEL")
    if model_name:
        return model_name

    try:
        import streamlit as st
        model_name = st.secrets.get("GEMINI_MODEL")
    except Exception:
        model_name = None

    return model_name or DEFAULT_MODEL


def get_llm(model_override: str = None):

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
        model=model_override or _get_model_name(),
        google_api_key=api_key,
        temperature=0.2,
    )

    return llm