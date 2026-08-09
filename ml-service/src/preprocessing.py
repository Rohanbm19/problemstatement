"""
preprocessing.py
----------------
Prepare historical demand data for time-series forecasting.

IMPORTANT:
The current inventory CSV (warehouse_raw.csv / warehouse_cleaned.csv)
contains a snapshot of warehouse inventory fields such as stock_level,
reorder_point, etc. It does NOT contain date-based historical demand.

Functions in this module expect data in the format:

    date, item_id, demand

Example:

    2026-01-01,ITM10025,12
    2026-01-02,ITM10025,15
    2026-01-03,ITM10025,11

In production the backend will supply this data via its API.
The local CSV may be used for ML development and testing only.
"""

import logging
import os
from datetime import date

import pandas as pd
import numpy as np

from src.data_cleaning import (
    validate_columns,
    validate_numeric_columns,
    remove_duplicates,
    handle_missing_values,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Expected schema for historical demand data
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = ["date", "item_id", "demand"]
NUMERIC_COLUMNS = ["demand"]

# Default path used only during ML development/testing.
# In production the backend sends history directly to the /forecast API.
DEFAULT_DATASET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "warehouse_raw.csv"
)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_dataset(path: str | None = None) -> pd.DataFrame:
    """
    Load a historical demand CSV for ML development / experimentation.

    The CSV must contain at minimum the columns: date, item_id, demand.

    NOTE: This function is for development and experimentation only.
    In production the backend sends historical demand to the /forecast
    endpoint directly; the ML service does NOT query PostgreSQL.

    Parameters
    ----------
    path : str | None
        Path to the CSV file. Defaults to DEFAULT_DATASET_PATH.

    Returns
    -------
    pd.DataFrame
        Cleaned and typed DataFrame.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If required columns are missing.
    """
    resolved_path = path or DEFAULT_DATASET_PATH

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(
            f"Dataset not found at '{resolved_path}'. "
            "The warehouse_raw.csv contains an inventory snapshot, not "
            "historical time-series demand. For demand forecasting, supply "
            "a CSV with columns: date, item_id, demand."
        )

    df = pd.read_csv(resolved_path)
    logger.info("Loaded dataset from '%s' — %d rows.", resolved_path, len(df))

    # Check required columns
    validate_columns(df, REQUIRED_COLUMNS)

    return df


# ---------------------------------------------------------------------------
# Column validation
# ---------------------------------------------------------------------------

def validate_time_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse and validate the 'date' column into datetime.date objects.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with a 'date' column.

    Returns
    -------
    pd.DataFrame
        DataFrame with 'date' column as datetime64 dtype.

    Raises
    ------
    ValueError
        If dates cannot be parsed.
    """
    df = df.copy()
    original_len = len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    invalid_count = df["date"].isna().sum()
    if invalid_count > 0:
        logger.warning(
            "%d row(s) had unparseable dates and will be dropped.",
            invalid_count,
        )
        df = df.dropna(subset=["date"])

    if len(df) == 0:
        raise ValueError("No valid dates remain after parsing. Check the date column.")

    logger.debug(
        "Date column validated: %d/%d rows retained.",
        len(df),
        original_len,
    )
    return df


# ---------------------------------------------------------------------------
# Full preprocessing pipeline
# ---------------------------------------------------------------------------

def prepare_time_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full preprocessing pipeline for historical demand data.

    Steps:
    1. Validate required columns.
    2. Parse and validate the date column.
    3. Coerce demand to numeric.
    4. Remove duplicates on (date, item_id).
    5. Handle missing values (drop rows with missing demand).
    6. Sort chronologically by (item_id, date).

    Parameters
    ----------
    df : pd.DataFrame
        Raw historical demand data with columns: date, item_id, demand.

    Returns
    -------
    pd.DataFrame
        Cleaned, sorted time-series DataFrame.
    """
    # Step 1 – column validation
    validate_columns(df, REQUIRED_COLUMNS)

    # Step 2 – date parsing
    df = validate_time_column(df)

    # Step 3 – numeric coercion
    df = validate_numeric_columns(df, NUMERIC_COLUMNS)

    # Step 4 – remove duplicate (date, item_id) rows
    df = remove_duplicates(df, subset=["date", "item_id"])

    # Step 5 – drop rows where demand is missing
    df = handle_missing_values(df, drop_columns=["item_id", "demand"])

    # Step 6 – chronological sort
    df = sort_by_date(df)

    logger.info(
        "Time-series preparation complete: %d rows, %d unique items.",
        len(df),
        df["item_id"].nunique(),
    )
    return df


def prepare_item_series(df: pd.DataFrame, item_id: str) -> pd.DataFrame:
    """
    Extract and prepare the time-series for a single item.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed full demand DataFrame.
    item_id : str
        The item identifier to extract.

    Returns
    -------
    pd.DataFrame
        Filtered, sorted DataFrame for the given item.

    Raises
    ------
    ValueError
        If the item is not found in the DataFrame.
    """
    item_df = df[df["item_id"] == item_id].copy()

    if item_df.empty:
        available = df["item_id"].unique().tolist()
        raise ValueError(
            f"Item '{item_id}' not found in historical demand data. "
            f"Available item IDs: {available[:10]}{'...' if len(available) > 10 else ''}"
        )

    item_df = sort_by_date(item_df)
    logger.debug(
        "Prepared series for item '%s': %d data points.", item_id, len(item_df)
    )
    return item_df


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

def sort_by_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort the DataFrame chronologically.

    If an 'item_id' column exists the sort key is (item_id, date),
    otherwise only 'date' is used.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with a 'date' column.

    Returns
    -------
    pd.DataFrame
        Sorted DataFrame with reset index.
    """
    sort_keys = ["item_id", "date"] if "item_id" in df.columns else ["date"]
    return df.sort_values(sort_keys).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Optional resampling
# ---------------------------------------------------------------------------

def resample_if_required(
    df: pd.DataFrame,
    freq: str = "D",
    fill_method: str = "ffill",
) -> pd.DataFrame:
    """
    Resample a single-item demand series to a regular frequency.

    This function is intended for use after ``prepare_item_series()``.
    It fills any gaps in the date range so the time series is contiguous,
    which is required by many forecasting models.

    Parameters
    ----------
    df : pd.DataFrame
        Single-item time-series DataFrame with columns: date, demand.
    freq : str
        Pandas offset alias for the target frequency (default: 'D' = daily).
    fill_method : str
        How to fill inserted rows: 'ffill', 'bfill', or '0' (zero-fill).

    Returns
    -------
    pd.DataFrame
        Resampled DataFrame with a contiguous date range.
    """
    df = df.copy()
    df = df.set_index("date")
    df.index = pd.DatetimeIndex(df.index)

    df_resampled = df["demand"].resample(freq).sum()  # sum within each period

    if fill_method == "ffill":
        df_resampled = df_resampled.ffill()
    elif fill_method == "bfill":
        df_resampled = df_resampled.bfill()
    else:
        df_resampled = df_resampled.fillna(0)

    result = df_resampled.reset_index()
    result.columns = ["date", "demand"]
    return result
