"""
test_forecast.py
----------------
Tests for src/forecast.py and src/evaluation.py

These tests do NOT require a Granite model.
The baseline moving average model is always available.
"""

import pytest
from datetime import date, timedelta

from src.forecast import (
    forecast_demand,
    forecast_available,
    get_model_status,
    validate_forecast_input,
    create_forecast_response,
    BaselineMovingAverageModel,
    GraniteForecastModel,
)
from src.evaluation import (
    calculate_mae,
    calculate_rmse,
    calculate_mape,
    chronological_train_test_split,
    evaluate_forecast,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HISTORY_7 = [
    {"date": f"2026-07-0{i}", "demand": float(10 + i)}
    for i in range(1, 8)
]

HISTORY_1 = [{"date": "2026-07-01", "demand": 15.0}]


# ---------------------------------------------------------------------------
# validate_forecast_input
# ---------------------------------------------------------------------------

class TestValidateForecastInput:
    def test_valid_input_passes(self):
        validate_forecast_input("ITM001", HISTORY_7, 7)  # no exception

    def test_empty_item_id_raises(self):
        with pytest.raises(ValueError, match="item_id"):
            validate_forecast_input("", HISTORY_7, 7)

    def test_whitespace_item_id_raises(self):
        with pytest.raises(ValueError, match="item_id"):
            validate_forecast_input("   ", HISTORY_7, 7)

    def test_zero_horizon_raises(self):
        with pytest.raises(ValueError, match="horizon"):
            validate_forecast_input("ITM001", HISTORY_7, 0)

    def test_negative_horizon_raises(self):
        with pytest.raises(ValueError, match="horizon"):
            validate_forecast_input("ITM001", HISTORY_7, -1)

    def test_empty_history_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_forecast_input("ITM001", [], 7)

    def test_negative_demand_raises(self):
        bad = [{"date": "2026-07-01", "demand": -5.0}]
        with pytest.raises(ValueError, match="negative"):
            validate_forecast_input("ITM001", bad, 7)


# ---------------------------------------------------------------------------
# BaselineMovingAverageModel
# ---------------------------------------------------------------------------

class TestBaselineModel:
    def setup_method(self):
        self.model = BaselineMovingAverageModel(window=7)

    def test_is_available(self):
        assert self.model.is_available is True

    def test_model_name_label(self):
        assert "Baseline" in self.model.model_name
        assert "Granite" not in self.model.model_name

    def test_predict_correct_count(self):
        result = self.model.predict(HISTORY_7, horizon=5)
        assert len(result) == 5

    def test_predict_returns_date_and_demand(self):
        result = self.model.predict(HISTORY_7, horizon=3)
        for point in result:
            assert "date" in point
            assert "predicted_demand" in point

    def test_predict_dates_sequential(self):
        result = self.model.predict(HISTORY_7, horizon=3)
        dates = [date.fromisoformat(p["date"]) for p in result]
        for i in range(1, len(dates)):
            assert dates[i] == dates[i - 1] + timedelta(days=1)

    def test_predict_with_single_point(self):
        result = self.model.predict(HISTORY_1, horizon=3)
        assert len(result) == 3
        for point in result:
            assert point["predicted_demand"] == 15.0

    def test_predicted_demand_non_negative(self):
        result = self.model.predict(HISTORY_7, horizon=7)
        for point in result:
            assert point["predicted_demand"] >= 0

    def test_window_larger_than_history_uses_all(self):
        model = BaselineMovingAverageModel(window=100)
        result = model.predict(HISTORY_7, horizon=1)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# GraniteForecastModel
# ---------------------------------------------------------------------------

class TestGraniteModel:
    def test_not_available_by_default(self):
        model = GraniteForecastModel()
        assert model.is_available is False

    def test_predict_raises_when_not_loaded(self):
        model = GraniteForecastModel()
        with pytest.raises(RuntimeError, match="not loaded"):
            model.predict(HISTORY_7, horizon=3)

    def test_load_returns_false(self):
        """load() should return False until STAGE 5 is implemented."""
        model = GraniteForecastModel()
        result = model.load()
        assert result is False


# ---------------------------------------------------------------------------
# get_model_status
# ---------------------------------------------------------------------------

class TestModelStatus:
    def test_status_has_model_key(self):
        status = get_model_status()
        assert "model" in status

    def test_status_has_available_key(self):
        status = get_model_status()
        assert "available" in status

    def test_granite_not_available(self):
        status = get_model_status()
        assert status["available"] is False

    def test_fallback_available_when_granite_missing(self):
        status = get_model_status()
        if not status["available"]:
            assert status.get("fallback_available") is True

    def test_message_not_empty_when_unavailable(self):
        status = get_model_status()
        if not status["available"]:
            assert status.get("message")


# ---------------------------------------------------------------------------
# forecast_demand
# ---------------------------------------------------------------------------

class TestForecastDemand:
    def test_returns_dict(self):
        result = forecast_demand("ITM001", HISTORY_7, horizon=3)
        assert isinstance(result, dict)

    def test_item_id_in_response(self):
        result = forecast_demand("ITM001", HISTORY_7, horizon=3)
        assert result["item_id"] == "ITM001"

    def test_horizon_in_response(self):
        result = forecast_demand("ITM001", HISTORY_7, horizon=5)
        assert result["horizon"] == 5

    def test_forecast_list_length(self):
        result = forecast_demand("ITM001", HISTORY_7, horizon=4)
        assert len(result["forecast"]) == 4

    def test_unsorted_history_sorted_internally(self):
        """forecast_demand must sort history before predicting."""
        shuffled = list(reversed(HISTORY_7))
        result = forecast_demand("ITM001", shuffled, horizon=1)
        assert result["forecast"][0]["date"] > HISTORY_7[-1]["date"]

    def test_empty_history_raises_value_error(self):
        with pytest.raises(ValueError):
            forecast_demand("ITM001", [], horizon=3)

    def test_negative_demand_raises_value_error(self):
        bad = [{"date": "2026-07-01", "demand": -10.0}]
        with pytest.raises(ValueError):
            forecast_demand("ITM001", bad, horizon=3)


# ---------------------------------------------------------------------------
# create_forecast_response
# ---------------------------------------------------------------------------

class TestCreateForecastResponse:
    def test_structure(self):
        result = create_forecast_response(
            item_id="ITM001",
            model_name="TestModel",
            horizon=2,
            forecast_points=[
                {"date": "2026-08-01", "predicted_demand": 10.0},
                {"date": "2026-08-02", "predicted_demand": 11.0},
            ],
        )
        assert result["item_id"] == "ITM001"
        assert result["model"] == "TestModel"
        assert result["horizon"] == 2
        assert len(result["forecast"]) == 2


# ---------------------------------------------------------------------------
# Evaluation: calculate_mae
# ---------------------------------------------------------------------------

class TestMAE:
    def test_perfect_prediction(self):
        assert calculate_mae([10, 20, 30], [10, 20, 30]) == 0.0

    def test_known_value(self):
        # |10-12| + |20-18| + |30-35| = 2 + 2 + 5 = 9 → mean = 3.0
        assert calculate_mae([10, 20, 30], [12, 18, 35]) == 3.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_mae([], [])

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            calculate_mae([1, 2, 3], [1, 2])


# ---------------------------------------------------------------------------
# Evaluation: calculate_rmse
# ---------------------------------------------------------------------------

class TestRMSE:
    def test_perfect_prediction(self):
        assert calculate_rmse([10, 20, 30], [10, 20, 30]) == 0.0

    def test_non_negative(self):
        result = calculate_rmse([10, 20], [15, 18])
        assert result >= 0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_rmse([], [])


# ---------------------------------------------------------------------------
# Evaluation: calculate_mape
# ---------------------------------------------------------------------------

class TestMAPE:
    def test_perfect_prediction(self):
        assert calculate_mape([10, 20, 30], [10, 20, 30]) == 0.0

    def test_non_negative(self):
        result = calculate_mape([10, 20], [12, 18])
        assert result >= 0

    def test_zero_actual_no_divide_error(self):
        """Zero actual demand should not cause a ZeroDivisionError."""
        result = calculate_mape([0, 10, 20], [1, 11, 21])
        assert result >= 0


# ---------------------------------------------------------------------------
# Evaluation: chronological_train_test_split
# ---------------------------------------------------------------------------

class TestChronologicalSplit:
    def test_split_sizes(self):
        history = [{"date": f"2026-07-{i:02d}", "demand": float(i)} for i in range(1, 11)]
        train, test = chronological_train_test_split(history, test_ratio=0.3)
        assert len(train) == 7
        assert len(test) == 3

    def test_no_shuffling(self):
        """Train must be earlier dates, test must be later dates."""
        history = [{"date": f"2026-07-{i:02d}", "demand": float(i)} for i in range(1, 11)]
        train, test = chronological_train_test_split(history, test_ratio=0.3)
        assert train[-1]["date"] < test[0]["date"]

    def test_single_point_raises(self):
        with pytest.raises(ValueError):
            chronological_train_test_split([{"date": "2026-07-01", "demand": 10.0}])

    def test_invalid_ratio_raises(self):
        history = [{"date": f"2026-07-{i:02d}", "demand": float(i)} for i in range(1, 11)]
        with pytest.raises(ValueError):
            chronological_train_test_split(history, test_ratio=0)


# ---------------------------------------------------------------------------
# Evaluation: evaluate_forecast
# ---------------------------------------------------------------------------

class TestEvaluateForecast:
    def test_perfect_forecast(self):
        actual = [{"date": f"2026-07-{i:02d}", "demand": float(i * 10)} for i in range(1, 6)]
        predicted = [{"date": f"2026-07-{i:02d}", "predicted_demand": float(i * 10)} for i in range(1, 6)]
        result = evaluate_forecast(actual, predicted)
        assert result["mae"] == 0.0
        assert result["rmse"] == 0.0
        assert result["mape"] == 0.0

    def test_result_has_all_metrics(self):
        actual = [{"date": "2026-07-01", "demand": 10.0}]
        predicted = [{"date": "2026-07-01", "predicted_demand": 12.0}]
        result = evaluate_forecast(actual, predicted)
        assert "mae" in result
        assert "rmse" in result
        assert "mape" in result
        assert "n_points" in result

    def test_length_mismatch_raises(self):
        actual = [{"date": "2026-07-01", "demand": 10.0}]
        predicted = [
            {"date": "2026-07-01", "predicted_demand": 10.0},
            {"date": "2026-07-02", "predicted_demand": 12.0},
        ]
        with pytest.raises(ValueError):
            evaluate_forecast(actual, predicted)
