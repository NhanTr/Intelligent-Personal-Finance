"""CLI script to prepare the optional Kaggle Daily Household Transactions dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_ml.config import load_config
from finance_ml.data.public_adapter import adapt_kaggle_daily_transactions


def main() -> None:
    parser = argparse.ArgumentParser(description="Adapt Kaggle Daily Household Transactions CSV if present.")
    parser.add_argument("--csv", type=Path, default=Path("data/raw/daily_household_transactions.csv"))
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed/real_public"))
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"[INFO] Optional public CSV not found at {args.csv}; skipping real_public stream preparation.")
        return

    cfg = load_config(args.config)
    clean_df, windows, manifest = adapt_kaggle_daily_transactions(args.csv, inr_to_vnd_rate=cfg.currency.inr_to_vnd_rate)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(args.out_dir / "transactions.csv", index=False)
    (args.out_dir / "profile_windows.json").write_text(
        json.dumps({k: v.model_dump(mode="json") for k, v in windows.items()}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Prepared real_public dataset: {len(clean_df)} valid transactions saved to {args.out_dir}")


if __name__ == "__main__":
    main()
