"""Router for CapEx data endpoints."""

import logging
import sqlite3
from collections.abc import Generator

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.models.schemas import CapExData, DataResponse
from app.services import abs_client, cache, data_processor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["data"])


def _get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency that yields a database connection."""
    yield from get_db()


@router.get("/data/capex", response_model=DataResponse)
def get_capex_data(
    db: sqlite3.Connection = Depends(_get_db_connection),
    force_refresh: bool = Query(False, description="Bypass cache and fetch fresh data from ABS"),
) -> DataResponse:
    """Return the latest Private New Capital Expenditure data.

    Checks the SQLite cache first (unless force_refresh is True). If the
    cache is still valid (within the configured TTL), returns the cached
    data immediately. If the cache is stale, attempts a fresh fetch from
    the ABS Indicator API. On failure, falls back to the stale cached data
    with a warning. If no cache exists at all and the ABS API is
    unavailable, returns an error.

    Args:
        db: SQLite connection injected by FastAPI's dependency system.
        force_refresh: When True, skip the cache and always fetch from ABS.

    Returns:
        DataResponse: Contains ``data`` (CapExData or None), ``from_cache``
        flag, ``cache_date`` timestamp, and ``error`` message.
    """
    # ------------------------------------------------------------------ #
    # 1. Check for valid (fresh) cache — skipped when force_refresh=True
    # ------------------------------------------------------------------ #
    cached_data, cached_at = cache.get_cached_data(db)
    if cached_data is not None and not force_refresh:
        logger.info("Returning valid cached CapEx data (fetched at %s)", cached_at)
        return DataResponse(
            data=cached_data,
            from_cache=False,  # cache is fresh, no warning needed
            cache_date=cached_at,
        )

    # ------------------------------------------------------------------ #
    # 2. Cache is stale or empty — try a fresh ABS fetch
    # ------------------------------------------------------------------ #
    logger.info("Cache is stale or empty; attempting fresh ABS fetch")
    try:
        raw = abs_client.fetch_capex_from_abs()
        fresh_data: CapExData = data_processor.process_abs_response(raw)
        cache.save_to_cache(db, fresh_data)
        logger.info("Fresh ABS data fetched and cached successfully")
        return DataResponse(data=fresh_data, from_cache=False)

    except (ConnectionError, ValueError) as exc:
        logger.warning("ABS fetch/process failed: %s", exc)
        # ---------------------------------------------------------------- #
        # 3. ABS fetch failed — try stale cache as fallback
        # ---------------------------------------------------------------- #
        stale_data, stale_at = cache.get_stale_data(db)
        if stale_data is not None:
            logger.info("Returning stale cached data (fetched at %s) as fallback", stale_at)
            return DataResponse(
                data=stale_data,
                from_cache=True,
                cache_date=stale_at,
                error=(
                    f"Showing cached data from {stale_at}. "
                    "Live data is currently unavailable."
                ),
            )

        # 4. No cache at all
        logger.error("No cache available and ABS fetch failed: %s", exc)
        return DataResponse(
            error=(
                "Unable to fetch data from ABS. "
                "Please check your internet connection and try again."
            )
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error fetching CapEx data: %s", exc)
        stale_data, stale_at = cache.get_stale_data(db)
        if stale_data is not None:
            return DataResponse(
                data=stale_data,
                from_cache=True,
                cache_date=stale_at,
                error=(
                    f"Showing cached data from {stale_at}. "
                    "An unexpected error occurred while fetching live data."
                ),
            )
        return DataResponse(
            error="An unexpected error occurred. Please try again later."
        )
