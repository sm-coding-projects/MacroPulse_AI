"""Tests for app.services.abs_client — ABS API fetch and SDMX parsing."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.abs_client import (
    _ABS_CAPEX_URL,
    _USER_AGENT,
    fetch_capex_from_abs,
    parse_sdmx_observations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int = 200,
    json_data: Any = None,
    raise_for_status_exc: Exception | None = None,
    content_bytes: bytes = b"{}",
) -> MagicMock:
    """Build a minimal mock requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.content = content_bytes

    if raise_for_status_exc is not None:
        mock_resp.raise_for_status.side_effect = raise_for_status_exc
    else:
        mock_resp.raise_for_status.return_value = None

    if json_data is not None:
        mock_resp.json.return_value = json_data
        mock_resp.content = json.dumps(json_data).encode()
    else:
        mock_resp.json.side_effect = ValueError("No JSON set")

    return mock_resp


# ---------------------------------------------------------------------------
# fetch_capex_from_abs — network-level tests
# ---------------------------------------------------------------------------


class TestFetchCapexFromAbs:
    """Tests for the fetch_capex_from_abs function."""

    def test_fetch_capex_success(self, sample_sdmx_response):
        """Successful fetch returns parsed SDMX dictionary with required keys."""
        mock_resp = _make_response(
            status_code=200,
            json_data=sample_sdmx_response,
            content_bytes=json.dumps(sample_sdmx_response).encode(),
        )

        with patch("app.services.abs_client.requests.get", return_value=mock_resp) as mock_get:
            with patch("app.services.abs_client._enforce_rate_limit"):
                result = fetch_capex_from_abs()

        mock_get.assert_called_once()
        assert "dataSets" in result
        assert "structure" in result

    def test_fetch_capex_correct_url(self, sample_sdmx_response):
        """fetch_capex_from_abs calls the correct ABS endpoint URL."""
        mock_resp = _make_response(
            status_code=200,
            json_data=sample_sdmx_response,
            content_bytes=json.dumps(sample_sdmx_response).encode(),
        )

        with patch("app.services.abs_client.requests.get", return_value=mock_resp) as mock_get:
            with patch("app.services.abs_client._enforce_rate_limit"):
                fetch_capex_from_abs()

        call_args = mock_get.call_args
        assert call_args[0][0] == _ABS_CAPEX_URL

    def test_fetch_capex_user_agent_header(self, sample_sdmx_response):
        """User-Agent header is set to the MacroPulse-AI value."""
        mock_resp = _make_response(
            status_code=200,
            json_data=sample_sdmx_response,
            content_bytes=json.dumps(sample_sdmx_response).encode(),
        )

        with patch("app.services.abs_client.requests.get", return_value=mock_resp) as mock_get:
            with patch("app.services.abs_client._enforce_rate_limit"):
                fetch_capex_from_abs()

        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers.get("User-Agent") == _USER_AGENT

    def test_fetch_capex_accept_header(self, sample_sdmx_response):
        """Accept header requests SDMX-JSON format."""
        mock_resp = _make_response(
            status_code=200,
            json_data=sample_sdmx_response,
            content_bytes=json.dumps(sample_sdmx_response).encode(),
        )

        with patch("app.services.abs_client.requests.get", return_value=mock_resp) as mock_get:
            with patch("app.services.abs_client._enforce_rate_limit"):
                fetch_capex_from_abs()

        headers = mock_get.call_args[1]["headers"]
        assert "sdmx" in headers.get("Accept", "").lower()

    def test_fetch_capex_timeout(self):
        """Timeout raises ConnectionError with a user-friendly message."""
        with patch(
            "app.services.abs_client.requests.get",
            side_effect=requests.Timeout("timed out"),
        ):
            with patch("app.services.abs_client._enforce_rate_limit"):
                with pytest.raises(ConnectionError) as exc_info:
                    fetch_capex_from_abs()

        assert "not responding" in str(exc_info.value).lower() or \
               "try again" in str(exc_info.value).lower()

    def test_fetch_capex_http_500_error(self):
        """HTTP 500 raises ConnectionError mentioning the status code."""
        http_exc = requests.HTTPError("500 error")
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        http_exc.response = mock_error_response

        with patch(
            "app.services.abs_client.requests.get",
            side_effect=http_exc,
        ):
            with patch("app.services.abs_client._enforce_rate_limit"):
                with pytest.raises(ConnectionError) as exc_info:
                    fetch_capex_from_abs()

        error_message = str(exc_info.value)
        assert "500" in error_message

    def test_fetch_capex_http_429_rate_limit(self):
        """HTTP 429 raises ConnectionError mentioning rate-limiting."""
        http_exc = requests.HTTPError("429 Too Many Requests")
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        http_exc.response = mock_error_response

        with patch(
            "app.services.abs_client.requests.get",
            side_effect=http_exc,
        ):
            with patch("app.services.abs_client._enforce_rate_limit"):
                with pytest.raises(ConnectionError) as exc_info:
                    fetch_capex_from_abs()

        error_message = str(exc_info.value).lower()
        assert "rate" in error_message or "limit" in error_message or "wait" in error_message

    def test_fetch_capex_connection_error(self):
        """Network failure raises ConnectionError mentioning connectivity."""
        with patch(
            "app.services.abs_client.requests.get",
            side_effect=requests.ConnectionError("DNS failure"),
        ):
            with patch("app.services.abs_client._enforce_rate_limit"):
                with pytest.raises(ConnectionError) as exc_info:
                    fetch_capex_from_abs()

        assert "reach" in str(exc_info.value).lower() or \
               "connect" in str(exc_info.value).lower()

    def test_fetch_capex_malformed_json(self):
        """Invalid JSON in the response body raises ValueError."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = b"this is not json"
        mock_resp.json.side_effect = ValueError("No JSON object could be decoded")

        with patch("app.services.abs_client.requests.get", return_value=mock_resp):
            with patch("app.services.abs_client._enforce_rate_limit"):
                with pytest.raises(ValueError) as exc_info:
                    fetch_capex_from_abs()

        assert "unexpected format" in str(exc_info.value).lower() or \
               "format" in str(exc_info.value).lower()

    def test_fetch_capex_missing_datasets_key(self):
        """Response missing 'dataSets' key raises ValueError."""
        bad_data = {"header": {}, "structure": {}}  # no dataSets
        mock_resp = _make_response(
            status_code=200,
            json_data=bad_data,
            content_bytes=json.dumps(bad_data).encode(),
        )

        with patch("app.services.abs_client.requests.get", return_value=mock_resp):
            with patch("app.services.abs_client._enforce_rate_limit"):
                with pytest.raises(ValueError) as exc_info:
                    fetch_capex_from_abs()

        assert "unexpected format" in str(exc_info.value).lower()

    def test_fetch_capex_missing_structure_key(self):
        """Response missing 'structure' key raises ValueError."""
        bad_data = {"dataSets": [{}]}  # no structure
        mock_resp = _make_response(
            status_code=200,
            json_data=bad_data,
            content_bytes=json.dumps(bad_data).encode(),
        )

        with patch("app.services.abs_client.requests.get", return_value=mock_resp):
            with patch("app.services.abs_client._enforce_rate_limit"):
                with pytest.raises(ValueError):
                    fetch_capex_from_abs()


# ---------------------------------------------------------------------------
# parse_sdmx_observations — unit tests for the flat parser
# ---------------------------------------------------------------------------


class TestParseSdmxObservationsFlat:
    """Tests for parse_sdmx_observations with flat observations format."""

    def test_parse_flat_returns_list(self, sample_sdmx_response):
        """Parsing a valid flat observations response returns a non-empty list."""
        records = parse_sdmx_observations(sample_sdmx_response)
        assert isinstance(records, list)
        assert len(records) > 0

    def test_parse_flat_records_have_required_fields(self, sample_sdmx_response):
        """Each parsed record contains TIME_PERIOD and value fields."""
        records = parse_sdmx_observations(sample_sdmx_response)
        for record in records:
            assert "TIME_PERIOD" in record, f"Missing TIME_PERIOD in {record}"
            assert "value" in record, f"Missing value in {record}"

    def test_parse_flat_records_have_dimension_fields(self, sample_sdmx_response):
        """Each record contains FREQUENCY, MEASURE, INDUSTRY, ASSET_TYPE, REGION."""
        records = parse_sdmx_observations(sample_sdmx_response)
        expected_dims = {"FREQUENCY", "MEASURE", "INDUSTRY", "ASSET_TYPE", "REGION"}
        for record in records:
            for dim in expected_dims:
                assert dim in record, f"Missing {dim} in {record}"

    def test_parse_flat_correct_time_periods(self, sample_sdmx_response):
        """Parsed records contain the expected quarter identifiers."""
        records = parse_sdmx_observations(sample_sdmx_response)
        periods = {r["TIME_PERIOD"] for r in records}
        assert "2024-Q3" in periods
        assert "2024-Q2" in periods
        assert "2022-Q4" in periods

    def test_parse_flat_values_are_floats(self, sample_sdmx_response):
        """Non-null observation values are parsed as floats."""
        records = parse_sdmx_observations(sample_sdmx_response)
        for record in records:
            if record["value"] is not None:
                assert isinstance(record["value"], float), \
                    f"Expected float, got {type(record['value'])} for {record}"

    def test_parse_flat_capex_act_records_present(self, sample_sdmx_response):
        """Records include CAPEX_ACT measure observations."""
        records = parse_sdmx_observations(sample_sdmx_response)
        act_records = [r for r in records if r.get("MEASURE") == "CAPEX_ACT"]
        assert len(act_records) > 0

    def test_parse_flat_capex_exp_records_present(self, sample_sdmx_response):
        """Records include CAPEX_EXP measure observations (for filter testing)."""
        records = parse_sdmx_observations(sample_sdmx_response)
        exp_records = [r for r in records if r.get("MEASURE") == "CAPEX_EXP"]
        assert len(exp_records) > 0

    def test_parse_empty_observations_returns_empty_list(self, sample_sdmx_response):
        """Dataset with no observations or series returns an empty list."""
        empty_response = {
            "dataSets": [{"action": "Information"}],  # no observations or series
            "structure": sample_sdmx_response["structure"],
        }
        records = parse_sdmx_observations(empty_response)
        assert records == []


# ---------------------------------------------------------------------------
# parse_sdmx_observations — unit tests for the series-based parser
# ---------------------------------------------------------------------------


class TestParseSdmxObservationsSeries:
    """Tests for parse_sdmx_observations with series-based format."""

    def test_parse_series_returns_list(self, sample_sdmx_series_response):
        """Parsing a valid series-based response returns a non-empty list."""
        records = parse_sdmx_observations(sample_sdmx_series_response)
        assert isinstance(records, list)
        assert len(records) > 0

    def test_parse_series_records_have_time_period(self, sample_sdmx_series_response):
        """Each record in series format has TIME_PERIOD."""
        records = parse_sdmx_observations(sample_sdmx_series_response)
        for record in records:
            assert "TIME_PERIOD" in record

    def test_parse_series_records_have_value(self, sample_sdmx_series_response):
        """Each record in series format has a value field."""
        records = parse_sdmx_observations(sample_sdmx_series_response)
        for record in records:
            assert "value" in record

    def test_parse_series_values_are_floats(self, sample_sdmx_series_response):
        """Non-null values in series format are floats."""
        records = parse_sdmx_observations(sample_sdmx_series_response)
        for record in records:
            if record["value"] is not None:
                assert isinstance(record["value"], float)

    def test_parse_series_correct_time_periods(self, sample_sdmx_series_response):
        """Series-based parsing returns the correct quarter identifiers."""
        records = parse_sdmx_observations(sample_sdmx_series_response)
        periods = {r["TIME_PERIOD"] for r in records}
        assert "2024-Q2" in periods
        assert "2023-Q3" in periods


# ---------------------------------------------------------------------------
# parse_sdmx_observations — error handling
# ---------------------------------------------------------------------------


class TestParseSdmxObservationsErrors:
    """Tests for error handling in parse_sdmx_observations."""

    def test_missing_datasets_raises_value_error(self):
        """Missing dataSets key raises ValueError."""
        bad_response: dict[str, Any] = {"structure": {}}
        with pytest.raises(ValueError):
            parse_sdmx_observations(bad_response)

    def test_empty_datasets_raises_value_error(self):
        """Empty dataSets list raises ValueError."""
        bad_response: dict[str, Any] = {
            "dataSets": [],
            "structure": {"dimensions": {"series": [], "observation": []}},
        }
        with pytest.raises(ValueError):
            parse_sdmx_observations(bad_response)

    def test_missing_structure_key_raises_value_error(self):
        """Missing structure key raises ValueError."""
        bad_response: dict[str, Any] = {"dataSets": [{}]}
        with pytest.raises(ValueError):
            parse_sdmx_observations(bad_response)

    def test_totally_empty_dict_raises_value_error(self):
        """Completely empty dict raises ValueError."""
        with pytest.raises(ValueError):
            parse_sdmx_observations({})
