"""Gemini model initialization and caching with API setup."""

from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm
from .custom_exceptions import ModelLoadError
from .utils import retry_on_exception
from .logger import logger

load_dotenv()

# Global state
_MODEL = None


@retry_on_exception(max_attempts=3, delay=1.0)
async def load_model(model_name: str = "groq/llama-3.3-70b-versatile"):
    """Load and cache the model name on startup."""
    global _MODEL
    try:
        _MODEL = LiteLlm(model=model_name)
        logger.info("Model '%s' loaded successfully", model_name)
    except Exception as err:
        logger.error("Model loading failed: %s", err)
        raise ModelLoadError(f"Model loading failed: {err}") from err


def get_model() -> LiteLlm:
    """Return the cached model name, or raise if not loaded."""
    if _MODEL is None:
        raise ModelLoadError(
            "Model not loaded; call load_model() during startup")
    return _MODEL
