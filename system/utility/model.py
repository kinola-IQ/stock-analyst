"""
Load and cache the Gemini model, with basic validation and retry support.
"""

import os
import contextlib
from dotenv import load_dotenv
import google.genai as genai

from .custom_exceptions import ModelLoadError
from .utils import retry_on_exception
from .logger import logger

# preparing access to api key from environment
load_dotenv()

# global variable to cache the model name after loading
MODEL = None
_CONFIGURED = False


# Handle Generative AI client connection
@retry_on_exception()
async def get_genai_client():
    """Context manager for Generative AI client."""
    global _CONFIGURED, MODEL
    api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key:
        raise ModelLoadError("GOOGLE_GENAI_API_KEY is missing")

    try:
        genai.Client(api_key=api_key)
        _CONFIGURED = True
        logger.info("api connection configured successfully")
        return _CONFIGURED
    except Exception as exc:
        logger.exception("api connection configuration failed")


# model intialization with retry logic
async def load_model(model_name: str = "gemini-1.5-flash") -> str:
    """connect to api and cache name of model to use on startup"""
    try:
        global MODEL
        await get_genai_client()
        MODEL = model_name
        logger.info(f"Model '{MODEL}' loaded and cached successfully")
        return MODEL
    except Exception as exc:
        logger.exception("Model loading failed")
        raise ModelLoadError(f"Model loading failed: {exc}") from exc


# model serving function
def get_model() -> str:
    """Return the cached model name, or raise if api connection has not been made."""
    if MODEL is None:
        raise ModelLoadError(
            "api connection not made, and so Model name cannot be cached yet."
            )
    return MODEL
