"""SQLite-backed cache for ABS CapEx and economic indicators data."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.schemas import CapExData, EconomicIndicatorsData

logger = logging.getLogger(__name__)


def is_cache_valid(db: sqlite3.Connection, ttl_hours: int = 24) -> bool:
    """Return True if a cache entry exists and was stored within the TTL window.

    Args:
        db: An open SQLite connection.
        ttl_hours: Number of hours a cache entry is considered fresh.
            Defaults to 24.

    Returns:
        bool: True when valid cached data exists, False otherwise.
    """
    try:
        row = db.execute(
            "SELECT fetched_at FROM capex_cache ORDER BY id DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error as exc:
        logger.error("Error querying cache validity: %s", exc)
        return False

    if row is None:
        return False

    try:
        fetched_at = datetime.fromisoformat(str(row["fetched_at"]))
        # Treat naive datetimes as UTC
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        expiry = fetched_at + timedelta(hours=ttl_hours)
        return datetime.now(tz=timezone.utc) < expiry
    except (ValueError, TypeError) as exc:
        logger.error("Failed to parse fetched_at timestamp: %s", exc)
        return False


def get_cached_data(
    db: sqlite3.Connection, ttl_hours: int = 24
) -> tuple[CapExData | None, str | None]:
    """Return cached CapExData if the cache is still valid, otherwise (None, None).

    Args:
        db: An open SQLite connection.
        ttl_hours: Number of hours a cache entry is considered fresh.

    Returns:
        tuple: (CapExData, fetched_at ISO string) if valid cache exists,
        otherwise (None, None).
    """
    if not is_cache_valid(db, ttl_hours):
        return None, None

    return _load_latest_row(db)


def get_stale_data(
    db: sqlite3.Connection,
) -> tuple[CapExData | None, str | None]:
    """Return the most recent cached CapExData regardless of its age.

    Use this as a fallback when the ABS API is unavailable but stale data
    is still useful to display to the user.

    Args:
        db: An open SQLite connection.

    Returns:
        tuple: (CapExData, fetched_at ISO string) if any cache entry exists,
        otherwise (None, None).
    """
    return _load_latest_row(db)


def save_to_cache(db: sqlite3.Connection, data: CapExData) -> None:
    """Persist a CapExData instance to the SQLite cache.

    Deletes all previous cache rows before inserting the new one so that
    the table never grows beyond a single entry.

    Args:
        db: An open SQLite connection.
        data: The CapExData to serialise and store.
    """
    try:
        data_json = data.model_dump_json()
        # Keep only the latest entry
        db.execute("DELETE FROM capex_cache")
        db.execute(
            "INSERT INTO capex_cache (data_json) VALUES (?)",
            (data_json,),
        )
        db.commit()
        logger.info("CapEx data saved to cache successfully")
    except sqlite3.Error as exc:
        logger.error("Failed to save data to cache: %s", exc)
        raise RuntimeError(
            "An internal error occurred while saving data to the cache."
        ) from exc


# --------------------------------------------------------------------------- #
# Private helpers
# --------------------------------------------------------------------------- #

def _load_latest_row(
    db: sqlite3.Connection,
) -> tuple[CapExData | None, str | None]:
    """Load and deserialise the most recent cache row.

    Args:
        db: An open SQLite connection.

    Returns:
        tuple: (CapExData, fetched_at ISO string) or (None, None).
    """
    try:
        row = db.execute(
            "SELECT data_json, fetched_at FROM capex_cache ORDER BY id DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error as exc:
        logger.error("Error reading from cache: %s", exc)
        return None, None

    if row is None:
        return None, None

    try:
        data = CapExData.model_validate_json(row["data_json"])
        fetched_at = str(row["fetched_at"])
        # Mark the data as coming from cache
        data.metadata["is_cached"] = True
        return data, fetched_at
    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Failed to deserialise cached data: %s", exc)
        return None, None


# --------------------------------------------------------------------------- #
# Indicators cache helpers
# --------------------------------------------------------------------------- #


def get_cached_indicators(
    conn: sqlite3.Connection,
    ttl_hours: int = settings.cache_ttl_hours,
) -> tuple[EconomicIndicatorsData | None, str | None]:
    """Return cached EconomicIndicatorsData if the cache is still fresh.

    Args:
        conn: An open SQLite connection.
        ttl_hours: Number of hours a cache entry is considered fresh.
            Defaults to the value from application settings.

    Returns:
        tuple: (EconomicIndicatorsData, fetched_at ISO string) when a valid
        cache entry exists, otherwise (None, None).
    """
    try:
        row = conn.execute(
            "SELECT fetched_at FROM indicators_cache ORDER BY id DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error as exc:
        logger.error("Error querying indicators cache validity: %s", exc)
        return None, None

    if row is None:
        return None, None

    try:
        fetched_at = datetime.fromisoformat(str(row["fetched_at"]))
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        if datetime.now(tz=timezone.utc) >= fetched_at + timedelta(hours=ttl_hours):
            return None, None
    except (ValueError, TypeError) as exc:
        logger.error("Failed to parse indicators fetched_at timestamp: %s", exc)
        return None, None

    return _load_latest_indicators_row(conn)


def get_stale_indicators(
    conn: sqlite3.Connection,
) -> tuple[EconomicIndicatorsData | None, str | None]:
    """Return the most recent cached EconomicIndicatorsData regardless of age.

    Use this as a fallback when the ABS API is unavailable but stale data
    is still useful to display to the user.

    Args:
        conn: An open SQLite connection.

    Returns:
        tuple: (EconomicIndicatorsData, fetched_at ISO string) if any cache
        entry exists, otherwise (None, None).
    """
    return _load_latest_indicators_row(conn)


def save_indicators_to_cache(
    conn: sqlite3.Connection,
    data: EconomicIndicatorsData,
) -> None:
    """Persist an EconomicIndicatorsData instance to the SQLite indicators cache.

    Deletes all previous cache rows before inserting the new one so that
    the table never grows beyond a single entry.

    Args:
        conn: An open SQLite connection.
        data: The EconomicIndicatorsData to serialise and store.

    Raises:
        RuntimeError: When the database write fails.
    """
    try:
        data_json = data.model_dump_json()
        # Keep only the latest entry
        conn.execute("DELETE FROM indicators_cache")
        conn.execute(
            "INSERT INTO indicators_cache (data_json) VALUES (?)",
            (data_json,),
        )
        conn.commit()
        logger.info("Indicators data saved to cache successfully")
    except sqlite3.Error as exc:
        logger.error("Failed to save indicators data to cache: %s", exc)
        raise RuntimeError(
            "An internal error occurred while saving indicators data to the cache."
        ) from exc


def _load_latest_indicators_row(
    conn: sqlite3.Connection,
) -> tuple[EconomicIndicatorsData | None, str | None]:
    """Load and deserialise the most recent indicators cache row.

    Args:
        conn: An open SQLite connection.

    Returns:
        tuple: (EconomicIndicatorsData, fetched_at ISO string) or (None, None).
    """
    try:
        row = conn.execute(
            "SELECT data_json, fetched_at FROM indicators_cache ORDER BY id DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error as exc:
        logger.error("Error reading from indicators cache: %s", exc)
        return None, None

    if row is None:
        return None, None

    try:
        data = EconomicIndicatorsData.model_validate_json(row["data_json"])
        fetched_at = str(row["fetched_at"])
        return data, fetched_at
    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Failed to deserialise cached indicators data: %s", exc)
        return None, None
