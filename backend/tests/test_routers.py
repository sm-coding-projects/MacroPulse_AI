"""Tests for FastAPI routers — data.py and analyze.py endpoints."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sse_starlette.sse import AppStatus

from app.main import app
from app.models.schemas import CapExData, CapExQuarter

# Import the dependency functions so we can override them
from app.routers import data as data_router
from app.routers import analyze as analyze_router
from app.database import get_db


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAPEX_URL = "/api/data/capex"
HEALTH_URL = "/api/health"
ANALYZE_URL = "/api/analyze"
SETTINGS_TEST_URL = "/api/settings/test"

SAMPLE_FETCHED_AT = "2024-12-15 10:30:00"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_capex_data(period: str = "2024-Q3") -> CapExData:
    """Return a minimal CapExData for mocking cache returns."""
    quarter = CapExQuarter(
        period=period,
        total=42567.8,
        mining=18234.5,
        manufacturing=5678.9,
        other_selected=18654.4,
        buildings_structures=19876.3,
        equipment_plant_machinery=22691.5,
        qoq_change=3.23,
        yoy_change=3.82,
    )
    return CapExData(
        quarters=[quarter],
        by_industry={
            "Total": [{"period": period, "value": 42567.8}],
            "Mining": [{"period": period, "value": 18234.5}],
            "Manufacturing": [{"period": period, "value": 5678.9}],
            "Other Selected Industries": [{"period": period, "value": 18654.4}],
        },
        by_asset_type={
            "Total": [{"period": period, "value": 42567.8}],
            "Buildings & Structures": [{"period": period, "value": 19876.3}],
            "Equipment, Plant & Machinery": [{"period": period, "value": 22691.5}],
        },
        metadata={
            "source": "Australian Bureau of Statistics — Catalogue No. 5625.0",
            "last_updated": "2024-12-15T00:00:00+00:00",
            "estimate_number": "N/A",
            "is_cached": False,
            "periods_available": [period],
        },
    )


def _make_db_override(mock_conn: sqlite3.Connection | MagicMock | None = None):
    """Return a FastAPI dependency override yielding a mock DB connection."""
    if mock_conn is None:
        mock_conn = MagicMock(spec=sqlite3.Connection)

    def override():
        yield mock_conn

    return override


def _get_client_with_db_override(mock_conn=None) -> TestClient:
    """Return a TestClient with the DB dependency overridden to avoid filesystem."""
    override = _make_db_override(mock_conn)
    # Override both routers' DB dependencies
    app.dependency_overrides[data_router._get_db_connection] = override
    app.dependency_overrides[analyze_router._get_db_connection] = override
    client = TestClient(app)
    return client


def _clear_overrides():
    """Remove all dependency overrides from the FastAPI app."""
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health check (no DB dependency — no override needed)
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Tests for the GET /api/health endpoint."""

    def test_health_check_returns_200(self, client):
        """GET /api/health returns HTTP 200."""
        response = client.get(HEALTH_URL)
        assert response.status_code == 200

    def test_health_check_returns_ok_status(self, client):
        """GET /api/health body contains status='ok'."""
        response = client.get(HEALTH_URL)
        body = response.json()
        assert body["status"] == "ok"

    def test_health_check_returns_service_name(self, client):
        """GET /api/health body contains the service name."""
        response = client.get(HEALTH_URL)
        body = response.json()
        assert "service" in body
        assert "macropulse" in body["service"].lower()


# ---------------------------------------------------------------------------
# GET /api/data/capex — cache hit (fresh)
# ---------------------------------------------------------------------------


class TestGetCapexDataCacheHit:
    """Tests for the capex endpoint when fresh cache data is available."""

    def setup_method(self):
        """Set up a mock DB override before each test."""
        self._mock_conn = MagicMock(spec=sqlite3.Connection)
        app.dependency_overrides[data_router._get_db_connection] = _make_db_override(self._mock_conn)
        app.dependency_overrides[analyze_router._get_db_connection] = _make_db_override(self._mock_conn)
        self._client = TestClient(app)

    def teardown_method(self):
        """Remove dependency overrides after each test."""
        _clear_overrides()

    def test_capex_fresh_cache_returns_200(self):
        """GET /api/data/capex returns 200 when fresh cached data exists."""
        capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        assert response.status_code == 200

    def test_capex_fresh_cache_returns_data(self):
        """GET /api/data/capex response body contains 'data' when cache is fresh."""
        capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["data"] is not None

    def test_capex_fresh_cache_from_cache_is_false(self):
        """Fresh cache response has from_cache=False (no staleness warning)."""
        capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["from_cache"] is False

    def test_capex_fresh_cache_returns_correct_quarter(self):
        """Response data contains the correct quarter period."""
        capex = _make_capex_data("2024-Q3")
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        body = response.json()
        quarters = body["data"]["quarters"]
        assert any(q["period"] == "2024-Q3" for q in quarters)

    def test_capex_fresh_cache_no_error_field(self):
        """Fresh cache response has error=null."""
        capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body.get("error") is None

    def test_capex_response_schema_shape(self):
        """Response body contains the required DataResponse fields."""
        capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        body = response.json()
        assert "data" in body
        assert "from_cache" in body
        assert "error" in body


# ---------------------------------------------------------------------------
# GET /api/data/capex — cache miss, ABS fetch success
# ---------------------------------------------------------------------------


class TestGetCapexDataCacheMissAbsSuccess:
    """Tests for the capex endpoint when cache is empty but ABS fetch succeeds."""

    def setup_method(self):
        self._mock_conn = MagicMock(spec=sqlite3.Connection)
        app.dependency_overrides[data_router._get_db_connection] = _make_db_override(self._mock_conn)
        self._client = TestClient(app)

    def teardown_method(self):
        _clear_overrides()

    def test_abs_success_returns_200(self, sample_sdmx_response):
        """Cache miss + successful ABS fetch returns HTTP 200."""
        fresh_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch("app.routers.data.abs_client.fetch_capex_from_abs", return_value=sample_sdmx_response):
                with patch("app.routers.data.data_processor.process_abs_response", return_value=fresh_capex):
                    with patch("app.routers.data.cache.save_to_cache"):
                        response = self._client.get(CAPEX_URL)
        assert response.status_code == 200

    def test_abs_success_returns_data(self, sample_sdmx_response):
        """Cache miss + ABS success returns populated data field."""
        fresh_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch("app.routers.data.abs_client.fetch_capex_from_abs", return_value=sample_sdmx_response):
                with patch("app.routers.data.data_processor.process_abs_response", return_value=fresh_capex):
                    with patch("app.routers.data.cache.save_to_cache"):
                        response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["data"] is not None

    def test_abs_success_from_cache_is_false(self, sample_sdmx_response):
        """Fresh data from ABS has from_cache=False."""
        fresh_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch("app.routers.data.abs_client.fetch_capex_from_abs", return_value=sample_sdmx_response):
                with patch("app.routers.data.data_processor.process_abs_response", return_value=fresh_capex):
                    with patch("app.routers.data.cache.save_to_cache"):
                        response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["from_cache"] is False

    def test_abs_success_saves_to_cache(self, sample_sdmx_response):
        """Successful ABS fetch triggers save_to_cache."""
        fresh_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch("app.routers.data.abs_client.fetch_capex_from_abs", return_value=sample_sdmx_response):
                with patch("app.routers.data.data_processor.process_abs_response", return_value=fresh_capex):
                    with patch("app.routers.data.cache.save_to_cache") as mock_save:
                        self._client.get(CAPEX_URL)
        mock_save.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/data/capex — cache miss, ABS failure, no stale cache
# ---------------------------------------------------------------------------


class TestGetCapexDataCacheMissAbsFailure:
    """Tests for the capex endpoint when cache is empty and ABS fetch fails."""

    def setup_method(self):
        self._mock_conn = MagicMock(spec=sqlite3.Connection)
        app.dependency_overrides[data_router._get_db_connection] = _make_db_override(self._mock_conn)
        self._client = TestClient(app)

    def teardown_method(self):
        _clear_overrides()

    def test_no_cache_abs_failure_returns_200(self):
        """No cache + ABS failure still returns HTTP 200 (error in body)."""
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS unavailable"),
            ):
                with patch("app.routers.data.cache.get_stale_data", return_value=(None, None)):
                    response = self._client.get(CAPEX_URL)
        assert response.status_code == 200

    def test_no_cache_abs_failure_returns_error_message(self):
        """No cache + ABS failure body contains a user-facing error message."""
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS unavailable"),
            ):
                with patch("app.routers.data.cache.get_stale_data", return_value=(None, None)):
                    response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["error"] is not None
        assert len(body["error"]) > 0

    def test_no_cache_abs_failure_data_is_null(self):
        """No cache + ABS failure has data=null in response."""
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS unavailable"),
            ):
                with patch("app.routers.data.cache.get_stale_data", return_value=(None, None)):
                    response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["data"] is None

    def test_no_cache_value_error_returns_error(self):
        """ValueError from process_abs_response results in error response."""
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch("app.routers.data.abs_client.fetch_capex_from_abs", return_value={}):
                with patch(
                    "app.routers.data.data_processor.process_abs_response",
                    side_effect=ValueError("Bad format"),
                ):
                    with patch("app.routers.data.cache.get_stale_data", return_value=(None, None)):
                        response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["data"] is None
        assert body["error"] is not None


# ---------------------------------------------------------------------------
# GET /api/data/capex — stale cache fallback on ABS failure
# ---------------------------------------------------------------------------


class TestGetCapexDataStaleCacheFallback:
    """Tests for the stale-cache fallback when ABS fetch fails."""

    def setup_method(self):
        self._mock_conn = MagicMock(spec=sqlite3.Connection)
        app.dependency_overrides[data_router._get_db_connection] = _make_db_override(self._mock_conn)
        self._client = TestClient(app)

    def teardown_method(self):
        _clear_overrides()

    def test_stale_cache_fallback_returns_200(self):
        """ABS failure with stale cache returns HTTP 200."""
        stale_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS down"),
            ):
                with patch(
                    "app.routers.data.cache.get_stale_data",
                    return_value=(stale_capex, SAMPLE_FETCHED_AT),
                ):
                    response = self._client.get(CAPEX_URL)
        assert response.status_code == 200

    def test_stale_cache_fallback_from_cache_is_true(self):
        """Stale cache fallback sets from_cache=True."""
        stale_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS down"),
            ):
                with patch(
                    "app.routers.data.cache.get_stale_data",
                    return_value=(stale_capex, SAMPLE_FETCHED_AT),
                ):
                    response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["from_cache"] is True

    def test_stale_cache_fallback_returns_data(self):
        """Stale cache fallback response contains non-null data."""
        stale_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS down"),
            ):
                with patch(
                    "app.routers.data.cache.get_stale_data",
                    return_value=(stale_capex, SAMPLE_FETCHED_AT),
                ):
                    response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["data"] is not None

    def test_stale_cache_fallback_includes_error_warning(self):
        """Stale cache fallback includes a warning in the error field."""
        stale_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS down"),
            ):
                with patch(
                    "app.routers.data.cache.get_stale_data",
                    return_value=(stale_capex, SAMPLE_FETCHED_AT),
                ):
                    response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["error"] is not None

    def test_stale_cache_fallback_cache_date_is_set(self):
        """Stale cache fallback includes cache_date in the response."""
        stale_capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.data.abs_client.fetch_capex_from_abs",
                side_effect=ConnectionError("ABS down"),
            ):
                with patch(
                    "app.routers.data.cache.get_stale_data",
                    return_value=(stale_capex, SAMPLE_FETCHED_AT),
                ):
                    response = self._client.get(CAPEX_URL)
        body = response.json()
        assert body["cache_date"] == SAMPLE_FETCHED_AT


# ---------------------------------------------------------------------------
# POST /api/settings/test (no DB dependency)
# ---------------------------------------------------------------------------


class TestSettingsTest:
    """Tests for the POST /api/settings/test endpoint."""

    _valid_payload: dict[str, Any] = {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key",
        "model": "gpt-4o",
    }

    def test_settings_test_valid_connection_returns_200(self, client):
        """Valid LLM credentials return HTTP 200."""
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(True, None),
        ):
            response = client.post(SETTINGS_TEST_URL, json=self._valid_payload)
        assert response.status_code == 200

    def test_settings_test_valid_connection_success_true(self, client):
        """Successful connection test returns {success: true}."""
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(True, None),
        ):
            response = client.post(SETTINGS_TEST_URL, json=self._valid_payload)
        body = response.json()
        assert body["success"] is True

    def test_settings_test_valid_connection_no_error(self, client):
        """Successful connection test has error=null."""
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(True, None),
        ):
            response = client.post(SETTINGS_TEST_URL, json=self._valid_payload)
        body = response.json()
        assert body["error"] is None

    def test_settings_test_invalid_key_returns_200(self, client):
        """Invalid API key still returns HTTP 200 (failure info in body)."""
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(False, "Invalid API key. Please check your credentials."),
        ):
            response = client.post(SETTINGS_TEST_URL, json=self._valid_payload)
        assert response.status_code == 200

    def test_settings_test_invalid_key_success_false(self, client):
        """Invalid API key returns {success: false}."""
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(False, "Invalid API key. Please check your credentials."),
        ):
            response = client.post(SETTINGS_TEST_URL, json=self._valid_payload)
        body = response.json()
        assert body["success"] is False

    def test_settings_test_invalid_key_error_message(self, client):
        """Invalid API key response has a non-empty error message."""
        error_msg = "Invalid API key. Please check your credentials."
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(False, error_msg),
        ):
            response = client.post(SETTINGS_TEST_URL, json=self._valid_payload)
        body = response.json()
        assert body["error"] == error_msg

    def test_settings_test_unreachable_endpoint_returns_failure(self, client):
        """Unreachable endpoint returns {success: false} with descriptive error."""
        error_msg = "Could not reach the LLM endpoint. Please verify the URL."
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(False, error_msg),
        ):
            response = client.post(SETTINGS_TEST_URL, json=self._valid_payload)
        body = response.json()
        assert body["success"] is False
        assert "reach" in body["error"].lower() or "url" in body["error"].lower()

    def test_settings_test_missing_base_url_returns_422(self, client):
        """POST to /settings/test without base_url returns HTTP 422."""
        payload = {"api_key": "sk-test", "model": "gpt-4"}
        response = client.post(SETTINGS_TEST_URL, json=payload)
        assert response.status_code == 422

    def test_settings_test_missing_model_returns_422(self, client):
        """POST to /settings/test without model returns HTTP 422."""
        payload = {"base_url": "https://api.openai.com/v1", "api_key": "sk-test"}
        response = client.post(SETTINGS_TEST_URL, json=payload)
        assert response.status_code == 422

    def test_settings_test_no_api_key_allowed(self, client):
        """POST to /settings/test with empty api_key is valid (remote models)."""
        payload = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "llama3.2",
        }
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(True, None),
        ):
            response = client.post(SETTINGS_TEST_URL, json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_settings_test_localhost_url_rejected(self, client):
        """POST to /settings/test with localhost base_url is rejected with HTTP 422."""
        payload = {
            "base_url": "http://localhost:11434/v1",
            "api_key": "",
            "model": "llama3.2",
        }
        response = client.post(SETTINGS_TEST_URL, json=payload)
        assert response.status_code == 422

    def test_settings_test_private_ip_rejected(self, client):
        """POST to /settings/test with a private IP base_url is rejected with HTTP 422."""
        payload = {
            "base_url": "http://192.168.1.50:11434/v1",
            "api_key": "",
            "model": "llama3.2",
        }
        response = client.post(SETTINGS_TEST_URL, json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------


class TestAnalyze:
    """Tests for the POST /api/analyze endpoint (SSE streaming)."""

    _valid_payload: dict[str, Any] = {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key",
        "model": "gpt-4o",
        "data_summary": {},
    }

    def setup_method(self):
        # Reset the AppStatus event so each SSE test gets a fresh event loop binding.
        AppStatus.should_exit_event = None
        self._mock_conn = MagicMock(spec=sqlite3.Connection)
        app.dependency_overrides[analyze_router._get_db_connection] = _make_db_override(self._mock_conn)
        self._client = TestClient(app)

    def teardown_method(self):
        _clear_overrides()
        # Clean up so the next test class is unaffected
        AppStatus.should_exit_event = None

    def test_analyze_missing_base_url_returns_422(self):
        """POST /api/analyze without base_url returns HTTP 422."""
        payload = {"api_key": "sk-test", "model": "gpt-4o"}
        response = self._client.post(ANALYZE_URL, json=payload)
        assert response.status_code == 422

    def test_analyze_missing_model_returns_422(self):
        """POST /api/analyze without model returns HTTP 422."""
        payload = {"base_url": "https://api.openai.com/v1", "api_key": "sk-test"}
        response = self._client.post(ANALYZE_URL, json=payload)
        assert response.status_code == 422

    def test_analyze_no_cache_returns_422_json(self):
        """POST /api/analyze with no cached data returns HTTP 422 JSON error."""
        with patch("app.routers.analyze.cache.get_cached_data", return_value=(None, None)):
            with patch("app.routers.analyze.cache.get_stale_data", return_value=(None, None)):
                response = self._client.post(ANALYZE_URL, json=self._valid_payload)
        assert response.status_code == 422
        body = response.json()
        assert body.get("error") is not None

    def test_analyze_no_cache_error_message_mentions_data(self):
        """No-data error message guides the user to fetch data first."""
        with patch("app.routers.analyze.cache.get_cached_data", return_value=(None, None)):
            with patch("app.routers.analyze.cache.get_stale_data", return_value=(None, None)):
                response = self._client.post(ANALYZE_URL, json=self._valid_payload)
        body = response.json()
        error_lower = body["error"].lower()
        assert "data" in error_lower or "capex" in error_lower or "fetch" in error_lower

    def test_analyze_with_cache_returns_sse_stream(self, sample_capex_data):
        """POST /api/analyze with cached data returns a streaming SSE response."""
        async def fake_stream(*args, **kwargs):
            yield "Hello"
            yield " world"

        with patch("app.routers.analyze.cache.get_cached_data", return_value=(sample_capex_data, SAMPLE_FETCHED_AT)):
            with patch("app.routers.analyze.stream_analysis", new=fake_stream):
                response = self._client.post(ANALYZE_URL, json=self._valid_payload)

        assert response.status_code == 200

    def test_analyze_with_stale_cache_returns_200(self, sample_capex_data):
        """POST /api/analyze with only stale cache data still streams successfully."""
        async def fake_stream(*args, **kwargs):
            yield "Analysis text"

        with patch("app.routers.analyze.cache.get_cached_data", return_value=(None, None)):
            with patch(
                "app.routers.analyze.cache.get_stale_data",
                return_value=(sample_capex_data, SAMPLE_FETCHED_AT),
            ):
                with patch("app.routers.analyze.stream_analysis", new=fake_stream):
                    response = self._client.post(ANALYZE_URL, json=self._valid_payload)

        assert response.status_code == 200

    def test_analyze_sse_content_type(self, sample_capex_data):
        """POST /api/analyze returns text/event-stream content type."""
        async def fake_stream(*args, **kwargs):
            yield "chunk"

        with patch("app.routers.analyze.cache.get_cached_data", return_value=(sample_capex_data, SAMPLE_FETCHED_AT)):
            with patch("app.routers.analyze.stream_analysis", new=fake_stream):
                response = self._client.post(ANALYZE_URL, json=self._valid_payload)

        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type

    def test_analyze_sse_body_contains_data(self, sample_capex_data):
        """SSE body contains 'data:' lines from the stream."""
        async def fake_stream(*args, **kwargs):
            yield "Analysis result"

        with patch("app.routers.analyze.cache.get_cached_data", return_value=(sample_capex_data, SAMPLE_FETCHED_AT)):
            with patch("app.routers.analyze.stream_analysis", new=fake_stream):
                response = self._client.post(ANALYZE_URL, json=self._valid_payload)

        assert b"data:" in response.content


# ---------------------------------------------------------------------------
# Response model validation
# ---------------------------------------------------------------------------


class TestResponseSchemas:
    """Smoke tests confirming response schemas match Pydantic models."""

    def setup_method(self):
        self._mock_conn = MagicMock(spec=sqlite3.Connection)
        app.dependency_overrides[data_router._get_db_connection] = _make_db_override(self._mock_conn)
        self._client = TestClient(app)

    def teardown_method(self):
        _clear_overrides()

    def test_capex_response_data_has_quarters_field(self):
        """CapEx response data contains a 'quarters' list."""
        capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        body = response.json()
        assert "quarters" in body["data"]
        assert isinstance(body["data"]["quarters"], list)

    def test_capex_response_quarter_has_all_fields(self):
        """Each quarter object has all required CapExQuarter fields."""
        capex = _make_capex_data()
        with patch("app.routers.data.cache.get_cached_data", return_value=(capex, SAMPLE_FETCHED_AT)):
            response = self._client.get(CAPEX_URL)
        quarter = response.json()["data"]["quarters"][0]
        for field in [
            "period",
            "total",
            "mining",
            "manufacturing",
            "other_selected",
            "buildings_structures",
            "equipment_plant_machinery",
        ]:
            assert field in quarter, f"Missing field '{field}' in quarter"

    def test_settings_response_has_success_field(self, client):
        """Settings test response always has 'success' boolean."""
        with patch(
            "app.routers.analyze.test_llm_connection",
            return_value=(True, None),
        ):
            response = client.post(
                SETTINGS_TEST_URL,
                json={
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-key",
                    "model": "gpt-4o",
                },
            )
        body = response.json()
        assert "success" in body
        assert isinstance(body["success"], bool)
