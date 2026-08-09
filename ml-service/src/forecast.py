
import os
import logging
from datetime import timedelta
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

GRANITE_MODEL_ID = os.getenv(
    "GRANITE_MODEL_ID",
    "ibm-granite/granite-timeseries-ttm-r2"
)

GRANITE_REVISION = os.getenv(
    "GRANITE_REVISION",
    "90-30-ft-r2.1"
)

CONTEXT_LENGTH = int(
    os.getenv("GRANITE_CONTEXT_LENGTH", "90")
)

PREDICTION_LENGTH = int(
    os.getenv("GRANITE_PREDICTION_LENGTH", "30")
)

# Demo mode:
# Real model context is 90 observations.
# For your demo, allow 7 observations and pad to 90.
DEMO_MIN_HISTORY = int(
    os.getenv("DEMO_MIN_HISTORY", "7")
)


# ============================================================
# GRANITE MODEL
# ============================================================

class GraniteForecastModel:

    def __init__(self):
        self.model = None
        self.available = False

        self.context_length = CONTEXT_LENGTH
        self.prediction_length = PREDICTION_LENGTH

    # --------------------------------------------------------
    # LOAD GRANITE
    # --------------------------------------------------------

    def load(self) -> bool:

        try:

            logger.info(
                "Loading Granite TTM: %s revision=%s",
                GRANITE_MODEL_ID,
                GRANITE_REVISION
            )

            from tsfm_public import (
                TinyTimeMixerForPrediction
            )

            self.model = (
                TinyTimeMixerForPrediction.from_pretrained(
                    GRANITE_MODEL_ID,
                    revision=GRANITE_REVISION
                )
            )

            self.available = True

            logger.info(
                "Granite TTM loaded successfully. "
                "context_length=%s "
                "prediction_length=%s "
                "demo_min_history=%s",
                self.context_length,
                self.prediction_length,
                DEMO_MIN_HISTORY
            )

            return True

        except Exception as exc:

            self.available = False
            self.model = None

            logger.exception(
                "Failed to load Granite TTM: %s",
                exc
            )

            return False


# ============================================================
# BASELINE FALLBACK
# ============================================================

def baseline_forecast(
    history: List[Dict[str, Any]],
    horizon: int
) -> List[Dict[str, Any]]:

    if not history:
        raise ValueError(
            "History cannot be empty"
        )

    values = []

    for row in history:

        try:

            value = float(row["demand"])

            if not np.isfinite(value):
                value = 0.0

            values.append(
                max(0.0, value)
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ):
            continue

    if not values:
        raise ValueError(
            "No valid demand values found in history"
        )

    # Last 7 observations
    window = min(
        7,
        len(values)
    )

    moving_average = (
        sum(values[-window:]) / window
    )

    last_date = pd.to_datetime(
        history[-1]["date"]
    ).date()

    forecast = []

    for i in range(
        1,
        horizon + 1
    ):

        forecast_date = (
            last_date +
            timedelta(days=i)
        )

        forecast.append({
            "date": forecast_date.isoformat(),
            "predicted_demand": round(
                moving_average,
                2
            )
        })

    return forecast


# ============================================================
# GRANITE FORECAST
# ============================================================

def granite_forecast(
    model: GraniteForecastModel,
    history: List[Dict[str, Any]],
    horizon: int
) -> List[Dict[str, Any]]:

    if not model.available:
        raise RuntimeError(
            "Granite model is not loaded"
        )

    if len(history) < DEMO_MIN_HISTORY:
        raise ValueError(
            f"Granite requires at least "
            f"{DEMO_MIN_HISTORY} history points "
            f"in demo mode."
        )

    try:

        import torch

        # ----------------------------------------------------
        # Prepare dataframe
        # ----------------------------------------------------

        df = pd.DataFrame(history)

        if "date" not in df.columns:
            raise ValueError(
                "History must contain date"
            )

        if "demand" not in df.columns:
            raise ValueError(
                "History must contain demand"
            )

        df["date"] = pd.to_datetime(
            df["date"]
        )

        df["demand"] = pd.to_numeric(
            df["demand"],
            errors="coerce"
        ).fillna(0.0)

        df = (
            df
            .sort_values("date")
            .drop_duplicates(
                subset=["date"],
                keep="last"
            )
            .reset_index(drop=True)
        )

        values = (
            df["demand"]
            .astype(float)
            .clip(lower=0)
            .to_numpy(
                dtype=np.float32
            )
        )

        if len(values) < DEMO_MIN_HISTORY:
            raise ValueError(
                f"Need at least "
                f"{DEMO_MIN_HISTORY} valid demand "
                f"observations."
            )

        # ----------------------------------------------------
        # Pad demo history to Granite's 90-point context
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # This is only for your demo.
        #
        # A real production implementation should provide
        # 90 genuine historical observations.
        # ----------------------------------------------------

        if len(values) < CONTEXT_LENGTH:

            padding_count = (
                CONTEXT_LENGTH -
                len(values)
            )

            # Repeat the first observation.
            padding_value = float(
                values[0]
            )

            padding = np.full(
                padding_count,
                padding_value,
                dtype=np.float32
            )

            values = np.concatenate(
                [padding, values]
            )

        else:

            values = values[
                -CONTEXT_LENGTH:
            ]

        # ----------------------------------------------------
        # Shape
        # ----------------------------------------------------
        #
        # Granite expects:
        #
        # [batch, context_length, channels]
        #
        # Example:
        #
        # [1, 90, 1]
        # ----------------------------------------------------

        past_values = torch.tensor(
            values,
            dtype=torch.float32
        ).reshape(
            1,
            CONTEXT_LENGTH,
            1
        )

        # ----------------------------------------------------
        # Frequency token
        # ----------------------------------------------------
        #
        # Your model is:
        #
        # 90-30-ft-r2.1
        #
        # "ft" means frequency prefix tuning.
        #
        # For daily data we use the daily frequency token.
        #
        # The TTM frequency vocabulary uses:
        #
        # 0 = minute
        # 1 = hour
        # 2 = day
        # 3 = week
        #
        # For this project the history is DAILY.
        # ----------------------------------------------------

        freq_token = torch.tensor(
            [2],
            dtype=torch.long
        )

        # ----------------------------------------------------
        # Move tensors to same device as model
        # ----------------------------------------------------

        try:

            device = next(
                model.model.parameters()
            ).device

            past_values = (
                past_values.to(device)
            )

            freq_token = (
                freq_token.to(device)
            )

        except (
            StopIteration,
            AttributeError
        ):

            # CPU fallback
            pass

        # ----------------------------------------------------
        # Granite inference
        # ----------------------------------------------------

        logger.info(
            "Running Granite inference: "
            "context=%s horizon=%s freq_token=%s",
            CONTEXT_LENGTH,
            horizon,
            2
        )

        with torch.no_grad():

            outputs = model.model(
                past_values=past_values,
                freq_token=freq_token
            )

        # ----------------------------------------------------
        # Extract predictions
        # ----------------------------------------------------

        prediction = None

        if hasattr(
            outputs,
            "prediction_outputs"
        ):

            prediction = (
                outputs.prediction_outputs
            )

        elif hasattr(
            outputs,
            "prediction"
        ):

            prediction = (
                outputs.prediction
            )

        elif hasattr(
            outputs,
            "predictions"
        ):

            prediction = (
                outputs.predictions
            )

        elif isinstance(
            outputs,
            tuple
        ):

            prediction = outputs[0]

        elif isinstance(
            outputs,
            dict
        ):

            if "prediction_outputs" in outputs:

                prediction = (
                    outputs[
                        "prediction_outputs"
                    ]
                )

            elif "prediction" in outputs:

                prediction = (
                    outputs[
                        "prediction"
                    ]
                )

            elif "predictions" in outputs:

                prediction = (
                    outputs[
                        "predictions"
                    ]
                )

        if prediction is None:

            raise RuntimeError(
                "Unable to extract predictions "
                "from Granite output."
            )

        # ----------------------------------------------------
        # Convert tensor → numpy
        # ----------------------------------------------------

        if hasattr(
            prediction,
            "detach"
        ):

            prediction = (
                prediction
                .detach()
                .cpu()
                .numpy()
            )

        prediction = np.asarray(
            prediction
        )

        logger.info(
            "Raw Granite prediction shape: %s",
            prediction.shape
        )

        prediction = (
            prediction
            .reshape(-1)
        )

        # ----------------------------------------------------
        # Check prediction length
        # ----------------------------------------------------

        if len(prediction) < horizon:

            raise RuntimeError(
                "Granite returned fewer "
                f"predictions than requested: "
                f"{len(prediction)} < {horizon}"
            )

        prediction = prediction[
            :horizon
        ]

        # ----------------------------------------------------
        # Build forecast response
        # ----------------------------------------------------

        last_date = (
            df["date"]
            .iloc[-1]
            .date()
        )

        forecast = []

        for i, value in enumerate(
            prediction,
            start=1
        ):

            forecast_date = (
                last_date +
                timedelta(days=i)
            )

            try:

                predicted_value = float(
                    value
                )

            except (
                TypeError,
                ValueError
            ):

                predicted_value = 0.0

            if not np.isfinite(
                predicted_value
            ):

                predicted_value = 0.0

            predicted_value = max(
                0.0,
                predicted_value
            )

            forecast.append({
                "date": (
                    forecast_date
                    .isoformat()
                ),
                "predicted_demand": round(
                    predicted_value,
                    2
                )
            })

        logger.info(
            "Granite forecast generated successfully "
            "for %s days.",
            len(forecast)
        )

        return forecast

    except Exception as exc:

        logger.exception(
            "Granite prediction failed: %s",
            exc
        )

        raise RuntimeError(
            f"Granite model inference failed: {exc}"
        ) from exc


# ============================================================
# MAIN FORECAST FUNCTION
# ============================================================

def forecast_demand(
    item_id: str,
    history: List[Dict[str, Any]],
    horizon: int,
    granite_model: Optional[
        GraniteForecastModel
    ] = None
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if not item_id:
        raise ValueError(
            "item_id is required"
        )

    if not history:
        raise ValueError(
            "history is required"
        )

    if horizon <= 0:
        raise ValueError(
            "horizon must be greater than 0"
        )

    if horizon > 30:
        raise ValueError(
            "horizon cannot be greater than 30"
        )

    # --------------------------------------------------------
    # Granite
    # --------------------------------------------------------

    if (
        granite_model is not None
        and granite_model.available
        and len(history) >= DEMO_MIN_HISTORY
    ):

        logger.info(
            "Using Granite TTM for "
            "item=%s history=%s horizon=%s",
            item_id,
            len(history),
            horizon
        )

        try:

            forecast = granite_forecast(
                granite_model,
                history,
                horizon
            )

            return {
                "item_id": item_id,
                "model": (
                    "Granite Time Series "
                    "(IBM TTM)"
                ),
                "horizon": horizon,
                "forecast": forecast
            }

        except Exception as exc:

            logger.exception(
                "GRANITE PREDICTION FAILED "
                "for %s: %s",
                item_id,
                exc
            )

            # IMPORTANT:
            # Do NOT silently return baseline here.
            #
            # During your demo/testing we want to know
            # whether Granite actually worked.
            raise RuntimeError(
                f"Granite prediction failed: {exc}"
            ) from exc

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------

    logger.info(
        "Using Baseline Moving Average for "
        "item=%s history=%s granite_available=%s",
        item_id,
        len(history),
        (
            granite_model.available
            if granite_model is not None
            else False
        )
    )

    forecast = baseline_forecast(
        history,
        horizon
    )

    return {
        "item_id": item_id,
        "model": (
            "Baseline (Moving Average)"
        ),
        "horizon": horizon,
        "forecast": forecast
    }

