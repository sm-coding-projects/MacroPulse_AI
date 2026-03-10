"""ABS Indicator API client for fetching Capital Expenditure data."""

import json
import logging
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ABS CapEx dataflow endpoint (SDMX-JSON)
_ABS_CAPEX_URL = "https://api.data.abs.gov.au/data/ABS,CAPEX/all"
_USER_AGENT = "MacroPulse-AI/1.0"
_TIMEOUT_SECONDS = 30
_MIN_REQUEST_DELAY = 2.0  # seconds between consecutive requests

# Module-level timestamp and lock to enforce minimum request delay thread-safely
_last_request_time: float = 0.0
_rate_limit_lock: threading.Lock = threading.Lock()


def _enforce_rate_limit() -> None:
    """Block until the minimum inter-request delay has elapsed.

    Uses a threading.Lock to prevent concurrent requests from racing on
    ``_last_request_time`` when multiple threads call this function simultaneously.
    """
    global _last_request_time
    with _rate_limit_lock:
        elapsed = time.monotonic() - _last_request_time
        if elapsed < _MIN_REQUEST_DELAY:
            time.sleep(_MIN_REQUEST_DELAY - elapsed)
        _last_request_time = time.monotonic()


def fetch_capex_from_abs() -> dict[str, Any]:
    """Fetch raw CapEx data from the ABS Indicator API.

    Performs a GET request to the ABS SDMX-JSON endpoint, enforces a
    minimum 2-second delay between calls, and returns the parsed JSON
    response as a plain dictionary.

    Returns:
        dict: The raw parsed SDMX-JSON response from the ABS API.

    Raises:
        ConnectionError: If the request times out or the server returns an
            HTTP error status.
        ValueError: If the response body cannot be parsed as valid JSON or
            is missing expected top-level keys.
    """
    _enforce_rate_limit()

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "application/vnd.sdmx.data+json;version=1.0",
    }

    logger.info("Fetching CapEx data from ABS: %s", _ABS_CAPEX_URL)

    try:
        response = requests.get(
            _ABS_CAPEX_URL,
            headers=headers,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout:
        logger.error("Request to ABS timed out after %ds", _TIMEOUT_SECONDS)
        raise ConnectionError(
            "The ABS data source is not responding. Please try again later."
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        logger.error("HTTP %s received from ABS API", status)
        if status == 429:
            raise ConnectionError(
                "The ABS API is rate-limiting requests. Please wait a moment and try again."
            )
        raise ConnectionError(
            f"The ABS data source returned an error (HTTP {status}). Please try again later."
        )
    except requests.ConnectionError as exc:
        logger.error("Connection to ABS API failed: %s", exc)
        raise ConnectionError(
            "Unable to reach the ABS API. Please check your internet connection."
        )

    try:
        data: dict[str, Any] = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse ABS API response as JSON: %s", exc)
        raise ValueError(
            "The data received from ABS was in an unexpected format. "
            "This may indicate an API change. Please try again later."
        )

    # The ABS API wraps dataSets and structure under a "data" envelope.
    # Normalise so the rest of the codebase always sees the flat layout.
    if "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    # Validate that the top-level keys we depend on are present
    if "dataSets" not in data or "structure" not in data:
        logger.error(
            "ABS response missing expected keys. Keys present: %s", list(data.keys())
        )
        raise ValueError(
            "The data received from ABS was in an unexpected format. "
            "This may indicate an API change. Please report this issue."
        )

    logger.info(
        "ABS API response received successfully (%d bytes)", len(response.content)
    )
    return data


def parse_sdmx_observations(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse SDMX-JSON observations into a flat list of records.

    Handles both the flat ``observations`` format and the nested
    ``series``-based format that some ABS endpoints return.

    Args:
        response: The raw SDMX-JSON dictionary returned by the ABS API.

    Returns:
        list[dict]: A list of observation records, each containing
        dimension values (FREQUENCY, MEASURE, INDUSTRY, ASSET_TYPE,
        REGION, TIME_PERIOD) and a ``value`` key.

    Raises:
        ValueError: If the response structure is unrecognisable.
    """
    try:
        dataset = response["dataSets"][0]
        structure = response["structure"]
        series_dims: list[dict[str, Any]] = structure["dimensions"].get("series", [])
        obs_dims: list[dict[str, Any]] = structure["dimensions"].get("observation", [])
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Cannot access SDMX structure: %s", exc)
        raise ValueError(
            "The data received from ABS was in an unexpected format."
        )

    # --- Flat observations format ---
    flat_observations: dict[str, Any] = dataset.get("observations", {})
    if flat_observations:
        return _parse_flat_observations(flat_observations, series_dims, obs_dims)

    # --- Series-based format ---
    series_data: dict[str, Any] = dataset.get("series", {})
    if series_data:
        return _parse_series_based(series_data, series_dims, obs_dims)

    logger.warning("ABS dataset contains neither 'observations' nor 'series' keys")
    return []


def _parse_flat_observations(
    observations: dict[str, Any],
    series_dims: list[dict[str, Any]],
    obs_dims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse the flat observations dict into records.

    Args:
        observations: Mapping of colon-separated index key to value array.
        series_dims: Series dimension metadata from the SDMX structure.
        obs_dims: Observation dimension metadata from the SDMX structure.

    Returns:
        list[dict]: Flat list of parsed observation records.
    """
    records: list[dict[str, Any]] = []

    for key, values in observations.items():
        try:
            indices = [int(i) for i in key.split(":")]
        except ValueError:
            logger.warning("Skipping malformed observation key: %s", key)
            continue

        record: dict[str, Any] = {}

        # Map series dimension indices
        for i, dim in enumerate(series_dims):
            if i < len(indices):
                dim_idx = indices[i]
                dim_values = dim.get("values", [])
                if dim_idx < len(dim_values):
                    record[dim["id"]] = dim_values[dim_idx]["id"]

        # Map observation dimension indices (typically just TIME_PERIOD)
        obs_start = len(series_dims)
        for i, dim in enumerate(obs_dims):
            idx_pos = obs_start + i
            if idx_pos < len(indices):
                dim_idx = indices[idx_pos]
                dim_values = dim.get("values", [])
                if dim_idx < len(dim_values):
                    record[dim["id"]] = dim_values[dim_idx]["id"]

        raw_value = values[0] if values else None
        record["value"] = float(raw_value) if raw_value is not None else None
        records.append(record)

    return records


def _parse_series_based(
    series_data: dict[str, Any],
    series_dims: list[dict[str, Any]],
    obs_dims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse the nested series-based observations dict into records.

    Args:
        series_data: Mapping of series key to ``{observations: {time_idx: [value]}}``
        series_dims: Series dimension metadata from the SDMX structure.
        obs_dims: Observation dimension metadata from the SDMX structure.

    Returns:
        list[dict]: Flat list of parsed observation records.
    """
    records: list[dict[str, Any]] = []

    for series_key, series_obj in series_data.items():
        try:
            series_indices = [int(i) for i in series_key.split(":")]
        except ValueError:
            logger.warning("Skipping malformed series key: %s", series_key)
            continue

        series_record: dict[str, Any] = {}

        # Decode series-level dimensions
        for i, dim in enumerate(series_dims):
            if i < len(series_indices):
                dim_idx = series_indices[i]
                dim_values = dim.get("values", [])
                if dim_idx < len(dim_values):
                    series_record[dim["id"]] = dim_values[dim_idx]["id"]

        # Decode each observation within this series
        obs_map: dict[str, Any] = series_obj.get("observations", {})
        for obs_key, obs_values in obs_map.items():
            try:
                obs_idx = int(obs_key)
            except ValueError:
                continue

            record = dict(series_record)
            # Map observation dimensions (typically TIME_PERIOD)
            for dim in obs_dims:
                dim_values = dim.get("values", [])
                if obs_idx < len(dim_values):
                    record[dim["id"]] = dim_values[obs_idx]["id"]

            raw_value = obs_values[0] if obs_values else None
            record["value"] = float(raw_value) if raw_value is not None else None
            records.append(record)

    return records
