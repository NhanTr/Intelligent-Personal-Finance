"""CLI script to generate deterministic synthetic VND dataset and demo CSVs."""

from __future__ import annotations

import argparse
from pathlib import Path

from finance_ml.config import load_config
from finance_ml.data.synthetic import generate_synthetic_dataset, save_synthetic_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic multi-user VND dataset.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    cfg = load_config(args.config)
    bundle = generate_synthetic_dataset(cfg)
    paths = save_synthetic_bundle(bundle, args.root)
    print(f"Generated {len(bundle.transactions_df)} synthetic transactions across {len(bundle.profile_windows)} profiles.")
    for name, p in paths.items():
        print(f"  {name}: {p}")


if __name__ == "__main__":
    main()
