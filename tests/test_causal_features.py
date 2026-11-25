from datetime import date, timedelta
import numpy as np
import pandas as pd
from finance_ml.schema import ProfileWindow
from finance_ml.features.forecast_features import build_forecast_dataset, build_single_forecast_features, FORECAST_FEATURE_COLUMNS
from finance_ml.features.anomaly_features import fit_anomaly_feature_state, transform_anomaly_features


def test_forecast_features_are_strictly_causal_and_match_single_inference():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(60)]
    daily_a = pd.DataFrame({
        "user_id": ["u1"] * 60,
        "date": dates,
        "total_expense_vnd": [100000.0 + (i % 7) * 10000.0 for i in range(60)],
        "tx_count": [2] * 60,
        "essential_expense_vnd": [70000.0] * 60,
    })
    daily_b = daily_a.copy()
    daily_b.loc[daily_b["date"] > date(2026, 2, 5), "total_expense_vnd"] = 99999999.0

    windows = {"u1": ProfileWindow(user_id="u1", tracking_start_date=dates[0], tracking_end_date=dates[-1])}
    ds_a = build_forecast_dataset(daily_a, windows, horizon_days=7, min_history_days=28)
    row_a = ds_a[ds_a["origin_date"] == date(2026, 2, 5)][list(FORECAST_FEATURE_COLUMNS)].reset_index(drop=True)
    single_b = build_single_forecast_features(daily_b, "u1", date(2026, 2, 5), min_history_days=28)[list(FORECAST_FEATURE_COLUMNS)].reset_index(drop=True)

    pd.testing.assert_frame_equal(row_a, single_b)


def test_anomaly_features_causal_invariance_and_cold_user_unknown_category():
    train_tx = pd.DataFrame([
        {"transaction_id": f"t{i}", "user_id": "u1", "timestamp": pd.Timestamp(pd.Timestamp("2026-01-01T10:00:00+07:00").to_pydatetime() + timedelta(days=i)), "type": "expense", "amount_vnd": 100000.0, "category": "food", "is_internal_transfer": False}
        for i in range(10)
    ])
    state = fit_anomaly_feature_state(train_tx)

    eval_a = pd.DataFrame([
        {"transaction_id": "e1", "user_id": "new_user", "timestamp": pd.Timestamp("2026-02-01T10:00:00+07:00"), "type": "expense", "amount_vnd": 500000.0, "category": "unseen_cat", "is_internal_transfer": False},
        {"transaction_id": "e2", "user_id": "new_user", "timestamp": pd.Timestamp("2026-02-02T10:00:00+07:00"), "type": "expense", "amount_vnd": 50000000.0, "category": "food", "is_internal_transfer": False},
    ])
    eval_b = eval_a.copy()
    eval_b.loc[1, "amount_vnd"] = 1.0

    X_a, ctx_a = transform_anomaly_features(eval_a, state)
    X_b, ctx_b = transform_anomaly_features(eval_b, state)

    assert np.isfinite(X_a).all()
    np.testing.assert_allclose(X_a[0], X_b[0])
    assert ctx_a.iloc[0]["user_amount_ratio"] == ctx_b.iloc[0]["user_amount_ratio"]


def test_anomaly_cat_ratio_falls_back_to_user_median_before_pooled_train():
    train_tx = pd.DataFrame([
        {"transaction_id": f"s{i}", "user_id": "u_low", "timestamp": pd.Timestamp(pd.Timestamp("2026-01-01T10:00:00+07:00").to_pydatetime() + timedelta(days=i)), "type": "expense", "amount_vnd": 50000.0, "category": "shopping", "is_internal_transfer": False}
        for i in range(10)
    ])
    state = fit_anomaly_feature_state(train_tx, min_prior_tx=5)

    # Established high-spending user (8 prior food tx at 1,000,000 VND, 0 prior shopping tx)
    high_user_tx = pd.DataFrame(
        [
            {"transaction_id": f"h{i}", "user_id": "u_high", "timestamp": pd.Timestamp(pd.Timestamp("2026-02-01T10:00:00+07:00").to_pydatetime() + timedelta(days=i)), "type": "expense", "amount_vnd": 1000000.0, "category": "food", "is_internal_transfer": False}
            for i in range(8)
        ]
        + [
            {"transaction_id": "h_shop", "user_id": "u_high", "timestamp": pd.Timestamp("2026-02-15T10:00:00+07:00"), "type": "expense", "amount_vnd": 1000000.0, "category": "shopping", "is_internal_transfer": False}
        ]
    )
    _, ctx = transform_anomaly_features(high_user_tx, state)
    shop_row = ctx[ctx["transaction_id"] == "h_shop"].iloc[0]
    assert 0.95 <= float(shop_row["user_cat_amount_ratio"]) <= 1.05
