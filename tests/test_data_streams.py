from pathlib import Path
import pandas as pd
from finance_ml.config import load_config
from finance_ml.data.synthetic import generate_synthetic_dataset
from finance_ml.data.public_adapter import adapt_kaggle_daily_transactions
from finance_ml.data.daily import aggregate_daily_spending


def test_synthetic_generator_is_deterministic_and_meets_spec_bounds():
    cfg = load_config(Path("configs/default.yaml"))
    b1 = generate_synthetic_dataset(cfg)
    b2 = generate_synthetic_dataset(cfg)
    pd.testing.assert_frame_equal(b1.transactions_df, b2.transactions_df)

    core_users = [u for u in b1.profile_windows if not u.startswith("user_short")]
    assert len(core_users) == 8
    assert "user_short_001" in b1.profile_windows
    short_w = b1.profile_windows["user_short_001"]
    assert (short_w.tracking_end_date - short_w.tracking_start_date).days + 1 == 14

    assert len(b1.transactions_df) >= 2000
    assert b1.transactions_df["is_internal_transfer"].any()
    daily = aggregate_daily_spending(
        b1.transactions_df[b1.transactions_df["user_id"].isin(core_users)],
        {u: b1.profile_windows[u] for u in core_users},
    )
    for _, grp in daily.groupby("user_id"):
        assert len(grp) >= 180
        assert (grp["total_expense_vnd"] == 0).any()

    assert "is_injected_anomaly" in b1.anomaly_eval_df.columns
    assert b1.anomaly_eval_df["is_injected_anomaly"].sum() >= 15


def test_kaggle_public_adapter_maps_transfers_and_currency(tmp_path: Path):
    sample_csv = tmp_path / "daily_household_transactions.csv"
    pd.DataFrame([
        {"Date": "20/09/2018 12:00:00", "Mode": "Cash", "Category": "Food", "Subcategory": "Lunch", "Note": "Rice", "Amount": 120.0, "Income/Expense": "Expense", "Currency": "INR"},
        {"Date": "21/09/2018 09:00:00", "Mode": "Bank", "Category": "Savings", "Subcategory": "", "Note": "Move", "Amount": 5000.0, "Income/Expense": "Transfer-Out", "Currency": "INR"},
        {"Date": "25/09/2018 09:00:00", "Mode": "Bank", "Category": "Salary", "Subcategory": "", "Note": "Pay", "Amount": 30000.0, "Income/Expense": "Income", "Currency": "INR"},
    ]).to_csv(sample_csv, index=False)

    clean_df, windows, manifest = adapt_kaggle_daily_transactions(sample_csv, inr_to_vnd_rate=300.0)
    assert manifest.source_type == "real_public"
    assert set(clean_df["user_id"]) == {"public_hh_001"}
    transfer_row = clean_df[clean_df["amount_vnd"] == 1500000.0].iloc[0]
    assert bool(transfer_row["is_internal_transfer"]) is True
    assert transfer_row["type"] == "expense"
