import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def _get_api_key():
    """Reads the Gemini API key from the environment (.env locally, a real
    env var in Docker/Render)."""

    return os.getenv("GOOGLE_API_KEY")


# "gemini-flash-latest" (the full-size alias) can resolve to a brand-new
# preview model with a tiny free quota (20 req/day, as happened here).
# Pinning to one exact version like "gemini-2.5-flash-lite" is *also*
# fragile — Google periodically retires specific model versions outright
# (a 404 NOT_FOUND, also hit here). "gemini-flash-lite-latest" is an alias
# Google keeps pointing at whatever its current lite model is, so it
# survives both kinds of change without a code edit.
DEFAULT_MODEL = "gemini-flash-lite-latest"


def _get_model_name():
    return os.getenv("GEMINI_MODEL") or DEFAULT_MODEL


def get_llm(model_override: str = None):

    api_key = _get_api_key()

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found. Add it to a .env file locally "
            "(GOOGLE_API_KEY=your-key) or set it as an environment variable "
            "in your deployment (e.g. Render)."
        )

    llm = ChatGoogleGenerativeAI(
        model=model_override or _get_model_name(),
        google_api_key=api_key,
        temperature=0.2,
    )

    return llm
