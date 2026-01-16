"""Utility helpers for the project.

Includes functions to build retry configuration for Google GenAI HTTP requests.
"""

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

