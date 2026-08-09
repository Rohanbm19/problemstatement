# TwinStock AI — ML Service

## 1. Purpose

The ML service is a **separate forecasting microservice** for the TwinStock AI warehouse system.

It receives historical demand data from the backend and returns demand forecasts.

It does **not** manage inventory, calculate stockout risk, or generate replenishment orders.
Those responsibilities remain in the backend.

---

## 2. Architecture

```
PostgreSQL
    ↓
Backend FastAPI (port 8000)
    ↓  POST /forecast  →  ML Service (port 8001)
                              ↓
                     IBM Granite Time Series (STAGE 5)
                              ↓
                       Demand Forecast
    ↓  ←  forecast response
Backend
    ↓
Stockout / Replenishment Logic
    ↓
Manager Dashboard (Frontend)
```

**Key separation:**

| Responsibility               | Service       |
|------------------------------|---------------|
| PostgreSQL / inventory data  | Backend       |
| Stockout risk calculation    | Backend       |
| Replenishment orders         | Backend       |
| Demand forecasting           | **ML Service**|
| Granite TTM inference        | **ML Service**|
| Forecast evaluation (MAE…)   | **ML Service**|

---

## 3. Folder Structure

```
ml-service/
│
├── data/
│   └── warehouse_raw.csv       ← inventory snapshot (for dev/experimentation only)
│
├── notebooks/
│   └── granite_test.ipynb      ← Granite TTM experimentation notebook
│
├── src/
│   ├── __init__.py
│   ├── data_cleaning.py        ← dataset validation & cleaning utilities
│   ├── preprocessing.py        ← time-series preparation pipeline
│   ├── forecast.py             ← main ML module (ForecastModel, GraniteForecastModel)
│   ├── evaluation.py           ← MAE, RMSE, MAPE, chronological split
│   ├── recommendation.py       ← kept for reference (backend handles replenishment)
│   └── stockout.py             ← kept for reference (backend handles stockout)
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py             ← FastAPI endpoint tests
│   ├── test_preprocessing.py   ← preprocessing pipeline tests
│   └── test_forecast.py        ← forecast & evaluation tests
│
├── app.py                      ← FastAPI entry point
├── README.md
└── requirements.txt
```

---

## 4. ML Service Responsibilities

- Accept historical demand data sent by the backend
- Validate and preprocess time-series data
- Generate demand forecasts using IBM Granite TTM (STAGE 5)
- Return structured forecast responses
- Evaluate forecast quality (MAE, RMSE, MAPE)
- Expose a clean REST API for backend integration

---

## 5. Backend Responsibilities (NOT in this service)

- PostgreSQL database management
- Inventory CRUD operations
- Stockout risk calculation (`backend/app/services/stockout.py`)
- Replenishment order logic (`backend/app/services/replenishment.py`)
- Final business decisions

---

## 6. API Endpoints

| Method | Endpoint           | Description                               |
|--------|--------------------|-------------------------------------------|
| GET    | `/`                | Service info                              |
| GET    | `/health`          | Health check                              |
| GET    | `/model/status`    | Granite model availability                |
| POST   | `/forecast`        | **Main forecast endpoint**                |
| POST   | `/forecast/{id}`   | Forecast with item_id as path parameter   |
| POST   | `/predict`         | Generic ML prediction (routes to forecast)|

---

## 7. Request Examples

### POST /forecast

```json
POST http://127.0.0.1:8001/forecast
Content-Type: application/json

{
    "item_id": "ITM10025",
    "horizon": 7,
    "history": [
        {"date": "2026-07-01", "demand": 12},
        {"date": "2026-07-02", "demand": 15},
        {"date": "2026-07-03", "demand": 11},
        {"date": "2026-07-04", "demand": 18},
        {"date": "2026-07-05", "demand": 14},
        {"date": "2026-07-06", "demand": 16},
        {"date": "2026-07-07", "demand": 13}
    ]
}
```

---

## 8. Response Examples

### Baseline model active (STAGE 1–4)

```json
{
    "item_id": "ITM10025",
    "model": "Baseline (Moving Average)",
    "horizon": 7,
    "forecast": [
        {"date": "2026-07-08", "predicted_demand": 14.14},
        {"date": "2026-07-09", "predicted_demand": 14.14},
        {"date": "2026-07-10", "predicted_demand": 14.14},
        {"date": "2026-07-11", "predicted_demand": 14.14},
        {"date": "2026-07-12", "predicted_demand": 14.14},
        {"date": "2026-07-13", "predicted_demand": 14.14},
        {"date": "2026-07-14", "predicted_demand": 14.14}
    ]
}
```

### Granite model active (STAGE 5)

```json
{
    "item_id": "ITM10025",
    "model": "Granite Time Series (IBM TTM)",
    "horizon": 7,
    "forecast": [
        {"date": "2026-07-08", "predicted_demand": 16.3},
        {"date": "2026-07-09", "predicted_demand": 17.1},
        ...
    ]
}
```

### GET /model/status (before Granite)

```json
{
    "model": "Granite Time Series (IBM TTM)",
    "available": false,
    "message": "Granite TTM model is not loaded yet. ...",
    "fallback_model": "Baseline (Moving Average)",
    "fallback_available": true
}
```

---

## 9. Running Instructions

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start the ML service

```bash
python -m uvicorn app:app --reload --port 8001
```

### Access Swagger UI

```
http://127.0.0.1:8001/docs
```

### Run tests

```bash
python -m pytest tests/ -v
```

---

## 10. Granite Integration (STAGE 5)

IBM Granite TTM is a pretrained time-series foundation model.

**To integrate in STAGE 5:**

1. Install the IBM TSFM package:

```bash
pip install ibm-granite-tsfm torch transformers
```

2. Implement `GraniteForecastModel.load()` in [`src/forecast.py`](src/forecast.py):

```python
from tsfm_public.models.tinytimemixer import TinyTimeMixerForPrediction
from tsfm_public import TimeSeriesForecastingPipeline

model_path = "ibm/TTM"  # or a local checkpoint path

self._model = TinyTimeMixerForPrediction.from_pretrained(model_path)
self._pipeline = TimeSeriesForecastingPipeline(
    model=self._model,
    timestamp_column="date",
    target_columns=["demand"],
    freq="D",
)
return True
```

3. Implement `GraniteForecastModel.predict()` to call `self._pipeline`.

4. Restart the ML service — `/model/status` will return `"available": true`.

---

## 11. Historical Data Format

The ML service expects demand history in this format:

```
date,item_id,demand
2026-01-01,ITM10025,12
2026-01-02,ITM10025,15
2026-01-03,ITM10025,11
```

**Important:** The existing `data/warehouse_raw.csv` contains an **inventory snapshot**, not historical time-series demand. It cannot be used directly for demand forecasting.

---

## 12. Limitations

| Limitation                             | Status                          |
|----------------------------------------|---------------------------------|
| Granite TTM not yet loaded             | STAGE 1 — baseline fallback active |
| No PostgreSQL connection               | By design — backend is the source of truth |
| No historical demand CSV available     | Backend must supply history via API |
| Baseline model is statistical, not AI  | Clearly labelled in all responses |

---

## 13. Backend Integration

The backend should call the ML service like this (Python `httpx` or `requests`):

```python
import httpx

ML_SERVICE_URL = "http://127.0.0.1:8001"

def get_demand_forecast(item_id: str, history: list[dict], horizon: int = 7):
    response = httpx.post(
        f"{ML_SERVICE_URL}/forecast",
        json={
            "item_id": item_id,
            "horizon": horizon,
            "history": history,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()
```

The backend then uses the returned `forecast` list in its stockout/replenishment logic:

```python
forecast_data = get_demand_forecast("ITM10025", history, horizon=7)
total_forecast_demand = sum(p["predicted_demand"] for p in forecast_data["forecast"])

# Pass forecast demand into backend stockout/replenishment logic
risk = calculate_stockout_risk_with_forecast(item, total_forecast_demand)
```

---

## 14. Forecast Evaluation (STAGE 6)

The `src/evaluation.py` module provides:

- `calculate_mae(actual, predicted)` — Mean Absolute Error
- `calculate_rmse(actual, predicted)` — Root Mean Squared Error
- `calculate_mape(actual, predicted)` — Mean Absolute Percentage Error
- `chronological_train_test_split(history, test_ratio=0.3)` — time-correct split
- `evaluate_forecast(actual, predicted)` — full evaluation dict

These will be used in STAGE 6 to compare the baseline model vs Granite TTM.

---

## Ports

| Service     | URL                         |
|-------------|-----------------------------|
| Backend     | http://127.0.0.1:8000       |
| ML Service  | http://127.0.0.1:8001       |
| Swagger     | http://127.0.0.1:8001/docs  |
