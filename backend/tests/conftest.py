"""Shared pytest fixtures for MacroPulse AI backend tests."""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import CapExData, CapExQuarter


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient wrapping the main application."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Temporary SQLite database
# ---------------------------------------------------------------------------


@pytest.fixture
def test_db(tmp_path):
    """Yield a fresh SQLite connection for each test.

    Creates the capex_cache table in a temporary file so tests never touch
    the production database path.
    """
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS capex_cache (
            id         INTEGER PRIMARY KEY,
            data_json  TEXT    NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Realistic SDMX-JSON fixture (flat observations format)
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_sdmx_response() -> dict[str, Any]:
    """Return a minimal but structurally valid SDMX-JSON response.

    The flat observations format uses colon-separated indices as keys:
      FREQUENCY : MEASURE : INDUSTRY : ASSET_TYPE : REGION : TIME_PERIOD

    Series dimension order (indices 0-4):
      0 = FREQUENCY  → Q (index 0)
      1 = MEASURE    → CAPEX_ACT (index 0), CAPEX_EXP (index 1)
      2 = INDUSTRY   → TOT(0), MIN(1), MFG(2), OTH(3)
      3 = ASSET_TYPE → TOT(0), BS(1), EPM(2)
      4 = REGION     → AUS (index 0)

    Observation dimension (index 5):
      0 = TIME_PERIOD → 8 quarters 2022-Q4 … 2024-Q3
    """
    time_periods = [
        {"id": "2022-Q4", "name": "Dec 2022"},
        {"id": "2023-Q1", "name": "Mar 2023"},
        {"id": "2023-Q2", "name": "Jun 2023"},
        {"id": "2023-Q3", "name": "Sep 2023"},
        {"id": "2023-Q4", "name": "Dec 2023"},
        {"id": "2024-Q1", "name": "Mar 2024"},
        {"id": "2024-Q2", "name": "Jun 2024"},
        {"id": "2024-Q3", "name": "Sep 2024"},
    ]

    # Values per quarter for each combination we care about.
    # Key format: (MEASURE_idx, INDUSTRY_idx, ASSET_idx)
    # All use FREQUENCY=Q(0) and REGION=AUS(0).
    #
    # Realistic $M figures for Australia:
    #   TOT/TOT → total capex
    #   MIN/TOT → mining
    #   MFG/TOT → manufacturing
    #   OTH/TOT → other selected
    #   TOT/BS  → buildings & structures
    #   TOT/EPM → equipment, plant & machinery

    combo_values: dict[tuple[int, int, int], list[float]] = {
        # (MEASURE, INDUSTRY, ASSET_TYPE): [Q0, Q1, Q2, Q3, Q4, Q5, Q6, Q7]
        (0, 0, 0): [39800.0, 40100.0, 40500.0, 41000.0, 41500.0, 40800.0, 41234.1, 42567.8],  # TOT/TOT
        (0, 1, 0): [16500.0, 16700.0, 17000.0, 17200.0, 17500.0, 17100.0, 17890.2, 18234.5],  # MIN/TOT
        (0, 2, 0): [5100.0,  5150.0,  5200.0,  5250.0,  5300.0,  5350.0,  5432.1,  5678.9],  # MFG/TOT
        (0, 3, 0): [18200.0, 18250.0, 18300.0, 18550.0, 18700.0, 18350.0, 17911.8, 18654.4],  # OTH/TOT
        (0, 0, 1): [18100.0, 18300.0, 18500.0, 18700.0, 18900.0, 18600.0, 19123.4, 19876.3],  # TOT/BS
        (0, 0, 2): [21700.0, 21800.0, 22000.0, 22300.0, 22600.0, 22200.0, 22110.7, 22691.5],  # TOT/EPM
        # Expected expenditure rows (MEASURE=1) — included to test filtering
        (1, 0, 0): [43000.0, 43500.0, 44000.0, 44500.0, 45000.0, 45500.0, 46000.0, 46500.0],
    }

    observations: dict[str, list[Any]] = {}
    for (measure_idx, industry_idx, asset_idx), values in combo_values.items():
        for time_idx, value in enumerate(values):
            key = f"0:{measure_idx}:{industry_idx}:{asset_idx}:0:{time_idx}"
            observations[key] = [value, 0, None]

    return {
        "header": {
            "id": "test-response",
            "prepared": "2024-12-15T00:00:00",
        },
        "dataSets": [
            {
                "action": "Information",
                "observations": observations,
            }
        ],
        "structure": {
            "dimensions": {
                "series": [
                    {
                        "id": "FREQUENCY",
                        "values": [{"id": "Q", "name": "Quarterly"}],
                    },
                    {
                        "id": "MEASURE",
                        "values": [
                            {"id": "CAPEX_ACT", "name": "Actual"},
                            {"id": "CAPEX_EXP", "name": "Expected"},
                        ],
                    },
                    {
                        "id": "INDUSTRY",
                        "values": [
                            {"id": "TOT", "name": "Total"},
                            {"id": "MIN", "name": "Mining"},
                            {"id": "MFG", "name": "Manufacturing"},
                            {"id": "OTH", "name": "Other Selected Industries"},
                        ],
                    },
                    {
                        "id": "ASSET_TYPE",
                        "values": [
                            {"id": "TOT", "name": "Total"},
                            {"id": "BS", "name": "Buildings & Structures"},
                            {"id": "EPM", "name": "Equipment, Plant & Machinery"},
                        ],
                    },
                    {
                        "id": "REGION",
                        "values": [{"id": "AUS", "name": "Australia"}],
                    },
                ],
                "observation": [
                    {
                        "id": "TIME_PERIOD",
                        "values": time_periods,
                    }
                ],
            }
        },
    }


# ---------------------------------------------------------------------------
# Series-based SDMX-JSON fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_sdmx_series_response() -> dict[str, Any]:
    """Return a minimal SDMX-JSON response in series-based format.

    Series keys encode (FREQUENCY:MEASURE:INDUSTRY:ASSET_TYPE:REGION);
    observation keys within each series are TIME_PERIOD indices.
    """
    time_periods = [
        {"id": "2023-Q3", "name": "Sep 2023"},
        {"id": "2023-Q4", "name": "Dec 2023"},
        {"id": "2024-Q1", "name": "Mar 2024"},
        {"id": "2024-Q2", "name": "Jun 2024"},
    ]

    series: dict[str, Any] = {
        "0:0:0:0:0": {  # Q / CAPEX_ACT / TOT / TOT / AUS
            "observations": {
                "0": [41000.0],
                "1": [41500.0],
                "2": [40800.0],
                "3": [41234.1],
            }
        },
        "0:0:1:0:0": {  # Q / CAPEX_ACT / MIN / TOT / AUS
            "observations": {
                "0": [17200.0],
                "1": [17500.0],
                "2": [17100.0],
                "3": [17890.2],
            }
        },
        "0:0:2:0:0": {  # Q / CAPEX_ACT / MFG / TOT / AUS
            "observations": {
                "0": [5250.0],
                "1": [5300.0],
                "2": [5350.0],
                "3": [5432.1],
            }
        },
        "0:0:3:0:0": {  # Q / CAPEX_ACT / OTH / TOT / AUS
            "observations": {
                "0": [18550.0],
                "1": [18700.0],
                "2": [18350.0],
                "3": [17911.8],
            }
        },
        "0:0:0:1:0": {  # Q / CAPEX_ACT / TOT / BS / AUS
            "observations": {
                "0": [18700.0],
                "1": [18900.0],
                "2": [18600.0],
                "3": [19123.4],
            }
        },
        "0:0:0:2:0": {  # Q / CAPEX_ACT / TOT / EPM / AUS
            "observations": {
                "0": [22300.0],
                "1": [22600.0],
                "2": [22200.0],
                "3": [22110.7],
            }
        },
    }

    return {
        "header": {
            "id": "test-series-response",
            "prepared": "2024-12-15T00:00:00",
        },
        "dataSets": [
            {
                "action": "Information",
                "series": series,
            }
        ],
        "structure": {
            "dimensions": {
                "series": [
                    {
                        "id": "FREQUENCY",
                        "values": [{"id": "Q", "name": "Quarterly"}],
                    },
                    {
                        "id": "MEASURE",
                        "values": [
                            {"id": "CAPEX_ACT", "name": "Actual"},
                            {"id": "CAPEX_EXP", "name": "Expected"},
                        ],
                    },
                    {
                        "id": "INDUSTRY",
                        "values": [
                            {"id": "TOT", "name": "Total"},
                            {"id": "MIN", "name": "Mining"},
                            {"id": "MFG", "name": "Manufacturing"},
                            {"id": "OTH", "name": "Other Selected Industries"},
                        ],
                    },
                    {
                        "id": "ASSET_TYPE",
                        "values": [
                            {"id": "TOT", "name": "Total"},
                            {"id": "BS", "name": "Buildings & Structures"},
                            {"id": "EPM", "name": "Equipment, Plant & Machinery"},
                        ],
                    },
                    {
                        "id": "REGION",
                        "values": [{"id": "AUS", "name": "Australia"}],
                    },
                ],
                "observation": [
                    {
                        "id": "TIME_PERIOD",
                        "values": time_periods,
                    }
                ],
            }
        },
    }


# ---------------------------------------------------------------------------
# Processed CapExData fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_capex_data() -> CapExData:
    """Return a fully populated CapExData object with 8 quarters of data."""
    quarters = [
        CapExQuarter(
            period="2022-Q4",
            total=39800.0,
            mining=16500.0,
            manufacturing=5100.0,
            other_selected=18200.0,
            buildings_structures=18100.0,
            equipment_plant_machinery=21700.0,
            qoq_change=None,
            yoy_change=None,
        ),
        CapExQuarter(
            period="2023-Q1",
            total=40100.0,
            mining=16700.0,
            manufacturing=5150.0,
            other_selected=18250.0,
            buildings_structures=18300.0,
            equipment_plant_machinery=21800.0,
            qoq_change=round((40100.0 - 39800.0) / 39800.0 * 100, 2),
            yoy_change=None,
        ),
        CapExQuarter(
            period="2023-Q2",
            total=40500.0,
            mining=17000.0,
            manufacturing=5200.0,
            other_selected=18300.0,
            buildings_structures=18500.0,
            equipment_plant_machinery=22000.0,
            qoq_change=round((40500.0 - 40100.0) / 40100.0 * 100, 2),
            yoy_change=None,
        ),
        CapExQuarter(
            period="2023-Q3",
            total=41000.0,
            mining=17200.0,
            manufacturing=5250.0,
            other_selected=18550.0,
            buildings_structures=18700.0,
            equipment_plant_machinery=22300.0,
            qoq_change=round((41000.0 - 40500.0) / 40500.0 * 100, 2),
            yoy_change=None,
        ),
        CapExQuarter(
            period="2023-Q4",
            total=41500.0,
            mining=17500.0,
            manufacturing=5300.0,
            other_selected=18700.0,
            buildings_structures=18900.0,
            equipment_plant_machinery=22600.0,
            qoq_change=round((41500.0 - 41000.0) / 41000.0 * 100, 2),
            yoy_change=round((41500.0 - 39800.0) / 39800.0 * 100, 2),
        ),
        CapExQuarter(
            period="2024-Q1",
            total=40800.0,
            mining=17100.0,
            manufacturing=5350.0,
            other_selected=18350.0,
            buildings_structures=18600.0,
            equipment_plant_machinery=22200.0,
            qoq_change=round((40800.0 - 41500.0) / 41500.0 * 100, 2),
            yoy_change=round((40800.0 - 40100.0) / 40100.0 * 100, 2),
        ),
        CapExQuarter(
            period="2024-Q2",
            total=41234.1,
            mining=17890.2,
            manufacturing=5432.1,
            other_selected=17911.8,
            buildings_structures=19123.4,
            equipment_plant_machinery=22110.7,
            qoq_change=round((41234.1 - 40800.0) / 40800.0 * 100, 2),
            yoy_change=round((41234.1 - 40500.0) / 40500.0 * 100, 2),
        ),
        CapExQuarter(
            period="2024-Q3",
            total=42567.8,
            mining=18234.5,
            manufacturing=5678.9,
            other_selected=18654.4,
            buildings_structures=19876.3,
            equipment_plant_machinery=22691.5,
            qoq_change=round((42567.8 - 41234.1) / 41234.1 * 100, 2),
            yoy_change=round((42567.8 - 41000.0) / 41000.0 * 100, 2),
        ),
    ]

    by_industry = {
        "Total": [{"period": q.period, "value": q.total} for q in quarters],
        "Mining": [{"period": q.period, "value": q.mining} for q in quarters],
        "Manufacturing": [{"period": q.period, "value": q.manufacturing} for q in quarters],
        "Other Selected Industries": [
            {"period": q.period, "value": q.other_selected} for q in quarters
        ],
    }
    by_asset_type = {
        "Total": [{"period": q.period, "value": q.total} for q in quarters],
        "Buildings & Structures": [
            {"period": q.period, "value": q.buildings_structures} for q in quarters
        ],
        "Equipment, Plant & Machinery": [
            {"period": q.period, "value": q.equipment_plant_machinery} for q in quarters
        ],
    }

    return CapExData(
        quarters=quarters,
        by_industry=by_industry,
        by_asset_type=by_asset_type,
        metadata={
            "source": "Australian Bureau of Statistics — Catalogue No. 5625.0",
            "last_updated": "2024-12-15T00:00:00+00:00",
            "estimate_number": "Data prepared 2024-12-15",
            "is_cached": False,
            "periods_available": [q.period for q in quarters],
        },
    )


# ---------------------------------------------------------------------------
# Mock LLM streaming chunks
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_response() -> list[str]:
    """Realistic LLM streaming response text chunks."""
    return [
        "## Headline Summary\n",
        "Australian private new capital expenditure rose 3.2% quarter-on-quarter "
        "to $42,567.8M in September 2024.\n\n",
        "## Sector Breakdown\n",
        "Mining CapEx increased to $18,234.5M, driven by continued investment "
        "in resources infrastructure.\n\n",
        "## Asset Mix\n",
        "Equipment, Plant & Machinery accounted for $22,691.5M.\n\n",
        "## Forward Estimates\n",
        "Forward estimates suggest continued growth in the near term.\n\n",
        "## Market Implications\n",
        "The data signals sustained business confidence in the Australian economy.",
    ]
