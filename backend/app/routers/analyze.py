"""Router for LLM analysis and settings test endpoints."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import AsyncGenerator, Generator

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.schemas import (
    AnalyzeRequest,
    ChatRequest,
    SettingsTestRequest,
    SettingsTestResponse,
)
from app.prompts.analysis import build_analysis_prompt, build_chat_prompt
from app.services import cache
from app.services.llm_proxy import stream_analysis, test_llm_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analyze"])


def _get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency that yields a database connection."""
    yield from get_db()


@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    db: sqlite3.Connection = Depends(_get_db_connection),
) -> EventSourceResponse:
    """Stream an AI-generated macroeconomic analysis via Server-Sent Events.

    Retrieves the latest CapEx data from cache, builds a structured prompt,
    and proxies a streaming completion request to the user-configured LLM
    endpoint. Text chunks are emitted as SSE events as they arrive.

    If no cached data is available, returns a JSON error response with
    HTTP 422. On LLM connection or runtime errors, emits an SSE error event
    before closing the stream.

    Args:
        body: AnalyzeRequest containing LLM config and optional data_summary.
        db: SQLite connection injected by FastAPI's dependency system.

    Returns:
        EventSourceResponse: SSE stream of text chunk events.
    """
    # ------------------------------------------------------------------ #
    # Resolve CapEx data — prefer fresh cache, fall back to any stale entry
    # ------------------------------------------------------------------ #
    capex_data, _ = cache.get_cached_data(db)
    if capex_data is None:
        capex_data, _ = cache.get_stale_data(db)

    if capex_data is None:
        return JSONResponse(
            status_code=422,
            content={
                "data": None,
                "error": (
                    "No CapEx data is available to analyse. "
                    "Please fetch data first by visiting the data page."
                ),
            },
        )

    # Build prompt from resolved CapEx data
    messages = build_analysis_prompt(capex_data)

    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events from the LLM streaming response."""
        try:
            async for chunk in stream_analysis(
                base_url=body.base_url,
                api_key=body.api_key,
                model=body.model,
                messages=messages,
            ):
                if chunk:
                    # Wrap in JSON so the frontend can read parsed.content
                    yield {"data": json.dumps({"content": chunk})}

            # Signal clean completion
            yield {"event": "done", "data": ""}

        except ConnectionError as exc:
            logger.warning("LLM connection error during analysis: %s", exc)
            yield {"event": "error", "data": str(exc)}
        except RuntimeError as exc:
            logger.error("Runtime error during analysis stream: %s", exc)
            yield {"event": "error", "data": str(exc)}
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in analysis event generator: %s", exc)
            yield {
                "event": "error",
                "data": "An unexpected error occurred. Please try again.",
            }

    return EventSourceResponse(event_generator())


@router.post("/chat")
async def chat(
    body: ChatRequest,
    db: sqlite3.Connection = Depends(_get_db_connection),
) -> EventSourceResponse:
    """Stream a follow-up Q&A response via Server-Sent Events.

    Reconstructs the full LLM context (original data + analysis + prior
    conversation turns) and appends the user's new question before
    streaming a response. This allows the LLM to answer follow-up
    questions with full awareness of the prior analysis.

    Args:
        body: ChatRequest containing LLM config, original analysis text,
              prior chat history, and the new question.
        db: SQLite connection injected by FastAPI's dependency system.

    Returns:
        EventSourceResponse: SSE stream of text chunk events.
    """
    capex_data, _ = cache.get_cached_data(db)
    if capex_data is None:
        capex_data, _ = cache.get_stale_data(db)

    if capex_data is None:
        return JSONResponse(
            status_code=422,
            content={
                "error": (
                    "No CapEx data is available. "
                    "Please fetch data first before asking questions."
                )
            },
        )

    messages = build_chat_prompt(
        data=capex_data,
        analysis=body.analysis,
        chat_history=[m.model_dump() for m in body.chat_history],
        question=body.question,
    )

    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events from the LLM streaming response."""
        try:
            async for chunk in stream_analysis(
                base_url=body.base_url,
                api_key=body.api_key,
                model=body.model,
                messages=messages,
            ):
                if chunk:
                    yield {"data": json.dumps({"content": chunk})}

            yield {"event": "done", "data": ""}

        except ConnectionError as exc:
            logger.warning("LLM connection error during chat: %s", exc)
            yield {"event": "error", "data": str(exc)}
        except RuntimeError as exc:
            logger.error("Runtime error during chat stream: %s", exc)
            yield {"event": "error", "data": str(exc)}
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in chat event generator: %s", exc)
            yield {
                "event": "error",
                "data": "An unexpected error occurred. Please try again.",
            }

    return EventSourceResponse(event_generator())


@router.post("/settings/test", response_model=SettingsTestResponse)
def test_settings(body: SettingsTestRequest) -> SettingsTestResponse:
    """Test connectivity and credentials for a user-configured LLM endpoint.

    Sends a minimal completion request (max_tokens=1) to the specified
    endpoint. Returns a simple success/failure result with a human-readable
    error message when the test fails.

    Args:
        body: SettingsTestRequest containing base_url, api_key, and model.

    Returns:
        SettingsTestResponse: ``{success: True}`` or
        ``{success: False, error: "..."}``
    """
    logger.info(
        "Testing LLM settings for endpoint %s with model %s",
        body.base_url,
        body.model,
    )
    success, error_message = test_llm_connection(
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
    )
    return SettingsTestResponse(success=success, error=error_message)
