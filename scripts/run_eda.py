"""CLI script to generate EDA charts and markdown report for a dataset stream."""

from __future__ import annotations

import argparse
from pathlib import Path

from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.reporting.eda import generate_eda_artifacts
from finance_ml.schema import DataManifest
from scripts.train import load_processed_stream


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EDA and generate separated figures/report.")
    parser.add_argument("--dataset", choices=["synthetic", "real_public"], default="synthetic")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    proc_dir = args.root / "data" / "processed" / args.dataset
    manifest_path = proc_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest missing at {manifest_path}. Run data generation/preparation first.")

    clean_df, windows = load_processed_stream(proc_dir)
    manifest = DataManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    daily_df = aggregate_daily_spending(clean_df, windows)

    figs = generate_eda_artifacts(
        dataset_name=args.dataset,
        clean_df=clean_df,
        daily_df=daily_df,
        manifest=manifest,
        figures_dir=args.root / "artifacts" / args.dataset / "figures",
        report_path=args.root / "docs" / "eda_report.md",
    )
    print(f"[{args.dataset}] EDA complete -> {len(figs)} figures saved, updated docs/eda_report.md")


if __name__ == "__main__":
    main()
