"""
forecast.py
-----------
Main ML forecasting module for TwinStock AI — STAGE 5.

Architecture
------------
Model hierarchy:
    ForecastModel          (abstract base)
        └── BaselineMovingAverageModel   ← always available, statistical only
        └── GraniteForecastModel         ← IBM Granite TTM R2.1 (daily, zero-shot)

Active model selection (``get_active_model()``):
    Priority 1: Granite TTM if loaded successfully
    Priority 2: Baseline Moving Average (development fallback)

IBM Granite TTM Details
-----------------------
Model:    ibm-granite/granite-timeseries-ttm-r2
Revision: 90-30-ft-r2.1
HF repo:  https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2

- context_length:    90 days (minimum required history)
- prediction_length: 30 days (we slice to the requested horizon)
- frequency:         daily  (freq_token = 1 in TTM R2.1 vocabulary)
- channels:          1  (univariate — single demand series)
- normalization:     handled internally by the model
- zero-shot:         yes, no fine-tuning required

IMPORTANT NOTES
---------------
- Predictions come from the real model — never faked or randomly generated.
- The baseline is clearly labelled and never presented as Granite output.
- The service does NOT query PostgreSQL or modify inventory.
- Stockout / replenishment decisions remain in the backend.
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Environment-variable configuration with sensible defaults
# ---------------------------------------------------------------------------

GRANITE_MODEL_ID: str = os.environ.get(
    "GRANITE_MODEL_ID", "ibm-granite/granite-timeseries-ttm-r2"
)
GRANITE_REVISION: str = os.environ.get(
    "GRANITE_REVISION", "90-30-ft-r2.1"
)
# context_length for the chosen revision (must match the model checkpoint)
GRANITE_CONTEXT_LENGTH: int = int(os.environ.get("GRANITE_CONTEXT_LENGTH", "90"))
# prediction_length produced by the chosen revision
GRANITE_PREDICTION_LENGTH: int = int(os.environ.get("GRANITE_PREDICTION_LENGTH", "30"))

# Daily freq_token value for TTM R2.1 (0=sub-daily, 1=daily, 2=weekly, …)
GRANITE_DAILY_FREQ_TOKEN: int = int(os.environ.get("GRANITE_DAILY_FREQ_TOKEN", "1"))


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class ForecastModel(ABC):
    """Abstract base class for all demand forecasting models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model name shown in API responses."""

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
            Chronologically sorted list of ``{"date": str, "demand": float}``
            dicts representing historical demand.
        horizon : int
            Number of future days to forecast.

        Returns
        -------
        list[dict]
            List of ``{"date": str (ISO), "predicted_demand": float}`` dicts.
        """


# ---------------------------------------------------------------------------
# BASELINE — Moving Average (development fallback)
# This is NOT Granite, NOT AI-powered, NOT a production model.
# ---------------------------------------------------------------------------

class BaselineMovingAverageModel(ForecastModel):
    """
    BASELINE MODEL – Moving Average.

    Used as a development fallback when the Granite TTM model is unavailable.
    It is NOT IBM Granite, NOT AI-powered, and NOT suitable for production use.

    Strategy: predict the rolling mean of the last ``window`` demand values
    for every step in the forecast horizon.
    """

    LABEL = "Baseline (Moving Average)"

    def __init__(self, window: int = 7):
        self._window = window

    @property
    def model_name(self) -> str:
        return self.LABEL

    @property
    def is_available(self) -> bool:
        return True

    def predict(self, history: list[dict], horizon: int) -> list[dict]:
        """Predict using the rolling mean of the last ``window`` demand values."""
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
# STAGE 5 — IBM Granite Time Series TTM R2.1
# ---------------------------------------------------------------------------

class GraniteForecastModel(ForecastModel):
    """
    IBM Granite Time Series (Granite TTM R2.1) — daily demand forecasting.

    Model: ibm-granite/granite-timeseries-ttm-r2 (revision: 90-30-ft-r2.1)

    Uses zero-shot inference; no fine-tuning required.

    Loading
    -------
    Call ``load()`` once during service startup.
    The loaded model weights are cached in memory and reused for every
    forecast request — they are NOT re-downloaded per request.

    Context requirement
    -------------------
    The 90-30-ft-r2.1 revision requires exactly 90 days of history.
    If fewer than 90 data points are provided, ``predict()`` raises
    ``ValueError`` so the caller can fall back to the baseline model.

    Scaling
    -------
    The TTM model applies internal instance normalization.
    No external scaling is required — the model accepts raw demand values
    and returns predictions in the same scale.
    """

    MODEL_NAME = "Granite Time Series (IBM TTM)"
    MIN_HISTORY = GRANITE_CONTEXT_LENGTH  # 90 days

    def __init__(self) -> None:
        self._model = None
        self._load_error: str | None = None

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def is_available(self) -> bool:
        return self._model is not None

    @property
    def load_error(self) -> str | None:
        """Return the error message from the last failed load(), or None."""
        return self._load_error

    def load(self) -> bool:
        """
        Load the IBM Granite TTM R2.1 model from HuggingFace.

        Returns True only if the model loaded successfully.
        The loaded model is stored in ``self._model`` and reused across
        all subsequent prediction calls.

        Steps:
        1. Import TinyTimeMixerForPrediction from tsfm_public.
        2. Load the pretrained weights from HuggingFace (or local cache).
        3. Set the model to eval() mode.
        4. Verify a quick dummy forward pass succeeds.
        5. Return True on success, False on any error.

        Environment variables:
            GRANITE_MODEL_ID   — HuggingFace repo ID
            GRANITE_REVISION   — branch / revision tag
        """
        try:
            logger.info(
                "Loading Granite TTM: %s @ %s …",
                GRANITE_MODEL_ID,
                GRANITE_REVISION,
            )

            # Lazy import so the service starts even if tsfm_public is absent
            from tsfm_public.models.tinytimemixer import (  # type: ignore[import]
                TinyTimeMixerForPrediction,
            )
            import torch

            model = TinyTimeMixerForPrediction.from_pretrained(
                GRANITE_MODEL_ID,
                revision=GRANITE_REVISION,
            )
            model.eval()

            # Smoke test — one forward pass with dummy data
            dummy = torch.zeros(1, GRANITE_CONTEXT_LENGTH, 1, dtype=torch.float32)
            freq_tok = torch.tensor([[GRANITE_DAILY_FREQ_TOKEN]], dtype=torch.long)
            with torch.no_grad():
                out = model(past_values=dummy, freq_token=freq_tok)
            if not hasattr(out, "prediction_outputs"):
                raise RuntimeError(
                    "Model output missing 'prediction_outputs'. "
                    "API may have changed — check tsfm_public version."
                )

            self._model = model
            self._load_error = None
            logger.info(
                "Granite TTM loaded successfully. "
                "context_length=%d prediction_length=%d",
                GRANITE_CONTEXT_LENGTH,
                GRANITE_PREDICTION_LENGTH,
            )
            return True

        except ImportError as exc:
            msg = (
                f"tsfm_public is not installed or not importable: {exc}. "
                "See README for installation instructions."
            )
            logger.warning(msg)
            self._load_error = msg
            return False

        except Exception as exc:
            msg = f"Failed to load Granite TTM: {exc}"
            logger.warning(msg)
            self._load_error = msg
            return False

    def predict(self, history: list[dict], horizon: int) -> list[dict]:
        """
        Run Granite TTM inference on the provided history.

        Parameters
        ----------
        history : list[dict]
            Sorted list of ``{"date": str, "demand": float}`` dicts.
            Must contain at least ``MIN_HISTORY`` (90) data points.
        horizon : int
            Number of future days to forecast. Must be <= 30 (model's
            prediction_length); larger horizons fall back to the baseline.

        Returns
        -------
        list[dict]
            List of ``{"date": str, "predicted_demand": float}`` dicts.

        Raises
        ------
        RuntimeError
            If the model is not loaded.
        ValueError
            If history is too short (< MIN_HISTORY) or horizon > prediction_length.
        """
        if not self.is_available:
            raise RuntimeError(
                "Granite TTM model is not loaded. Call load() first."
            )

        if len(history) < self.MIN_HISTORY:
            raise ValueError(
                f"Granite TTM requires at least {self.MIN_HISTORY} days of history "
                f"(provided: {len(history)}). Use the baseline fallback for shorter series."
            )

        if horizon > GRANITE_PREDICTION_LENGTH:
            raise ValueError(
                f"Granite TTM revision '{GRANITE_REVISION}' supports a maximum horizon of "
                f"{GRANITE_PREDICTION_LENGTH} days (requested: {horizon})."
            )

        import torch  # already loaded at this point

        # Build the demand array from the most recent MIN_HISTORY points
        demands = np.array(
            [float(p["demand"]) for p in history[-self.MIN_HISTORY:]], dtype=np.float32
        )

        # Input tensor: [batch=1, context_length, channels=1]
        input_tensor = torch.tensor(demands, dtype=torch.float32).reshape(
            1, self.MIN_HISTORY, 1
        )
        freq_token = torch.tensor(
            [[GRANITE_DAILY_FREQ_TOKEN]], dtype=torch.long
        )

        with torch.no_grad():
            output = self._model(past_values=input_tensor, freq_token=freq_token)

        raw_predictions: np.ndarray = (
            output.prediction_outputs[0, :horizon, 0].cpu().numpy()
        )

        # Safety: clamp negatives to zero, replace any NaN/inf
        raw_predictions = np.where(
            np.isfinite(raw_predictions), raw_predictions, 0.0
        )
        raw_predictions = np.clip(raw_predictions, 0.0, None)

        # Generate forecast dates
        last_date = pd.to_datetime(history[-1]["date"])
        forecasts = []
        for i, pred_val in enumerate(raw_predictions, start=1):
            forecast_date = (last_date + timedelta(days=i)).date()
            forecasts.append(
                {
                    "date": str(forecast_date),
                    "predicted_demand": round(float(pred_val), 4),
                }
            )

        logger.info(
            "[Granite TTM] item forecast complete. horizon=%d first_pred=%.4f",
            horizon,
            float(raw_predictions[0]) if len(raw_predictions) > 0 else 0.0,
        )
        return forecasts


# ---------------------------------------------------------------------------
# Model registry — loaded once at module import time
# ---------------------------------------------------------------------------

_granite_model = GraniteForecastModel()
_granite_available = _granite_model.load()  # loads at startup; result cached

_baseline_model = BaselineMovingAverageModel(window=7)


def get_active_model() -> ForecastModel:
    """
    Return the best available forecasting model.

    Priority:
        1. Granite TTM (when loaded)
        2. Baseline Moving Average (always available as fallback)
    """
    if _granite_model.is_available:
        return _granite_model
    return _baseline_model


def get_model_status() -> dict:
    """
    Return the current model availability status for the /model/status endpoint.

    Returns
    -------
    dict
    """
    if _granite_model.is_available:
        return {
            "model": GraniteForecastModel.MODEL_NAME,
            "available": True,
            "revision": GRANITE_REVISION,
            "context_length": GRANITE_CONTEXT_LENGTH,
            "prediction_length": GRANITE_PREDICTION_LENGTH,
            "fallback_model": BaselineMovingAverageModel.LABEL,
            "fallback_available": True,
        }

    return {
        "model": GraniteForecastModel.MODEL_NAME,
        "available": False,
        "message": _granite_model.load_error or "Granite TTM is not loaded.",
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
    Validate inputs for a forecast request.

    Raises ValueError with a descriptive message on any failure.
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
    Generate a demand forecast for a single warehouse item.

    Model selection logic:
    1. If Granite TTM is loaded AND history >= 90 days AND horizon <= 30:
       → use Granite (real AI predictions)
    2. Otherwise → use Baseline Moving Average (clearly labelled)

    Parameters
    ----------
    item_id : str
    historical_data : list[dict]
        ``[{"date": str, "demand": float}, …]``
    horizon : int
        Days to forecast (default: 7).

    Returns
    -------
    dict
        ``{"item_id", "model", "horizon", "forecast": [{"date", "predicted_demand"}]}``
    """
    logger.info(
        "forecast_demand called — item_id='%s' horizon=%d history_len=%d",
        item_id,
        horizon,
        len(historical_data) if historical_data else 0,
    )

    validate_forecast_input(item_id, historical_data, horizon)

    # Sort history chronologically
    sorted_history = sorted(historical_data, key=lambda x: str(x["date"]))

    # Decide which model to use
    model = _select_model(sorted_history, horizon)

    forecast_points = model.predict(sorted_history, horizon)

    logger.info(
        "Forecast complete — item_id='%s' model='%s' points=%d",
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


def _select_model(sorted_history: list[dict], horizon: int) -> ForecastModel:
    """
    Select the best available model for the given history and horizon.

    Granite TTM is used when:
    - It is loaded and available.
    - History has >= GRANITE_CONTEXT_LENGTH (90) data points.
    - Requested horizon <= GRANITE_PREDICTION_LENGTH (30).

    Otherwise the baseline moving-average model is used.
    """
    if _granite_model.is_available:
        if len(sorted_history) < GraniteForecastModel.MIN_HISTORY:
            logger.info(
                "Granite available but history too short (%d < %d). "
                "Falling back to %s.",
                len(sorted_history),
                GraniteForecastModel.MIN_HISTORY,
                BaselineMovingAverageModel.LABEL,
            )
        elif horizon > GRANITE_PREDICTION_LENGTH:
            logger.info(
                "Granite available but horizon=%d exceeds model max=%d. "
                "Falling back to %s.",
                horizon,
                GRANITE_PREDICTION_LENGTH,
                BaselineMovingAverageModel.LABEL,
            )
        else:
            return _granite_model

    return _baseline_model


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
    """Build the standard forecast response dict."""
    return {
        "item_id": item_id,
        "model": model_name,
        "horizon": horizon,
        "forecast": forecast_points,
    }
