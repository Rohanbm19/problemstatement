"""
evaluation.py
-------------
Forecast evaluation utilities for TwinStock AI ML Service.

These functions are used to measure the quality of demand forecasts
against known actual values.

IMPORTANT:
- Chronological (time-ordered) train/test splits are used exclusively.
- Time-series data is NEVER randomly shuffled before splitting.
- A random split would cause data leakage and produce misleadingly
  optimistic evaluation metrics.

Default split strategy:
    70% of chronological data → training / context window
    30% of chronological data → test / evaluation window

Supported metrics:
    MAE   – Mean Absolute Error
    RMSE  – Root Mean Squared Error
    MAPE  – Mean Absolute Percentage Error
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Individual metrics
# ---------------------------------------------------------------------------

def calculate_mae(actual: list[float], predicted: list[float]) -> float:
    """
    Mean Absolute Error.

    MAE = mean(|actual - predicted|)

    Parameters
    ----------
    actual : list[float]
        True observed demand values.
    predicted : list[float]
        Forecasted demand values (must be the same length as actual).

    Returns
    -------
    float
        MAE value.

    Raises
    ------
    ValueError
        If the lists have different lengths or are empty.
    """
    actual_arr, predicted_arr = _validate_arrays(actual, predicted)
    mae = float(np.mean(np.abs(actual_arr - predicted_arr)))
    logger.debug("MAE = %.4f", mae)
    return round(mae, 4)


def calculate_rmse(actual: list[float], predicted: list[float]) -> float:
    """
    Root Mean Squared Error.

    RMSE = sqrt(mean((actual - predicted)^2))

    Parameters
    ----------
    actual : list[float]
    predicted : list[float]

    Returns
    -------
    float
        RMSE value.
    """
    actual_arr, predicted_arr = _validate_arrays(actual, predicted)
    rmse = float(np.sqrt(np.mean((actual_arr - predicted_arr) ** 2)))
    logger.debug("RMSE = %.4f", rmse)
    return round(rmse, 4)


def calculate_mape(
    actual: list[float],
    predicted: list[float],
    epsilon: float = 1e-8,
) -> float:
    """
    Mean Absolute Percentage Error.

    MAPE = mean(|actual - predicted| / max(|actual|, epsilon)) * 100

    A small epsilon is added to the denominator to avoid division by zero
    when actual demand is zero.

    Parameters
    ----------
    actual : list[float]
    predicted : list[float]
    epsilon : float
        Small constant to prevent division by zero (default: 1e-8).

    Returns
    -------
    float
        MAPE as a percentage (0–100+).
    """
    actual_arr, predicted_arr = _validate_arrays(actual, predicted)
    denominator = np.maximum(np.abs(actual_arr), epsilon)
    mape = float(np.mean(np.abs(actual_arr - predicted_arr) / denominator) * 100)
    logger.debug("MAPE = %.4f%%", mape)
    return round(mape, 4)


# ---------------------------------------------------------------------------
# Chronological train/test split
# ---------------------------------------------------------------------------

def chronological_train_test_split(
    history: list[dict],
    test_ratio: float = 0.3,
) -> tuple[list[dict], list[dict]]:
    """
    Split historical demand into a training set and a test set using a
    CHRONOLOGICAL split — no random shuffling.

    The data is assumed to already be sorted by date (ascending). The last
    ``test_ratio`` fraction of records becomes the test set.

    Example with test_ratio=0.3 and 10 data points:
        - Training: indices 0..6  (7 points = 70%)
        - Test:     indices 7..9  (3 points = 30%)

    Parameters
    ----------
    history : list[dict]
        Sorted list of ``{"date": ..., "demand": float}`` dicts.
    test_ratio : float
        Fraction of data to use for testing (default: 0.3).

    Returns
    -------
    tuple[list[dict], list[dict]]
        (train_history, test_history)

    Raises
    ------
    ValueError
        If there are fewer than 2 data points.
    """
    if len(history) < 2:
        raise ValueError(
            f"At least 2 historical data points are required for evaluation. "
            f"Got {len(history)}."
        )

    if not (0 < test_ratio < 1):
        raise ValueError(f"test_ratio must be between 0 and 1, got {test_ratio}.")

    n_test = max(1, int(len(history) * test_ratio))
    n_train = len(history) - n_test

    train = history[:n_train]
    test = history[n_train:]

    logger.info(
        "Chronological split: %d train / %d test (test_ratio=%.2f)",
        len(train),
        len(test),
        test_ratio,
    )
    return train, test


# ---------------------------------------------------------------------------
# Full evaluation
# ---------------------------------------------------------------------------

def evaluate_forecast(
    actual: list[dict],
    predicted: list[dict],
) -> dict:
    """
    Compute MAE, RMSE, and MAPE for a set of actual vs predicted demand points.

    Parameters
    ----------
    actual : list[dict]
        List of ``{"date": ..., "demand": float}`` dicts (chronological).
    predicted : list[dict]
        List of ``{"date": ..., "predicted_demand": float}`` dicts.
        Must be the same length as actual.

    Returns
    -------
    dict
        Evaluation metrics::

            {
                "n_points": int,
                "mae": float,
                "rmse": float,
                "mape": float
            }
    """
    if len(actual) != len(predicted):
        raise ValueError(
            f"actual and predicted must have the same length. "
            f"Got actual={len(actual)}, predicted={len(predicted)}."
        )

    actual_values = [float(p["demand"]) for p in actual]
    predicted_values = [float(p["predicted_demand"]) for p in predicted]

    return {
        "n_points": len(actual_values),
        "mae": calculate_mae(actual_values, predicted_values),
        "rmse": calculate_rmse(actual_values, predicted_values),
        "mape": calculate_mape(actual_values, predicted_values),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_arrays(
    actual: list[float], predicted: list[float]
) -> tuple[np.ndarray, np.ndarray]:
    """Convert to numpy arrays and validate shape."""
    if len(actual) == 0 or len(predicted) == 0:
        raise ValueError("actual and predicted cannot be empty.")
    if len(actual) != len(predicted):
        raise ValueError(
            f"actual (len={len(actual)}) and predicted (len={len(predicted)}) "
            "must have the same length."
        )
    return np.array(actual, dtype=float), np.array(predicted, dtype=float)
