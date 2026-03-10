"""Tests for app.services.data_processor — SDMX to CapExData transformations."""

from __future__ import annotations

from typing import Any

import pytest

from app.models.schemas import CapExData, CapExQuarter
from app.services.data_processor import (
    _QUARTERS_TO_RETURN,
    build_data_summary,
    process_abs_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_quarter_fields(quarter: CapExQuarter) -> None:
    """Assert that all required fields on a CapExQuarter are present and numeric."""
    assert isinstance(quarter.period, str)
    assert len(quarter.period) > 0
    assert isinstance(quarter.total, float)
    assert isinstance(quarter.mining, float)
    assert isinstance(quarter.manufacturing, float)
    assert isinstance(quarter.other_selected, float)
    assert isinstance(quarter.buildings_structures, float)
    assert isinstance(quarter.equipment_plant_machinery, float)


# ---------------------------------------------------------------------------
# process_abs_response — happy path
# ---------------------------------------------------------------------------


class TestProcessAbsResponseHappy:
    """Happy-path tests for process_abs_response."""

    def test_process_valid_response_returns_capex_data(self, sample_sdmx_response):
        """A valid SDMX response produces a CapExData instance."""
        result = process_abs_response(sample_sdmx_response)
        assert isinstance(result, CapExData)

    def test_process_valid_response_returns_8_quarters(self, sample_sdmx_response):
        """Valid 8-quarter dataset returns exactly 8 CapExQuarter objects."""
        result = process_abs_response(sample_sdmx_response)
        assert len(result.quarters) == _QUARTERS_TO_RETURN

    def test_process_valid_response_quarters_have_required_fields(self, sample_sdmx_response):
        """Every quarter object has all required numeric fields populated."""
        result = process_abs_response(sample_sdmx_response)
        for quarter in result.quarters:
            _assert_quarter_fields(quarter)

    def test_process_valid_response_most_recent_quarter_is_last(self, sample_sdmx_response):
        """Quarters are ordered chronologically; most recent is the last element."""
        result = process_abs_response(sample_sdmx_response)
        periods = [q.period for q in result.quarters]
        assert periods[-1] == "2024-Q3"
        assert periods[0] == "2022-Q4"

    def test_process_valid_response_total_capex_value(self, sample_sdmx_response):
        """Most recent quarter total matches the fixture value."""
        result = process_abs_response(sample_sdmx_response)
        latest = result.quarters[-1]
        assert latest.period == "2024-Q3"
        # The fixture puts 42567.8 as the total for 2024-Q3
        assert abs(latest.total - 42567.8) < 1.0

    def test_process_valid_response_mining_value(self, sample_sdmx_response):
        """Mining CapEx for the most recent quarter matches the fixture value."""
        result = process_abs_response(sample_sdmx_response)
        latest = result.quarters[-1]
        assert abs(latest.mining - 18234.5) < 1.0

    def test_process_valid_response_has_by_industry(self, sample_sdmx_response):
        """Result contains by_industry dictionary with expected industry keys."""
        result = process_abs_response(sample_sdmx_response)
        assert "Total" in result.by_industry
        assert "Mining" in result.by_industry
        assert "Manufacturing" in result.by_industry
        assert "Other Selected Industries" in result.by_industry

    def test_process_valid_response_has_by_asset_type(self, sample_sdmx_response):
        """Result contains by_asset_type dictionary with expected asset keys."""
        result = process_abs_response(sample_sdmx_response)
        assert "Total" in result.by_asset_type
        assert "Buildings & Structures" in result.by_asset_type
        assert "Equipment, Plant & Machinery" in result.by_asset_type

    def test_process_valid_response_metadata_present(self, sample_sdmx_response):
        """Metadata dictionary contains source, last_updated, and is_cached."""
        result = process_abs_response(sample_sdmx_response)
        assert "source" in result.metadata
        assert "last_updated" in result.metadata
        assert "is_cached" in result.metadata
        assert result.metadata["is_cached"] is False

    def test_process_valid_response_filters_capex_exp(self, sample_sdmx_response):
        """Expected expenditure records (CAPEX_EXP) are excluded from results."""
        result = process_abs_response(sample_sdmx_response)
        # The fixture has CAPEX_EXP values of ~43000-46500. Real totals should
        # be in the 39800-42567 range. If CAPEX_EXP leaked in, totals would
        # be massively inflated.
        for quarter in result.quarters:
            assert quarter.total < 50000.0, (
                f"Quarter {quarter.period} total={quarter.total} suggests "
                "CAPEX_EXP records were not filtered out."
            )

    def test_process_valid_response_by_industry_series_length(self, sample_sdmx_response):
        """Each industry series has one entry per returned quarter."""
        result = process_abs_response(sample_sdmx_response)
        for industry, series in result.by_industry.items():
            assert len(series) == len(result.quarters), \
                f"Industry '{industry}' has {len(series)} entries, expected {len(result.quarters)}"

    def test_process_valid_response_by_asset_series_length(self, sample_sdmx_response):
        """Each asset series has one entry per returned quarter."""
        result = process_abs_response(sample_sdmx_response)
        for asset, series in result.by_asset_type.items():
            assert len(series) == len(result.quarters), \
                f"Asset '{asset}' has {len(series)} entries, expected {len(result.quarters)}"

    def test_process_series_based_response(self, sample_sdmx_series_response):
        """Series-based SDMX format is parsed and returns valid CapExData."""
        result = process_abs_response(sample_sdmx_series_response)
        assert isinstance(result, CapExData)
        assert len(result.quarters) > 0
        for q in result.quarters:
            _assert_quarter_fields(q)


# ---------------------------------------------------------------------------
# process_abs_response — error cases
# ---------------------------------------------------------------------------


class TestProcessAbsResponseErrors:
    """Error path tests for process_abs_response."""

    def test_process_empty_observations_raises_value_error(self, sample_sdmx_response):
        """An SDMX response with an empty observations dict raises ValueError."""
        empty_response = dict(sample_sdmx_response)
        empty_response["dataSets"] = [{"action": "Information", "observations": {}}]
        with pytest.raises(ValueError) as exc_info:
            process_abs_response(empty_response)
        assert "no observations" in str(exc_info.value).lower() or \
               "empty" in str(exc_info.value).lower()

    def test_process_missing_datasets_raises_value_error(self):
        """A response missing dataSets raises ValueError."""
        with pytest.raises(ValueError):
            process_abs_response({"structure": {}})

    def test_process_only_capex_exp_data_raises_value_error(self, sample_sdmx_response):
        """A dataset containing only CAPEX_EXP (no CAPEX_ACT) raises ValueError.

        After filtering for CAPEX_ACT, the DataFrame is empty, so the processor
        must raise rather than return zero-filled data.
        """
        import copy
        # Replace all observation keys: change measure index 0 -> 1 (CAPEX_EXP)
        response = copy.deepcopy(sample_sdmx_response)
        old_obs = response["dataSets"][0]["observations"]
        new_obs = {}
        for key, values in old_obs.items():
            parts = key.split(":")
            parts[1] = "1"  # set MEASURE index to 1 = CAPEX_EXP
            new_key = ":".join(parts)
            new_obs[new_key] = values
        response["dataSets"][0]["observations"] = new_obs

        with pytest.raises(ValueError) as exc_info:
            process_abs_response(response)
        # Should complain about no actual expenditure data
        assert "no" in str(exc_info.value).lower() or \
               "empty" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Percentage change calculations
# ---------------------------------------------------------------------------


class TestPercentageCalculations:
    """Tests for QoQ and YoY percentage change accuracy."""

    def test_qoq_change_first_quarter_is_none(self, sample_sdmx_response):
        """The first quarter has no QoQ change (no previous quarter to compare)."""
        result = process_abs_response(sample_sdmx_response)
        assert result.quarters[0].qoq_change is None

    def test_qoq_change_second_quarter_is_calculated(self, sample_sdmx_response):
        """The second quarter has a QoQ percentage change value."""
        result = process_abs_response(sample_sdmx_response)
        assert result.quarters[1].qoq_change is not None

    def test_qoq_change_formula_correctness(self, sample_sdmx_response):
        """QoQ percentage change matches (current - previous) / previous * 100."""
        result = process_abs_response(sample_sdmx_response)
        for i in range(1, len(result.quarters)):
            current = result.quarters[i]
            previous = result.quarters[i - 1]
            if previous.total != 0 and current.qoq_change is not None:
                expected = round(
                    (current.total - previous.total) / previous.total * 100, 2
                )
                assert abs(current.qoq_change - expected) < 0.01, (
                    f"Quarter {current.period}: expected QoQ={expected}, "
                    f"got {current.qoq_change}"
                )

    def test_yoy_change_first_four_quarters_are_none(self, sample_sdmx_response):
        """The first four quarters have no YoY change (insufficient history)."""
        result = process_abs_response(sample_sdmx_response)
        for i in range(4):
            assert result.quarters[i].yoy_change is None, \
                f"Quarter {result.quarters[i].period} should have yoy_change=None"

    def test_yoy_change_fifth_quarter_is_calculated(self, sample_sdmx_response):
        """The fifth quarter (index 4) has a YoY change value."""
        result = process_abs_response(sample_sdmx_response)
        assert result.quarters[4].yoy_change is not None

    def test_yoy_change_formula_correctness(self, sample_sdmx_response):
        """YoY change matches (current - year_ago) / year_ago * 100."""
        result = process_abs_response(sample_sdmx_response)
        for i in range(4, len(result.quarters)):
            current = result.quarters[i]
            year_ago = result.quarters[i - 4]
            if year_ago.total != 0 and current.yoy_change is not None:
                expected = round(
                    (current.total - year_ago.total) / year_ago.total * 100, 2
                )
                assert abs(current.yoy_change - expected) < 0.01, (
                    f"Quarter {current.period}: expected YoY={expected}, "
                    f"got {current.yoy_change}"
                )


# ---------------------------------------------------------------------------
# Partial data handling
# ---------------------------------------------------------------------------


class TestPartialData:
    """Tests for processing responses with fewer than 8 quarters."""

    def _make_partial_response(
        self, sample_sdmx_response: dict[str, Any], num_quarters: int
    ) -> dict[str, Any]:
        """Return a copy of sample_sdmx_response with only num_quarters time periods."""
        import copy
        response = copy.deepcopy(sample_sdmx_response)

        # Trim time period values in structure
        time_dim = response["structure"]["dimensions"]["observation"][0]
        time_dim["values"] = time_dim["values"][:num_quarters]

        # Trim observations to only include time indices < num_quarters
        old_obs = response["dataSets"][0]["observations"]
        new_obs = {}
        for key, values in old_obs.items():
            parts = key.split(":")
            time_idx = int(parts[-1])
            if time_idx < num_quarters:
                new_obs[key] = values
        response["dataSets"][0]["observations"] = new_obs
        return response

    def test_process_fewer_than_8_quarters_returns_available(self, sample_sdmx_response):
        """Dataset with only 3 quarters returns 3 quarters (not an error)."""
        partial = self._make_partial_response(sample_sdmx_response, 3)
        result = process_abs_response(partial)
        assert isinstance(result, CapExData)
        assert len(result.quarters) == 3

    def test_process_single_quarter_returns_one_quarter(self, sample_sdmx_response):
        """Dataset with exactly 1 quarter returns that single quarter."""
        partial = self._make_partial_response(sample_sdmx_response, 1)
        result = process_abs_response(partial)
        assert len(result.quarters) == 1
        assert result.quarters[0].qoq_change is None
        assert result.quarters[0].yoy_change is None

    def test_process_more_than_8_quarters_limits_to_8(self, sample_sdmx_response):
        """Processor caps returned quarters at _QUARTERS_TO_RETURN (8)."""
        # The fixture already has exactly 8; this confirms it stays at 8
        result = process_abs_response(sample_sdmx_response)
        assert len(result.quarters) <= _QUARTERS_TO_RETURN


# ---------------------------------------------------------------------------
# Industry breakdown consistency
# ---------------------------------------------------------------------------


class TestIndustryBreakdown:
    """Tests for internal consistency of industry and asset aggregations."""

    def test_by_industry_series_have_period_and_value_keys(self, sample_sdmx_response):
        """Every item in by_industry series has 'period' and 'value' keys."""
        result = process_abs_response(sample_sdmx_response)
        for industry, series in result.by_industry.items():
            for item in series:
                assert "period" in item, f"Missing 'period' in {industry} series item"
                assert "value" in item, f"Missing 'value' in {industry} series item"

    def test_by_asset_type_series_have_period_and_value_keys(self, sample_sdmx_response):
        """Every item in by_asset_type series has 'period' and 'value' keys."""
        result = process_abs_response(sample_sdmx_response)
        for asset, series in result.by_asset_type.items():
            for item in series:
                assert "period" in item, f"Missing 'period' in {asset} series item"
                assert "value" in item, f"Missing 'value' in {asset} series item"

    def test_total_industry_matches_total_quarter(self, sample_sdmx_response):
        """by_industry['Total'] values match quarters[*].total for each period."""
        result = process_abs_response(sample_sdmx_response)
        quarter_totals = {q.period: q.total for q in result.quarters}
        for item in result.by_industry.get("Total", []):
            period = item["period"]
            assert abs(item["value"] - quarter_totals[period]) < 0.01, (
                f"by_industry Total mismatch for {period}: "
                f"series={item['value']}, quarter={quarter_totals[period]}"
            )

    def test_total_asset_matches_total_quarter(self, sample_sdmx_response):
        """by_asset_type['Total'] values match quarters[*].total for each period."""
        result = process_abs_response(sample_sdmx_response)
        quarter_totals = {q.period: q.total for q in result.quarters}
        for item in result.by_asset_type.get("Total", []):
            period = item["period"]
            assert abs(item["value"] - quarter_totals[period]) < 0.01, (
                f"by_asset_type Total mismatch for {period}: "
                f"series={item['value']}, quarter={quarter_totals[period]}"
            )


# ---------------------------------------------------------------------------
# build_data_summary
# ---------------------------------------------------------------------------


class TestBuildDataSummary:
    """Tests for build_data_summary text rendering."""

    def test_build_summary_returns_string(self, sample_capex_data):
        """build_data_summary returns a non-empty string."""
        summary = build_data_summary(sample_capex_data)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_build_summary_contains_current_quarter_period(self, sample_capex_data):
        """Summary mentions the most recent quarter's period."""
        summary = build_data_summary(sample_capex_data)
        assert "2024-Q3" in summary

    def test_build_summary_contains_total_capex_value(self, sample_capex_data):
        """Summary contains the total CapEx figure for the most recent quarter."""
        summary = build_data_summary(sample_capex_data)
        # 42567.8 formatted as $42,567.8M
        assert "42,567.8" in summary

    def test_build_summary_contains_mining_value(self, sample_capex_data):
        """Summary contains mining figure for the current quarter."""
        summary = build_data_summary(sample_capex_data)
        assert "18,234.5" in summary

    def test_build_summary_contains_previous_quarter(self, sample_capex_data):
        """Summary includes the previous quarter's section."""
        summary = build_data_summary(sample_capex_data)
        assert "Previous Quarter" in summary
        assert "2024-Q2" in summary

    def test_build_summary_contains_year_ago_quarter(self, sample_capex_data):
        """Summary includes the year-ago quarter's section."""
        summary = build_data_summary(sample_capex_data)
        assert "Year-Ago Quarter" in summary

    def test_build_summary_contains_trend_section(self, sample_capex_data):
        """Summary includes the 8-Quarter Trend section."""
        summary = build_data_summary(sample_capex_data)
        assert "8-Quarter Trend" in summary

    def test_build_summary_empty_data_returns_fallback(self):
        """An empty quarters list returns the 'No data available.' message."""
        empty_data = CapExData(
            quarters=[],
            by_industry={},
            by_asset_type={},
            metadata={},
        )
        summary = build_data_summary(empty_data)
        assert summary == "No data available."

    def test_build_summary_contains_qoq_change(self, sample_capex_data):
        """Summary includes QoQ percentage change for the current quarter."""
        summary = build_data_summary(sample_capex_data)
        assert "QoQ" in summary

    def test_build_summary_single_quarter_no_prev_section(self):
        """With only one quarter, there is no Previous Quarter section."""
        single_data = CapExData(
            quarters=[
                CapExQuarter(
                    period="2024-Q3",
                    total=42567.8,
                    mining=18234.5,
                    manufacturing=5678.9,
                    other_selected=18654.4,
                    buildings_structures=19876.3,
                    equipment_plant_machinery=22691.5,
                    qoq_change=None,
                    yoy_change=None,
                )
            ],
            by_industry={},
            by_asset_type={},
            metadata={"source": "ABS", "estimate_number": "N/A"},
        )
        summary = build_data_summary(single_data)
        assert "Previous Quarter" not in summary
