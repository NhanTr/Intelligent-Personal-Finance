"""CLI script to evaluate F3/F4 on validation, rolling CV, and (if unlocked) test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import joblib
import pandas as pd

from finance_ml.config import load_config
from finance_ml.data.cleaning import clean_transactions
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.evaluation.metrics import compute_anomaly_injection_metrics, compute_forecast_metrics
from finance_ml.evaluation.rolling_cv import generate_expanding_cv_splits
from finance_ml.evaluation.split import assign_forecast_origins, assign_transaction_splits, compute_time_cutoffs
from finance_ml.evaluation.test_guard import TestLockGuard
from finance_ml.features.forecast_features import FORECAST_FEATURE_COLUMNS, build_forecast_dataset
from finance_ml.models.anomaly import score_expense_anomalies
from finance_ml.models.forecast import build_linear_regression_model, build_rf_model, Last7DaysBaseline
from scripts.train import filter_eligible_windows, load_processed_stream


def _evaluate_forecast_models_on_split(
    split_df: pd.DataFrame,
    all_models: dict[str, object],
    target_improvement_pct: float,
) -> dict[str, dict[str, object]]:
    feat_cols = list(FORECAST_FEATURE_COLUMNS)
    X = split_df[feat_cols]
    y = split_df["target_next_7d_vnd"].to_numpy(dtype=float)
    users = split_df["user_id"]

    b_pred = all_models["baseline_last_7d"].predict(X)
    b_res = compute_forecast_metrics(y, b_pred, users, baseline_mae=None, target_improvement_pct=target_improvement_pct)
    b_mae = float(b_res["mae_vnd"])

    out: dict[str, dict[str, object]] = {"baseline_last_7d": b_res}
    for name, est in all_models.items():
        if name == "baseline_last_7d":
            continue
        pred = est.predict(X)
        out[name] = compute_forecast_metrics(y, pred, users, baseline_mae=b_mae, target_improvement_pct=target_improvement_pct)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate F3/F4 models with strict 1-shot test lock.")
    parser.add_argument("--dataset", choices=["synthetic", "real_public"], default="synthetic")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--unlock-test", action="store_true", help="Explicitly unlock 1-shot test evaluation.")
    parser.add_argument("--reason", type=str, default=None, help="Audit reason when --unlock-test is set.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    ds_art_dir = args.root / "artifacts" / args.dataset
    metrics_dir = ds_art_dir / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    active_ptr = json.loads((ds_art_dir / "models" / "active.json").read_text(encoding="utf-8"))
    bundle = joblib.load(Path(active_ptr["bundle_dir"]) / "bundle.joblib")

    proc_dir = args.root / "data" / "processed" / args.dataset
    clean_df, all_windows = load_processed_stream(proc_dir)
    core_windows = filter_eligible_windows(all_windows, min_days=180)
    core_df = clean_df[clean_df["user_id"].isin(core_windows.keys())].copy()
    daily_df = aggregate_daily_spending(core_df, core_windows)
    cutoffs = compute_time_cutoffs(daily_df, cfg.split_ratios)

    f_raw = build_forecast_dataset(
        daily_df,
        core_windows,
        horizon_days=cfg.forecast.horizon_days,
        min_history_days=cfg.forecast.min_history_days,
    )
    f_split = assign_forecast_origins(
        f_raw,
        cutoffs,
        horizon_days=cfg.forecast.horizon_days,
        min_step_days=cfg.forecast.origin_step_days,
    )

    # 1. Validation evaluation
    val_f3 = _evaluate_forecast_models_on_split(
        f_split[f_split["split"] == "validation"],
        bundle.all_forecast_models,
        cfg.forecast.target_improvement_pct,
    )

    exp_df = core_df[(core_df["type"] == "expense") & (~core_df["is_internal_transfer"])].copy()
    exp_split = assign_transaction_splits(exp_df, cutoffs)
    val_scored = score_expense_anomalies(
        exp_split[exp_split["split"] == "validation"],
        bundle.anomaly_detector,
        history_expense_df=exp_split[exp_split["split"] == "train"],
    )

    # 2. Expanding-window rolling CV inside train+validation only
    folds = generate_expanding_cv_splits(daily_df, cutoffs, n_splits=3)
    best_rf_params = bundle.metadata.get("best_rf_params", {"n_estimators": 100, "max_depth": 6, "min_samples_leaf": 5})
    cv_records: list[dict[str, object]] = []
    feat_cols = list(FORECAST_FEATURE_COLUMNS)
    for idx, f_cut in enumerate(folds):
        fold_assigned = assign_forecast_origins(
            f_raw,
            f_cut,
            horizon_days=cfg.forecast.horizon_days,
            min_step_days=cfg.forecast.origin_step_days,
        )
        tr_fold = fold_assigned[fold_assigned["split"] == "train"]
        va_fold = fold_assigned[fold_assigned["split"] == "validation"]
        if tr_fold.empty or va_fold.empty:
            continue
        fold_models = {
            "baseline_last_7d": Last7DaysBaseline().fit(tr_fold[feat_cols], tr_fold["target_next_7d_vnd"].to_numpy()),
            "linear_regression": build_linear_regression_model().fit(tr_fold[feat_cols], tr_fold["target_next_7d_vnd"].to_numpy()),
            "random_forest": build_rf_model(best_rf_params, seed=cfg.seed).fit(tr_fold[feat_cols], tr_fold["target_next_7d_vnd"].to_numpy()),
        }
        fold_res = _evaluate_forecast_models_on_split(va_fold, fold_models, cfg.forecast.target_improvement_pct)
        cv_records.append(
            {
                "fold": idx + 1,
                "train_end": str(f_cut.train_end),
                "val_start": str(f_cut.val_start),
                "val_end": str(f_cut.val_end),
                "models": {k: {"mae_vnd": v["mae_vnd"], "rmse_vnd": v["rmse_vnd"], "n_samples": v["n_samples"]} for k, v in fold_res.items()},
            }
        )

    val_payload = {
        "dataset": args.dataset,
        "model_version": bundle.version,
        "selected_forecast_model": bundle.selected_forecast_name,
        "forecast_validation": val_f3,
        "rolling_cv": cv_records,
        "anomaly_validation": {
            "threshold": bundle.anomaly_detector.threshold,
            "total_evaluated": int(len(val_scored)),
            "flagged_count": int(val_scored["is_anomaly"].sum()),
            "alert_rate": float(val_scored["is_anomaly"].mean()) if len(val_scored) > 0 else 0.0,
        },
    }
    (metrics_dir / "validation_metrics.json").write_text(
        json.dumps(val_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 3. Synthetic injected-anomaly benchmark (strictly isolated)
    anom_eval_csv = proc_dir / "anomaly_eval.csv"
    if args.dataset == "synthetic" and anom_eval_csv.exists():
        raw_aeval = pd.read_csv(anom_eval_csv)
        clean_aeval, _ = clean_transactions(raw_aeval)
        label_map = dict(zip(raw_aeval["transaction_id"].astype(str), raw_aeval["is_injected_anomaly"].astype(bool)))
        scored_aeval = score_expense_anomalies(
            clean_aeval,
            bundle.anomaly_detector,
            history_expense_df=exp_split[exp_split["split"] == "train"],
        )
        y_true_inj = scored_aeval["transaction_id"].astype(str).map(label_map).fillna(False).to_numpy(dtype=bool)
        inj_metrics = compute_anomaly_injection_metrics(y_true_inj, scored_aeval["is_anomaly"].to_numpy(dtype=bool))
        (metrics_dir / "synthetic_anomaly_eval.json").write_text(
            json.dumps(inj_metrics, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # 4. Optional 1-shot test evaluation (guarded by TestLockGuard; skipped when --unlock-test is False)
    if args.unlock_test:
        guard = TestLockGuard(metrics_dir / "test_evaluation_lock.json")
        lock_state = guard.verify_and_record(unlock=True, reason=args.reason, config_hash=cfg.config_hash())
        test_f3 = _evaluate_forecast_models_on_split(
            f_split[f_split["split"] == "test"],
            bundle.all_forecast_models,
            cfg.forecast.target_improvement_pct,
        )
        dev_history = exp_split[exp_split["split"].isin(["train", "validation"])]
        test_scored = score_expense_anomalies(
            exp_split[exp_split["split"] == "test"],
            bundle.anomaly_detector,
            history_expense_df=dev_history,
        )
        test_payload = {
            "dataset": args.dataset,
            "model_version": bundle.version,
            "selected_forecast_model": bundle.selected_forecast_name,
            "unlock_count": lock_state["unlock_count"],
            "forecast_test": test_f3,
            "anomaly_test": {
                "threshold": bundle.anomaly_detector.threshold,
                "total_evaluated": int(len(test_scored)),
                "flagged_count": int(test_scored["is_anomaly"].sum()),
                "alert_rate": float(test_scored["is_anomaly"].mean()) if len(test_scored) > 0 else 0.0,
            },
        }
        (metrics_dir / "test_metrics.json").write_text(
            json.dumps(test_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[{args.dataset}] Test split unlocked & evaluated (unlock_count={lock_state['unlock_count']}).")
    else:
        print(f"[{args.dataset}] Validation & rolling CV complete. Test split remains LOCKED (policy 2A).")


if __name__ == "__main__":
    main()
