"""
data_cleaning.py
----------------
General dataset validation and cleaning utilities.

These utilities operate on pandas DataFrames and are intended for
use during ML development and dataset preparation. They are NOT
responsible for backend inventory management.
"""

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Column validation
# ---------------------------------------------------------------------------

def validate_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    """
    Raise ValueError if any required column is missing from df.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to check.
    required_columns : list[str]
        Column names that must be present.

    Raises
    ------
    ValueError
        If one or more required columns are absent.
    """
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    logger.debug("Column validation passed. Required: %s", required_columns)


def validate_numeric_columns(
    df: pd.DataFrame, numeric_columns: list[str]
) -> pd.DataFrame:
    """
    Coerce specified columns to numeric dtype and log any conversion failures.

    Non-numeric values that cannot be coerced are replaced with NaN so that
    subsequent cleaning steps can decide how to handle them.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    numeric_columns : list[str]
        Column names that should contain numeric data.

    Returns
    -------
    pd.DataFrame
        DataFrame with the specified columns cast to numeric.
    """
    df = df.copy()
    for col in numeric_columns:
        if col not in df.columns:
            logger.warning("Numeric column '%s' not found – skipping.", col)
            continue
        before_nulls = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        after_nulls = df[col].isna().sum()
        new_nulls = after_nulls - before_nulls
        if new_nulls > 0:
            logger.warning(
                "Column '%s': %d value(s) could not be coerced to numeric "
                "and were replaced with NaN.",
                col,
                new_nulls,
            )
    return df


# ---------------------------------------------------------------------------
# Duplicate handling
# ---------------------------------------------------------------------------

def remove_duplicates(
    df: pd.DataFrame, subset: list[str] | None = None
) -> pd.DataFrame:
    """
    Remove duplicate rows from the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    subset : list[str] | None
        Column names to consider when identifying duplicates.
        If None, all columns are used.

    Returns
    -------
    pd.DataFrame
        DataFrame with duplicate rows removed.
    """
    original_len = len(df)
    df = df.drop_duplicates(subset=subset)
    removed = original_len - len(df)
    if removed:
        logger.info("Removed %d duplicate row(s).", removed)
    return df


# ---------------------------------------------------------------------------
# Missing value handling
# ---------------------------------------------------------------------------

def handle_missing_values(
    df: pd.DataFrame,
    drop_columns: list[str] | None = None,
    fill_strategy: dict | None = None,
) -> pd.DataFrame:
    """
    Handle missing values without destroying useful data.

    Strategy:
    - Rows where key identifier columns contain NaN are dropped.
    - For other columns a per-column fill strategy may be provided.
    - If no fill strategy is provided, rows with remaining NaNs are dropped
      and a warning is logged.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    drop_columns : list[str] | None
        Columns for which a NaN value means the row must be discarded.
        Default: None (no forced drops beyond strategy).
    fill_strategy : dict | None
        Mapping of ``{column_name: value_or_method}`` where
        ``value_or_method`` can be a scalar, ``"ffill"``, ``"bfill"``,
        or ``"median"``.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame.
    """
    df = df.copy()
    original_len = len(df)

    # Drop rows where critical identifier columns are NaN
    if drop_columns:
        df = df.dropna(subset=drop_columns)
        dropped = original_len - len(df)
        if dropped:
            logger.info(
                "Dropped %d row(s) with NaN in critical columns %s.",
                dropped,
                drop_columns,
            )

    # Apply per-column fill strategy
    if fill_strategy:
        for col, method in fill_strategy.items():
            if col not in df.columns:
                continue
            if method == "ffill":
                df[col] = df[col].ffill()
            elif method == "bfill":
                df[col] = df[col].bfill()
            elif method == "median":
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
            else:
                # Treat as a scalar fill value
                df[col] = df[col].fillna(method)

    remaining_nulls = df.isna().sum().sum()
    if remaining_nulls > 0:
        logger.warning(
            "%d remaining NaN value(s) in DataFrame. "
            "Dropping affected rows to avoid corrupt data.",
            remaining_nulls,
        )
        df = df.dropna()

    return df
