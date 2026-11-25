"""Feedback-aware retraining pipeline with same-window validation comparison and atomic promotion gate."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

from finance_ml.config import PipelineConfig, load_config
from finance_ml.data.cleaning import _parse_bool, _parse_vn_timestamp, clean_transactions
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.data.io import filter_eligible_windows, load_processed_stream
from finance_ml.evaluation.split import assign_forecast_origins, assign_transaction_splits, compute_time_cutoffs
from finance_ml.features.forecast_features import FORECAST_FEATURE_COLUMNS, build_forecast_dataset
from finance_ml.inference.loader import ModelBundleLoader
from finance_ml.inference.predictor import detect_anomalies, predict_next_7d
from finance_ml.models.anomaly import train_anomaly_detector
from finance_ml.models.forecast import train_and_select_forecast_models
from finance_ml.models.registry import save_model_bundle, set_active_pointer
from finance_ml.schema import FeedbackRecord, ProfileWindow


def _normalize_feedback_df(feedback_df: pd.DataFrame | None) -> pd.DataFrame | None:
    if feedback_df is None or feedback_df.empty:
        return None

    parsed_rows: list[dict[str, Any]] = []
    for row in feedback_df.to_dict(orient="records"):
        ts = _parse_vn_timestamp(row.get("created_at"))
        if ts is None:
            continue
        rec = FeedbackRecord(
            transaction_id=str(row["transaction_id"]).strip(),
            user_id=str(row["user_id"]).strip(),
            is_confirmed_anomaly=_parse_bool(row.get("is_confirmed_anomaly")),
            model_version=str(row.get("model_version", "unknown")).strip() or "unknown",
            created_at=ts,
        )
        parsed_rows.append(
            {
                "transaction_id": rec.transaction_id,
                "user_id": rec.user_id,
                "is_confirmed_anomaly": rec.is_confirmed_anomaly,
                "model_version": rec.model_version,
                "created_at": pd.Timestamp(rec.created_at),
            }
        )

    if not parsed_rows:
        return None

    norm = pd.DataFrame(parsed_rows)
    norm = norm.sort_values(["created_at", "transaction_id"], kind="mergesort")
    norm = norm.drop_duplicates(subset=["transaction_id"], keep="last").reset_index(drop=True)
    return norm


def retrain_and_maybe_promote(
    transactions_df: pd.DataFrame,
    profile_windows: dict[str, ProfileWindow],
    feedback_df: pd.DataFrame | None,
    dataset_dir: Path,
    global_active_pointer: Path | None,
    config: PipelineConfig,
    new_version: str,
    force_promote: bool = False,
) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    target_version_dir = dataset_dir / "models" / new_version
    if target_version_dir.exists():
        raise FileExistsError(
            f"Candidate version directory already exists at {target_version_dir}; "
            "choose a new semantic version to preserve rollback history."
        )

    ds_active_ptr = dataset_dir / "models" / "active.json"
    loaded_active = (
        ModelBundleLoader(ds_active_ptr, allow_baseline_fallback=False).load()
        if ds_active_ptr.exists()
        else None
    )

    clean_df, _ = clean_transactions(transactions_df)
    core_windows = filter_eligible_windows(profile_windows, min_days=180)
    core_df = clean_df[clean_df["user_id"].isin(core_windows.keys())].copy()

    daily_df = aggregate_daily_spending(core_df, core_windows)
    cutoffs = compute_time_cutoffs(daily_df, config.split_ratios)

    f_raw = build_forecast_dataset(
        daily_df,
        core_windows,
        horizon_days=config.forecast.horizon_days,
        min_history_days=config.forecast.min_history_days,
    )
    f_split = assign_forecast_origins(
        f_raw,
        cutoffs,
        horizon_days=config.forecast.horizon_days,
        min_step_days=config.forecast.origin_step_days,
    )
    train_f = f_split[f_split["split"] == "train"]
    val_f = f_split[f_split["split"] == "validation"]

    cand_f_out = train_and_select_forecast_models(train_f, val_f, config)
    cand_val_mae = float(cand_f_out.val_comparison[cand_f_out.selected_name]["mae_vnd"])

    exp_df = core_df[(core_df["type"] == "expense") & (~core_df["is_internal_transfer"])].copy()
    exp_split = assign_transaction_splits(exp_df, cutoffs)
    train_exp = exp_split[exp_split["split"] == "train"]
    val_exp = exp_split[exp_split["split"] == "validation"]

    norm_fb = _normalize_feedback_df(feedback_df)
    confirmed_train_ids: set[str] = set()
    val_fb_subset: pd.DataFrame | None = None
    if norm_fb is not None and not norm_fb.empty:
        train_ids_set = set(train_exp["transaction_id"].astype(str))
        val_ids_set = set(val_exp["transaction_id"].astype(str))
        confirmed_train_ids = set(
            norm_fb[
                norm_fb["is_confirmed_anomaly"].astype(bool)
                & norm_fb["transaction_id"].astype(str).isin(train_ids_set)
            ]["transaction_id"].astype(str)
        )
        val_fb_subset = norm_fb[norm_fb["transaction_id"].astype(str).isin(val_ids_set)].copy()

    cand_det = train_anomaly_detector(
        train_exp,
        val_exp,
        config,
        confirmed_anomaly_ids=confirmed_train_ids,
        val_feedback_df=val_fb_subset,
    )

    cand_dir = save_model_bundle(
        dataset_dir,
        new_version,
        cand_f_out,
        cand_det,
        {
            "seed": config.seed,
            "config_hash": config.config_hash(),
            "cutoffs": cutoffs.model_dump(mode="json"),
            "retrained_with_feedback_rows": 0 if norm_fb is None else int(len(norm_fb)),
        },
    )

    # Candidate inference smoke test
    smoke_test_passed = False
    try:
        cand_loaded = ModelBundleLoader(cand_dir, allow_baseline_fallback=False).load()
        smoke_uid = sorted(core_windows.keys())[0]
        smoke_f3 = predict_next_7d(core_df, smoke_uid, cutoffs.val_end, cand_loaded)
        smoke_f4 = detect_anomalies(core_df, smoke_uid, cand_loaded)
        smoke_test_passed = (
            smoke_f3.predicted_total_vnd is not None
            and math.isfinite(float(smoke_f3.predicted_total_vnd))
            and smoke_f4.status == "ok"
        )
    except Exception:
        smoke_test_passed = False

    active_val_mae: float | None = None
    f3_gate_ok = True
    if loaded_active is not None and loaded_active.bundle is not None:
        X_val = val_f[list(FORECAST_FEATURE_COLUMNS)]
        y_val = val_f["target_next_7d_vnd"].to_numpy(dtype=float)
        active_pred = loaded_active.bundle.forecast_estimator.predict(X_val)
        active_val_mae = float(np.mean(np.abs(y_val - active_pred)))
        f3_gate_ok = cand_val_mae <= active_val_mae * config.retrain.max_mae_regression_ratio

    lo, hi = config.anomaly.alert_rate_bounds
    f4_gate_ok = lo <= cand_det.validation_alert_rate <= hi
    promoted = bool((f3_gate_ok and f4_gate_ok and smoke_test_passed) or force_promote)

    if promoted:
        set_active_pointer(ds_active_ptr, cand_dir, new_version, dataset_dir.name)
        if global_active_pointer is not None:
            set_active_pointer(global_active_pointer, cand_dir, new_version, dataset_dir.name)

    report = {
        "new_version": new_version,
        "promoted": promoted,
        "force_promote": force_promote,
        "f3_gate_ok": f3_gate_ok,
        "f4_gate_ok": f4_gate_ok,
        "smoke_test_passed": smoke_test_passed,
        "candidate_selected_forecast": cand_f_out.selected_name,
        "candidate_val_mae": cand_val_mae,
        "active_val_mae_on_new_window": active_val_mae,
        "candidate_anomaly_alert_rate": cand_det.validation_alert_rate,
        "excluded_confirmed_train_anomalies": len(confirmed_train_ids),
        "bundle_dir": str(cand_dir),
    }
    (cand_dir / "retrain_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain F3 & F4 models with updated transactions and feedback.")
    parser.add_argument("--dataset", choices=["synthetic", "real_public"], default="synthetic")
    parser.add_argument("--version", required=True, help="New candidate semantic version (e.g. v1.1.0)")
    parser.add_argument("--feedback-csv", type=Path, default=None, help="Optional CSV of user anomaly feedback.")
    parser.add_argument("--force-promote", action="store_true")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    cfg = load_config(args.config)
    proc_dir = args.root / "data" / "processed" / args.dataset
    clean_df, windows = load_processed_stream(proc_dir)
    fb_df = pd.read_csv(args.feedback_csv) if args.feedback_csv and args.feedback_csv.exists() else None

    ds_art_dir = args.root / "artifacts" / args.dataset
    global_ptr = (args.root / "artifacts" / "models" / "active.json") if args.dataset == "synthetic" else None
    rep = retrain_and_maybe_promote(
        clean_df,
        windows,
        fb_df,
        ds_art_dir,
        global_ptr,
        cfg,
        new_version=args.version,
        force_promote=args.force_promote,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
