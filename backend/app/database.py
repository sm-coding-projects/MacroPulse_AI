"""SQLite database setup and connection management for MacroPulse AI."""

import logging
import sqlite3
from collections.abc import Generator

from app.config import settings

logger = logging.getLogger(__name__)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite database connection with WAL mode enabled.

    Yields:
        sqlite3.Connection: An open database connection. The caller is
        responsible for committing transactions; the connection is closed
        automatically when the generator is exhausted.
    """
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        # Enable WAL mode for concurrent reads without blocking writes
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create database tables if they do not already exist.

    Called once at application startup via the FastAPI lifespan handler.
    Creates the ``capex_cache`` table used to store serialised CapEx data
    fetched from the ABS Indicator API.
    """
    logger.info("Initialising database at %s", settings.database_path)
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capex_cache (
                id          INTEGER PRIMARY KEY,
                data_json   TEXT    NOT NULL,
                fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS indicators_cache (
                id          INTEGER PRIMARY KEY,
                data_json   TEXT    NOT NULL,
                fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        logger.info("Database initialised successfully")
    except sqlite3.Error as exc:
        logger.error("Failed to initialise database: %s", exc)
        raise
    finally:
        conn.close()
