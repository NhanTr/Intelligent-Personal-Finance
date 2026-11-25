from pathlib import Path
import numpy as np
import pandas as pd
from finance_ml.config import load_config
from finance_ml.data.synthetic import generate_synthetic_dataset
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.evaluation.split import compute_time_cutoffs, assign_forecast_origins, assign_transaction_splits
from finance_ml.features.forecast_features import build_forecast_dataset, FORECAST_FEATURE_COLUMNS
from finance_ml.models.forecast import train_and_select_forecast_models
from finance_ml.models.anomaly import train_anomaly_detector, score_expense_anomalies
from finance_ml.models.registry import save_model_bundle, set_active_pointer


def test_forecast_training_fallback_when_noise_beats_ml():
    cfg = load_config(Path("configs/default.yaml"))
    rng = np.random.default_rng(0)
    cols = list(FORECAST_FEATURE_COLUMNS)
    train_df = pd.DataFrame(rng.normal(100, 10, size=(40, len(cols))), columns=cols)
    train_df["user_id"] = "u1"
    train_df["target_next_7d_vnd"] = rng.uniform(1e6, 5e6, size=40)

    val_df = pd.DataFrame(rng.normal(100, 10, size=(15, len(cols))), columns=cols)
    val_df["user_id"] = "u1"
    val_df["spend_last_7d"] = 2000000.0
    val_df["target_next_7d_vnd"] = 2000000.0

    out = train_and_select_forecast_models(train_df, val_df, cfg)
    assert out.selected_name == "baseline_last_7d"
    assert out.fallback_used is True


def test_end_to_end_synthetic_train_and_bundle_save(tmp_path: Path):
    cfg = load_config(Path("configs/default.yaml"))
    syn = generate_synthetic_dataset(cfg)
    core_windows = {k: v for k, v in syn.profile_windows.items() if not k.startswith("user_short")}
    core_tx = syn.transactions_df[syn.transactions_df["user_id"].isin(core_windows)]
    daily = aggregate_daily_spending(core_tx, core_windows)
    cutoffs = compute_time_cutoffs(daily, cfg.split_ratios)

    f_ds = assign_forecast_origins(build_forecast_dataset(daily, core_windows), cutoffs)
    f_out = train_and_select_forecast_models(
        f_ds[f_ds["split"] == "train"], f_ds[f_ds["split"] == "validation"], cfg
    )
    assert set(f_out.val_comparison.keys()) == {"baseline_last_7d", "linear_regression", "random_forest"}

    exp_tx = core_tx[(core_tx["type"] == "expense") & (~core_tx["is_internal_transfer"])]
    exp_split = assign_transaction_splits(exp_tx, cutoffs)
    det = train_anomaly_detector(
        exp_split[exp_split["split"] == "train"], exp_split[exp_split["split"] == "validation"], cfg
    )
    scored = score_expense_anomalies(exp_split[exp_split["split"] == "validation"], det, exp_split[exp_split["split"] == "train"])
    assert 0.01 <= scored["is_anomaly"].mean() <= 0.10
    flagged = scored[scored["is_anomaly"]]
    assert all(len(r) >= 1 for r in flagged["reasons"])

    bdir = save_model_bundle(tmp_path / "synthetic", "v1.0.0", f_out, det, {"seed": cfg.seed})
    set_active_pointer(tmp_path / "models" / "active.json", bdir, "v1.0.0", "synthetic")
    assert (bdir / "bundle.joblib").exists()
    assert (bdir / "metadata.json").exists()
