# TwinStock AI — ML Service

## 1. Purpose

The ML service is a **separate forecasting microservice** for the TwinStock AI warehouse system.

It receives historical demand data from the backend and returns real demand forecasts powered by **IBM Granite Time Series TTM R2.1**.

It does **not** manage inventory, calculate stockout risk, or generate replenishment orders — those remain in the backend.

---

## 2. Architecture

```
PostgreSQL
    ↓
Backend FastAPI (port 8000)
    ↓  POST /forecast  →  ML Service (port 8001)
                              ↓
                    IBM Granite TTM R2.1
                    (ibm-granite/granite-timeseries-ttm-r2)
                              ↓
                    Zero-shot Demand Forecast
    ↓  ←  forecast response
Backend
    ↓
Stockout / Replenishment Logic
    ↓
Manager Dashboard
```

**Separation of concerns:**

| Responsibility               | Service        |
|------------------------------|----------------|
| PostgreSQL / inventory data  | Backend        |
| Stockout risk calculation    | Backend        |
| Replenishment orders         | Backend        |
| Business decisions           | Backend        |
| Demand forecasting           | **ML Service** |
| IBM Granite TTM inference    | **ML Service** |
| Forecast evaluation          | **ML Service** |

---

## 3. Folder Structure

```
ml-service/
│
├── data/
│   └── warehouse_raw.csv       ← inventory snapshot only (NOT time-series demand)
│
├── notebooks/
│   └── granite_test.ipynb      ← Granite TTM experimentation notebook
│
├── src/
│   ├── __init__.py
│   ├── data_cleaning.py        ← dataset validation & cleaning utilities
│   ├── preprocessing.py        ← time-series preparation pipeline
│   ├── forecast.py             ← ForecastModel, GraniteForecastModel, BaselineModel
│   ├── evaluation.py           ← MAE, RMSE, MAPE, chronological split
│   ├── recommendation.py       ← kept for reference (backend handles replenishment)
│   └── stockout.py             ← kept for reference (backend handles stockout)
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_preprocessing.py
│   └── test_forecast.py
│
├── app.py                      ← FastAPI entry point
├── README.md
└── requirements.txt
```

---

## 4. Granite TTM Model Details

| Property | Value |
|---|---|
| HuggingFace repo | `ibm-granite/granite-timeseries-ttm-r2` |
| Revision | `90-30-ft-r2.1` |
| Context length | **90 days** (minimum history required) |
| Max forecast horizon | **30 days** |
| Frequency | Daily (`freq_token=1`) |
| Fine-tuning | Not required — zero-shot |
| Scaling | Internal instance normalization — no preprocessing needed |
| Model size | ~3 MB (cached by HuggingFace after first download) |

---

## 5. Installation

### Windows

```bat
py -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
```

### Install base dependencies

```bash
python -m pip install fastapi uvicorn pandas numpy pydantic httpx pytest
python -m pip install torch transformers datasets accelerate scikit-learn scipy
```

### Install tsfm_public (IBM Granite TSFM source)

> **Note:** The PyPI `granite-tsfm` package (version 0.0.0) is a placeholder.
> The real `tsfm_public` library must be installed from the GitHub source.

**Python 3.11 / 3.12 / 3.13:**
```bash
pip install "git+https://github.com/ibm-granite/granite-tsfm.git"
```

**Python 3.14 (current environment):**
The granite-tsfm GitHub package requires Python `<3.14`. Install `tsfm_public` manually:

```python
import urllib.request, zipfile, io, os, sys, shutil

url = 'https://github.com/ibm-granite/granite-tsfm/archive/refs/heads/main.zip'
with urllib.request.urlopen(url, timeout=120) as resp:
    data = resp.read()

zf = zipfile.ZipFile(io.BytesIO(data))
site_pkg = next(p for p in sys.path if 'site-packages' in p and os.path.isdir(p))
dest = os.path.join(site_pkg, 'tsfm_public')
if os.path.exists(dest):
    shutil.rmtree(dest)
prefix = 'granite-tsfm-main/tsfm_public/'
for name in zf.namelist():
    if name.startswith(prefix) and not name.endswith('/'):
        rel = name[len('granite-tsfm-main/'):]
        out_path = os.path.join(site_pkg, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with zf.open(name) as src, open(out_path, 'wb') as dst:
            dst.write(src.read())
```

---

## 6. Running

### Start the ML service

```bash
python -m uvicorn app:app --reload --port 8001
```

### Swagger UI

```
http://127.0.0.1:8001/docs
```

### Run tests

```bash
python -m pytest tests/ -v
```

### Run integration tests (requires network + Granite download)

```bash
RUN_GRANITE_TESTS=1 python -m pytest tests/test_forecast.py::TestGraniteIntegration -v
```

---

## 7. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |
| `GET` | `/model/status` | Granite model availability |
| `POST` | `/forecast` | **Main forecast endpoint** |
| `POST` | `/forecast/{item_id}` | Forecast with path parameter |
| `POST` | `/predict` | Generic prediction (routes to forecast) |

---

## 8. Request / Response Examples

### POST /forecast (request)

```json
POST http://127.0.0.1:8001/forecast
Content-Type: application/json

{
    "item_id": "ITM10025",
    "horizon": 7,
    "history": [
        {"date": "2026-01-01", "demand": 12},
        {"date": "2026-01-02", "demand": 15},
        ...90+ days total...
        {"date": "2026-04-01", "demand": 18}
    ]
}
```

### POST /forecast (response — Granite active)

```json
{
    "item_id": "ITM10025",
    "model": "Granite Time Series (IBM TTM)",
    "horizon": 7,
    "forecast": [
        {"date": "2026-04-02", "predicted_demand": 16.3201},
        {"date": "2026-04-03", "predicted_demand": 17.1045},
        {"date": "2026-04-04", "predicted_demand": 15.8832},
        {"date": "2026-04-05", "predicted_demand": 14.9917},
        {"date": "2026-04-06", "predicted_demand": 16.7123},
        {"date": "2026-04-07", "predicted_demand": 18.0041},
        {"date": "2026-04-08", "predicted_demand": 17.5509}
    ]
}
```

### POST /forecast (response — baseline fallback, short history)

```json
{
    "item_id": "ITM10025",
    "model": "Baseline (Moving Average)",
    "horizon": 7,
    "forecast": [
        {"date": "2026-07-08", "predicted_demand": 14.14},
        ...
    ]
}
```

### GET /model/status (Granite loaded)

```json
{
    "model": "Granite Time Series (IBM TTM)",
    "available": true,
    "revision": "90-30-ft-r2.1",
    "context_length": 90,
    "prediction_length": 30,
    "fallback_model": "Baseline (Moving Average)",
    "fallback_available": true
}
```

### GET /model/status (Granite not loaded)

```json
{
    "model": "Granite Time Series (IBM TTM)",
    "available": false,
    "message": "...",
    "fallback_model": "Baseline (Moving Average)",
    "fallback_available": true
}
```

---

## 9. Historical Data Requirements

The ML service expects demand history in this format:

```
date,item_id,demand
2026-01-01,ITM10025,12
2026-01-02,ITM10025,15
```

**Minimum for Granite TTM:** 90 consecutive daily demand observations per item.

**Important:** `data/warehouse_raw.csv` is an **inventory snapshot** containing fields like `stock_level`, `reorder_point`, etc. It is NOT historical time-series demand and cannot be used for forecasting.

In production, the **backend** provides historical demand via `POST /forecast`.

---

## 10. Model Selection Logic

```
Incoming forecast request
        ↓
History >= 90 days AND horizon <= 30 days AND Granite loaded?
        ↓ YES                           ↓ NO
Granite TTM R2.1              Baseline Moving Average
(real AI predictions)         (labelled clearly as baseline)
```

The `model` field in every response identifies which model generated the predictions.

---

## 11. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GRANITE_MODEL_ID` | `ibm-granite/granite-timeseries-ttm-r2` | HuggingFace model repo |
| `GRANITE_REVISION` | `90-30-ft-r2.1` | Model branch/revision |
| `GRANITE_CONTEXT_LENGTH` | `90` | Input context window |
| `GRANITE_PREDICTION_LENGTH` | `30` | Model output window |
| `GRANITE_DAILY_FREQ_TOKEN` | `1` | Frequency token for daily data |

---

## 12. Backend Integration

```python
import httpx

ML_SERVICE_URL = "http://127.0.0.1:8001"

def get_demand_forecast(item_id: str, history: list[dict], horizon: int = 7):
    response = httpx.post(
        f"{ML_SERVICE_URL}/forecast",
        json={
            "item_id": item_id,
            "horizon": horizon,
            "history": history,  # at least 90 dicts: {"date": str, "demand": float}
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()

# In backend stockout/replenishment logic:
forecast_data = get_demand_forecast("ITM10025", history, horizon=7)
total_forecast_demand = sum(
    p["predicted_demand"] for p in forecast_data["forecast"]
)
# Pass total_forecast_demand to backend stockout/replenishment service
```

---

## 13. Limitations

| Limitation | Detail |
|---|---|
| Minimum history | 90 days required for Granite. Shorter history uses baseline fallback. |
| Max horizon | 30 days (Granite model constraint). Longer horizons use baseline. |
| Python 3.14 | `granite-tsfm` package requires Python <3.14. Use manual `tsfm_public` install (see above). |
| No fine-tuning | Zero-shot only. For higher accuracy, fine-tuning on real warehouse data is possible in future stages. |
| CPU-only | `torch` installed CPU-only. GPU acceleration available if CUDA is installed. |
| Internet required | First run downloads ~3MB model weights from HuggingFace (cached after that). |
| No PostgreSQL | ML service does not connect to the database. Backend must supply history. |

---

## Ports

| Service | URL |
|---|---|
| Backend | http://127.0.0.1:8000 |
| ML Service | http://127.0.0.1:8001 |
| Swagger | http://127.0.0.1:8001/docs |
