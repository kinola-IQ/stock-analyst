"""Utility helpers for the project.

Includes functions to build retry configuration for Google GenAI HTTP requests.
"""

import time
from functools import wraps
from typing import Callable, Any
from google.genai import types


# retry configurable
def retry_config():
    """Return retry configuration for transient HTTP errors.

    This is useful for handling rate limits and temporary service
    unavailability. Common retriable status codes include
    429, 500, 503, and 504.
    """

    return types.HttpRetryOptions(
        attempts=5,  # Maximum retry attempts
        exp_base=7,  # Delay multiplier
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
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

