from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from finance_ml.evaluation.split import compute_time_cutoffs, assign_forecast_origins
from finance_ml.evaluation.rolling_cv import generate_expanding_cv_splits
from finance_ml.evaluation.metrics import compute_forecast_metrics
from finance_ml.evaluation.test_guard import TestLockGuard


def test_forecast_origins_purge_boundary_overlap_and_enforce_7d_spacing():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(300)]
    daily = pd.DataFrame({"user_id": ["u1"] * 300, "date": dates, "total_expense_vnd": 100000.0})
    cutoffs = compute_time_cutoffs(daily, (0.6, 0.2, 0.2))

    origins = pd.DataFrame({"user_id": ["u1"] * 260, "origin_date": dates[28:288]})
    assigned = assign_forecast_origins(origins, cutoffs, horizon_days=7, min_step_days=7)

    train_rows = assigned[assigned["split"] == "train"]
    val_rows = assigned[assigned["split"] == "validation"]
    test_rows = assigned[assigned["split"] == "test"]

    assert (train_rows["origin_date"] + timedelta(days=7) <= cutoffs.train_end).all()
    assert (val_rows["origin_date"] >= cutoffs.val_start).all()
    assert (val_rows["origin_date"] + timedelta(days=7) <= cutoffs.val_end).all()
    assert (test_rows["origin_date"] >= cutoffs.test_start).all()
    for _, grp in assigned.groupby(["user_id", "split"]):
        diffs = grp["origin_date"].sort_values().diff().dropna().apply(lambda d: d.days)
        assert (diffs >= 7).all()


def test_expanding_cv_never_touches_test_period():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(300)]
    daily = pd.DataFrame({"user_id": ["u1"] * 300, "date": dates, "total_expense_vnd": 100000.0})
    cutoffs = compute_time_cutoffs(daily, (0.6, 0.2, 0.2))
    folds = generate_expanding_cv_splits(daily, cutoffs, n_splits=3)
    assert len(folds) == 3
    assert all(f.val_end <= cutoffs.val_end for f in folds)


def test_forecast_metrics_computes_mae_rmse_and_10pct_target_without_mape():
    y_true = np.array([0.0, 1000000.0, 500000.0])
    y_pred = np.array([100000.0, 900000.0, 500000.0])
    users = pd.Series(["u1", "u1", "u2"])
    m = compute_forecast_metrics(y_true, y_pred, users, baseline_mae=100000.0)
    assert "mape" not in m
    assert m["meets_10pct_target"] is True
    assert set(m["per_user"].keys()) == {"u1", "u2"}


def test_one_shot_test_lock_guard(tmp_path: Path):
    guard = TestLockGuard(tmp_path / "test_evaluation_lock.json")
    with pytest.raises(PermissionError):
        guard.verify_and_record(unlock=False, reason=None, config_hash="abc")

    rec1 = guard.verify_and_record(unlock=True, reason="Initial Day-14 test run", config_hash="abc")
    assert rec1["unlock_count"] == 1

    with pytest.raises(PermissionError):
        guard.verify_and_record(unlock=True, reason="", config_hash="abc")
