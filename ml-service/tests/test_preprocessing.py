"""
test_preprocessing.py
---------------------
Tests for src/preprocessing.py

These tests are self-contained and do not depend on the local CSV file
or any running services.
"""

import pytest
import pandas as pd
from datetime import date

from src.preprocessing import (
    validate_time_column,
    prepare_time_series,
    prepare_item_series,
    sort_by_date,
    resample_if_required,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


VALID_ROWS = [
    {"date": "2026-07-03", "item_id": "ITM001", "demand": 11},
    {"date": "2026-07-01", "item_id": "ITM001", "demand": 12},
    {"date": "2026-07-02", "item_id": "ITM001", "demand": 15},
    {"date": "2026-07-01", "item_id": "ITM002", "demand": 30},
    {"date": "2026-07-02", "item_id": "ITM002", "demand": 27},
]


# ---------------------------------------------------------------------------
# validate_time_column
# ---------------------------------------------------------------------------

class TestValidateTimeColumn:
    def test_valid_dates_parsed(self):
        df = make_df([
            {"date": "2026-07-01", "item_id": "ITM001", "demand": 10},
            {"date": "2026-07-02", "item_id": "ITM001", "demand": 12},
        ])
        result = validate_time_column(df)
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_invalid_dates_dropped(self):
        df = make_df([
            {"date": "2026-07-01", "item_id": "ITM001", "demand": 10},
            {"date": "not-a-date", "item_id": "ITM001", "demand": 12},
        ])
        result = validate_time_column(df)
        assert len(result) == 1  # bad row dropped

    def test_all_invalid_dates_raises(self):
        df = make_df([
            {"date": "bad1", "item_id": "ITM001", "demand": 10},
            {"date": "bad2", "item_id": "ITM001", "demand": 12},
        ])
        with pytest.raises(ValueError, match="No valid dates"):
            validate_time_column(df)


# ---------------------------------------------------------------------------
# sort_by_date
# ---------------------------------------------------------------------------

class TestSortByDate:
    def test_sorts_ascending(self):
        df = make_df([
            {"date": "2026-07-03", "item_id": "ITM001", "demand": 11},
            {"date": "2026-07-01", "item_id": "ITM001", "demand": 12},
            {"date": "2026-07-02", "item_id": "ITM001", "demand": 15},
        ])
        df["date"] = pd.to_datetime(df["date"])
        result = sort_by_date(df)
        dates = result["date"].tolist()
        assert dates == sorted(dates)

    def test_sorts_by_item_then_date(self):
        df = make_df([
            {"date": "2026-07-02", "item_id": "ITM002", "demand": 27},
            {"date": "2026-07-01", "item_id": "ITM001", "demand": 12},
            {"date": "2026-07-01", "item_id": "ITM002", "demand": 30},
        ])
        df["date"] = pd.to_datetime(df["date"])
        result = sort_by_date(df)
        assert result.iloc[0]["item_id"] == "ITM001"
        assert result.iloc[1]["item_id"] == "ITM002"

    def test_resets_index(self):
        df = make_df([
            {"date": "2026-07-03", "demand": 11},
            {"date": "2026-07-01", "demand": 12},
        ])
        df["date"] = pd.to_datetime(df["date"])
        result = sort_by_date(df)
        assert list(result.index) == list(range(len(result)))


# ---------------------------------------------------------------------------
# prepare_time_series
# ---------------------------------------------------------------------------

class TestPrepareTimeSeries:
    def test_valid_data_returns_dataframe(self):
        df = make_df(VALID_ROWS)
        result = prepare_time_series(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(VALID_ROWS)

    def test_sorted_chronologically(self):
        df = make_df(VALID_ROWS)
        result = prepare_time_series(df)
        dates_by_item = result.groupby("item_id")["date"].apply(list)
        for item, dates in dates_by_item.items():
            assert dates == sorted(dates)

    def test_missing_date_column_raises(self):
        df = make_df([{"item_id": "ITM001", "demand": 10}])
        with pytest.raises(ValueError, match="Missing required columns"):
            prepare_time_series(df)

    def test_missing_demand_column_raises(self):
        df = make_df([{"date": "2026-07-01", "item_id": "ITM001"}])
        with pytest.raises(ValueError, match="Missing required columns"):
            prepare_time_series(df)

    def test_removes_duplicates(self):
        rows_with_dup = VALID_ROWS + [
            {"date": "2026-07-01", "item_id": "ITM001", "demand": 99}  # duplicate
        ]
        df = make_df(rows_with_dup)
        result = prepare_time_series(df)
        assert len(result) == len(VALID_ROWS)

    def test_drops_rows_with_missing_demand(self):
        rows = VALID_ROWS + [
            {"date": "2026-07-10", "item_id": "ITM001", "demand": None}
        ]
        df = make_df(rows)
        result = prepare_time_series(df)
        assert len(result) == len(VALID_ROWS)


# ---------------------------------------------------------------------------
# prepare_item_series
# ---------------------------------------------------------------------------

class TestPrepareItemSeries:
    def _get_prepped_df(self):
        df = make_df(VALID_ROWS)
        return prepare_time_series(df)

    def test_filters_correct_item(self):
        df = self._get_prepped_df()
        result = prepare_item_series(df, "ITM001")
        assert all(result["item_id"] == "ITM001")

    def test_unknown_item_raises(self):
        df = self._get_prepped_df()
        with pytest.raises(ValueError, match="not found"):
            prepare_item_series(df, "NONEXISTENT")

    def test_sorted_by_date(self):
        df = self._get_prepped_df()
        result = prepare_item_series(df, "ITM001")
        dates = result["date"].tolist()
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# resample_if_required
# ---------------------------------------------------------------------------

class TestResampleIfRequired:
    def test_fills_gaps(self):
        # Create sparse data: Jan 1 and Jan 5 (gap of 3 days)
        df = pd.DataFrame([
            {"date": pd.Timestamp("2026-01-01"), "demand": 10.0},
            {"date": pd.Timestamp("2026-01-05"), "demand": 20.0},
        ])
        result = resample_if_required(df, freq="D", fill_method="ffill")
        # Should have dates: Jan 1, 2, 3, 4, 5
        assert len(result) == 5

    def test_result_columns(self):
        df = pd.DataFrame([
            {"date": pd.Timestamp("2026-01-01"), "demand": 10.0},
            {"date": pd.Timestamp("2026-01-03"), "demand": 20.0},
        ])
        result = resample_if_required(df)
        assert "date" in result.columns
        assert "demand" in result.columns
