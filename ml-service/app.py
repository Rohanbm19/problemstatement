import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.forecast import (
    GraniteForecastModel,
    forecast_demand,
    CONTEXT_LENGTH,
    PREDICTION_LENGTH,
    DEMO_MIN_HISTORY,
    GRANITE_REVISION,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s [%(levelname)s] "
        "%(name)s - %(message)s"
    ),
)

logger = logging.getLogger("ml-service")


# ============================================================
# GLOBAL GRANITE MODEL
# ============================================================

granite_model = GraniteForecastModel()


# ============================================================
# STARTUP / SHUTDOWN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info(
        "===== TwinStock AI ML Service starting on port 8001 ====="
    )

    logger.info(
        "Primary model : Granite Time Series (IBM TTM)"
    )

    # --------------------------------------------------------
    # Load Granite
    # --------------------------------------------------------

    available = granite_model.load()

    logger.info(
        "Model available: %s",
        available
    )

    logger.info(
        "DEBUG Granite object: %s",
        granite_model
    )

    logger.info(
        "DEBUG granite_model.available = %s",
        granite_model.available
    )

    # --------------------------------------------------------
    # Model status
    # --------------------------------------------------------

    if available:

        logger.info(
            "Granite revision: %s "
            "context=%s "
            "prediction=%s "
            "demo_min_history=%s",
            GRANITE_REVISION,
            CONTEXT_LENGTH,
            PREDICTION_LENGTH,
            DEMO_MIN_HISTORY,
        )

    else:

        logger.warning(
            "Granite unavailable. "
            "Baseline Moving Average will be used."
        )

    logger.info(
        "Fallback model : Baseline (Moving Average)"
    )

    yield

    logger.info(
        "===== TwinStock AI ML Service shutting down ====="
    )


# ============================================================
# FASTAPI
# ============================================================

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="TwinStock AI ML Service",
    description=(
        "Demand forecasting service "
        "using IBM Granite TTM"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class HistoryPoint(BaseModel):

    date: str

    demand: float


class ForecastRequest(BaseModel):

    item_id: str

    horizon: int = Field(
        default=7,
        gt=0,
        le=30
    )

    history: List[HistoryPoint]


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "service": "TwinStock AI ML Service",
        "status": "running",
        "primary_model": (
            "Granite Time Series "
            "(IBM TTM)"
        ),
        "granite_available": (
            granite_model.available
        ),
        "fallback_model": (
            "Baseline (Moving Average)"
        ),
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "granite_available": (
            granite_model.available
        ),
        "fallback_available": True,
    }


# ============================================================
# MODEL STATUS
# ============================================================

@app.get("/model/status")
async def model_status():

    if granite_model.available:

        return {
            "model": (
                "Granite Time Series "
                "(IBM TTM)"
            ),
            "available": True,
            "revision": GRANITE_REVISION,
            "context_length": CONTEXT_LENGTH,
            "prediction_length": PREDICTION_LENGTH,
            "demo_min_history": (
                DEMO_MIN_HISTORY
            ),
            "fallback_model": (
                "Baseline (Moving Average)"
            ),
            "fallback_available": True,
        }

    return {
        "model": (
            "Granite Time Series "
            "(IBM TTM)"
        ),
        "available": False,
        "message": (
            "Granite TTM could not be loaded."
        ),
        "fallback_model": (
            "Baseline (Moving Average)"
        ),
        "fallback_available": True,
    }


# ============================================================
# MAIN FORECAST ENDPOINT
# ============================================================

@app.post("/forecast")
async def forecast(
    request: ForecastRequest
):

    try:

        history = [
            {
                "date": point.date,
                "demand": point.demand,
            }
            for point in request.history
        ]

        result = forecast_demand(
            item_id=request.item_id,
            history=history,
            horizon=request.horizon,
            granite_model=granite_model,
        )

        return result

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except RuntimeError as exc:

        logger.exception(
            "Forecast runtime error: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail=f"Forecast failed: {exc}"
        ) from exc

    except Exception as exc:

        logger.exception(
            "Forecast request failed: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail=f"Forecast failed: {exc}"
        ) from exc


# ============================================================
# FORECAST BY ITEM ID
# ============================================================

@app.post("/forecast/{item_id}")
async def forecast_by_item_id(
    item_id: str,
    request: ForecastRequest,
):

    try:

        history = [
            {
                "date": point.date,
                "demand": point.demand,
            }
            for point in request.history
        ]

        result = forecast_demand(
            item_id=item_id,
            history=history,
            horizon=request.horizon,
            granite_model=granite_model,
        )

        return result

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except RuntimeError as exc:

        logger.exception(
            "Forecast runtime error: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail=f"Forecast failed: {exc}"
        ) from exc

    except Exception as exc:

        logger.exception(
            "Forecast request failed: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail=f"Forecast failed: {exc}"
        ) from exc


# ============================================================
# GENERIC PREDICT ENDPOINT
# ============================================================

@app.post("/predict")
async def predict(
    request: ForecastRequest
):

    return await forecast(request)