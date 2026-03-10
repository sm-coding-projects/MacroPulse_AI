"""Router for economic indicators endpoint."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator

from fastapi import APIRouter, Depends

from app.database import get_db
from app.models.schemas import IndicatorsResponse
from app.services import indicators_client
from app.services.cache import (
    get_cached_indicators,
    get_stale_indicators,
    save_indicators_to_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["indicators"])


def _get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency that yields a database connection."""
    yield from get_db()


@router.get("/data/indicators", response_model=IndicatorsResponse)
def get_indicators(
    db: sqlite3.Connection = Depends(_get_db_connection),
) -> IndicatorsResponse:
    """Return economic context indicators for Australia (GDP, CPI, unemployment, wages).

    Checks the SQLite cache first. If the cache is still valid (within the
    configured TTL), returns the cached data immediately. If the cache is
    stale, attempts a fresh fetch from the ABS API. On failure, falls back to
    the stale cached data with a warning. If no cache exists at all and the
    ABS API is unavailable, returns an error message.

    Args:
        db: SQLite connection injected by FastAPI's dependency system.

    Returns:
        IndicatorsResponse: Contains ``data`` (EconomicIndicatorsData or None),
        ``from_cache`` flag, ``cache_date`` timestamp, and ``error`` message.
    """
    # ------------------------------------------------------------------ #
    # 1. Check for valid (fresh) cache
    # ------------------------------------------------------------------ #
    cached, cached_at = get_cached_indicators(db)
    if cached is not None:
        logger.info(
            "Returning valid cached indicators data (fetched at %s)", cached_at
        )
        return IndicatorsResponse(
            data=cached,
            from_cache=False,  # cache is fresh, no warning needed
            cache_date=cached_at,
        )

    # ------------------------------------------------------------------ #
    # 2. Cache is stale or empty — try a fresh ABS fetch
    # ------------------------------------------------------------------ #
    logger.info("Indicators cache is stale or empty; fetching from ABS")
    try:
        fresh = indicators_client.fetch_all_indicators()
        save_indicators_to_cache(db, fresh)
        logger.info("Fresh indicators data fetched and cached successfully")
        return IndicatorsResponse(data=fresh)

    except Exception as exc:  # noqa: BLE001
        logger.warning("Indicators fetch failed: %s", exc)

        # ---------------------------------------------------------------- #
        # 3. Fetch failed — try stale cache as fallback
        # ---------------------------------------------------------------- #
        stale, stale_at = get_stale_indicators(db)
        if stale is not None:
            logger.info(
                "Returning stale indicators cache (fetched at %s) as fallback",
                stale_at,
            )
            return IndicatorsResponse(
                data=stale,
                from_cache=True,
                cache_date=stale_at,
                error=(
                    f"Showing cached data from {stale_at}. "
                    "Live data is currently unavailable."
                ),
            )

        # 4. No cache at all
        logger.error("No indicators cache available and ABS fetch failed: %s", exc)
        return IndicatorsResponse(
            error=(
                "Unable to fetch economic indicators from ABS. "
                "Please check your internet connection and try again."
            )
        )
