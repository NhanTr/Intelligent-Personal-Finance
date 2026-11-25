from datetime import date, datetime
from pathlib import Path
import pytest
from pydantic import ValidationError
from finance_ml.config import load_config
from finance_ml.schema import TransactionRecord, ForecastResult, normalize_category


def test_load_default_config():
    cfg = load_config(Path("configs/default.yaml"))
    assert cfg.seed == 42
    assert cfg.split_ratios == (0.6, 0.2, 0.2)
    assert cfg.forecast.horizon_days == 7
    assert cfg.forecast.min_history_days == 28


def test_normalize_category_handles_unknown_and_aliases():
    assert normalize_category("Food & Dining") == "food"
    assert normalize_category("Ăn uống") == "food"
    assert normalize_category("CRYPTO_MEME") == "other"
    assert normalize_category("") == "other"
    assert normalize_category(None) == "other"


def test_transaction_record_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        TransactionRecord(
            transaction_id="tx_1",
            user_id="user_001",
            timestamp=datetime.fromisoformat("2026-03-01T10:00:00+07:00"),
            type="expense",
            amount_vnd=0.0,
            category="food",
        )


def test_forecast_result_insufficient_data_contract():
    res = ForecastResult(
        status="insufficient_data",
        user_id="user_short_001",
        as_of_date=date(2026, 2, 10),
        horizon_days=7,
        forecast_start_date=date(2026, 2, 11),
        forecast_end_date=date(2026, 2, 17),
        predicted_total_vnd=None,
        unit="VND",
        model_name="none",
        model_version="v1.0.0",
        days_available=14,
        min_days_required=28,
        limitations_note="Cần tối thiểu 28 ngày lịch sử để dự báo chi tiêu 7 ngày tới.",
    )
    assert res.unit == "VND"
    assert res.predicted_total_vnd is None
