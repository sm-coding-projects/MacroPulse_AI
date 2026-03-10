"""Pydantic request and response models for MacroPulse AI."""

from __future__ import annotations

import ipaddress
import urllib.parse
from typing import Any

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Hostnames that must never be reached (Docker-internal, common service names)
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "backend",
        "frontend",
        "db",
        "database",
        "redis",
        "postgres",
        "postgresql",
        "mysql",
        "mongo",
        "mongodb",
        "elasticsearch",
    }
)


def _validate_llm_base_url(value: str) -> str:
    """Validate base_url for LLM endpoints.

    Checks:
    - Scheme must be http or https.
    - Host must not be a loopback address (127.x.x.x, ::1).
    - Host must not be a link-local address (169.254.x.x).
    - Host must not match a known Docker-internal service name.

    Private LAN addresses (192.168.x.x, 10.x.x.x, 172.16-31.x.x) are
    permitted so that local LLM servers (e.g. LM Studio, Ollama) can be used.

    Args:
        value: The raw base_url string submitted by the user.

    Returns:
        str: The validated base_url (unchanged if valid).

    Raises:
        ValueError: With a descriptive message if the URL fails any check.
    """
    parsed = urllib.parse.urlparse(value)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed."
        )

    host = parsed.hostname or ""
    if not host:
        raise ValueError("The base_url must include a hostname.")

    # Reject known Docker-internal service names
    if host.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(
            f"The hostname '{host}' is not permitted. "
            "Please use a valid LLM endpoint."
        )

    # Attempt to parse as an IP address for range checks
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Not an IP address — no further checks needed
        return value

    if addr.is_loopback:
        raise ValueError(
            "Loopback addresses (e.g. 127.0.0.1, ::1) are not permitted."
        )

    if addr.is_link_local:
        raise ValueError(
            "Link-local addresses (169.254.x.x) are not permitted."
        )

    return value


class CapExQuarter(BaseModel):
    """Capital expenditure figures for a single quarter."""

    period: str = Field(..., description="Quarter identifier, e.g. '2024-Q3'")
    total: float = Field(..., description="Total CapEx across all industries ($M)")
    mining: float = Field(..., description="Mining industry CapEx ($M)")
    manufacturing: float = Field(..., description="Manufacturing industry CapEx ($M)")
    other_selected: float = Field(
        ..., description="Other Selected Industries CapEx ($M)"
    )
    buildings_structures: float = Field(
        ..., description="Buildings & Structures asset type CapEx ($M)"
    )
    equipment_plant_machinery: float = Field(
        ..., description="Equipment, Plant & Machinery asset type CapEx ($M)"
    )
    qoq_change: float | None = Field(
        default=None,
        description="Quarter-on-quarter percentage change in total CapEx",
    )
    yoy_change: float | None = Field(
        default=None,
        description="Year-on-year percentage change in total CapEx",
    )


class CapExData(BaseModel):
    """Structured CapEx dataset covering the most recent quarters."""

    quarters: list[CapExQuarter] = Field(
        ..., description="List of quarterly CapEx records, most recent first"
    )
    by_industry: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="CapEx series keyed by industry name",
    )
    by_asset_type: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="CapEx series keyed by asset type",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Source info: source, last_updated, estimate_number, is_cached",
    )


class ChatMessage(BaseModel):
    """A single turn in a follow-up Q&A conversation."""

    role: Literal["user", "assistant"] = Field(
        ..., description="Who sent this message"
    )
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    base_url: str = Field(
        ..., description="Base URL of the OpenAI-compatible LLM endpoint"
    )
    api_key: str = Field(
        default="", description="API key for the LLM endpoint (empty for local models)"
    )
    model: str = Field(..., description="Model identifier to use for completion")
    question: str = Field(..., description="The user's follow-up question")
    analysis: str = Field(
        ..., description="The original AI analysis text, used as conversation context"
    )
    chat_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior Q&A turns in the current session (excluding the new question)",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Prevent SSRF by rejecting non-public or disallowed base_url values."""
        return _validate_llm_base_url(v)


class AnalyzeRequest(BaseModel):
    """Request body for the POST /api/analyze endpoint."""

    base_url: str = Field(
        ..., description="Base URL of the OpenAI-compatible LLM endpoint"
    )
    api_key: str = Field(
        default="", description="API key for the LLM endpoint (empty for local models)"
    )
    model: str = Field(..., description="Model identifier to use for completion")
    data_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional pre-built data summary; backend will build one if empty",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Prevent SSRF by rejecting non-public or disallowed base_url values."""
        return _validate_llm_base_url(v)


class AnalyzeResponse(BaseModel):
    """Response body for the POST /api/analyze endpoint."""

    analysis: str = Field(..., description="AI-generated markdown analysis text")
    tokens_used: int | None = Field(
        default=None, description="Total tokens consumed by the request, if reported"
    )


class SettingsTestRequest(BaseModel):
    """Request body for the POST /api/settings/test endpoint."""

    base_url: str = Field(..., description="Base URL of the LLM endpoint to test")
    api_key: str = Field(default="", description="API key to validate")
    model: str = Field(..., description="Model identifier to use in the test request")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Prevent SSRF by rejecting non-public or disallowed base_url values."""
        return _validate_llm_base_url(v)


class SettingsTestResponse(BaseModel):
    """Response body for the POST /api/settings/test endpoint."""

    success: bool = Field(..., description="Whether the connection test passed")
    error: str | None = Field(
        default=None, description="Human-readable error message if success is False"
    )


class DataResponse(BaseModel):
    """Generic wrapper returned by GET /api/data/capex."""

    data: CapExData | None = Field(
        default=None, description="The CapEx dataset, or null on error"
    )
    from_cache: bool = Field(
        default=False,
        description="True when the response was served from stale cache",
    )
    cache_date: str | None = Field(
        default=None, description="ISO-8601 timestamp of the cached data, if applicable"
    )
    error: str | None = Field(
        default=None, description="Human-readable error message, or null on success"
    )


class IndicatorPoint(BaseModel):
    """A single time-period data point for an economic indicator."""

    period: str = Field(
        ..., description="Quarter string e.g. '2024-Q3' or month '2024-01'"
    )
    value: float = Field(..., description="Indicator value")


class EconomicIndicatorsData(BaseModel):
    """Bundled economic context indicators."""

    gdp_growth: list[IndicatorPoint] = Field(
        default_factory=list, description="GDP QoQ growth % (8 quarters)"
    )
    cpi_inflation: list[IndicatorPoint] = Field(
        default_factory=list, description="CPI YoY % (8 quarters)"
    )
    unemployment_rate: list[IndicatorPoint] = Field(
        default_factory=list,
        description="Unemployment rate % (8 quarters, quarterly avg)",
    )
    wage_growth: list[IndicatorPoint] = Field(
        default_factory=list, description="WPI YoY % (8 quarters)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndicatorsResponse(BaseModel):
    """Response wrapper for GET /api/data/indicators."""

    data: EconomicIndicatorsData | None = Field(default=None)
    from_cache: bool = Field(default=False)
    cache_date: str | None = Field(default=None)
    error: str | None = Field(default=None)
