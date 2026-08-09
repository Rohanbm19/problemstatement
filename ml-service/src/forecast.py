"""
forecast.py
-----------
Main ML forecasting module for TwinStock AI.

Architecture
------------
This module provides a clean, pluggable forecasting interface designed
so that the IBM Granite Time Series model (Granite TTM) can be dropped
in as the concrete implementation once it is available.

Current stage: STAGE 1 – API architecture built, baseline model provided.

Model hierarchy:
    ForecastModel          (abstract base)
        └── BaselineMovingAverageModel   ← STAGE 4: development baseline only
        └── GraniteForecastModel         ← STAGE 5: IBM Granite TTM (not yet loaded)

The active model is determined at startup by ``get_active_model()``.

IMPORTANT:
- The baseline model is clearly labelled and NOT presented as AI.
- Granite predictions are NOT faked or randomly generated.
- When Granite is unavailable the API returns an honest "not available" response.
- This service predicts only. Business decisions (stockout / replenishment)
  remain in the backend.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic-compatible data structures (plain dataclasses used here to avoid
# a circular import with app.py; app.py owns the Pydantic models)
# ---------------------------------------------------------------------------

class ForecastModel(ABC):
    """Abstract base class for all demand forecasting models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model name."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True only when the model is actually loaded and ready."""

    @abstractmethod
    def predict(
        self,
        history: list[dict],
        horizon: int,
    ) -> list[dict]:
        """
        Generate a demand forecast.

        Parameters
        ----------
        history : list[dict]
            Sorted list of ``{"date": date, "demand": float}`` dicts
            representing historical demand.
        horizon : int
            Number of future days to forecast.

        Returns
        -------
        list[dict]
            List of ``{"date": str (ISO), "predicted_demand": float}`` dicts.
        """


# ---------------------------------------------------------------------------
# STAGE 4: Baseline Model (Moving Average)
# This is a DEVELOPMENT BASELINE only — clearly labelled.
# It is NOT Granite, NOT AI, NOT a production model.
# ---------------------------------------------------------------------------

class BaselineMovingAverageModel(ForecastModel):
    """
    BASELINE MODEL – Moving Average.

    This is a simple statistical baseline used during development and testing.
    It is NOT IBM Granite, NOT AI-powered, and NOT suitable for production use.

    Strategy: use the mean demand of the last `window` historical data points
    as the predicted demand for every day in the forecast horizon.
    """

    LABEL = "Baseline (Moving Average)"  # always shown in responses

    def __init__(self, window: int = 7):
        self._window = window

    @property
    def model_name(self) -> str:
        return self.LABEL

    @property
    def is_available(self) -> bool:
        return True

    def predict(self, history: list[dict], horizon: int) -> list[dict]:
        """
        Predict using the rolling mean of the last `window` demand values.
        """
        demands = [float(p["demand"]) for p in history]
        window_data = demands[-self._window:] if len(demands) >= self._window else demands
        avg_demand = float(np.mean(window_data)) if window_data else 0.0

        last_date = pd.to_datetime(history[-1]["date"])
        forecasts = []
        for i in range(1, horizon + 1):
            forecast_date = (last_date + timedelta(days=i)).date()
            forecasts.append(
                {
                    "date": str(forecast_date),
                    "predicted_demand": round(avg_demand, 2),
                }
            )

        logger.debug(
            "[%s] window=%d avg=%.2f horizon=%d",
            self.LABEL,
            self._window,
            avg_demand,
            horizon,
        )
        return forecasts


# ---------------------------------------------------------------------------
# STAGE 5: IBM Granite Time Series model (not yet loaded)
# ---------------------------------------------------------------------------

class GraniteForecastModel(ForecastModel):
    """
    IBM Granite Time Series (Granite TTM) forecasting model.

    This class is the integration point for IBM Granite.
    It will be fully implemented in STAGE 5 when the Granite TTM weights
    and ``tsfm_public`` / ``granite-tsfm`` package are available.

    The model is NOT available until it is explicitly loaded.
    DO NOT fake or randomly generate predictions here.
    """

    MODEL_NAME = "Granite Time Series (IBM TTM)"

    def __init__(self):
        self._model = None
        self._pipeline = None

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def is_available(self) -> bool:
        return self._model is not None and self._pipeline is not None

    def load(self) -> bool:
        """
        Attempt to load the IBM Granite TTM model.

        Returns True if loading succeeded, False otherwise.
        This method will be implemented in STAGE 5 when:
        - ``tsfm_public`` (IBM TSFM) package is installed
        - Granite TTM model weights are available (HuggingFace or local)

        STAGE 5 implementation outline:
        -----------------------------------------------------------------------
        from tsfm_public.models.tinytimemixer import TinyTimeMixerForPrediction
        from tsfm_public import TimeSeriesForecastingPipeline

        model_path = "ibm/TTM"   # or local checkpoint

        self._model = TinyTimeMixerForPrediction.from_pretrained(model_path)
        self._pipeline = TimeSeriesForecastingPipeline(
            model=self._model,
            timestamp_column="date",
            target_columns=["demand"],
            freq="D",
        )
        return True
        -----------------------------------------------------------------------
        """
        logger.info(
            "GraniteForecastModel.load() called — Granite TTM not yet "
            "installed. Install 'ibm-granite-tsfm' and implement this method "
            "in STAGE 5."
        )
        return False

    def predict(self, history: list[dict], horizon: int) -> list[dict]:
        """
        Generate demand forecast using IBM Granite TTM.

        This will be implemented in STAGE 5. Until then, callers should
        check ``is_available`` before calling this method.
        """
        if not self.is_available:
            raise RuntimeError(
                "Granite TTM model is not loaded. "
                "Call load() first or check is_available."
            )

        # STAGE 5 implementation will call self._pipeline here.
        # Placeholder — this branch is unreachable while model is not loaded.
        raise NotImplementedError("Granite TTM predict() not yet implemented.")


# ---------------------------------------------------------------------------
# Model registry — single active model instance
# ---------------------------------------------------------------------------

# The Granite model instance (not yet loaded)
_granite_model = GraniteForecastModel()

# Attempt to load Granite at startup; it will silently remain unavailable.
_granite_available = _granite_model.load()

# Baseline model for development
_baseline_model = BaselineMovingAverageModel(window=7)


def get_active_model() -> ForecastModel:
    """
    Return the best available model.

    Priority:
        1. Granite TTM (if loaded)
        2. Baseline Moving Average (development only)
    """
    if _granite_model.is_available:
        return _granite_model
    return _baseline_model


def get_model_status() -> dict:
    """
    Return the current model availability status.

    Returns
    -------
    dict
        Status dict suitable for the /model/status API response.
    """
    if _granite_model.is_available:
        return {
            "model": GraniteForecastModel.MODEL_NAME,
            "available": True,
        }

    return {
        "model": GraniteForecastModel.MODEL_NAME,
        "available": False,
        "message": (
            "Granite TTM model is not loaded yet. "
            "Install 'ibm-granite-tsfm' and implement GraniteForecastModel.load() "
            "in src/forecast.py (STAGE 5). "
            "A baseline moving-average model is used as a development fallback."
        ),
        "fallback_model": BaselineMovingAverageModel.LABEL,
        "fallback_available": True,
    }


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_forecast_input(
    item_id: str,
    history: list[dict],
    horizon: int,
) -> None:
    """
    Validate the inputs for a forecast request.

    Parameters
    ----------
    item_id : str
    history : list[dict]  – each dict has 'date' and 'demand'
    horizon : int

    Raises
    ------
    ValueError
        With a descriptive message if any validation fails.
    """
    if not item_id or not item_id.strip():
        raise ValueError("item_id cannot be empty.")

    if horizon <= 0:
        raise ValueError(f"horizon must be > 0, got {horizon}.")

    if not history:
        raise ValueError("Historical demand data (history) cannot be empty.")

    for i, point in enumerate(history):
        demand_val = float(point.get("demand", 0))
        if demand_val < 0:
            raise ValueError(
                f"Demand values must be >= 0. "
                f"Found negative value {demand_val} at index {i}."
            )


# ---------------------------------------------------------------------------
# Core forecast function
# ---------------------------------------------------------------------------

def forecast_demand(
    item_id: str,
    historical_data: list[dict],
    horizon: int = 7,
) -> dict:
    """
    Generate a demand forecast for a single item.

    This is the primary ML function called by the API endpoints.

    The function:
    1. Validates inputs.
    2. Sorts historical data chronologically.
    3. Selects the best available model.
    4. Calls model.predict() to generate the forecast.
    5. Returns a structured response.

    If Granite is not available, the response clearly states this and
    falls back to the baseline model (labelled as BASELINE only).

    Parameters
    ----------
    item_id : str
        Warehouse item identifier.
    historical_data : list[dict]
        List of ``{"date": str|date, "demand": float}`` dicts.
    horizon : int
        Number of future days to forecast (default: 7).

    Returns
    -------
    dict
        Structured forecast response.
    """
    logger.info(
        "forecast_demand called — item_id='%s' horizon=%d history_len=%d",
        item_id,
        horizon,
        len(historical_data) if historical_data else 0,
    )

    # Validate
    validate_forecast_input(item_id, historical_data, horizon)

    # Sort history chronologically
    sorted_history = sorted(historical_data, key=lambda x: str(x["date"]))

    # Select model
    model = get_active_model()

    # Generate prediction
    forecast_points = model.predict(sorted_history, horizon)

    logger.info(
        "Forecast generated — item_id='%s' model='%s' points=%d",
        item_id,
        model.model_name,
        len(forecast_points),
    )

    return create_forecast_response(
        item_id=item_id,
        model_name=model.model_name,
        horizon=horizon,
        forecast_points=forecast_points,
    )


def forecast_available() -> bool:
    """Return True if any forecasting model is currently available."""
    return get_active_model().is_available


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------

def create_forecast_response(
    item_id: str,
    model_name: str,
    horizon: int,
    forecast_points: list[dict],
) -> dict:
    """
    Build the standard forecast response dict.

    Parameters
    ----------
    item_id : str
    model_name : str
    horizon : int
    forecast_points : list[dict]  – list of {"date": str, "predicted_demand": float}

    Returns
    -------
    dict
    """
    return {
        "item_id": item_id,
        "model": model_name,
        "horizon": horizon,
        "forecast": forecast_points,
    }
