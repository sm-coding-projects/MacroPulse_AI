"""Fetch and parse ABS economic indicators (GDP, CPI, LF, WPI)."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import requests

from app.models.schemas import EconomicIndicatorsData, IndicatorPoint

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.data.abs.gov.au/data/"
_HEADERS: dict[str, str] = {
    "User-Agent": "MacroPulse-AI/1.0",
    "Accept": "application/vnd.sdmx.data+json;version=1.0",
}
_TIMEOUT = 30
_N_QUARTERS = 8


def _get(path: str) -> dict[str, Any]:
    """GET from the ABS API and normalise the data envelope.

    Args:
        path: The URL path segment appended to the base URL.

    Returns:
        dict: The normalised payload containing ``dataSets`` and ``structure``.

    Raises:
        requests.HTTPError: On non-2xx HTTP responses.
        ValueError: When the response is missing expected SDMX-JSON keys.
    """
    resp = requests.get(_BASE_URL + path, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    body: dict[str, Any] = resp.json()
    # The ABS API wraps the SDMX payload under a "data" key in newer versions
    payload: dict[str, Any] = body.get("data", body)
    if "dataSets" not in payload or "structure" not in payload:
        raise ValueError(
            f"Unexpected ABS response structure for path '{path}'. "
            "Missing 'dataSets' or 'structure' keys."
        )
    return payload


def _obs_series(payload: dict[str, Any], series_key: str) -> dict[str, list[Any]]:
    """Return the observations dict for a given series key.

    Args:
        payload: The normalised SDMX-JSON payload from ``_get()``.
        series_key: Colon-separated dimension index key, e.g. ``"0:0:0:0:0"``.

    Returns:
        dict: Mapping of time-index strings to observation arrays.

    Raises:
        ValueError: When the series key is absent from the dataset.
    """
    series: dict[str, Any] = payload["dataSets"][0].get("series", {})
    if series_key not in series:
        available = list(series.keys())[:5]
        raise ValueError(
            f"Series key '{series_key}' not found in response. "
            f"Available keys (first 5): {available}"
        )
    return series[series_key]["observations"]


def _time_values(payload: dict[str, Any]) -> list[str]:
    """Extract ordered time-period ID strings from the SDMX structure.

    Args:
        payload: The normalised SDMX-JSON payload from ``_get()``.

    Returns:
        list[str]: Time period IDs in index order, e.g. ``["2023-Q1", "2023-Q2", ...]``.
    """
    obs_dims: list[dict[str, Any]] = payload["structure"]["dimensions"]["observation"]
    return [v["id"] for v in obs_dims[0]["values"]]


def _last_n_points(
    obs: dict[str, list[Any]],
    time_vals: list[str],
    n: int,
) -> list[IndicatorPoint]:
    """Return the last ``n`` non-null observations as ``IndicatorPoint`` instances.

    Args:
        obs: Observations dict mapping time-index string to value array.
        time_vals: Ordered list of time-period ID strings.
        n: Maximum number of most-recent points to return.

    Returns:
        list[IndicatorPoint]: Most recent points sorted oldest-first.
    """
    sorted_keys = sorted(obs.keys(), key=int)
    points: list[IndicatorPoint] = []
    for ti in sorted_keys:
        val = obs[ti][0]
        if val is not None:
            points.append(
                IndicatorPoint(period=time_vals[int(ti)], value=float(val))
            )
    return points[-n:]


def fetch_gdp_growth() -> list[IndicatorPoint]:
    """Fetch GDP quarter-on-quarter percentage change, seasonally adjusted.

    Returns:
        list[IndicatorPoint]: Up to 8 most recent quarterly GDP QoQ % points.

    Raises:
        requests.HTTPError: On HTTP-level failures from the ABS API.
        ValueError: On unexpected response structure or missing series.
    """
    payload = _get("ABS,ANA_AGG/M6.GPM.20.AUS.Q")
    obs = _obs_series(payload, "0:0:0:0:0")
    return _last_n_points(obs, _time_values(payload), _N_QUARTERS)


def fetch_cpi_inflation() -> list[IndicatorPoint]:
    """Fetch CPI year-on-year percentage change, all groups, weighted avg 8 cities.

    Returns:
        list[IndicatorPoint]: Up to 8 most recent quarterly CPI YoY % points.

    Raises:
        requests.HTTPError: On HTTP-level failures from the ABS API.
        ValueError: On unexpected response structure or missing series.
    """
    payload = _get("ABS,CPI_Q/3.999901.20.50.Q")
    obs = _obs_series(payload, "0:0:0:0:0")
    return _last_n_points(obs, _time_values(payload), _N_QUARTERS)


def fetch_unemployment_rate() -> list[IndicatorPoint]:
    """Fetch unemployment rate %, seasonally adjusted, aggregated to quarterly.

    Monthly LF data (series key ``6:0:0:0:7:0``) is averaged across the three
    calendar months within each quarter. Only quarters where all three monthly
    values are present are included.

    Returns:
        list[IndicatorPoint]: Up to 8 most recent quarterly unemployment rate points.

    Raises:
        requests.HTTPError: On HTTP-level failures from the ABS API.
        ValueError: On unexpected response structure or missing series.
    """
    payload = _get("ABS,LF/all")
    obs = _obs_series(payload, "6:0:0:0:7:0")
    time_vals = _time_values(payload)

    # Build a list of (period_string, float_value) for all non-null monthly obs
    monthly: list[tuple[str, float]] = []
    for ti in sorted(obs.keys(), key=int):
        val = obs[ti][0]
        if val is not None:
            monthly.append((time_vals[int(ti)], float(val)))

    # Aggregate monthly readings into quarterly averages
    quarter_vals: dict[str, list[float]] = defaultdict(list)
    for period, val in monthly:
        m = re.match(r"(\d{4})-(\d{2})", period)
        if m:
            year = int(m.group(1))
            month = int(m.group(2))
            q = (month - 1) // 3 + 1
            quarter_key = f"{year}-Q{q}"
            quarter_vals[quarter_key].append(val)

    # Only include quarters where all 3 monthly values are available
    quarterly = sorted(
        [
            IndicatorPoint(
                period=k,
                value=round(sum(v) / len(v), 4),
            )
            for k, v in quarter_vals.items()
            if len(v) == 3
        ],
        key=lambda p: p.period,
    )
    return quarterly[-_N_QUARTERS:]


def fetch_wage_growth() -> list[IndicatorPoint]:
    """Fetch WPI year-on-year percentage change, total hourly rates incl bonuses.

    Covers all industries, private and public, Australia total, original series
    (series key ``1:0:1:0:0:0:0``).

    Returns:
        list[IndicatorPoint]: Up to 8 most recent quarterly wage growth % points.

    Raises:
        requests.HTTPError: On HTTP-level failures from the ABS API.
        ValueError: On unexpected response structure or missing series.
    """
    payload = _get("ABS,WPI/all")
    obs = _obs_series(payload, "1:0:1:0:0:0:0")
    return _last_n_points(obs, _time_values(payload), _N_QUARTERS)


def fetch_all_indicators() -> EconomicIndicatorsData:
    """Fetch all four ABS economic indicators and return a bundled response.

    Each indicator is fetched independently. Partial failures are logged and
    an empty list is used for any indicator that could not be fetched, so that
    the other indicators are still returned.

    Returns:
        EconomicIndicatorsData: Bundled indicator data with metadata.
    """
    errors: list[str] = []

    def _safe_fetch(name: str, fn: Any) -> list[IndicatorPoint]:
        """Wrap a fetch function to absorb exceptions and log failures."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch %s indicator: %s", name, exc)
            errors.append(name)
            return []

    gdp = _safe_fetch("GDP", fetch_gdp_growth)
    cpi = _safe_fetch("CPI", fetch_cpi_inflation)
    unemp = _safe_fetch("unemployment", fetch_unemployment_rate)
    wpi = _safe_fetch("WPI", fetch_wage_growth)

    if errors:
        logger.warning("Indicators fetch had partial failures: %s", errors)

    return EconomicIndicatorsData(
        gdp_growth=gdp,
        cpi_inflation=cpi,
        unemployment_rate=unemp,
        wage_growth=wpi,
        metadata={
            "source": "Australian Bureau of Statistics",
            "last_updated": datetime.now(tz=timezone.utc).isoformat(),
            "partial_failure": errors if errors else None,
        },
    )
