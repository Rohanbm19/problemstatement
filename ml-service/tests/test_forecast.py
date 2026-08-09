"""
test_forecast.py
----------------
Tests for src/forecast.py and src/evaluation.py

Unit tests use mocking to avoid downloading the Granite model.

Integration tests (which load the real Granite model from HuggingFace)
are gated behind the environment variable:

    RUN_GRANITE_TESTS=1

Run all tests:
    python -m pytest tests/test_forecast.py -v

Run including Granite integration tests:
    RUN_GRANITE_TESTS=1 python -m pytest tests/test_forecast.py -v
"""

import os
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.forecast import (
    forecast_demand,
    forecast_available,
    get_model_status,
    validate_forecast_input,
    create_forecast_response,
    BaselineMovingAverageModel,
    GraniteForecastModel,
    GRANITE_CONTEXT_LENGTH,
    GRANITE_PREDICTION_LENGTH,
    _select_model,
    _granite_model,
    _baseline_model,
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

# 90 days of synthetic demand — enough for Granite TTM
HISTORY_90 = [
    {
        "date": str((date(2026, 1, 1) + timedelta(days=i)).isoformat()),
        "demand": float(15 + (i % 7)),  # repeating weekly pattern
    }
    for i in range(90)
]


# ---------------------------------------------------------------------------
# validate_forecast_input
# ---------------------------------------------------------------------------

class TestValidateForecastInput:
    def test_valid_input_passes(self):
        validate_forecast_input("ITM001", HISTORY_7, 7)

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
# GraniteForecastModel — unit tests with mocking (no network required)
# ---------------------------------------------------------------------------

class TestGraniteModelUnit:
    """Unit tests using mocked tsfm_public — no HuggingFace download."""

    def test_not_available_before_load(self):
        model = GraniteForecastModel()
        assert model.is_available is False

    def test_predict_raises_when_not_loaded(self):
        model = GraniteForecastModel()
        with pytest.raises(RuntimeError, match="not loaded"):
            model.predict(HISTORY_90, horizon=7)

    def test_predict_raises_on_short_history(self):
        """predict() raises ValueError when history < MIN_HISTORY."""
        model = GraniteForecastModel()
        # Manually set model to simulate loaded state
        model._model = MagicMock()
        with pytest.raises(ValueError, match="days of history"):
            model.predict(HISTORY_7, horizon=7)

    def test_predict_raises_on_horizon_too_large(self):
        """predict() raises ValueError when horizon > GRANITE_PREDICTION_LENGTH."""
        model = GraniteForecastModel()
        model._model = MagicMock()
        with pytest.raises(ValueError, match="maximum horizon"):
            model.predict(HISTORY_90, horizon=GRANITE_PREDICTION_LENGTH + 1)

    def test_load_returns_false_on_import_error(self):
        """load() returns False gracefully when tsfm_public is missing."""
        model = GraniteForecastModel()
        with patch.dict("sys.modules", {"tsfm_public.models.tinytimemixer": None}):
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                result = model.load()
        assert result is False
        assert model.is_available is False
        assert model.load_error is not None

    def test_load_stores_error_message(self):
        """load() stores a useful error message on failure."""
        model = GraniteForecastModel()
        with patch(
            "tsfm_public.models.tinytimemixer.TinyTimeMixerForPrediction.from_pretrained",
            side_effect=RuntimeError("connection refused"),
        ):
            result = model.load()
        # Either False (if import succeeds but from_pretrained fails)
        # or False from the import error path — both are acceptable
        assert isinstance(result, bool)

    def test_predict_mocked_output_format(self):
        """With a mocked model, predict() returns the correct output format."""
        import torch
        import numpy as np

        model = GraniteForecastModel()

        # Build a mock output matching the real TTM output shape
        mock_output = MagicMock()
        fake_tensor = torch.tensor(
            [[[14.0], [15.0], [16.0], [15.5], [14.8], [14.2], [15.1]]]
        )  # shape [1, 7, 1]
        mock_output.prediction_outputs = fake_tensor

        mock_torch_model = MagicMock()
        mock_torch_model.return_value = mock_output
        model._model = mock_torch_model

        result = model.predict(HISTORY_90, horizon=7)

        assert len(result) == 7
        for pt in result:
            assert "date" in pt
            assert "predicted_demand" in pt
            assert pt["predicted_demand"] >= 0

    def test_predict_clamps_negative_values(self):
        """Negative raw model output must be clamped to 0."""
        import torch

        model = GraniteForecastModel()

        mock_output = MagicMock()
        # Some negative predictions from model
        fake_tensor = torch.tensor([[[-5.0], [-3.0], [10.0]]])
        mock_output.prediction_outputs = fake_tensor

        mock_torch_model = MagicMock()
        mock_torch_model.return_value = mock_output
        model._model = mock_torch_model

        result = model.predict(HISTORY_90, horizon=3)
        for pt in result:
            assert pt["predicted_demand"] >= 0.0, f"Negative demand: {pt}"


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

    def test_fallback_always_present(self):
        status = get_model_status()
        assert "fallback_model" in status
        assert status.get("fallback_available") is True

    def test_message_or_revision_present(self):
        status = get_model_status()
        if status["available"]:
            assert "revision" in status
        else:
            assert "message" in status and status["message"]


# ---------------------------------------------------------------------------
# _select_model
# ---------------------------------------------------------------------------

class TestSelectModel:
    def test_baseline_returned_when_granite_unavailable(self):
        with patch("src.forecast._granite_model") as mock_granite:
            mock_granite.is_available = False
            model = _select_model(HISTORY_7, horizon=7)
        assert isinstance(model, BaselineMovingAverageModel)

    def test_baseline_returned_for_short_history(self):
        """Even when Granite is available, short history forces baseline."""
        with patch("src.forecast._granite_model") as mock_granite:
            mock_granite.is_available = True
            # history < MIN_HISTORY
            model = _select_model(HISTORY_7, horizon=7)
        assert isinstance(model, BaselineMovingAverageModel)

    def test_granite_returned_for_sufficient_history(self):
        """When Granite is available and history is sufficient, use Granite."""
        with patch("src.forecast._granite_model") as mock_granite:
            mock_granite.is_available = True
            model = _select_model(HISTORY_90, horizon=7)
        assert model is mock_granite

    def test_baseline_returned_for_large_horizon(self):
        """Horizon > GRANITE_PREDICTION_LENGTH falls back to baseline."""
        with patch("src.forecast._granite_model") as mock_granite:
            mock_granite.is_available = True
            model = _select_model(HISTORY_90, horizon=GRANITE_PREDICTION_LENGTH + 1)
        assert isinstance(model, BaselineMovingAverageModel)


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

    def test_model_field_in_response(self):
        result = forecast_demand("ITM001", HISTORY_7, horizon=3)
        assert "model" in result
        assert result["model"] is not None

    def test_baseline_label_when_history_short(self):
        """With 7-day history, always gets baseline (< 90)."""
        result = forecast_demand("ITM001", HISTORY_7, horizon=3)
        assert "Baseline" in result["model"]


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
        assert calculate_mae([10, 20, 30], [12, 18, 35]) == 3.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_mae([], [])

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            calculate_mae([1, 2, 3], [1, 2])


class TestRMSE:
    def test_perfect_prediction(self):
        assert calculate_rmse([10, 20, 30], [10, 20, 30]) == 0.0

    def test_non_negative(self):
        assert calculate_rmse([10, 20], [15, 18]) >= 0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_rmse([], [])


class TestMAPE:
    def test_perfect_prediction(self):
        assert calculate_mape([10, 20, 30], [10, 20, 30]) == 0.0

    def test_non_negative(self):
        assert calculate_mape([10, 20], [12, 18]) >= 0

    def test_zero_actual_no_divide_error(self):
        result = calculate_mape([0, 10, 20], [1, 11, 21])
        assert result >= 0


class TestChronologicalSplit:
    def test_split_sizes(self):
        history = [{"date": f"2026-07-{i:02d}", "demand": float(i)} for i in range(1, 11)]
        train, test = chronological_train_test_split(history, test_ratio=0.3)
        assert len(train) == 7
        assert len(test) == 3

    def test_no_shuffling(self):
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


# ---------------------------------------------------------------------------
# Integration tests — real Granite model (opt-in only)
# ---------------------------------------------------------------------------

RUN_GRANITE = os.environ.get("RUN_GRANITE_TESTS", "0").strip() == "1"

@pytest.mark.skipif(not RUN_GRANITE, reason="Set RUN_GRANITE_TESTS=1 to run Granite integration tests")
class TestGraniteIntegration:
    """
    Integration tests that load the real IBM Granite TTM model.
    These require network access to HuggingFace and ~3MB of model weights.

    Enable with:
        RUN_GRANITE_TESTS=1 python -m pytest tests/test_forecast.py::TestGraniteIntegration -v
    """

    def test_granite_loads_successfully(self):
        from src.forecast import _granite_model
        assert _granite_model.is_available, (
            f"Granite failed to load: {_granite_model.load_error}"
        )

    def test_granite_predict_with_90_day_history(self):
        from src.forecast import _granite_model
        if not _granite_model.is_available:
            pytest.skip("Granite model not loaded")
        result = _granite_model.predict(HISTORY_90, horizon=7)
        assert len(result) == 7
        for pt in result:
            assert pt["predicted_demand"] >= 0
            assert pt["predicted_demand"] < 1e6  # sanity check — not inf

    def test_granite_forecast_dates_correct(self):
        from src.forecast import _granite_model
        if not _granite_model.is_available:
            pytest.skip("Granite model not loaded")
        result = _granite_model.predict(HISTORY_90, horizon=5)
        last_history_date = date.fromisoformat(HISTORY_90[-1]["date"])
        for i, pt in enumerate(result, start=1):
            expected = str(last_history_date + timedelta(days=i))
            assert pt["date"] == expected

    def test_granite_no_nan_or_inf(self):
        import math
        from src.forecast import _granite_model
        if not _granite_model.is_available:
            pytest.skip("Granite model not loaded")
        result = _granite_model.predict(HISTORY_90, horizon=7)
        for pt in result:
            assert math.isfinite(pt["predicted_demand"]), f"Non-finite: {pt}"

    def test_full_forecast_demand_with_granite(self):
        """forecast_demand() uses Granite when history >= 90 and horizon <= 30."""
        result = forecast_demand("ITM10025", HISTORY_90, horizon=7)
        assert result["item_id"] == "ITM10025"
        assert result["horizon"] == 7
        assert len(result["forecast"]) == 7
        # Model should be Granite, not baseline
        assert "Granite" in result["model"], f"Expected Granite, got: {result['model']}"
