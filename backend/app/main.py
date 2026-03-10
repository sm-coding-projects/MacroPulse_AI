"""FastAPI application entry point for MacroPulse AI backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import analyze, data, indicators

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application lifespan handler.

    Initialises the SQLite database (creates tables if missing) on startup
    and performs any required cleanup on shutdown.

    Args:
        app: The FastAPI application instance.
    """
    logger.info("MacroPulse AI backend starting up")
    init_db()
    yield
    logger.info("MacroPulse AI backend shutting down")


app = FastAPI(
    title="MacroPulse AI API",
    description=(
        "Backend API for MacroPulse AI — fetches Australian Bureau of Statistics "
        "Capital Expenditure data and proxies AI analysis requests."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------ #
# CORS middleware — allow requests from the configured frontend origins
# ------------------------------------------------------------------ #
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #
app.include_router(data.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(indicators.router, prefix="/api")


# ------------------------------------------------------------------ #
# Health check
# ------------------------------------------------------------------ #
@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, Any]:
    """Return a simple health check response.

    Used by Docker health checks and load balancers to verify the
    service is running and responsive.

    Returns:
        dict: ``{"status": "ok", "service": "macropulse-ai-backend"}``
    """
    return {"status": "ok", "service": "macropulse-ai-backend"}
