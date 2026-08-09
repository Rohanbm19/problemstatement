"""
app.py
------
TwinStock AI ML Service – FastAPI entry point.

Run with:
    python -m uvicorn app:app --reload --port 8001

Swagger UI:
    http://127.0.0.1:8001/docs

Architecture notes:
-------------------
- This service is a SEPARATE MICROSERVICE from the backend (port 8000).
- It does NOT query PostgreSQL directly.
- It does NOT duplicate backend inventory, stockout, or replenishment logic.
- The backend sends historical demand data → this service returns forecasts.
- Business decisions (stockout / reorder) remain in the backend.

Flow:
    Backend → POST /forecast → ML Service → forecast response → Backend
"""

import logging
from contextlib import asynccontextmanager
from datetime import date as date_type
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from src.forecast import (
    forecast_demand,
    forecast_available,
    get_model_status,
    validate_forecast_input,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ml-service")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Log service startup information."""
    status = get_model_status()
    logger.info("===== TwinStock AI ML Service starting on port 8001 =====")
    logger.info("Primary model : %s", status["model"])
    logger.info("Model available: %s", status["available"])
    if status["available"]:
        logger.info(
            "Granite revision: %s  context=%s  prediction=%s",
            status.get("revision"),
            status.get("context_length"),
            status.get("prediction_length"),
        )
    else:
        logger.info("Granite load message: %s", status.get("message"))
        logger.info(
            "Fallback model : %s (available=%s)",
            status.get("fallback_model"),
            status.get("fallback_available"),
        )
    yield


app = FastAPI(
    title="TwinStock AI ML Service",
    description=(
        "Demand forecasting microservice for the TwinStock AI warehouse system. "
        "Accepts historical demand data from the backend and returns demand forecasts. "
        "Powered by IBM Granite Time Series TTM R2.1 (ibm-granite/granite-timeseries-ttm-r2)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8000",   # backend
    "http://127.0.0.1:8000",  # backend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class DemandPoint(BaseModel):
    """A single historical demand observation."""

    date: date_type = Field(..., description="Date of the demand observation (YYYY-MM-DD)")
    demand: float = Field(..., description="Observed demand quantity (must be >= 0)")

    @field_validator("demand")
    @classmethod
    def demand_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"demand must be >= 0, got {v}")
        return v


class ForecastRequest(BaseModel):
    """Request body for POST /forecast and POST /predict."""

    item_id: str = Field(..., description="Warehouse item identifier (e.g. ITM10025)")
    horizon: int = Field(
        default=7,
        ge=1,
        description="Number of future days to forecast (minimum: 1)",
    )
    history: list[DemandPoint] = Field(
        ...,
        description="Historical demand observations sorted by date (ascending)",
    )

    @field_validator("item_id")
    @classmethod
    def item_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("item_id cannot be empty or whitespace.")
        return v.strip()

    @model_validator(mode="after")
    def history_not_empty(self) -> "ForecastRequest":
        if not self.history:
            raise ValueError("history cannot be empty.")
        return self


class ForecastPoint(BaseModel):
    """A single forecast output point."""

    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    predicted_demand: float = Field(..., description="Forecasted demand quantity")


class ForecastResponse(BaseModel):
    """Response body for forecast endpoints."""

    item_id: str
    model: Optional[str]
    horizon: int
    forecast: list[ForecastPoint]


class ModelStatusResponse(BaseModel):
    """Response body for GET /model/status."""

    model: str
    available: bool
    message: Optional[str] = None
    revision: Optional[str] = None
    context_length: Optional[int] = None
    prediction_length: Optional[int] = None
    fallback_model: Optional[str] = None
    fallback_available: Optional[bool] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get(
    "/",
    summary="Service root",
    tags=["General"],
)
def root():
    """Return basic service information."""
    return {
        "service": "TwinStock AI ML Service",
        "status": "running",
        "purpose": "Warehouse demand forecasting",
        "docs": "http://127.0.0.1:8001/docs",
        "backend": "http://127.0.0.1:8000",
    }


@app.get(
    "/health",
    summary="Health check",
    tags=["General"],
)
def health_check():
    """Return service health status. Does NOT require a database connection."""
    return {"status": "healthy"}


@app.get(
    "/model/status",
    response_model=ModelStatusResponse,
    summary="Forecasting model status",
    tags=["Model"],
)
def model_status():
    """
    Return whether the IBM Granite Time Series model is available.

    - ``available: false`` means Granite TTM is not yet loaded.
      A baseline (moving average) fallback model will be used instead.
    - ``available: true`` means Granite is loaded and active.
    """
    status = get_model_status()
    logger.info("GET /model/status — available=%s", status["available"])
    return status


@app.post(
    "/forecast",
    response_model=ForecastResponse,
    summary="Generate demand forecast",
    tags=["Forecasting"],
)
def post_forecast(request: ForecastRequest):
    """
    Generate a demand forecast for a single warehouse item.

    **Request body:**
    - ``item_id``: warehouse item identifier
    - ``horizon``: number of future days to forecast (default: 7)
    - ``history``: list of ``{date, demand}`` historical observations

    **Response:**
    - When a model is available: returns ``{item_id, model, horizon, forecast[]}``
    - The current active model is shown in the ``model`` field.
    - If only the baseline is available the model name will be
      ``"Baseline (Moving Average)"`` — NOT Granite.

    **Backend integration example:**
    ```json
    POST http://127.0.0.1:8001/forecast
    {
        "item_id": "ITM10025",
        "horizon": 7,
        "history": [
            {"date": "2026-07-01", "demand": 12},
            {"date": "2026-07-02", "demand": 15}
        ]
    }
    ```
    """
    history_as_dicts = [
        {"date": str(point.date), "demand": point.demand}
        for point in request.history
    ]

    logger.info(
        "POST /forecast — item_id='%s' horizon=%d history_len=%d",
        request.item_id,
        request.horizon,
        len(history_as_dicts),
    )

    try:
        result = forecast_demand(
            item_id=request.item_id,
            historical_data=history_as_dicts,
            horizon=request.horizon,
        )
    except ValueError as exc:
        logger.warning("Forecast validation error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Unexpected forecast error: %s", str(exc))
        raise HTTPException(status_code=500, detail="Internal ML service error.")

    return result


@app.post(
    "/forecast/{item_id}",
    response_model=ForecastResponse,
    summary="Generate demand forecast for a specific item (path param)",
    tags=["Forecasting"],
)
def post_forecast_item(item_id: str, request: ForecastRequest):
    """
    Generate a demand forecast with item_id supplied as a path parameter.

    The ``item_id`` in the path takes precedence over the one in the body.
    This endpoint is intended for direct backend integration:

    ```
    POST /forecast/ITM10025
    ```

    The backend provides historical demand in the request body.
    The ML service does NOT query PostgreSQL.
    """
    history_as_dicts = [
        {"date": str(point.date), "demand": point.demand}
        for point in request.history
    ]

    logger.info(
        "POST /forecast/%s — horizon=%d history_len=%d",
        item_id,
        request.horizon,
        len(history_as_dicts),
    )

    try:
        result = forecast_demand(
            item_id=item_id,
            historical_data=history_as_dicts,
            horizon=request.horizon,
        )
    except ValueError as exc:
        logger.warning("Forecast validation error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Unexpected forecast error: %s", str(exc))
        raise HTTPException(status_code=500, detail="Internal ML service error.")

    return result


@app.post(
    "/predict",
    response_model=ForecastResponse,
    summary="Generic ML prediction endpoint",
    tags=["Forecasting"],
)
def predict(request: ForecastRequest):
    """
    Generic ML prediction endpoint.

    Internally routes to the demand forecasting pipeline.
    Use ``POST /forecast`` for more explicit semantics; this endpoint
    exists for backend convenience.

    Request/response format is identical to ``POST /forecast``.
    """
    history_as_dicts = [
        {"date": str(point.date), "demand": point.demand}
        for point in request.history
    ]

    logger.info(
        "POST /predict — item_id='%s' horizon=%d history_len=%d",
        request.item_id,
        request.horizon,
        len(history_as_dicts),
    )

    try:
        result = forecast_demand(
            item_id=request.item_id,
            historical_data=history_as_dicts,
            horizon=request.horizon,
        )
    except ValueError as exc:
        logger.warning("Predict validation error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Unexpected predict error: %s", str(exc))
        raise HTTPException(status_code=500, detail="Internal ML service error.")

    return result
