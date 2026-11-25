from datetime import date
import pandas as pd
from finance_ml.data.cleaning import clean_transactions
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.schema import ProfileWindow


def test_clean_transactions_deduplicates_and_rejects_bad_rows():
    raw = pd.DataFrame([
        {"transaction_id": "t1", "user_id": "u1", "timestamp": "2026-01-02T08:00:00+07:00", "type": "expense", "amount_vnd": 50000, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t1", "user_id": "u1", "timestamp": "2026-01-02T08:00:00+07:00", "type": "expense", "amount_vnd": 50000, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t2", "user_id": "u1", "timestamp": "2026-01-02T09:00:00+07:00", "type": "expense", "amount_vnd": -100, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t3", "user_id": "u1", "timestamp": "2026-01-03T12:00:00+07:00", "type": "expense", "amount_vnd": 200000, "category": "transfer", "is_internal_transfer": True},
    ])
    clean_df, report = clean_transactions(raw)
    assert report.input_rows == 4
    assert report.deduplicated_rows == 1
    assert report.dropped_invalid_rows == 1
    assert report.internal_transfer_rows == 1
    assert len(clean_df) == 2


def test_daily_aggregation_zero_fills_only_inside_window_and_excludes_transfers_and_income():
    raw = pd.DataFrame([
        {"transaction_id": "t0", "user_id": "u1", "timestamp": "2025-12-31T10:00:00+07:00", "type": "expense", "amount_vnd": 99999, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t1", "user_id": "u1", "timestamp": "2026-01-01T10:00:00+07:00", "type": "expense", "amount_vnd": 100000, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t2", "user_id": "u1", "timestamp": "2026-01-01T12:00:00+07:00", "type": "expense", "amount_vnd": 500000, "category": "transfer", "is_internal_transfer": True},
        {"transaction_id": "t3", "user_id": "u1", "timestamp": "2026-01-01T15:00:00+07:00", "type": "income", "amount_vnd": 10000000, "category": "salary", "is_internal_transfer": False},
    ])
    clean_df, _ = clean_transactions(raw)
    windows = {"u1": ProfileWindow(user_id="u1", tracking_start_date=date(2026, 1, 1), tracking_end_date=date(2026, 1, 3))}
    daily = aggregate_daily_spending(clean_df, windows)

    assert list(daily["date"]) == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    assert list(daily["total_expense_vnd"]) == [100000.0, 0.0, 0.0]
    assert list(daily["tx_count"]) == [1, 0, 0]
    assert not daily.isna().any().any()
