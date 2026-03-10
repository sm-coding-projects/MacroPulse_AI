"""Tests for app.services.cache — SQLite caching logic."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.models.schemas import CapExData, CapExQuarter
from app.services.cache import (
    get_cached_data,
    get_stale_data,
    is_cache_valid,
    save_to_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_capex_data(period: str = "2024-Q3") -> CapExData:
    """Return a minimal valid CapExData for caching tests."""
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


def _insert_row_with_timestamp(
    db: sqlite3.Connection, data: CapExData, fetched_at: str
) -> None:
    """Insert a cache row with an explicit fetched_at timestamp."""
    data_json = data.model_dump_json()
    db.execute("DELETE FROM capex_cache")
    db.execute(
        "INSERT INTO capex_cache (data_json, fetched_at) VALUES (?, ?)",
        (data_json, fetched_at),
    )
    db.commit()


# ---------------------------------------------------------------------------
# save_to_cache
# ---------------------------------------------------------------------------


class TestSaveToCache:
    """Tests for the save_to_cache function."""

    def test_save_inserts_a_row(self, test_db):
        """save_to_cache inserts exactly one row into the database."""
        data = _minimal_capex_data()
        save_to_cache(test_db, data)

        count = test_db.execute("SELECT COUNT(*) FROM capex_cache").fetchone()[0]
        assert count == 1

    def test_save_stores_valid_json(self, test_db):
        """The stored data_json field can be parsed as JSON."""
        data = _minimal_capex_data()
        save_to_cache(test_db, data)

        row = test_db.execute("SELECT data_json FROM capex_cache").fetchone()
        parsed = json.loads(row[0])
        assert isinstance(parsed, dict)
        assert "quarters" in parsed

    def test_save_overwrites_previous_entry(self, test_db):
        """Saving twice leaves only the most recent entry (single-row cache)."""
        data_old = _minimal_capex_data("2024-Q2")
        data_new = _minimal_capex_data("2024-Q3")

        save_to_cache(test_db, data_old)
        save_to_cache(test_db, data_new)

        count = test_db.execute("SELECT COUNT(*) FROM capex_cache").fetchone()[0]
        assert count == 1

        row = test_db.execute("SELECT data_json FROM capex_cache").fetchone()
        saved = CapExData.model_validate_json(row[0])
        assert saved.quarters[0].period == "2024-Q3"

    def test_save_sets_fetched_at_timestamp(self, test_db):
        """save_to_cache populates the fetched_at column with a timestamp."""
        data = _minimal_capex_data()
        save_to_cache(test_db, data)

        row = test_db.execute("SELECT fetched_at FROM capex_cache").fetchone()
        assert row[0] is not None
        assert len(str(row[0])) > 0


# ---------------------------------------------------------------------------
# is_cache_valid
# ---------------------------------------------------------------------------


class TestIsCacheValid:
    """Tests for the is_cache_valid function."""

    def test_empty_cache_returns_false(self, test_db):
        """is_cache_valid returns False when the table is empty."""
        result = is_cache_valid(test_db, ttl_hours=24)
        assert result is False

    def test_fresh_cache_returns_true(self, test_db):
        """is_cache_valid returns True when data was just stored."""
        data = _minimal_capex_data()
        save_to_cache(test_db, data)

        result = is_cache_valid(test_db, ttl_hours=24)
        assert result is True

    def test_expired_cache_returns_false(self, test_db):
        """is_cache_valid returns False when cached data is older than the TTL."""
        data = _minimal_capex_data()
        old_timestamp = (
            datetime.now(tz=timezone.utc) - timedelta(hours=25)
        ).isoformat()
        _insert_row_with_timestamp(test_db, data, old_timestamp)

        result = is_cache_valid(test_db, ttl_hours=24)
        assert result is False

    def test_cache_exactly_at_boundary_returns_false(self, test_db):
        """Cache entry at exactly TTL age is considered expired."""
        data = _minimal_capex_data()
        boundary_timestamp = (
            datetime.now(tz=timezone.utc) - timedelta(hours=24, seconds=1)
        ).isoformat()
        _insert_row_with_timestamp(test_db, data, boundary_timestamp)

        result = is_cache_valid(test_db, ttl_hours=24)
        assert result is False

    def test_custom_ttl_respected(self, test_db):
        """is_cache_valid respects the provided ttl_hours parameter."""
        data = _minimal_capex_data()
        # Stored 2 hours ago
        two_hours_ago = (
            datetime.now(tz=timezone.utc) - timedelta(hours=2)
        ).isoformat()
        _insert_row_with_timestamp(test_db, data, two_hours_ago)

        # With 1-hour TTL, this is expired
        assert is_cache_valid(test_db, ttl_hours=1) is False
        # With 3-hour TTL, this is still fresh
        assert is_cache_valid(test_db, ttl_hours=3) is True


# ---------------------------------------------------------------------------
# get_cached_data
# ---------------------------------------------------------------------------


class TestGetCachedData:
    """Tests for the get_cached_data function."""

    def test_empty_db_returns_none_tuple(self, test_db):
        """Empty cache returns (None, None)."""
        data, fetched_at = get_cached_data(test_db, ttl_hours=24)
        assert data is None
        assert fetched_at is None

    def test_fresh_cache_returns_capex_data(self, test_db):
        """Fresh cache returns a deserialized CapExData instance."""
        original = _minimal_capex_data()
        save_to_cache(test_db, original)

        data, fetched_at = get_cached_data(test_db, ttl_hours=24)
        assert data is not None
        assert isinstance(data, CapExData)

    def test_fresh_cache_returns_correct_data(self, test_db):
        """Retrieved CapExData matches the data that was saved."""
        original = _minimal_capex_data("2024-Q3")
        save_to_cache(test_db, original)

        data, _ = get_cached_data(test_db, ttl_hours=24)
        assert data is not None
        assert data.quarters[0].period == "2024-Q3"
        assert abs(data.quarters[0].total - 42567.8) < 0.01

    def test_fresh_cache_returns_fetched_at_string(self, test_db):
        """Fresh cache returns a non-None fetched_at timestamp string."""
        original = _minimal_capex_data()
        save_to_cache(test_db, original)

        _, fetched_at = get_cached_data(test_db, ttl_hours=24)
        assert fetched_at is not None
        assert isinstance(fetched_at, str)

    def test_expired_cache_returns_none(self, test_db):
        """Expired cache returns (None, None)."""
        data = _minimal_capex_data()
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=25)).isoformat()
        _insert_row_with_timestamp(test_db, data, old_ts)

        result_data, result_at = get_cached_data(test_db, ttl_hours=24)
        assert result_data is None
        assert result_at is None

    def test_cached_data_is_marked_as_cached(self, test_db):
        """Retrieved CapExData has is_cached=True in metadata."""
        original = _minimal_capex_data()
        save_to_cache(test_db, original)

        data, _ = get_cached_data(test_db, ttl_hours=24)
        assert data is not None
        assert data.metadata.get("is_cached") is True


# ---------------------------------------------------------------------------
# get_stale_data
# ---------------------------------------------------------------------------


class TestGetStaleData:
    """Tests for the get_stale_data function."""

    def test_empty_db_returns_none_tuple(self, test_db):
        """Empty cache returns (None, None) even for stale data lookup."""
        data, fetched_at = get_stale_data(test_db)
        assert data is None
        assert fetched_at is None

    def test_stale_data_returns_capex_data(self, test_db):
        """get_stale_data returns data even when it's older than the TTL."""
        original = _minimal_capex_data()
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
        _insert_row_with_timestamp(test_db, original, old_ts)

        data, fetched_at = get_stale_data(test_db)
        assert data is not None
        assert isinstance(data, CapExData)

    def test_stale_data_returns_correct_quarter(self, test_db):
        """get_stale_data returns the correct stored data."""
        original = _minimal_capex_data("2024-Q1")
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=48)).isoformat()
        _insert_row_with_timestamp(test_db, original, old_ts)

        data, _ = get_stale_data(test_db)
        assert data is not None
        assert data.quarters[0].period == "2024-Q1"

    def test_stale_data_fetched_at_is_string(self, test_db):
        """get_stale_data returns fetched_at as a string."""
        original = _minimal_capex_data()
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=48)).isoformat()
        _insert_row_with_timestamp(test_db, original, old_ts)

        _, fetched_at = get_stale_data(test_db)
        assert fetched_at is not None
        assert isinstance(fetched_at, str)

    def test_fresh_data_also_returned_by_get_stale(self, test_db):
        """get_stale_data returns fresh data too (it ignores TTL)."""
        original = _minimal_capex_data()
        save_to_cache(test_db, original)

        data, _ = get_stale_data(test_db)
        assert data is not None

    def test_stale_data_is_marked_as_cached(self, test_db):
        """Data returned by get_stale_data has is_cached=True."""
        original = _minimal_capex_data()
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(days=3)).isoformat()
        _insert_row_with_timestamp(test_db, original, old_ts)

        data, _ = get_stale_data(test_db)
        assert data is not None
        assert data.metadata.get("is_cached") is True
