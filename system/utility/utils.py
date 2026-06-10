"""Utility helpers for the project.

Includes functions to build retry configuration and environment variable handling.
"""

import os
import time
from functools import wraps
from typing import Callable, Any
from google.genai import types


def get_env(name: str, default: str = "") -> str:
    """Get environment variable with sanitization (strip quotes and whitespace)."""
    value = os.getenv(name, default)
    return value.strip().strip("'\"") if value else default


def retry_config():
    """Return retry configuration for transient HTTP errors.

    Handles rate limits and temporary service unavailability.
    """
    return types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504],
    )


def retry_on_exception(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry a function on exception.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff: Multiplier for delay on each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

