"""Proxy layer for OpenAI-compatible LLM endpoints with streaming support."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

logger = logging.getLogger(__name__)

_ANALYSIS_TIMEOUT = 60.0      # seconds for streaming analysis requests
_TEST_TIMEOUT = 10.0          # seconds for connection test requests
_MAX_REDIRECTS = 1            # never follow more than one redirect
_MAX_RESPONSE_BYTES = 1 << 20  # 1 MiB cap on streamed LLM response


def _safe_log_url(base_url: str) -> str:
    """Strip query parameters and fragment from a URL before logging.

    Args:
        base_url: The raw URL string, potentially containing query parameters
            or a fragment that may include sensitive tokens.

    Returns:
        str: A sanitised URL with the query string and fragment removed.
    """
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _build_headers(api_key: str) -> dict[str, str]:
    """Construct HTTP headers for LLM API requests.

    Args:
        api_key: The user-provided API key. Empty string is valid for
            local endpoints such as Ollama.

    Returns:
        dict: Headers including Authorization (when key is non-empty)
        and Content-Type.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _chat_completions_url(base_url: str) -> str:
    """Derive the chat completions URL from a base URL.

    Strips trailing slashes from ``base_url`` and appends the standard
    OpenAI-compatible path segment.

    Args:
        base_url: User-supplied base URL, e.g. ``https://api.openai.com/v1``.

    Returns:
        str: Full URL for the chat completions endpoint.
    """
    return base_url.rstrip("/") + "/chat/completions"


def test_llm_connection(
    base_url: str, api_key: str, model: str
) -> tuple[bool, str | None]:
    """Send a minimal completion request to validate LLM credentials and reachability.

    Performs a synchronous POST with ``max_tokens=1`` to avoid consuming
    significant quota. Returns immediately on success or with a descriptive
    error message on failure.

    Args:
        base_url: Base URL of the OpenAI-compatible LLM endpoint.
        api_key: API key (may be empty for local models).
        model: Model identifier to use in the test request.

    Returns:
        tuple: ``(True, None)`` on success, ``(False, error_message)`` on failure.
    """
    url = _chat_completions_url(base_url)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 1,
        "stream": False,
    }

    logger.info("Testing LLM connection to %s with model %s", _safe_log_url(base_url), model)

    try:
        with httpx.Client(
            timeout=_TEST_TIMEOUT,
            max_redirects=_MAX_REDIRECTS,
            follow_redirects=True,
        ) as client:
            response = client.post(
                url,
                json=payload,
                headers=_build_headers(api_key),
            )

        if response.status_code in (401, 403):
            logger.warning("LLM auth failure (HTTP %d) for %s", response.status_code, _safe_log_url(base_url))
            return False, "Invalid API key. Please check your credentials."

        if response.status_code == 404:
            return False, (
                f"The endpoint was not found at {url}. "
                "Please verify your Base URL and model name."
            )

        if not response.is_success:
            return False, (
                f"The LLM endpoint returned an error (HTTP {response.status_code}). "
                "Please check your settings and try again."
            )

        return True, None

    except httpx.ConnectTimeout:
        logger.warning("LLM connection timed out: %s", _safe_log_url(base_url))
        return False, (
            "Could not reach the LLM endpoint. The request timed out. "
            "Please verify the URL and your network connection."
        )
    except httpx.ReadTimeout:
        logger.warning("LLM read timed out: %s", _safe_log_url(base_url))
        return False, (
            "The LLM endpoint did not respond in time. "
            "Please try again or check the endpoint status."
        )
    except (httpx.ConnectError, httpx.UnsupportedProtocol):
        logger.warning("LLM DNS/connection error: %s", _safe_log_url(base_url))
        return False, (
            "Could not reach the LLM endpoint. Please verify the URL is correct "
            "and the server is running."
        )
    except httpx.TooManyRedirects:
        return False, (
            "The LLM endpoint redirected too many times. "
            "Please check the Base URL."
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error testing LLM connection: %s", exc)
        return False, "An unexpected error occurred while testing the connection."


async def stream_analysis(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    """Stream text chunks from an OpenAI-compatible chat completions endpoint.

    Sends a streaming POST request and yields text deltas parsed from
    SSE ``data:`` lines as they arrive.

    Args:
        base_url: Base URL of the OpenAI-compatible LLM endpoint.
        api_key: API key (may be empty for local models).
        model: Model identifier to use for completion.
        messages: Full messages array in OpenAI chat format.

    Yields:
        str: Incremental text chunks from the LLM response.

    Raises:
        ConnectionError: If the endpoint is unreachable or returns an error.
        RuntimeError: If an unexpected error occurs during streaming.
    """
    url = _chat_completions_url(base_url)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    logger.info("Starting streaming analysis via %s with model %s", _safe_log_url(base_url), model)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=_ANALYSIS_TIMEOUT,
                write=10.0,
                pool=5.0,
            ),
            max_redirects=_MAX_REDIRECTS,
            follow_redirects=True,
        ) as client:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers=_build_headers(api_key),
            ) as response:
                if response.status_code in (401, 403):
                    raise ConnectionError(
                        "Invalid API key. Please check your credentials in Settings."
                    )
                if response.status_code == 404:
                    raise ConnectionError(
                        f"The LLM endpoint was not found at {url}. "
                        "Please verify your Base URL and model name."
                    )
                if not response.is_success:
                    raise ConnectionError(
                        f"The LLM endpoint returned an error (HTTP {response.status_code}). "
                        "Please check your settings and try again."
                    )

                bytes_received: int = 0
                async for line in response.aiter_lines():
                    bytes_received += len(line.encode("utf-8"))
                    if bytes_received > _MAX_RESPONSE_BYTES:
                        logger.warning(
                            "LLM response exceeded %d bytes; truncating stream",
                            _MAX_RESPONSE_BYTES,
                        )
                        break
                    chunk = _parse_sse_line(line)
                    if chunk is not None:
                        yield chunk

    except (ConnectionError, RuntimeError):
        raise
    except httpx.ConnectTimeout:
        raise ConnectionError(
            "Could not reach the LLM endpoint. The request timed out. "
            "Please verify the URL and your network connection."
        )
    except httpx.ReadTimeout:
        raise ConnectionError(
            "The LLM endpoint stopped responding during the analysis. "
            "Please try again."
        )
    except (httpx.ConnectError, httpx.UnsupportedProtocol):
        raise ConnectionError(
            "Could not reach the LLM endpoint. Please verify the URL is correct "
            "and the server is running."
        )
    except httpx.TooManyRedirects:
        raise ConnectionError(
            "The LLM endpoint redirected too many times. Please check the Base URL."
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during LLM streaming: %s", exc)
        raise RuntimeError(
            "An unexpected error occurred while generating the analysis. "
            "Please try again."
        ) from exc


def _parse_sse_line(line: str) -> str | None:
    """Extract the text delta from a single SSE data line.

    Args:
        line: A raw SSE line from the streaming response, e.g.
            ``data: {"choices": [{"delta": {"content": "Hello"}}]}``.

    Returns:
        str: The extracted text content, or None if the line should be skipped
        (ping, done sentinel, or non-data line).
    """
    if not line.startswith("data:"):
        return None

    payload = line[len("data:"):].strip()

    if payload == "[DONE]":
        return None

    try:
        parsed = json.loads(payload)
        choices = parsed.get("choices", [])
        if not choices:
            return None
        delta = choices[0].get("delta", {})
        return delta.get("content")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None
