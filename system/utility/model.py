"""Gemini model initialization and caching with API setup."""

import os
import google.genai as genai
from dotenv import load_dotenv
from .custom_exceptions import ModelLoadError
from .utils import retry_on_exception, get_env
from .logger import logger

load_dotenv()

# Global state
_MODEL = None
_CLIENT = None
_CONFIGURED = False


def _configure_genai_client():
    """Initialize the GenAI client with API key."""
    global _CONFIGURED, _CLIENT
    if _CONFIGURED:
        return
    
    api_key = get_env("GOOGLE_API_KEY")
    if not api_key:
        raise ModelLoadError("GOOGLE_API_KEY is missing or empty")
    
    try:
        _CLIENT = genai.Client(api_key=api_key)
        _CONFIGURED = True
        logger.info("GenAI client initialized successfully")
    except Exception as e:
        logger.error(f"GenAI client initialization failed: {e}")
        raise ModelLoadError(f"GenAI client initialization failed: {e}") from e


@retry_on_exception(max_attempts=3, delay=1.0)
async def load_model(model_name: str = "gemini-2.5-pro") -> str:
    """Load and cache the model name on startup."""
    global _MODEL
    try:
        # _configure_genai_client()
        _MODEL = model_name
        logger.info(f"Model '{_MODEL}' loaded successfully")
        return _MODEL
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise ModelLoadError(f"Model loading failed: {e}") from e


def get_model() -> str:
    """Return the cached model name, or raise if not loaded."""
    if _MODEL is None:
        raise ModelLoadError("Model not loaded; call load_model() during startup")
    return _MODEL


def get_client():
    """Return the GenAI client, or raise if not initialized."""
    if _CLIENT is None:
        raise ModelLoadError("GenAI client not initialized; call load_model() during startup")
    return _CLIENT
