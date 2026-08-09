"""
test_api.py
-----------
Tests for the TwinStock AI ML Service FastAPI endpoints.

Run with:
    python -m pytest tests/ -v

These tests do NOT require a running ML service instance or a Granite model.
They use the FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient

# Must be imported from the ml-service root — ensure CWD is ml-service/
from app import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_service_name(self):
        data = client.get("/").json()
        assert data["service"] == "TwinStock AI ML Service"

    def test_root_status_running(self):
        data = client.get("/").json()
        assert data["status"] == "running"


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_healthy(self):
        data = client.get("/health").json()
        assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# GET /model/status
# ---------------------------------------------------------------------------

class TestModelStatus:
    def test_model_status_returns_200(self):
        response = client.get("/model/status")
        assert response.status_code == 200

    def test_model_status_has_required_fields(self):
        data = client.get("/model/status").json()
        assert "model" in data
        assert "available" in data

    def test_granite_not_available_yet(self):
        """Granite is not loaded — available must be False."""
        data = client.get("/model/status").json()
        # Granite TTM is not installed in STAGE 1
        assert data["available"] is False

    def test_model_name_is_granite(self):
        data = client.get("/model/status").json()
        assert "Granite" in data["model"]

    def test_message_present_when_unavailable(self):
        data = client.get("/model/status").json()
        if not data["available"]:
            assert "message" in data
            assert data["message"]  # not empty


# ---------------------------------------------------------------------------
# POST /forecast — valid requests
# ---------------------------------------------------------------------------

VALID_HISTORY = [
    {"date": "2026-07-01", "demand": 12},
    {"date": "2026-07-02", "demand": 15},
    {"date": "2026-07-03", "demand": 11},
    {"date": "2026-07-04", "demand": 18},
    {"date": "2026-07-05", "demand": 14},
    {"date": "2026-07-06", "demand": 16},
    {"date": "2026-07-07", "demand": 13},
]

VALID_REQUEST = {
    "item_id": "ITM10025",
    "horizon": 3,
    "history": VALID_HISTORY,
}


class TestForecastValid:
    def test_forecast_returns_200(self):
        response = client.post("/forecast", json=VALID_REQUEST)
        assert response.status_code == 200

    def test_forecast_has_item_id(self):
        data = client.post("/forecast", json=VALID_REQUEST).json()
        assert data["item_id"] == "ITM10025"

    def test_forecast_has_correct_horizon(self):
        data = client.post("/forecast", json=VALID_REQUEST).json()
        assert data["horizon"] == 3

    def test_forecast_returns_correct_number_of_points(self):
        data = client.post("/forecast", json=VALID_REQUEST).json()
        assert len(data["forecast"]) == 3

    def test_forecast_points_have_date_and_demand(self):
        data = client.post("/forecast", json=VALID_REQUEST).json()
        for point in data["forecast"]:
            assert "date" in point
            assert "predicted_demand" in point

    def test_forecast_predicted_demand_is_non_negative(self):
        data = client.post("/forecast", json=VALID_REQUEST).json()
        for point in data["forecast"]:
            assert point["predicted_demand"] >= 0

    def test_forecast_model_field_present(self):
        data = client.post("/forecast", json=VALID_REQUEST).json()
        assert "model" in data

    def test_forecast_dates_are_future(self):
        """Forecast dates must come after the last history date."""
        import datetime
        data = client.post("/forecast", json=VALID_REQUEST).json()
        last_history_date = datetime.date(2026, 7, 7)
        for point in data["forecast"]:
            forecast_date = datetime.date.fromisoformat(point["date"])
            assert forecast_date > last_history_date

    def test_forecast_default_horizon_7(self):
        request_no_horizon = {
            "item_id": "ITM10025",
            "history": VALID_HISTORY,
        }
        data = client.post("/forecast", json=request_no_horizon).json()
        assert len(data["forecast"]) == 7


# ---------------------------------------------------------------------------
# POST /forecast — invalid requests
# ---------------------------------------------------------------------------

class TestForecastInvalid:
    def test_empty_history_returns_422(self):
        response = client.post("/forecast", json={
            "item_id": "ITM10025",
            "horizon": 7,
            "history": [],
        })
        assert response.status_code == 422

    def test_missing_history_returns_422(self):
        response = client.post("/forecast", json={
            "item_id": "ITM10025",
            "horizon": 7,
        })
        assert response.status_code == 422

    def test_empty_item_id_returns_422(self):
        response = client.post("/forecast", json={
            "item_id": "",
            "horizon": 7,
            "history": VALID_HISTORY,
        })
        assert response.status_code == 422

    def test_whitespace_item_id_returns_422(self):
        response = client.post("/forecast", json={
            "item_id": "   ",
            "horizon": 7,
            "history": VALID_HISTORY,
        })
        assert response.status_code == 422

    def test_negative_demand_returns_422(self):
        bad_history = [
            {"date": "2026-07-01", "demand": 12},
            {"date": "2026-07-02", "demand": -5},  # invalid
        ]
        response = client.post("/forecast", json={
            "item_id": "ITM10025",
            "horizon": 7,
            "history": bad_history,
        })
        assert response.status_code == 422

    def test_invalid_horizon_zero_returns_422(self):
        response = client.post("/forecast", json={
            "item_id": "ITM10025",
            "horizon": 0,
            "history": VALID_HISTORY,
        })
        assert response.status_code == 422

    def test_invalid_horizon_negative_returns_422(self):
        response = client.post("/forecast", json={
            "item_id": "ITM10025",
            "horizon": -1,
            "history": VALID_HISTORY,
        })
        assert response.status_code == 422

    def test_invalid_date_format_returns_422(self):
        bad_history = [
            {"date": "not-a-date", "demand": 12},
        ]
        response = client.post("/forecast", json={
            "item_id": "ITM10025",
            "horizon": 3,
            "history": bad_history,
        })
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /forecast/{item_id}
# ---------------------------------------------------------------------------

class TestForecastItemPath:
    def test_path_forecast_returns_200(self):
        response = client.post("/forecast/ITM10025", json={
            "item_id": "ITM10025",
            "horizon": 3,
            "history": VALID_HISTORY,
        })
        assert response.status_code == 200

    def test_path_item_id_used_in_response(self):
        """Path item_id overrides body item_id."""
        response = client.post("/forecast/ITM99999", json={
            "item_id": "ITM10025",
            "horizon": 3,
            "history": VALID_HISTORY,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["item_id"] == "ITM99999"


# ---------------------------------------------------------------------------
# POST /predict
# ---------------------------------------------------------------------------

class TestPredict:
    def test_predict_returns_200(self):
        response = client.post("/predict", json=VALID_REQUEST)
        assert response.status_code == 200

    def test_predict_response_matches_forecast(self):
        """predict and forecast must return the same structure."""
        predict_data = client.post("/predict", json=VALID_REQUEST).json()
        forecast_data = client.post("/forecast", json=VALID_REQUEST).json()
        # Same structure — item_id, horizon, model, forecast keys
        assert set(predict_data.keys()) == set(forecast_data.keys())
        assert predict_data["item_id"] == forecast_data["item_id"]
        assert predict_data["horizon"] == forecast_data["horizon"]
