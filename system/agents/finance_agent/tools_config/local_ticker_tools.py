from __future__ import annotations

import json
import re
import time
from datetime import date
from typing import Any, Literal, Optional

import requests
from dotenv import load_dotenv


load_dotenv()


# Configuration
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRIES = 2
DEFAULT_HISTORY_DAYS = 365


FinancialDataset = Literal[
    "historical",
    "fundamentals",
    "news",
    "sentiment",
]

ToolStatus = Literal[
    "success",
    "partial",
    "error",
]


# Generic helpers

def _error(
    *,
    code: str,
    message: str,
    source: str,
    endpoint: str,
    retryable: bool = False,
    http_status: Optional[int] = None,
    details: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Construct a machine-readable error object.

    The returned structure is intentionally explicit so an LLM/tool caller
    can distinguish authentication failures, rate limits, invalid requests,
    upstream failures, and network failures without inspecting prose.
    """
    result: dict[str, Any] = {
        "code": code,
        "message": message,
        "source": source,
        "endpoint": endpoint,
        "retryable": retryable,
    }

    if http_status is not None:
        result["http_status"] = http_status

    if details is not None:
        result["details"] = details

    return result


def _validate_date(value: Optional[str], field_name: str) -> Optional[str]:
    """Validate a YYYY-MM-DD date string or return None."""
    if value is None:
        return None

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format; received {value!r}."
        ) from exc

    return parsed.isoformat()


def _validate_year(
    value: Optional[int],
    field_name: str,
) -> Optional[int]:
    """Validate a four-digit calendar year."""
    if value is None:
        return None

    if value < 1900 or value > date.today().year + 1:
        raise ValueError(
            f"{field_name} must be a valid calendar year; received {value}."
        )

    return value


def _validate_symbol(symbol: str) -> str:
    """
    Validate an EODHD ticker.

    Examples:
        AIICO.XNSA
        AAPL.US
        MTNN.XNSA
    """
    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError("symbol must not be empty.")

    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]*", normalized):
        raise ValueError(
            f"Invalid symbol {symbol!r}. "
            "Expected a market identifier such as 'AIICO.XNSA'."
        )

    return normalized


def _validate_country_code(country_code: str) -> str:
    """Validate a two-letter ISO-style lowercase country code."""
    normalized = country_code.strip().lower()

    if not re.fullmatch(r"[a-z]{2}", normalized):
        raise ValueError(
            f"country_code must contain exactly two letters; "
            f"received {country_code!r}."
        )

    return normalized


def _safe_payload(response: requests.Response) -> Any:
    """
    Extract an API response body safely.

    APIs may return JSON, plain text, or HTML on an error response.
    """
    try:
        return response.json()
    except ValueError:
        return response.text[:2000]


def _extract_error_details(payload: Any) -> Optional[str]:
    """Convert common API error payloads into concise diagnostic text."""
    if payload is None:
        return None

    if isinstance(payload, str):
        return payload[:1000]

    if isinstance(payload, dict):
        for key in (
            "error",
            "message",
            "detail",
            "description",
            "error_message",
        ):
            value = payload.get(key)
            if value:
                return str(value)[:1000]

    try:
        return json.dumps(payload)[:1000]
    except (TypeError, ValueError):
        return str(payload)[:1000]


def _request_json(
    *,
    session: requests.Session,
    source: str,
    endpoint: str,
    url: str,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
) -> tuple[Optional[Any], Optional[dict[str, Any]]]:
    """
    Perform an HTTP GET request and return either JSON data or a structured
    error.

    Retry policy:
      - 429: retry because the request may be rate-limited.
      - 5xx: retry because the upstream service may be temporarily failing.
      - Network/timeout errors: retry.
      - 4xx other than 429: do not retry because the request/authentication
        problem is expected to persist without changing the request.
    """
    last_error: Optional[dict[str, Any]] = None

    for attempt in range(retries + 1):
        try:
            response = session.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )

        except requests.Timeout as exc:
            last_error = _error(
                code="NETWORK_TIMEOUT",
                message=(
                    f"{source} request timed out after "
                    f"{timeout} seconds."
                ),
                source=source,
                endpoint=endpoint,
                retryable=True,
                details=str(exc),
            )

            if attempt < retries:
                time.sleep(2 ** attempt)
                continue

            return None, last_error

        except requests.ConnectionError as exc:
            last_error = _error(
                code="NETWORK_CONNECTION_ERROR",
                message=f"Could not connect to {source}.",
                source=source,
                endpoint=endpoint,
                retryable=True,
                details=str(exc),
            )

            if attempt < retries:
                time.sleep(2 ** attempt)
                continue

            return None, last_error

        except requests.RequestException as exc:
            return None, _error(
                code="REQUEST_ERROR",
                message=f"Unexpected HTTP client error while calling {source}.",
                source=source,
                endpoint=endpoint,
                retryable=False,
                details=str(exc),
            )

        status = response.status_code

        if 200 <= status < 300:
            try:
                return response.json(), None
            except ValueError as exc:
                return None, _error(
                    code="INVALID_JSON_RESPONSE",
                    message=(
                        f"{source} returned a successful HTTP response "
                        "but the body was not valid JSON."
                    ),
                    source=source,
                    endpoint=endpoint,
                    retryable=False,
                    http_status=status,
                    details=str(exc),
                )

        payload = _safe_payload(response)
        details = _extract_error_details(payload)

        if status == 401:
            return None, _error(
                code="AUTHENTICATION_ERROR",
                message=(
                    f"{source} rejected the API credentials. "
                    "Check that the configured API key exists, is valid, "
                    "and has not expired or been revoked."
                ),
                source=source,
                endpoint=endpoint,
                retryable=False,
                http_status=status,
                details=details,
            )

        if status == 403:
            return None, _error(
                code="AUTHORIZATION_ERROR",
                message=(
                    f"{source} understood the request but refused access. "
                    "The API key may lack permission for this endpoint or "
                    "the endpoint may not be included in the current plan."
                ),
                source=source,
                endpoint=endpoint,
                retryable=False,
                http_status=status,
                details=details,
            )

        if status == 404:
            return None, _error(
                code="NOT_FOUND",
                message=(
                    f"{source} could not find the requested resource. "
                    "Check the ticker, country code, endpoint, or requested "
                    "dataset."
                ),
                source=source,
                endpoint=endpoint,
                retryable=False,
                http_status=status,
                details=details,
            )

        if status == 429:
            retry_after = response.headers.get("Retry-After")

            try:
                wait_seconds = max(1, int(retry_after or "5"))
            except ValueError:
                wait_seconds = 5

            last_error = _error(
                code="RATE_LIMITED",
                message=(
                    f"{source} rate-limited the request. "
                    f"Retry after approximately {wait_seconds} seconds."
                ),
                source=source,
                endpoint=endpoint,
                retryable=True,
                http_status=status,
                details=details,
            )

            if attempt < retries:
                time.sleep(wait_seconds)
                continue

            return None, last_error

        if 400 <= status < 500:
            return None, _error(
                code="CLIENT_REQUEST_ERROR",
                message=(
                    f"{source} rejected the request with HTTP {status}. "
                    "Check the supplied parameters."
                ),
                source=source,
                endpoint=endpoint,
                retryable=False,
                http_status=status,
                details=details,
            )

        if status >= 500:
            last_error = _error(
                code="UPSTREAM_SERVER_ERROR",
                message=(
                    f"{source} returned HTTP {status}. "
                    "The provider may be temporarily unavailable."
                ),
                source=source,
                endpoint=endpoint,
                retryable=True,
                http_status=status,
                details=details,
            )

            if attempt < retries:
                time.sleep(2 ** attempt)
                continue

            return None, last_error

    return None, last_error


def _build_tool_result(
    *,
    tool_name: str,
    request: dict[str, Any],
    data: dict[str, Any],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build the standard agent-facing response.

    `partial` means at least one requested dataset succeeded and at least
    one requested dataset failed.

    `error` means no requested dataset succeeded.
    """
    if not errors:
        status: ToolStatus = "success"
    elif data:
        status = "partial"
    else:
        status = "error"

    return {
        "tool": tool_name,
        "status": status,
        "ok": bool(data),
        "request": request,
        "data": data,
        "errors": errors,
    }
