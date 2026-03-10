"""Transform raw ABS SDMX observations into structured CapExData models."""

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.models.schemas import CapExData, CapExQuarter
from app.services.abs_client import parse_sdmx_observations

logger = logging.getLogger(__name__)

# Dimension value IDs as returned by api.data.abs.gov.au/data/ABS,CAPEX/all
# Update these constants if the ABS API changes its codes.
_MEASURE_ACTUAL     = "M1"        # Actual Expenditure
_MEASURE_ACTUAL_ALT = "CAPEX_ACT" # Legacy indicator API fallback
_MEASURE_EXPECTED   = "M2"

# Industry IDs — single source of truth used by _build_quarters AND the series builders.
_IND_TOT = "TOT"   # Total, including Education and Health
_IND_MIN = "P01"   # Mining
_IND_MFG = "P02"   # Manufacturing
_IND_OTH = "P95"   # Non-Mining, including Education and Health

# Asset-type IDs — same principle.
_AST_TOT = "TOT"   # Total
_AST_BS  = "1"     # Buildings and Structures
_AST_EPM = "2"     # Equipment, Plant and Machinery

# Human-readable labels keyed by the same IDs.
_INDUSTRY_MAP = {
    _IND_TOT: "Total",
    _IND_MIN: "Mining",
    _IND_MFG: "Manufacturing",
    _IND_OTH: "Other Selected Industries",
}

_ASSET_MAP = {
    _AST_TOT: "Total",
    _AST_BS:  "Buildings & Structures",
    _AST_EPM: "Equipment, Plant & Machinery",
}

_QUARTERS_TO_RETURN = 8


def process_abs_response(raw: dict[str, Any]) -> CapExData:
    """Transform a raw ABS SDMX-JSON response into a structured CapExData object.

    Parses flat/series-based SDMX observations, filters for actual expenditure
    (CAPEX_ACT), pivots by quarter/industry/asset type using Pandas, calculates
    quarter-on-quarter and year-on-year percentage changes, and returns the most
    recent 8 quarters.

    Args:
        raw: The raw SDMX-JSON dictionary as returned by ``fetch_capex_from_abs``.

    Returns:
        CapExData: Structured model with ``quarters``, ``by_industry``,
        ``by_asset_type``, and ``metadata`` fields.

    Raises:
        ValueError: If the data is malformed, missing required columns, or
            contains no usable records after filtering.
    """
    try:
        records = parse_sdmx_observations(raw)
    except ValueError:
        raise  # already carries a user-facing message

    if not records:
        raise ValueError(
            "No observations were found in the ABS response. "
            "The API may have returned an empty dataset."
        )

    try:
        df = pd.DataFrame(records)
        _validate_required_columns(df)
    except (pd.errors.ParserError, ValueError, KeyError, TypeError) as exc:
        logger.error("Failed to build DataFrame from ABS records: %s", exc)
        raise ValueError(
            "The data received from ABS was in an unexpected format. "
            "This may indicate an API change. Please report this issue."
        )

    # ------------------------------------------------------------------ #
    # Filter: keep only actual expenditure, Australia-wide, quarterly
    # ------------------------------------------------------------------ #
    df = _filter_records(df)

    if df.empty:
        raise ValueError(
            "No actual expenditure data was found after filtering the ABS response. "
            "The dataset may have changed structure."
        )

    # ------------------------------------------------------------------ #
    # Sort periods chronologically and take the last N quarters
    # ------------------------------------------------------------------ #
    df = df.sort_values("TIME_PERIOD")
    all_periods = df["TIME_PERIOD"].unique()
    recent_periods = sorted(all_periods)[-_QUARTERS_TO_RETURN:]
    df = df[df["TIME_PERIOD"].isin(recent_periods)]

    # ------------------------------------------------------------------ #
    # Build per-quarter summary rows
    # ------------------------------------------------------------------ #
    quarters = _build_quarters(df, recent_periods)

    # ------------------------------------------------------------------ #
    # Build by_industry and by_asset_type series for charting
    # ------------------------------------------------------------------ #
    by_industry = _build_industry_series(df, recent_periods)
    by_asset_type = _build_asset_series(df, recent_periods)

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #
    metadata: dict[str, Any] = {
        "source": "Australian Bureau of Statistics — Catalogue No. 5625.0",
        "last_updated": datetime.now(tz=timezone.utc).isoformat(),
        "estimate_number": _extract_estimate_number(raw),
        "is_cached": False,
        "periods_available": list(recent_periods),
    }

    return CapExData(
        quarters=quarters,
        by_industry=by_industry,
        by_asset_type=by_asset_type,
        metadata=metadata,
    )


def build_data_summary(data: CapExData) -> str:
    """Render a concise text summary of CapExData for inclusion in LLM prompts.

    Args:
        data: A populated CapExData instance.

    Returns:
        str: Multi-line text summary with current, previous, and year-ago
        quarter figures plus percentage changes.
    """
    quarters = data.quarters
    if not quarters:
        return "No data available."

    lines: list[str] = []

    current = quarters[-1]
    prev = quarters[-2] if len(quarters) >= 2 else None
    year_ago = quarters[-5] if len(quarters) >= 5 else None

    lines.append(f"=== ABS Private New Capital Expenditure Data ===")
    lines.append(f"Source: {data.metadata.get('source', 'ABS')}")
    lines.append(
        f"Estimate: {data.metadata.get('estimate_number', 'N/A')}"
    )
    lines.append("")

    lines.append(f"--- Current Quarter: {current.period} ---")
    lines.append(f"  Total CapEx:                    ${current.total:,.1f}M")
    lines.append(f"  Mining:                         ${current.mining:,.1f}M")
    lines.append(f"  Manufacturing:                  ${current.manufacturing:,.1f}M")
    lines.append(f"  Other Selected Industries:      ${current.other_selected:,.1f}M")
    lines.append(f"  Buildings & Structures:         ${current.buildings_structures:,.1f}M")
    lines.append(f"  Equipment, Plant & Machinery:   ${current.equipment_plant_machinery:,.1f}M")

    if current.qoq_change is not None:
        lines.append(f"  QoQ Change (total):             {current.qoq_change:+.1f}%")
    if current.yoy_change is not None:
        lines.append(f"  YoY Change (total):             {current.yoy_change:+.1f}%")

    if prev:
        lines.append("")
        lines.append(f"--- Previous Quarter: {prev.period} ---")
        lines.append(f"  Total CapEx:                    ${prev.total:,.1f}M")
        lines.append(f"  Mining:                         ${prev.mining:,.1f}M")
        lines.append(f"  Manufacturing:                  ${prev.manufacturing:,.1f}M")
        lines.append(f"  Other Selected Industries:      ${prev.other_selected:,.1f}M")
        lines.append(f"  Buildings & Structures:         ${prev.buildings_structures:,.1f}M")
        lines.append(f"  Equipment, Plant & Machinery:   ${prev.equipment_plant_machinery:,.1f}M")

    if year_ago:
        lines.append("")
        lines.append(f"--- Year-Ago Quarter: {year_ago.period} ---")
        lines.append(f"  Total CapEx:                    ${year_ago.total:,.1f}M")
        lines.append(f"  Mining:                         ${year_ago.mining:,.1f}M")
        lines.append(f"  Manufacturing:                  ${year_ago.manufacturing:,.1f}M")
        lines.append(f"  Other Selected Industries:      ${year_ago.other_selected:,.1f}M")
        lines.append(f"  Buildings & Structures:         ${year_ago.buildings_structures:,.1f}M")
        lines.append(f"  Equipment, Plant & Machinery:   ${year_ago.equipment_plant_machinery:,.1f}M")

    lines.append("")
    lines.append("--- 8-Quarter Trend (Total CapEx, $M) ---")
    for q in quarters:
        change_str = ""
        if q.qoq_change is not None:
            change_str = f"  QoQ: {q.qoq_change:+.1f}%"
        lines.append(f"  {q.period}: ${q.total:,.1f}M{change_str}")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Private helpers
# --------------------------------------------------------------------------- #

def _validate_required_columns(df: pd.DataFrame) -> None:
    """Raise ValueError if required dimension columns are absent."""
    required = {"TIME_PERIOD", "value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"ABS response is missing required fields: {missing}. "
            "The API may have changed its response format."
        )


def _filter_records(df: pd.DataFrame) -> pd.DataFrame:
    """Retain only actual expenditure, quarterly, Australia-wide records.

    Handles both the legacy indicator.data.abs.gov.au dimension IDs and the
    current api.data.abs.gov.au dimension IDs transparently.
    """
    mask = pd.Series([True] * len(df), index=df.index)

    # MEASURE: actual expenditure only; accept both legacy and newer API IDs
    if "MEASURE" in df.columns:
        mask &= df["MEASURE"].isin([_MEASURE_ACTUAL, _MEASURE_ACTUAL_ALT])

    # Frequency: quarterly only
    if "FREQ" in df.columns:
        mask &= df["FREQ"] == "Q"
    elif "FREQUENCY" in df.columns:
        mask &= df["FREQUENCY"] == "Q"

    # Region/State: Australia-wide only
    if "STATE" in df.columns:
        mask &= df["STATE"] == "AUS"
    elif "REGION" in df.columns:
        mask &= df["REGION"] == "AUS"

    # Drop null values
    mask &= df["value"].notna()

    filtered = df[mask].copy()

    # Seasonal adjustment: the ABS only publishes SA (TSEST=20) for aggregate
    # totals, not for industry/asset breakdowns. Use Original (TSEST=10) so
    # all breakdown series are present. Fall back to any TSEST if 10 is absent.
    if "TSEST" in filtered.columns:
        orig = filtered[filtered["TSEST"] == "10"]
        if not orig.empty:
            filtered = orig
        # else: leave all TSEST values in rather than returning an empty frame

    # Price adjustment: current price preferred; ignore if it empties the frame
    if "PRICE_ADJUSTMENT" in filtered.columns:
        cur = filtered[filtered["PRICE_ADJUSTMENT"] == "CUR"]
        if not cur.empty:
            filtered = cur

    logger.debug(
        "After filtering: %d rows. INDUSTRY values: %s. ASSET values: %s.",
        len(filtered),
        filtered["INDUSTRY"].unique().tolist() if "INDUSTRY" in filtered.columns else "N/A",
        (
            filtered["ASSET_TYPE"].unique().tolist()
            if "ASSET_TYPE" in filtered.columns
            else filtered["ASSET"].unique().tolist()
            if "ASSET" in filtered.columns
            else "N/A"
        ),
    )

    return filtered


def _safe_get(df: pd.DataFrame, industry: str, asset: str, period: str) -> float:
    """Return the value for a given industry/asset/period combination, or 0.0."""
    industry_col = "INDUSTRY" if "INDUSTRY" in df.columns else None
    # New API uses "ASSET"; legacy API used "ASSET_TYPE"
    asset_col = "ASSET" if "ASSET" in df.columns else ("ASSET_TYPE" if "ASSET_TYPE" in df.columns else None)

    subset = df[df["TIME_PERIOD"] == period]

    if industry_col and industry != "ANY":
        subset = subset[subset[industry_col] == industry]
    if asset_col and asset != "ANY":
        subset = subset[subset[asset_col] == asset]

    if subset.empty:
        return 0.0

    return float(subset["value"].sum())


def _build_quarters(
    df: pd.DataFrame, periods: list[str]
) -> list[CapExQuarter]:
    """Construct a list of CapExQuarter objects, one per period.

    Args:
        df: Filtered DataFrame with actual expenditure records.
        periods: Chronologically sorted list of period strings.

    Returns:
        list[CapExQuarter]: One entry per period with aggregated totals
        and percentage changes.
    """
    quarters: list[CapExQuarter] = []

    for period in periods:
        total = _safe_get(df, _IND_TOT, _AST_TOT, period)
        mining = _safe_get(df, _IND_MIN, _AST_TOT, period)
        manufacturing = _safe_get(df, _IND_MFG, _AST_TOT, period)
        other_selected = _safe_get(df, _IND_OTH, _AST_TOT, period)
        buildings = _safe_get(df, _IND_TOT, _AST_BS, period)
        equipment = _safe_get(df, _IND_TOT, _AST_EPM, period)

        quarters.append(
            CapExQuarter(
                period=period,
                total=total,
                mining=mining,
                manufacturing=manufacturing,
                other_selected=other_selected,
                buildings_structures=buildings,
                equipment_plant_machinery=equipment,
                qoq_change=None,
                yoy_change=None,
            )
        )

    # Calculate percentage changes now that all quarters are built
    for i, quarter in enumerate(quarters):
        if i >= 1 and quarters[i - 1].total:
            prev_total = quarters[i - 1].total
            quarter.qoq_change = round(
                ((quarter.total - prev_total) / prev_total) * 100, 2
            )
        if i >= 4 and quarters[i - 4].total:
            year_ago_total = quarters[i - 4].total
            quarter.yoy_change = round(
                ((quarter.total - year_ago_total) / year_ago_total) * 100, 2
            )

    return quarters


def _build_industry_series(
    df: pd.DataFrame, periods: list[str]
) -> dict[str, list[dict[str, Any]]]:
    """Build a by_industry charting dictionary.

    Args:
        df: Filtered DataFrame.
        periods: Ordered list of period strings.

    Returns:
        dict: Industry name -> list of {period, value} dicts.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    industry_col = "INDUSTRY" if "INDUSTRY" in df.columns else None
    # New API uses "ASSET"; legacy API used "ASSET_TYPE"
    asset_col = "ASSET" if "ASSET" in df.columns else ("ASSET_TYPE" if "ASSET_TYPE" in df.columns else None)

    for ind_id, ind_name in _INDUSTRY_MAP.items():
        series: list[dict[str, Any]] = []
        for period in periods:
            subset = df[df["TIME_PERIOD"] == period]
            if industry_col:
                subset = subset[subset[industry_col] == ind_id]
            if asset_col:
                subset = subset[subset[asset_col] == _AST_TOT]
            value = float(subset["value"].sum()) if not subset.empty else 0.0
            series.append({"period": period, "value": value})
        result[ind_name] = series

    return result


def _build_asset_series(
    df: pd.DataFrame, periods: list[str]
) -> dict[str, list[dict[str, Any]]]:
    """Build a by_asset_type charting dictionary.

    Args:
        df: Filtered DataFrame.
        periods: Ordered list of period strings.

    Returns:
        dict: Asset type name -> list of {period, value} dicts.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    industry_col = "INDUSTRY" if "INDUSTRY" in df.columns else None
    # New API uses "ASSET"; legacy API used "ASSET_TYPE"
    asset_col = "ASSET" if "ASSET" in df.columns else ("ASSET_TYPE" if "ASSET_TYPE" in df.columns else None)

    for asset_id, asset_name in _ASSET_MAP.items():
        series: list[dict[str, Any]] = []
        for period in periods:
            subset = df[df["TIME_PERIOD"] == period]
            if industry_col:
                subset = subset[subset[industry_col] == _IND_TOT]
            if asset_col:
                subset = subset[subset[asset_col] == asset_id]
            value = float(subset["value"].sum()) if not subset.empty else 0.0
            series.append({"period": period, "value": value})
        result[asset_name] = series

    return result


def _extract_estimate_number(raw: dict[str, Any]) -> str:
    """Attempt to extract the ABS estimate number from the response header.

    Args:
        raw: The raw SDMX-JSON response dictionary.

    Returns:
        str: The estimate number if found, otherwise 'N/A'.
    """
    try:
        prepared = raw.get("header", {}).get("prepared", "")
        # ABS doesn't directly embed the estimate number in SDMX-JSON headers,
        # so we return a placeholder. The frontend can note it's not available.
        if prepared:
            return f"Data prepared {prepared[:10]}"
    except (AttributeError, TypeError):
        pass
    return "N/A"
