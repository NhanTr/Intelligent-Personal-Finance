"""CLI script to train F3 forecast and F4 anomaly models on a processed dataset stream."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

from finance_ml.config import load_config
from finance_ml.data.cleaning import clean_transactions
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.evaluation.split import assign_forecast_origins, assign_transaction_splits, compute_time_cutoffs
from finance_ml.features.forecast_features import build_forecast_dataset
from finance_ml.models.anomaly import train_anomaly_detector
from finance_ml.models.forecast import train_and_select_forecast_models
from finance_ml.models.registry import save_model_bundle, set_active_pointer
from finance_ml.schema import ProfileWindow


def load_processed_stream(proc_dir: Path) -> tuple[pd.DataFrame, dict[str, ProfileWindow]]:
    tx_path = proc_dir / "transactions.csv"
    win_path = proc_dir / "profile_windows.json"
    if not tx_path.exists() or not win_path.exists():
        raise FileNotFoundError(f"Processed stream not found in {proc_dir}. Run data preparation first.")
    raw_tx = pd.read_csv(tx_path)
    clean_df, _ = clean_transactions(raw_tx)
    raw_win = json.loads(win_path.read_text(encoding="utf-8"))
    windows = {k: ProfileWindow.model_validate(v) for k, v in raw_win.items()}
    return clean_df, windows


def filter_eligible_windows(windows: dict[str, ProfileWindow], min_days: int = 180) -> dict[str, ProfileWindow]:
    return {
        u: w
        for u, w in windows.items()
        if (w.tracking_end_date - w.tracking_start_date).days + 1 >= min_days
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train F3 and F4 models for a dataset stream.")
    parser.add_argument("--dataset", choices=["synthetic", "real_public"], default="synthetic")
    parser.add_argument("--version", default="v1.0.0")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    cfg = load_config(args.config)
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

    f_out = train_and_select_forecast_models(
        f_split[f_split["split"] == "train"],
        f_split[f_split["split"] == "validation"],
        cfg,
    )

    exp_df = core_df[(core_df["type"] == "expense") & (~core_df["is_internal_transfer"])].copy()
    exp_split = assign_transaction_splits(exp_df, cutoffs)
    det = train_anomaly_detector(
        exp_split[exp_split["split"] == "train"],
        exp_split[exp_split["split"] == "validation"],
        cfg,
    )

    ds_art_dir = args.root / "artifacts" / args.dataset
    meta = {
        "seed": cfg.seed,
        "config_hash": cfg.config_hash(),
        "cutoffs": cutoffs.model_dump(mode="json"),
        "val_forecast_comparison": f_out.val_comparison,
    }
    bundle_dir = save_model_bundle(ds_art_dir, args.version, f_out, det, meta)
    set_active_pointer(ds_art_dir / "models" / "active.json", bundle_dir, args.version, args.dataset)
    if args.dataset == "synthetic":
        set_active_pointer(args.root / "artifacts" / "models" / "active.json", bundle_dir, args.version, args.dataset)

    (ds_art_dir / "split_manifest.json").write_text(
        json.dumps(cutoffs.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[{args.dataset}] Trained version={args.version} -> selected F3={f_out.selected_name}, F4 threshold={det.threshold:.4f}")


if __name__ == "__main__":
    main()
