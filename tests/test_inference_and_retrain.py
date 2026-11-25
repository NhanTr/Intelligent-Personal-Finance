from datetime import date
from pathlib import Path
import pandas as pd
from finance_ml.config import load_config
from finance_ml.data.synthetic import generate_synthetic_dataset
from finance_ml.inference.loader import ModelBundleLoader
from finance_ml.inference.predictor import predict_next_7d, detect_anomalies
from finance_ml.inference.benchmark import run_latency_benchmark
from scripts.retrain import retrain_and_maybe_promote


def test_missing_model_falls_back_to_baseline_and_short_history_returns_insufficient(tmp_path: Path):
    cfg = load_config(Path("configs/default.yaml"))
    syn = generate_synthetic_dataset(cfg)
    fallback_bundle = ModelBundleLoader(tmp_path / "missing_active.json", allow_baseline_fallback=True).load()
    assert fallback_bundle.fallback_only is True

    short_res = predict_next_7d(syn.transactions_df, "user_short_001", date(2026, 1, 14), fallback_bundle)
    assert short_res.status == "insufficient_data"
    assert short_res.days_available == 14

    future_only_res = predict_next_7d(syn.transactions_df, "user_001", date(2025, 12, 15), fallback_bundle)
    assert future_only_res.status == "insufficient_data"
    assert future_only_res.days_available == 0

    ok_res = predict_next_7d(syn.transactions_df, "user_001", date(2026, 6, 15), fallback_bundle)
    assert ok_res.status == "fallback_baseline"
    assert ok_res.predicted_total_vnd is not None and ok_res.predicted_total_vnd >= 0.0


def test_retrain_atomic_promotion_and_latency_under_3_seconds(tmp_path: Path):
    cfg = load_config(Path("configs/default.yaml"))
    syn = generate_synthetic_dataset(cfg)
    ds_dir = tmp_path / "synthetic"
    active_ptr = tmp_path / "models" / "active.json"

    r1 = retrain_and_maybe_promote(syn.transactions_df, syn.profile_windows, None, ds_dir, active_ptr, cfg, "v1.0.0")
    assert r1["promoted"] is True

    flagged_tx_id = syn.transactions_df[
        (syn.transactions_df["user_id"] == "user_001") & (syn.transactions_df["type"] == "expense")
    ].iloc[0]["transaction_id"]
    fb = pd.DataFrame([{
        "transaction_id": flagged_tx_id,
        "user_id": "user_001",
        "is_confirmed_anomaly": True,
        "model_version": "v1.0.0",
        "created_at": "2026-05-01T10:00:00+07:00",
    }])
    r2 = retrain_and_maybe_promote(syn.transactions_df, syn.profile_windows, fb, ds_dir, active_ptr, cfg, "v1.1.0")
    assert "candidate_val_mae" in r2 and "active_val_mae_on_new_window" in r2

    bundle = ModelBundleLoader(active_ptr).load()
    anom = detect_anomalies(syn.transactions_df, "user_001", bundle)
    assert anom.model_version in {"v1.0.0", "v1.1.0"}

    bench = run_latency_benchmark(bundle, syn.transactions_df, "user_001", date(2026, 9, 1), n_runs=25)
    assert bench["n_runs"] == 25
    assert bench["max_latency_sec"] <= 3.0
