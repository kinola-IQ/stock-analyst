"""
Load and cache the Gemini model, with basic validation and retry support.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

from .custom_exceptions import ModelLoadError
from .utils import retry_on_exception
from .logger import logger

load_dotenv()

MODEL = None
_CONFIGURED = False

# api connection
def _configure_genai() -> None:
    """configures connection to api
    Args:
    None

    Returns:
    None
    """
    global _CONFIGURED

    if _CONFIGURED:
        return

    api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key:
        raise ModelLoadError("GOOGLE_GENAI_API_KEY is missing")

    genai.configure(api_key=api_key)
    _CONFIGURED = True

# model intialization with retry logic
@retry_on_exception()
def load_model():
    """Create and cache the Gemini model instance."""
    global MODEL

    if MODEL is not None:
        return MODEL

    try:
        _configure_genai()
        MODEL = genai.GenerativeModel("gemini-1.5-flash")
        return MODEL
    except Exception as exc:
        logger.exception("Model loading failed")
        raise ModelLoadError(f"Model loading failed: {exc}") from exc


# model serving function
def get_model():
    """Return the cached model instance, or raise if it has not been loaded."""
    if MODEL is None:
        raise ModelLoadError("Model has not been loaded yet. Call get_model() first.")
    return MODEL
